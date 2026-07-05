# Kế hoạch thay thế MinIO bằng AWS S3

## Lý do

- MinIO chạy trên một container trong Docker Swarm, nếu node `data` die thì mất toàn bộ dữ liệu Iceberg (checkpoint + parquet)
- MinIO không có replication/backup tự động — dữ liệu chỉ là một volume local trên EBS của EC2
- AWS S3 cung cấp durability 99.999999999%, replication cross-region, lifecycle policy
- Trino + Spark đã hỗ trợ S3 native qua Iceberg `S3FileIO` — chỉ cần đổi endpoint

---

## Kiến trúc hiện tại (MinIO)

```
Docker Swarm
  └─ node:data (ip-172-31-1-8)
       └─ service: minio (port 9000)
            ├─ bucket: cryptoprice/
            │    ├─ iceberg/         ← Parquet files (coin_ticker, coin_trades, coin_klines)
            │    ├─ checkpoints/     ← Spark streaming checkpoints
            │    └─ warehouse/       ← (không dùng, legacy)
            └─ volume: minio-data (docker volume trên node data)
```

## Kiến trúc đích (AWS S3)

```
AWS S3
  └─ bucket: lmview-lakehouse (ap-southeast-1)
       ├─ data/iceberg/         ← Parquet files
       ├─ data/checkpoints/     ← Spark streaming checkpoints
       ├──┬────────────────────────────────────────────
         │ ← Iceberg JDBC catalog vẫn dùng PostgreSQL
         │ ← Trino connects tới S3 qua Iceberg connector
         │ ← Spark connects tới S3 qua S3FileIO / Hadoop S3A
```

---

## Bước 1: Tạo S3 bucket + IAM user

### 1.1 Tạo S3 bucket

- **Bucket name**: `lmview-lakehouse`
- **Region**: `ap-southeast-1` (Singapore — gần EC2 ở Jakarta/Singapore)
- **Block Public Access**: ALL enabled (private hoàn toàn)
- **Bucket Versioning**: Enabled (phục hồi accidental delete)
- **Default encryption**: SSE-S3
- **Lifecycle rule** (optional):
  - Sau 30 ngày: transition `checkpoints/` → Glacier Instant Retrieval
  - Sau 90 ngày: transition `checkpoints/` → Glacier Deep Archive
  - Xóa sau 365 ngày

**AWS CLI**:
```bash
# Tạo bucket
aws s3api create-bucket \
  --bucket lmview-lakehouse \
  --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket lmview-lakehouse \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket lmview-lakehouse \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true

# Lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket lmview-lakehouse \
  --lifecycle-configuration file://lifecycle.json
```

**lifecycle.json**:
```json
{
  "Rules": [
    {
      "Id": "checkpoints-tiering",
      "Filter": {"Prefix": "data/checkpoints/"},
      "Status": "Enabled",
      "Transitions": [
        {"Days": 30,  "StorageClass": "GLACIER_IR"},
        {"Days": 90,  "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 365}
    }
  ]
}
```

### 1.2 Tạo IAM user + access key

- **IAM user**: `lmview-lakehouse-svc`
- **Policy**: inline policy với quyền tối thiểu

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::lmview-lakehouse"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::lmview-lakehouse/data/*"
    }
  ]
}
```

Lưu `AWS_ACCESS_KEY_ID` và `AWS_SECRET_ACCESS_KEY` — sẽ dùng ở bước 3.

---

## Bước 2: Sao chép dữ liệu từ MinIO → S3

Dùng `aws s3 sync` để copy toàn bộ dữ liệu hiện có.

### 2.1 Cài AWS CLI vào network chung

```bash
# Chạy container tạm
docker run -d --name s3-migration \
  --network cryptoprice_crypto-net \
  amazon/aws-cli:2.17.0 sleep 3600

# Cấu hình credentials
docker exec s3-migration aws configure set aws_access_key_id <AKIA...>
docker exec s3-migration aws configure set aws_secret_access_key <...>
docker exec s3-migration aws configure set region ap-southeast-1
```

### 2.2 Copy dữ liệu

```bash
# List objects trên MinIO
docker run --rm --network cryptoprice_crypto-net --entrypoint sh \
  minio/mc:RELEASE.2025-08-13T08-35-41Z \
  -c "mc alias set s3 http://minio:9000 minioadmin MinIOCryptoStorage2026! \
      && mc ls -r s3/cryptoprice/iceberg/"

# Sync Iceberg data từ MinIO → S3
docker exec s3-migration \
  aws s3 sync \
  --endpoint-url http://minio:9000 \
  s3://cryptoprice/iceberg/ \
  s3://lmview-lakehouse/data/iceberg/

# Sync checkpoints
docker exec s3-migration \
  aws s3 sync \
  --endpoint-url http://minio:9000 \
  s3://cryptoprice/checkpoints/ \
  s3://lmview-lakehouse/data/checkpoints/

# Verify
docker exec s3-migration aws s3 ls --recursive s3://lmview-lakehouse/data/ | wc -l
```

> **Lưu ý checkpoints**: Spark streaming cần checkpoint files để biết offset đã đọc. Nếu migration xảy ra khi pipeline đang chạy, checkpoint files sẽ bị inconsistent. Nên **stop pipeline trước khi copy checkpoints**.

---

## Bước 3: Cập nhật config trong hệ thống

Các file cần thay đổi (thay `MINIO_ENDPOINT=http://minio:9000` → `S3_ENDPOINT=https://s3.ap-southeast-1.amazonaws.com`):

### 3.1 `.env` — thêm S3 vars, giữ MinIO cho rollback

```bash
# ── MinIO (S3-compatible — LEGACY, sẽ xoá sau migration) ─────────────────
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=MinIOCryptoStorage2026!

# ── AWS S3 (thay thế MinIO) ──────────────────────────────────────────────
S3_ENDPOINT=https://s3.ap-southeast-1.amazonaws.com
S3_REGION=ap-southeast-1
S3_BUCKET=lmview-lakehouse
S3_PREFIX=data
AWS_ACCESS_KEY_ID=<IAM access key>
AWS_SECRET_ACCESS_KEY=<IAM secret key>
```

### 3.2 `.env.example` — thêm S3 vars mẫu

```bash
# ── AWS S3 (lakehouse object storage) ─────────────────────────────────────
S3_ENDPOINT=${S3_ENDPOINT:-https://s3.ap-southeast-1.amazonaws.com}
S3_REGION=${S3_REGION:-ap-southeast-1}
S3_BUCKET=${S3_BUCKET:-lmview-lakehouse}
S3_PREFIX=${S3_PREFIX:-data}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
```

### 3.3 `src/common/config.py`

```python
# ── MinIO / S3 ───────────────────────────────────────────────────────────────
# Sử dụng env mới. Khi chưa set S3 vars, fallback về MinIO (backward compat).
S3_ENDPOINT     = os.environ.get("S3_ENDPOINT",     "http://minio:9000")
S3_REGION       = os.environ.get("S3_REGION",       "us-east-1")
S3_BUCKET       = os.environ.get("S3_BUCKET",       "cryptoprice")
S3_PREFIX       = os.environ.get("S3_PREFIX",       "")  # "data" khi dùng S3
AWS_ACCESS_KEY  = os.environ.get("AWS_ACCESS_KEY_ID",     os.environ.get("MINIO_ACCESS_KEY", ""))
AWS_SECRET_KEY  = os.environ.get("AWS_SECRET_ACCESS_KEY", os.environ.get("MINIO_SECRET_KEY", ""))

# Iceberg warehouse path
S3_WAREHOUSE = f"s3://{S3_BUCKET}/{S3_PREFIX}/iceberg" if S3_PREFIX else f"s3://{S3_BUCKET}/iceberg"

# Checkpoint paths
S3_CHECKPOINT_TICKER = f"s3://{S3_BUCKET}/{S3_PREFIX}/checkpoints/crypto_ticker_v1" if S3_PREFIX else f"s3://{S3_BUCKET}/checkpoints/crypto_ticker_v1"
S3_CHECKPOINT_TRADES = f"s3://{S3_BUCKET}/{S3_PREFIX}/checkpoints/crypto_trades_v1" if S3_PREFIX else f"s3://{S3_BUCKET}/checkpoints/crypto_trades_v1"
S3_CHECKPOINT_KLINES = f"s3://{S3_BUCKET}/{S3_PREFIX}/checkpoints/crypto_klines_v1" if S3_PREFIX else f"s3://{S3_BUCKET}/checkpoints/crypto_klines_v1"
```

### 3.4 `src/lakehouse/pipeline.py`

Thay đổi phần build spark session:

```python
# OLD (MinIO)
.config("spark.sql.catalog.iceberg_catalog.s3.endpoint",         MINIO_ENDPOINT)
.config("spark.sql.catalog.iceberg_catalog.s3.access-key-id",     MINIO_ACCESS_KEY)
.config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", MINIO_SECRET_KEY)
.config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "true")
.config("spark.hadoop.fs.s3a.endpoint",        MINIO_ENDPOINT)
.config("spark.hadoop.fs.s3a.access.key",      MINIO_ACCESS_KEY)
.config("spark.hadoop.fs.s3a.secret.key",      MINIO_SECRET_KEY)
.config("spark.hadoop.fs.s3a.path.style.access", "true")
.config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")

# NEW (S3)
.config("spark.sql.catalog.iceberg_catalog.s3.endpoint",         S3_ENDPOINT)
.config("spark.sql.catalog.iceberg_catalog.s3.access-key-id",     AWS_ACCESS_KEY)
.config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", AWS_SECRET_KEY)
.config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "false")  # S3 uses virtual-hosted
.config("spark.hadoop.fs.s3a.endpoint",        S3_ENDPOINT)
.config("spark.hadoop.fs.s3a.access.key",      AWS_ACCESS_KEY)
.config("spark.hadoop.fs.s3a.secret.key",      AWS_SECRET_KEY)
.config("spark.hadoop.fs.s3a.path.style.access", "false")
.config("spark.hadoop.fs.s3a.connection.ssl.enabled", "true")

# Thêm region (quan trọng cho S3)
.config("spark.sql.catalog.iceberg_catalog.client.region",        S3_REGION)
.config("spark.hadoop.fs.s3a.endpoint.region",                    S3_REGION)
```

### 3.5 `src/batch/unified/silver_to_gold.py` và `daily_aggregation.py`

Tương tự pipeline.py — thay endpoint, credentials, path-style-access:

```python
# OLD
.config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
.config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", ""))
.config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", ""))
.config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
.config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "true")

# NEW
.config("spark.hadoop.fs.s3a.endpoint", os.getenv("S3_ENDPOINT", "https://s3.ap-southeast-1.amazonaws.com"))
.config("spark.hadoop.fs.s3a.access.key", os.getenv("AWS_ACCESS_KEY_ID", ""))
.config("spark.hadoop.fs.s3a.secret.key", os.getenv("AWS_SECRET_ACCESS_KEY", ""))
.config("spark.sql.catalog.iceberg_catalog.s3.endpoint", os.getenv("S3_ENDPOINT"))
.config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "false")
.config("spark.sql.catalog.iceberg_catalog.client.region", os.getenv("S3_REGION", "ap-southeast-1"))
```

### 3.6 `docker/trino/etc/catalog/iceberg.properties`

```properties
# OLD (MinIO)
fs.native-s3.enabled=true
s3.endpoint=http://minio:9000
s3.region=us-east-1
s3.path-style-access=true
s3.aws-access-key=__MINIO_ROOT_USER__
s3.aws-secret-key=__MINIO_ROOT_PASSWORD__

# NEW (S3)
fs.native-s3.enabled=true
s3.endpoint=https://s3.ap-southeast-1.amazonaws.com
s3.region=ap-southeast-1
s3.path-style-access=false
s3.aws-access-key=__AWS_ACCESS_KEY_ID__
s3.aws-secret-key=__AWS_SECRET_ACCESS_KEY__
```

### 3.6b `docker/trino/entrypoint.sh` — thêm substitution cho S3 vars

Trino dùng entrypoint script để substitute `__PLACEHOLDER__` trong `iceberg.properties`. Cần thêm 2 dòng substitution:

```bash
# Trong docker/trino/entrypoint.sh, thêm sau dòng MINIO_ROOT_PASSWORD:
sed -i \
  -e "s|__POSTGRES_USER__|${POSTGRES_USER:?POSTGRES_USER is required}|g" \
  -e "s|__POSTGRES_PASSWORD__|${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}|g" \
  -e "s|__MINIO_ROOT_USER__|${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}|g" \
  -e "s|__MINIO_ROOT_PASSWORD__|${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}|g" \
  -e "s|__AWS_ACCESS_KEY_ID__|${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}|g" \       # ← THÊM
  -e "s|__AWS_SECRET_ACCESS_KEY__|${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}|g" \  # ← THÊM
  "$CATALOG"
```

### 3.7 `docker-compose.yml` — Xoá MinIO service

Sau khi dữ liệu đã sync và pipeline chạy ổn định với S3, xoá:

```yaml
# DELETE toàn bộ section này:
  minio:
    <<: *logging
    profiles: ["dev", "prod"]
    ...
  minio-init:
    ...
  minio-data:
    ...
```

### 3.8 Docker Swarm — xoá placement constraint

```yaml
# docker-compose.swarm.yml — xoá:
  minio:
    deploy:
      placement:
        constraints: [node.labels.role == data]
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 1G
```

### 3.9 Spark submit supervisor — thêm env mới

Trong `docker-compose.yml` service `spark-submit`:

```yaml
    environment:
      S3_ENDPOINT: https://s3.ap-southeast-1.amazonaws.com
      S3_REGION: ap-southeast-1
      S3_BUCKET: lmview-lakehouse
      S3_PREFIX: data
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
```

---

## Bước 4: Update Iceberg catalog entries trong PostgreSQL

Iceberg JDBC catalog lưu đường dẫn warehouse trong table `iceberg.properties`. Khi đổi sang S3, cần update trỏ từ `s3://cryptoprice/iceberg/...` → `s3://lmview-lakehouse/data/iceberg/...`.

```bash
# Kết nối đến PostgreSQL catalog
docker run --rm --network cryptoprice_crypto-net \
  postgres:16-alpine \
  psql "postgresql://iceberg:PostgresIcebergSecure79!@postgres:5432/iceberg_catalog" \
  -c "SELECT * FROM iceberg_catalog.\"iceberg_tables\";"
```

Nếu dùng JDBC catalog, Iceberg tự động lưu metadata location trong `iceberg_tables` table. Cần update:

```sql
-- Update warehouse path cho mỗi table
UPDATE iceberg_tables
SET metadata_location = replace(metadata_location,
    's3://cryptoprice/iceberg',
    's3://lmview-lakehouse/data/iceberg');

UPDATE iceberg_tables
SET previous_metadata_location = replace(previous_metadata_location,
    's3://cryptoprice/iceberg',
    's3://lmview-lakehouse/data/iceberg');
```

---

## Bước 5: Deploy và verify

### 5.1 Build lại images

```bash
cd /mnt/efs/LMView

# Rebuild spark images (nếu thay Dockerfile)
# docker compose build spark-submit

# Apply env changes
export AWS_ACCESS_KEY_ID=<AKIA...>
export AWS_SECRET_ACCESS_KEY=<...>

# Deploy
bash scripts/deploy_aws_swarm.sh
```

### 5.2 Sequence chuyển đổi (zero-downtime)

1. **Stop spark-submit** (dừng ghi mới vào Iceberg)
   ```bash
   docker service scale cryptoprice_spark-submit=0
   ```

2. **Copy dữ liệu MinIO → S3** (xem Bước 2)

3. **Update catalog trong PostgreSQL** (xem Bước 4)

4. **Deploy config mới** (env + compose + trino config)
   ```bash
   docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice
   ```

5. **Start spark-submit** — ghi vào S3
   ```bash
   docker service scale cryptoprice_spark-submit=1
   ```

6. **Verify**
   ```bash
   # Spark pipeline chạy?
   docker service logs cryptoprice_spark-submit --tail 10

   # Dữ liệu ghi vào S3?
   aws s3 ls --recursive s3://lmview-lakehouse/data/iceberg/ | head

   # Trino query được?
   curl -s -X POST "http://trino:8080/v1/statement" \
     -H "X-Trino-User: admin" \
     -d "SELECT count(*) FROM iceberg_catalog.crypto_lakehouse.coin_klines"

   # API trả về candles?
   curl -s "https://lmview.duckdns.org/api/klines?symbol=BTCUSDT&interval=1m&limit=5"
   ```

### 5.3 Rollback

Nếu gặp lỗi:

```bash
# Stop pipeline
docker service scale cryptoprice_spark-submit=0

# Rollback env (set MINIO_ENDPOINT=http://minio:9000)
docker service update --env-add MINIO_ENDPOINT=http://minio:9000 cryptoprice_spark-submit

# Restore trino config
# (dùng config cũ với s3.endpoint=http://minio:9000)

# Start pipeline lại
docker service scale cryptoprice_spark-submit=1
```

Không cần xoá dữ liệu trên MinIO — MinIO vẫn chạy với data cũ.

---

## Tổng kết files cần thay đổi

| File | Thay đổi | Priority |
|---|---|---|
| `.env` | Thêm `S3_ENDPOINT`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_PREFIX` | **Cần** |
| `.env.example` | Thêm S3 vars mẫu | **Nên** |
| `src/common/config.py` | Thêm S3 config, fallback về MinIO | **Cần** |
| `src/lakehouse/pipeline.py` | Đổi endpoint, region, path-style-access | **Cần** |
| `src/batch/unified/silver_to_gold.py` | Đổi endpoint, region | **Cần** |
| `src/batch/unified/daily_aggregation.py` | Đổi endpoint, region | **Cần** |
| `docker/trino/etc/catalog/iceberg.properties` | Đổi s3.endpoint, region, credentials | **Cần** |
| `docker-compose.yml` | Xoá minio, minio-init, minio-data services (sau khi migration xong) | **Sau** |
| `docker-compose.swarm.yml` | Xoá minio placement constraint | **Sau** |
| `scripts/deploy_aws_swarm.sh` | Có thể cần thêm S3 env vars | **Nếu cần** |

---

## Chi phí AWS S3 (ước lượng)

| Item | Size | Cost/tháng (ap-southeast-1) |
|---|---|---|
| Iceberg parquet (200 symbols, 5y 1m) | ~50 GB | $1.15 |
| Spark checkpoints | ~5 GB | $0.12 |
| Glacier IR (checkpoints >30 ngày) | ~3 GB | $0.03 |
| **Total** | **~58 GB** | **~$1.30/tháng** |

+ PUT/GET requests: ~$0.01/tháng
= **Tổng ~$1.50/tháng** — rẻ hơn chạy MinIO container 24/7.

---

## Timeline

| Phase | Thời gian | Mô tả |
|---|---|---|
| **Phase 1: Prepare** | 30 phút | Tạo S3 bucket + IAM user + credentials trong .env |
| **Phase 2: Copy data** | 15 phút | `aws s3 sync` từ MinIO → S3 |
| **Phase 3: Update config** | 45 phút | Sửa code + properties files + build images |
| **Phase 4: Deploy + verify** | 30 phút | Deploy stack, verify pipeline, rollback nếu lỗi |
| **Phase 5: Cleanup** | 1 tuần sau | Xoá MinIO services khỏi compose files nếu ổn định |
| **Total** | **~2-3 giờ** | |

---

## Rủi ro

1. **Checkpoint corruption**: Spark streaming checkpoints lưu offset Kafka. Nếu copy không atomic, pipeline có thể reprocess or skip messages. **Giải pháp**: stop pipeline trước khi copy, dùng `aws s3 sync --delete --no-follow-symlinks`.

2. **Permission denied**: IAM policy thiếu quyền. **Giải pháp**: test với `aws s3 ls s3://lmview-lakehouse/` từ container trước.

3. **Cross-region latency**: S3 ap-southeast-1 (Singapore) latency tới EC2 ở Jakarta: ~20-40ms. Không ảnh hưởng tới streaming batch 1 phút.

4. **Iceberg metadata mismatch**: Nếu metadata_location trong PostgreSQL catalog chưa được update, Spark/Trino sẽ tìm metadata ở bucket cũ. **Giải pháp**: update JDBC catalog hoặc dùng `ALTER TABLE SET LOCATION`.

---

## Lệnh quick reference

```bash
# ===== SETUP =====
# Tạo bucket
aws s3api create-bucket --bucket lmview-lakehouse --region ap-southeast-1 \
  --create-bucket-configuration LocationConstraint=ap-southeast-1

# Tạo IAM user + policy
aws iam create-user --user-name lmview-lakehouse-svc
aws iam put-user-policy --user-name lmview-lakehouse-svc \
  --policy-name lmview-s3-access \
  --policy-document file://s3-access-policy.json
aws iam create-access-key --user-name lmview-lakehouse-svc

# ===== DATA MIGRATION =====
# Sync từ MinIO → S3
aws s3 sync --endpoint-url http://minio:9000 \
  s3://cryptoprice/iceberg/ \
  s3://lmview-lakehouse/data/iceberg/

# Verify
aws s3 ls --recursive --summarize s3://lmview-lakehouse/data/ | tail -5

# ===== POST-DEPLOY VERIFY =====
# Trino query
curl -s -X POST "http://trino:8080/v1/statement" \
  -H "X-Trino-User: admin" \
  -d "SELECT count(*) FROM iceberg.iceberg.iceberg_tables"

# Spark pipeline log
docker service logs cryptoprice_spark-submit --tail 15

# S3 latest data
aws s3 ls --recursive s3://lmview-lakehouse/data/iceberg/ | sort | tail -10
```

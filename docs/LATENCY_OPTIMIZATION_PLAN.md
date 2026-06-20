# LATENCY OPTIMIZATION PLAN — LMView

> Mục tiêu: Giảm candle delay từ 2h → realtime (< 5s), scale lên 671 symbols, ổn định production.
> Version: 0.25.52 | Updated: 2026-06-19

---

## Phase 0 Status: ✅ COMPLETE

### Mục tiêu
- Ổn định producer WebSocket (giảm reconnect, timeout)
- Fix Flink Redis writes (Sentinel cluster)
- Giảm candle delay từ 2h → dưới 60s

### Phân tích ban đầu
- **Producer**: Kline WS dùng 8 connection, thường xuyên timeout/disconnect → Binance rate limit
- **Flink writes**: KeyDB writes bị lỗi `NOAUTH`, `MOVED`, hoặc replica full → do dùng Redis standalone config, không phải Sentinel
- **Candle delay**: 2h do Flink gap_fill + checkpoint 60s + không có dữ liệu kịp thời

### Thay đổi chi tiết

#### 1. Cấu hình connection producer

**File**: `src/common/config.py`
```python
# Symbol mỗi connection giảm từ 50 → 40
KLINE_SYMBOLS_PER_CONN = 40
```
- Tổng 200 symbols → 5 connection (thay vì 8)
- Mỗi connection ít symbol hơn → ít message hơn → giảm rate limit

#### 2. Tăng ping timeout + auto-reconnect

**File**: `src/producer/main.py` — `run_combined_batch`
```python
ws_kwargs = {
    "ping_interval": 10,      # giảm từ 30s → 10s (giữ connection alive)
    "ping_timeout": 5,        # giảm từ 10s → 5s (phát hiện die sớm)
    "autoreconnect": True,    # bật auto-reconnect
    "allow_disconnect": True, # không crash nếu mất kết nối
}
```

#### 3. Kline WS split: 8 conn → 5 conn

**File**: `src/producer/main.py`
- Trước: 8 connections, mỗi conn 25 symbol
- Sau: 5 connections, mỗi conn 40 symbol
- Code: `split_into_batches(active_symbols, max_per_conn=40)`

#### 4. Flink Redis Sentinel config

**File**: `docker-compose.swarm.yml` (runtime)
```yaml
REDIS_SENTINELS: redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
REDIS_MASTER_NAME: mymaster
```
- Ghi vào KeyDB qua Sentinel → tự động failover, không lỗi MOVED
- Giảm replica errors từ 100% → 0%

#### 5. Remove jar mount gây fail (Flink TM)

**File**: `docker-compose.swarm.yml`
- Xóa mount `flink-python-1.18.1.jar` không tồn tại → gây crash TaskManager
- TM restart ngay sau update

### Kết quả đo lường
| Metric | Before | After |
|---|---|---|
| Kline WS connections | 8 | 5 |
| Timeout errors | ~20/h | 0/h |
| Flink Redis write errors | 100% replicas | 0% (Sentinel) |
| Candle delay (P95) | 2h | 35s |
| Flink job status | RUNNING | RUNNING (5/5 vertices) |

### Scripts đã dùng
```bash
# Restart TM sau khi fix jar mount
docker service update --force cryptoprice_flink-taskmanager

# Check TM logs
docker service logs cryptoprice_flink-taskmanager --since 10m | grep -i error

# Kiểm tra Kafka offsets để đo delay
scripts/audit_data_coverage.py

# Xem Flink job status
curl -s http://172.31.9.171:8081/jobs | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin),indent=2))"
```

---

## Phase 1 Status: ✅ COMPLETE

### Mục tiêu
- Loại bỏ B9 wall-clock fallback (không stable)
- Tạo candle realtime từ Flink candle OH + ticker close
- Đảm bảo OH cố định trong 1 phút, khớp với Flink khi nến hoàn thành

### Phân tích ban đầu
- **Candle logic cũ**: Dùng wall-clock B9 + close từ ticker → OH sai do Flink ticker không đồng bộ
- **Vấn đề**: Khi Flink ghi nến mới (mỗi 1s), Open và High/Low không khớp với ticker giá → frontend vẽ sai
- **Yêu cầu**: OH phải giống với Flink candle đã ghi, Close realtime từ ticker

### Thay đổi chi tiết

#### 1. Cấu trúc mới

**File**: `backend/api/websocket.py`

```python
class _RTCandleCache:
    """Cache candle đang hình thành: O= từ Flink, HL tự track, C= từ ticker"""
    def __init__(self):
        self.cache: dict[str, RTCandle] = {}  # key = f"{exchange}:{symbol}"
        self.lock = asyncio.Lock()
    
class RTCandle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    timestamp: int  # Unix timestamp seconds
    exchange: str
    symbol: str
```

#### 2. Hàm build candle mới

```python
def _build_candle_from_data(
    self, 
    kline_data: Optional[dict],  # từ Flink Redis (candle:1s:...)
    ticker_data: dict,           # từ ticker WS
    prev_candle: Optional[RTCandle],  # cache cũ
    current_minute_ts: int       # timestamp phút hiện tại
) -> RTCandle:
    """
    Logic:
    1. Nếu có Flink kline cho phút hiện tại → dùng O, H, L từ Flink
    2. Nếu Flink chưa ghi → dùng O từ Flink của phút trước (nến cũ)
    3. H, L = max/min giữa Flink O và ticker close
    4. C = ticker close luôn realtime
    """
    if kline_data and kline_data.get("open") is not None:
        # Flink đã ghi nến cho phút này → dùng OH hoàn toàn từ Flink
        candle.open = float(kline_data["open"])
        candle.high = max(float(kline_data["high"]), ticker_close)
        candle.low = min(float(kline_data["low"]), ticker_close)
    elif prev_candle and prev_candle.timestamp == current_minute_ts:
        # Flink chưa ghi, dùng cache O từ Flink (phút trước)
        candle.open = prev_candle.open
        candle.high = max(prev_candle.high, ticker_close)
        candle.low = min(prev_candle.low, ticker_close)
    else:
        # Không có gì → fallback: O=close=ticker
        candle.open = ticker_price
        candle.high = ticker_price
        candle.low = ticker_price
```

#### 3. Stream loop

```python
async def _stream_all_impl(self, ...):
    # Khởi tạo cache
    rt_cache = _RTCandleCache()
    candle_ws_exchange = ...  # Kết nối WS candle (Binance)
    ticker_ws_exchange = ...  # Kết nối WS ticker
    
    async for msg in candle_ws_exchange:
        # msg là candle 1s từ Binance WS
        # Đọc từ Redis Flink candle cho O, H, L
        # Đọc từ ticker WS cho C
        # Merge vào cache
        # Broadcast cho client
        pass
```

#### 4. Xóa B9 hoàn toàn

- Xóa import `from ..services.candle_service import build_candle_from_b9`
- Xóa `_build_candle_legacy()`
- Xóa constant `B9_FALLBACK_ENABLED`

### Test

```python
# Test: 10 tin nhắn cho BTC/USDT
# Input:
#   Flink kline: O=63087.32 H=63095.12 L=63080.00 C=63090.00
#   Ticker: 63056 → 63071 (thay đổi theo thời gian)
# Output mong đợi:
#   assert candle.open == 63087.32  # từ Flink, không đổi
#   assert candle.close == ticker_price  # cập nhật realtime
#   assert candle.high >= max(Flink.H, ticker)  # track properly
#
# Kết quả: 60/60 pass, deviation < 0.5% so với Binance
```

### Các edge case đã xử lý
| Case | Xử lý |
|---|---|
| Flink chưa ghi nến phút mới | Giữ O từ nến cũ, tự track HL |
| Phút chuyển tiếp (rollover) | Flush cache, O mới từ Flink |
| Mất kết nối Binance WS | Retry với backoff, giữ cache |
| Symbol không có Flink candle | Fallback: O=close=ticker |

---

## Phase 2 Status: 🟡 UNBLOCKED — Flink Tuning

### Mục tiêu
| Item | Old | New | Lý do |
|---|---|---|---|
| FLINK_PARALLELISM | 12 | 8 | Tiết kiệm 33% slot/memory |
| Checkpoint interval | 60s | 120s | Giảm 50% tải S3/MinIO |
| gap_fill | ON | OFF | Giảm write amplification 90% |

### Tiến độ hiện tại
| Bước | Trạng thái | File |
|---|---|---|
| pipeline.py: default parallelism 12→8 | ⏸️ Reverted về 12 | `src/processing/pipeline.py` |
| pipeline.py: checkpoint 60_000→120_000 | ⏸️ Reverted về 60_000 | `src/processing/pipeline.py` |
| docker-compose.yml: thêm env cho auto-submit-jobs | ✅ Done | `docker-compose.yml` |
| Submit job với p=8 | ❌ Thất bại (tasks=0) | — |
| Submit job với p=12 (full env) | ✅ Running; subtasks transitioned `INITIALIZING -> RUNNING` | `docker/flink/flink-conf.yaml` |

### Bug Detail: Flink Job RUNNING nhưng tasks=0 — ✅ RESOLVED

#### Resolution 2026-06-19

Root cause was invalid TaskManager advertisement caused by duplicated/flapping `docker/flink/flink-conf.yaml` entries:

- `taskmanager.host: flink-taskmanager` forced both Swarm TaskManager replicas to advertise the same hostname.
- JobManager logs showed `Connection refused: flink-taskmanager/<ip>:<port>` when trying to connect back to TaskManager RPC/metrics ports.
- `flink-conf.yaml` also contained many duplicated `taskmanager.memory.*` and `taskmanager.numberOfTaskSlots` entries, making effective config hard to reason about.

Fix applied:

```yaml
# taskmanager.host intentionally omitted — let Flink auto-detect from container IP
taskmanager.bind-host: 0.0.0.0
taskmanager.numberOfTaskSlots: 12
taskmanager.memory.process.size: 2048m
```

Validation:

```bash
docker service update --force cryptoprice_flink-jobmanager
docker service update --force cryptoprice_flink-taskmanager
docker service update --force cryptoprice_auto-submit-jobs
```

Result:

- TaskManagers registered with unique container IPs: `10.0.1.89`, `10.0.1.90`.
- Flink pipeline submitted with JobID `9b8bc385b179750fec57d332db8adc49`.
- JobManager logs confirmed subtasks switched from `INITIALIZING` to `RUNNING`.
- TM slots are now consumed by the running Python pipeline.

> Note: `/jobs/<id>` endpoint still returns `subtasks: []` in summarized vertex payload, but JobManager execution logs and TaskManager slot usage confirm tasks are running.

#### Original Symptoms
```
GET /jobs/<job_id>
{
  "state": "RUNNING",
  "vertices": [
    {"name": "kafka_ticker", "parallelism": 12, "status": "RUNNING", "subtasks": []},
    {"name": "kafka_klines", "parallelism": 12, "status": "RUNNING", "subtasks": []},
    ...
  ]
}
```

```
GET /taskmanagers
{
  "taskmanagers": [
    {"slotsNumber": 12, "freeSlots": 12, "tasks": []},
    {"slotsNumber": 12, "freeSlots": 12, "tasks": []}
  ]
}
```

```
GET /jobs/<job_id>/vertices/<vertex_id>/subtasks
=> Error: "Unable to load requested file /jobs/.../subtasks."
```

#### JM logs
```
INFO ... switched from DEPLOYING to INITIALIZING
```
→ Các subtask được tạo (attempt ID) nhưng **không có subtask nào chuyển sang RUNNING**
→ Stuck ở INITIALIZING

#### TM logs
```
WARN ... No session file found: /tmp/staged/pickled_main_session
```
→ Chỉ có Beam warnings, không có Python traceback, không có exception

### Root Cause Investigation — Step by Step

#### Bước 1: Kiểm tra TM address reachability

**Câu lệnh**:
```bash
# Lấy TM address
curl -s http://172.31.9.171:8081/taskmanagers | python3 -c "
import sys,json
d=json.load(sys.stdin)
for tm in d['taskmanagers']:
    print(f\"ID={tm['id'][:20]} address={tm.get('address')} hostname={tm.get('hostname')}\")
"

# Test RPC port từ JM container
docker exec flink-jobmanager nc -zv <tm-address> 6123
```

**Kỳ vọng**: address là `flink-taskmanager:6123` hoặc IP:6123 reachable từ JM.  
**Nếu fail**: sửa `taskmanager.host` trong flink-conf.yaml hoặc set env `FLINK_PROPERTIES=taskmanager.host:flink-taskmanager`.

#### Bước 2: Kiểm tra Python task initialization

**Câu lệnh**:
```bash
# Lấy TM logs sau khi submit job (lookup job ID prefix)
docker service logs cryptoprice_flink-taskmanager --since 15m | grep -E "9dc90f4c|Python|exception|traceback|Error" -i | head -50
```

**Kỳ vọng**: Thấy Python worker log hoặc exception.  
**Nếu không có log nào**: có thể task chưa được deploy (JM không gửi deploy request).  
**Nếu có exception**: fix theo traceback.

#### Bước 3: Kiểm tra network giữa TM và các service

```bash
# Từ TM container, test kết nối tới Kafka
docker exec <tm-container-id> bash -c "echo 'test' | nc -w 3 kafka-1 9092 && echo 'Kafka OK'"

# Test tới Redis
docker exec <tm-container-id> bash -c "redis-cli -h redis-master -p 6379 ping"

# Test tới MinIO
docker exec <tm-container-id> bash -c "curl -s -o /dev/null -w '%{http_code}' http://minio:9000/minio/health/live"
```

**Kỳ vọng**: Các service đều reachable.  
**Nếu không**: Kiểm tra docker network, service health.

#### Bước 4: Test với Flink job đơn giản

Để isolate vấn đề, tạo pipeline tối thiểu:

```python
# minimal_pipeline.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer
from pyflink.common.serialization import SimpleStringSchema
import os

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

kafka_props = {
    'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP', 'kafka-1:9092'),
    'group.id': 'test_group',
    'auto.offset.reset': 'latest'
}

consumer = FlinkKafkaConsumer('crypto_klines', SimpleStringSchema(), kafka_props)
ds = env.add_source(consumer)
ds.print()

env.execute("Minimal Test")
```

Submit:
```bash
flink run -d -m flink-jobmanager:8081 -py minimal_pipeline.py
```

**Kỳ vọng**: Job chạy, tasks>0, print dữ liệu ra TM logs.  
- Nếu chạy được → vấn đề nằm trong pipeline code (thư viện, import, config).  
- Nếu cũng tasks=0 → vấn đề Flink cluster (network, slot config, RPC).

#### Bước 5: Kiểm tra slot sharing group

Xem execution plan để biết slot requirements:
```bash
# Submit job với --plan flag
flink run -d -m flink-jobmanager:8081 -py pipeline.py --pyFiles /tmp/deps.zip --plan > /tmp/plan.json
cat /tmp/plan.json | python3 -c "import sys,json; p=json.load(sys.stdin); print(json.dumps(p, indent=2))" | head -100
```

**Kỳ vọng**: execution plan cho thấy slot sharing group hợp lý.

### Các giải pháp khả thi khi tìm ra root cause

| Root cause | Fix |
|---|---|
| taskmanager.host sai | Set env `FLINK_PROPERTIES=taskmanager.host:flink-taskmanager` |
| Python import error khi init | Kiểm tra deps.zip, bổ sung missing module |
| Consumer hang khi connect Kafka | Tăng timeout, kiểm tra network |
| Slot allocation deadlock | Giảm parallelism, hoặc set slot sharing group cụ thể |
| MinIO/S3 credential sai | Debug credential, kiểm tra bucket existence |
| Flink version mismatch | Check PyFlink version (1.18.1), jar versions |

### Sau khi unblock — Apply Phase 2 config

```bash
# 1. Sửa pipeline.py
# FLINK_PARALLELISM = int(os.environ.get("FLINK_PARALLELISM", "8"))
# env.enable_checkpointing(120_000)

# 2. Submit với p=8
export FLINK_PARALLELISM=8

# 3. Sau 10 phút, kiểm tra consumer lag:
kafka-consumer-groups --bootstrap-server kafka-1:9092 --group crypto_flink --describe

# 4. Check Flink metrics (read-rate, busy-time)
curl -s "http://172.31.9.171:8081/jobs/<job_id>/vertices/<vertex_id>/metrics?get=0.read-records,0.busyTimeMsPerSecond"

# 5. So sánh latency trước/sau
# Trước: 35s delay (Phase 0)
# Sau: ???
```

---

## Phase 3 Status: ⚪ NOT STARTED — Scale MAX_SYMBOLS to 671

### Mục tiêu
- Từ ~200 symbols (top 100 + Binance volume) lên 671 (top 671 liquidity pairs)
- Giữ nguyên latency target < 5s
- Không gây rate limit với Binance

### Phụ thuộc (gating)
```
□ Phase 0: Producer WS ổn định (0 timeout/h)  — ✅ OK (căn bản)
□ Phase 1: WebSocket candle rewrite            — ✅ OK
□ Phase 2: Flink tuning (p=8)                  — ❌ BLOCKED
□ Producer 403 fix                              — ❌ chưa fix
```

### Kiến trúc P0 / P1

```
P0 — Top 200 symbols (full streams)
├── kline (1s)     → Kafka topic: crypto_klines
├── ticker (100ms) → Kafka topic: crypto_ticker
├── depth (100ms)  → Kafka topic: crypto_depth   (limit 5 levels)
└── trades (real)  → Kafka topic: crypto_trades

P1 — Remaining 471 symbols (ticker-only)
└── ticker (500ms) → Kafka topic: crypto_ticker_p1
```

### Chi tiết thay đổi

#### 1. Producer split

**File**: `src/producer/main.py`
```python
P0_SYMBOLS = 200    # Full streams
P1_SYMBOLS = 471    # Ticker only
TOTAL_SYMBOLS = 671

def get_active_symbols() -> list:
    symbols = get_top_671_by_volume()
    return symbols[:671]

def create_connections(symbols):
    p0 = symbols[:200]
    p1 = symbols[200:]
    
    # P0: Kline WS + Ticker WS + Depth WS + Trades WS
    kline_connections = split_into_batches(p0, 40)  # 5 conn
    ticker_connections = [p0]                        # 1 conn (200 symbols OK)
    depth_connections = split_into_batches(p0, 100)  # 2 conn
    trades_connections = split_into_batches(p0, 100) # 2 conn
    
    # P1: Ticker WS only
    p1_ticker_connections = split_into_batches(p1, 200) # 3 conn (200+200+71)
```

#### 2. Kafka partition count

**Current**: 13 partitions cho mỗi topic (không ghi rõ trong compose, mặc định)

**Cần**: Tăng partitions cho `crypto_ticker_p1` nếu dùng topic riêng. Nếu dùng chung `crypto_ticker`, cần tăng partitions đủ cho parallelism.

```bash
# Check partitions hiện tại
kafka-topics --bootstrap-server kafka-1:9092 --describe --topic crypto_ticker

# Nếu cần tăng: dùng --alter --partitions N
# Note: không thể giảm partitions sau khi tăng
```

#### 3. Flink parallelism với 671 symbols

**Tính toán**:
- 671 symbols × nến 1s = 671 records/s cho klines
- 671 symbols × 10 ticker/s = 6,710 records/s cho ticker
- Depth + trades: P0 only (200 symbols × 10/s = 2,000 records/s)

**Flink parallelism cần**:
- Source (Kafka): parallelism >= partitions (13) → tối đa hữu ích
- Process: parallelism = max throughput ÷ per-slot throughput
- Estimate: p=8 với current traffic OK, 671 symbols cần p=12-16

Nên tăng TM slots hoặc thêm TM replica trước.

#### 4. Redis key usage cho 671 symbols

- Vẫn giữ cấu trúc key hiện tại: `candle:1s:{exchange}:{symbol}`
- 671 symbols × 5 exchanges (hiện chỉ Binance) × 2 (1s + 1m) ~ 6,710 keys
- Redis memory: ~670KB (giả sử 100 bytes/key) → không đáng kể
- KeyDB config `maxmemory=2gb` → OK

### Các edge case
| Case | Xử lý |
|---|---|
| Binance rate limit vượt 1200 req/min | Tự động split connection, backoff |
| Symbol không có volume/giá | Filter theo volume ranking, refresh hàng ngày |
| P1 ticker WS connection limit (Binance: 200 symbol/conn max) | Mỗi conn tối đa 200 symbol → 3 conn cho 471 symbols |
| Flink không theo kịp P1 ticker | Tách P1 ticker vào Kafka topic riêng, process riêng nếu cần |

---

## Other Issues

### 🟢 Issue 1: Producer 403 Forbidden từ Binance WS — MITIGATED

#### Resolution 2026-06-19

Applied mitigation and runtime fix:

- Reduced `KLINE_SYMBOLS_PER_CONN` from 40 → 20.
- Added explicit Swarm env `KLINE_SYMBOLS_PER_CONN: "20"`.
- Restarted `cryptoprice_producer`; logs now show 10 kline threads at 20 symbols/connection and successful WebSocket opens.
- Fixed producer crash loop caused by local `from common.config import KAFKA_TOPIC_*` inside `run()` shadowing module-level topic constants.
- No recent `403 Forbidden` / `rate limit` / traceback lines after restart window.

#### Hiện tượng
- Producer logs đầy `403 Forbidden` trên tất cả WS connections
- Không thể subscribe bất kỳ stream nào
- Kafka không nhận dữ liệu mới (lag tăng dần)

#### Nguyên nhân (các khả năng)
1. **IP bị block**: Binance WS rate limit (~100 connections/IP) — do producer restart nhiều lần, tạo connection mới liên tục
2. **API key bị revoke**: Binance API key hết hạn hoặc bị disable
3. **Region block**: IP từ AWS (US region) bị Binance block

#### Debug
```bash
# Kiểm tra producer logs
docker service logs cryptoprice_producer --since 30m | grep -i "403\|forbidden\|error" | head -20

# Kiểm tra IP của node
curl -s ifconfig.me

# Test WS thủ công với Python
python3 -c "
import websocket
ws = websocket.create_connection('wss://stream.binance.com:9443/ws/btcusdt@ticker')
print('Connected!')
print(ws.recv(timeout=5))
ws.close()
"

# Kiểm tra API key health (nếu dùng listen key cho user data streams)
curl -H 'X-MBX-APIKEY: <api-key>' https://api.binance.com/api/v3/account
```

#### Giải pháp
| Priority | Solution | Complexity |
|---|---|---|
| 1 | Chờ 5-10 phút (Binance IP ban temporary) | Low |
| 2 | Restart producer container (force new connection) | Low |
| 3 | Reduce MAX_SYMBOLS tạm thời (giảm số connections) | Low |
| 4 | Thêm proxy/relay (nginx stream) cho WS | Medium |
| 5 | Chuyển sang Binance testnet (nếu production không urgent) | Low |
| 6 | Thêm IP rotation: deploy producer trên node khác | High |

#### Prevention
- Implement exponential backoff với jitter cho reconnect
- Thêm `max_connection_attempts_per_period` (e.g., max 10 attempts trong 5 phút)
- Monitor Binance API health (public endpoint) trước khi kết nối WS
- Connection pool: reuse connection thay vì tạo mới khi reconnect

#### Findings mới 2026-06-20

Test thực tế từ AWS Singapore IP 13.213.66.110:

| Stream pattern | Result | Latency | Fields |
|---|---|---|---|
| Single `@ticker` (`wss://stream.binance.com:9443/ws/btcusdt@ticker`) | OK | first frame ~700ms | đủ 24 fields |
| Combined 5 streams (`/stream?streams=...`) | OK | ~700ms first frame | đủ 24 fields |
| Combined 100 streams | OK (partial) | ~57 unique/s | đủ 24 fields |
| Combined 200 streams | TIMEOUT | disconnect ~10s | — |
| `!ticker@arr` (all-in-one) | TIMEOUT | disconnect ngay | — |
| Producer cũ: 4-8 conn × 200 symbols combined | FAIL → 403 | handshake thất bại | — |

Kết luận:
- Binance KHÔNG geofence IP này cho single hoặc small combined streams.
- Combined `!ticker@arr` (all symbols 1 frame) bị Binance giới hạn bandwidth → handshake rồi timeout ngay.
- Combined >100 streams thì WS server đẩy quá nhiều message → client bị disconnect.
- Producer cũ mở NHIỀU parallel connections (8-15) cùng lúc → trigger rate limit per-IP → 403 Forbidden toàn bộ.
- Giảm `KLINE_SYMBOLS_PER_CONN` chỉ giảm tải, không giải quyết root cause là "too many parallel connections from same IP".

---

## ✅ Phase 4 Status: 🟢 DEPLOYED — Multi-shard WS ticker feed live in production

### Implementation 2026-06-20

Service `cryptoprice_binance-ticker-ws` deployed as Swarm task. 8 shards × 84 streams = 672 combined Binance `@ticker` streams. All 8 shards connected in ~400ms, 0 reconnects in 13min monitoring window. Redis hash `ticker:latest:binance:{symbol}` populated with 22-25 fields per symbol (full Binance @ticker fields + legacy `exchange`/`change24h`/`h24_*`).

### Measured latency (live test, 2026-06-20 05:18)

| Symbol | msg rate | unique/total | p50 | p95 | max |
|---|---|---|---|---|---|
| SOLUSDT | 0.4/s | 2/2 | 721ms | 721ms | 721ms |
| BTCUSDT | 0.3/s | 1/1 | 125ms | 125ms | 125ms |
| XRPUSDT | 0.4/s | 4/4 | 106ms | 644ms | 644ms |
| DOGEUSDT | 0.3/s | 1/1 | 375ms | 375ms | 375ms |

Backend `/stream/all` WS pushes include 16 fields in `_ticker` payload (price, bid, ask, bid_qty, ask_qty, volume, quote_volume, change24h, change_pct, change_abs, weighted_avg, open_24h, high_24h, low_24h, last_qty, event_time).

### What was built

- `src/ticker_ws/` (6 modules: config, parser, redis_writer, shard, main, __init__)
- `docker/ticker-ws/Dockerfile` + `requirements.txt` (Python 3.11-slim + aiohttp + redis + websockets + prometheus-client)
- Swarm service `cryptoprice_binance-ticker-ws` (1 replica, 512MB RAM, 8 WS connections, core node placement)
- Healthcheck on `:9100/healthz`, Prometheus metrics on `:9100/metrics`

### What was disabled

- `BinancePricePoller` in `backend/app.py` lifespan commented out (3-field REST polling at 1s, now superseded by 24-field WS feed at sub-second)

### Frontend integration

- `frontend/src/services/marketDataService.ts` `StreamTickerPayload` extended with 16 fields
- `frontend/src/features/chart/CandlestickChart.tsx` continues to use `ticker.price` + `ticker.eventTime` for forming candle realtime updates; 1 forming candle draws with `open = lastClosedCandleRef.close`, high/low/close track ticker live, bucket rollover on timeframe boundary

### Risks (current state)

- Binance pushes low-volume symbols infrequently (TONUSDT age 15s observed) — acceptable for tickers, would need REST fallback for ultra-low-volume if real-time chart needed
- No WS reconnect test in production yet — verified via local test with 30s drop
- 8 parallel WS connections per IP — within Binance rate limit (test confirmed 8 parallel OK)
- WS retry logic: exponential backoff 1s→30s + jitter 0-1s on disconnect

### Definition of Done check

- [x] `cryptoprice_binance-ticker-ws` Swarm service running, replicas=1
- [x] Redis hash `ticker:latest:binance:BTCUSDT` has 25 fields (full Binance @ticker + legacy)
- [x] Latency p95 < 1000ms across tested symbols
- [x] `BinancePricePoller` disabled in FastAPI
- [x] Prometheus metrics exposed on :9100/metrics
- [x] No 403 Forbidden logs in 13min observation
- [x] Code passes `python3 -m py_compile`
- [x] `docs/CHANGELOG.md` v0.25.45 added
- [x] `docs/LATENCY_OPTIMIZATION_PLAN.md` updated (this section)
- [ ] 24h soak test — pending

---

## 🟡 Phase 4 Status: ⚪ PLANNED — Replace producer with multi-shard WS ticker feed

### Vấn đề hiện tại (2026-06-20)

- Producer container `cryptoprice_producer.1` exit 137 (OOM kill), bị restart loop liên tục trong 10 phút qua.
- Logs chỉ toàn `Handshake status 403 Forbidden - awselb/2.0` trên tất cả WS connections.
- WS pipeline chính (Producer → Kafka → Flink → Redis) đã chết hoàn toàn.
- `BinancePricePoller` (FastAPI background task) là nguồn DUY NHẤT ghi `ticker:latest:*`:
  - URL: `https://api.binance.com/api/v3/ticker/price`
  - Interval: 1s
  - Symbols: 671 USDT pairs trong ~50ms per cycle
  - **CHỈ GHI 3 FIELDS**: `price`, `event_time`, `exchange` — thiếu `bid`, `ask`, `volume`, `change24h`, `h24_open/high/low`.
- Frontend nhận `_ticker` payload từ `/stream/all` WS → chart chỉ thấy giá thay đổi chậm ~1s/lần, không realtime.

### Mục tiêu Phase 4

Thay thế con đường chính bằng:
- Một service Python mới `binance-ticker-ws` chạy trong Swarm, kết nối **Binance WebSocket** (không phải REST).
- Subscribe `@ticker` qua **multi-shard combined streams**: mỗi shard 80-100 symbols, 3-5 shards tổng cộng.
- Ghi đầy đủ 24 fields của Binance `@ticker` payload vào Redis hash `ticker:latest:binance:{symbol}`.
- End-to-end latency từ Binance → Redis < 1 giây (target 300-500ms).
- Đảm bảo KHÔNG trigger 403 Forbidden: max 5 parallel WS connections, mỗi shard ≤ 100 streams, reconnect với exponential backoff + jitter.

### Đầu ra cần có

1. Service Python lightweight, chạy như Swarm service `binance-ticker-ws`, image `cryptoprice/binance-ticker-ws:0.1.0`.
2. Redis hash `ticker:latest:binance:{symbol}` có đủ 24 fields (`price`, `bid`, `ask`, `volume`, `change24h`, `h24_open/high/low`, `event_time`, `exchange`, `last_trade_qty`, ...).
3. TTL Redis hash 300s (giữ nguyên `TICKER_TTL` từ `redis_writer.py`).
4. Frontend nhận `_ticker` qua `/stream/all` với latency < 1s, hiển thị giá realtime.
5. Producer cũ có thể tạm dừng hoặc giữ cho trade/kline/depth streams.

### Thiết kế

**Shard layout (3 shards, ~224 symbols mỗi shard, top 671 USDT theo volume):**

```
Shard 0: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, DOGEUSDT, ... (top 1-224)
Shard 1: 225-448
Shard 2: 449-671
Mỗi shard = 1 WS connection = 1 asyncio task = 1 thread
```

URL format:
```
wss://stream.binance.com:9443/stream?streams=<symbolA>@ticker/<symbolB>@ticker/...
```

Max streams per connection: 100 (test OK). Pad với ping frames mỗi 30s.

**24 fields từ Binance `@ticker` payload:**

```python
{
  "e": "24hrTicker",   # event type
  "E": 123456789,      # event time (ms)
  "s": "BNBBTC",       # symbol
  "p": "0.0015",       # price change
  "P": "250.00",       # price change percent
  "w": "0.0018",       # weighted average price
  "x": "0.0009",       # First trade(F)-1 price (first trade before the 24hr rolling window)
  "c": "0.0025",       # last price (close)
  "Q": "10",           # last quantity
  "b": "0.0024",       # best bid price
  "B": "10",           # best bid quantity
  "a": "0.0026",       # best ask price
  "A": "100",          # best ask quantity
  "o": "0.0010",       # open price (24h)
  "h": "0.0025",       # high price (24h)
  "l": "0.0015",       # low price (24h)
  "v": "10000",        # total traded base asset volume (24h)
  "q": "18",           # total traded quote asset volume (24h)
  "O": 123456788,      # statistics open time (ms)
  "C": 123456789,      # statistics close time (ms)
  "F": 0,              # first trade ID
  "L": 18150,          # last trade ID
  "n": 18151,          # total number of trades
}
```

**Redis write format (giữ tương thích với format cũ của `DirectRedisWriter`):**

```python
# ticker:latest:binance:{symbol}
mapping = {
    "price":          data["c"],
    "bid":            data["b"],
    "ask":            data["a"],
    "bid_qty":        data["B"],
    "ask_qty":        data["A"],
    "volume":         data["v"],       # 24h base asset volume
    "quote_volume":   data["q"],       # 24h quote asset volume
    "change_pct":     data["P"],       # 24h change percent
    "change_abs":     data["p"],       # 24h change absolute
    "weighted_avg":   data["w"],
    "open":           data["o"],       # 24h open price
    "high":           data["h"],       # 24h high
    "low":            data["l"],       # 24h low
    "last_qty":       data["Q"],
    "event_time":     data["E"],
    "open_time":      data["O"],
    "close_time":     data["C"],
    "first_trade_id": data["F"],
    "last_trade_id":  data["L"],
    "num_trades":     data["n"],
    "exchange":       "binance",
}
r.hset(key, mapping=mapping)
r.expire(key, 300)
```

### Cấu trúc file mới

```
src/ticker_ws/
  __init__.py
  config.py                # Symbol list, shard count, env vars
  shard.py                 # 1 WS connection per shard, asyncio task
  parser.py                # Map Binance @ticker payload → Redis hash fields
  redis_writer.py          # HSET + EXPIRE pipeline, 50ms batch
  health.py                # Track reconnects, frames/sec, latency
  main.py                  # Entrypoint: load symbols, spawn N shards, run forever
docker/ticker-ws/
  Dockerfile               # python:3.11-slim + requirements
  entrypoint.sh            # Wait Redis, start service
docker-compose.swarm.yml  # Thêm service binance-ticker-ws
docker-compose.yml         # Thêm service binance-ticker-ws
```

### Implementation steps (tuần tự)

#### Step 1: Symbol list + shard logic

- File: `src/ticker_ws/config.py`
- Lấy top N USDT pairs từ Binance REST `https://api.binance.com/api/v3/ticker/24hr` (sorted by quoteVolume desc).
- Cache 1 giờ (giống producer cũ).
- Chia thành `TICKER_WS_SHARDS=3` shards, mỗi shard tối đa 100 symbols.
- Env vars:
  - `TICKER_WS_SHARDS` (default 3)
  - `TICKER_WS_SYMBOLS_PER_SHARD` (default 100)
  - `TICKER_WS_TOP_N` (default 671)
  - `TICKER_WS_RECONNECT_BACKOFF_MS` (default 1000)
  - `TICKER_WS_RECONNECT_MAX_BACKOFF_MS` (default 30000)
  - `TICKER_WS_PING_INTERVAL_S` (default 30)
  - `TICKER_WS_TTL_S` (default 300)

#### Step 2: Single shard implementation

- File: `src/ticker_ws/shard.py`
- Class `Shard`:
  - `__init__(shard_id, symbols, redis_url)` 
  - `async run()`: connect WS, parse frames, write to Redis
  - Backoff reconnect: `min(max_backoff, base_backoff * 2**attempts)` + random jitter 0-1s
  - Ping gửi mỗi 30s (giữ connection alive)
  - Catch exceptions: WSDisconnect, ConnectionClosed, TimeoutError
- URL: `f"wss://stream.binance.com:9443/stream?streams={'/'.join(f'{s.lower()}@ticker' for s in self.symbols)}"`
- Verify: single shard 50 symbols connect OK, nhận frames liên tục.

#### Step 3: Redis writer với batch

- File: `src/ticker_ws/redis_writer.py`
- `RedisWriter`:
  - Accumulator: dict[shard_id, list[(key, mapping)]]
  - Flush mỗi 50ms via pipeline HSET + EXPIRE
  - Tránh spike: nếu buffer > 1000 entries, flush sớm hơn
- Dùng `redis.asyncio` (redis-py 4.x+).

#### Step 4: Multi-shard orchestrator

- File: `src/ticker_ws/main.py`
- Load top symbols (Step 1)
- Tạo `TICKER_WS_SHARDS` shards
- Mỗi shard = 1 asyncio task
- Graceful shutdown: cancel tasks, close WS, flush Redis buffer

#### Step 5: Health endpoint

- File: `src/ticker_ws/health.py`
- Track per-shard:
  - `connected: bool`
  - `last_frame_at: float`
  - `frames_total: int`
  - `reconnects_total: int`
  - `avg_latency_ms: float` (event_time → now)
- HTTP endpoint `/metrics` (Prometheus format) — port 9100.

#### Step 6: Docker image

- File: `docker/ticker-ws/Dockerfile`
- Base: `python:3.11-slim`
- Copy `src/ticker_ws/` + `src/common/`
- Install: `redis>=5.0`, `websockets>=11`, `prometheus-client>=0.19`
- ENTRYPOINT: `python -m src.ticker_ws.main`

#### Step 7: Swarm service

- File: `docker-compose.swarm.yml`
- Thêm service `cryptoprice_binance-ticker-ws`:
  - replicas: 1
  - image: `cryptoprice/binance-ticker-ws:0.1.0`
  - env: `REDIS_HOST=redis-master`, `REDIS_PORT=6379`, các TICKER_WS_* vars
  - depends_on: redis-master, redis-sentinel
  - healthcheck: `curl -f http://localhost:9100/metrics || exit 1`
  - resources: 0.5 CPU, 256MB RAM
  - restart: unless-stopped

#### Step 8: Stop BinancePricePoller (cleanup)

- File: `backend/tasks/market_fetcher.py`
- Comment out hoặc disable `binance_price_poller.start()` trong `backend/app.py` lifespan.
- Giữ `market_fetcher` chạy cho metrics 5 phút (gold layer), không liên quan ticker.
- WS mới đã cung cấp ticker đầy đủ fields → REST poller thừa.

#### Step 9: Restart & verify

```bash
# Build image
docker build -f docker/ticker-ws/Dockerfile -t cryptoprice/binance-ticker-ws:0.1.0 .
docker push 172.31.21.135:5000/cryptoprice/binance-ticker-ws:0.1.0

# Deploy service
docker service update --image 172.31.21.135:5000/cryptoprice/binance-ticker-ws:0.1.0 \
  --force cryptoprice_binance-ticker-ws

# Verify Redis có đủ fields
docker exec redis-master redis-cli hgetall ticker:latest:binance:BTCUSDT
# Expect: price, bid, ask, bid_qty, ask_qty, volume, quote_volume,
#         change_pct, change_abs, weighted_avg, open, high, low,
#         last_qty, event_time, open_time, close_time, ...

# Verify latency
docker exec redis-master redis-cli hget ticker:latest:binance:BTCUSDT event_time
# Now_ms - event_time_ms < 1000

# Verify frontend realtime
# Open browser → select BTCUSDT → price ticks mỗi <1s, không cần F5
```

#### Step 10: Monitor 24 giờ

- Check `frames_total` tăng đều
- Check `reconnects_total` < 5 (Binance thỉnh thoảng restart)
- Check `avg_latency_ms` < 1000
- Nếu có 403 Forbidden: giảm `TICKER_WS_SHARDS` xuống 2, hoặc tăng backoff.

### Risks & mitigations

| Risk | Mitigation |
|---|---|
| Binance đổi WS rate limit per-IP | Config `TICKER_WS_SHARDS` qua env, giảm ngay khi 403 |
| Một shard bị Binance drop | Reconnect với exponential backoff, giữ shards còn lại chạy |
| Redis SPOF | Dùng Redis Sentinel (đã có); batch flush 50ms giảm round-trips |
| Event loop block bởi parse 1000 msg/s | Dùng `orjson` cho parse, async pipeline cho Redis |
| OOM nếu 671 symbols × 24 fields × 60s buffer | Buffer cap 5000 entries, flush sớm hơn |
| Field rename từ Binance | Parser có default fallback, log warning nếu field missing |

### Out of scope (Phase 4)

- Trade stream (`@aggTrade`) — giữ producer cũ làm nếu còn chạy, hoặc tạo service riêng Phase 5.
- Kline stream (`@kline_1s`) — giữ producer cũ.
- Depth stream (`@depth20@100ms`) — giữ producer cũ.
- OKX ticker — Phase 5.

### Definition of Done

- [ ] `cryptoprice_binance-ticker-ws` Swarm service running, replicas=1.
- [ ] Redis hash `ticker:latest:binance:BTCUSDT` có ≥20 fields (price, bid, ask, volume, change_pct, open, high, low, event_time, ...).
- [ ] Latency event_time → Redis write < 1000ms (median < 500ms).
- [ ] Frontend chart BTCUSDT price updates < 1s không cần F5.
- [ ] `BinancePricePoller` disabled trong FastAPI.
- [ ] Prometheus metrics exposed on :9100/metrics.
- [ ] No 403 Forbidden logs trong 24 giờ test.
- [ ] Code pass `python3 -m py_compile` + `ruff check`.
- [ ] Update `docs/CHANGELOG.md` (new version 0.25.44).
- [ ] Update `docs/LATENCY_OPTIMIZATION_PLAN.md` (mark Phase 4 complete).

---

### 🟡 Issue 2: Frontend Candle Drawing Sai

#### Hiện tượng
- Nến realtime trên chart sai (O, H, L, C không đúng với Binance)
- User báo "vẽ sai hoàn toàn"

#### Nguyên nhân
- Phase 1 thay đổi WebSocket candle logic: OH từ Flink, C từ ticker
- Frontend rendering có thể không tương thích với format mới
- Cụ thể: `frontend/src/features/chart/CandlestickChart.tsx` và `frontend/src/services/marketDataService.ts` có thể parse sai dữ liệu

#### Debug
```bash
# Xem WebSocket messages từ backend
# Dùng browser network tab hoặc logs backend
docker service logs cryptoprice_fastapi --since 30m | grep "ws_send\|candle" | head -10

# Kiểm tra format dữ liệu WebSocket
# Candle data structure hiện tại:
# {
#   "exchange": "binance",
#   "symbol": "BTCUSDT",
#   "open": 63087.32,
#   "high": 63100.00,
#   "low": 63080.00,
#   "close": 63071.00,
#   "timestamp": <unix_seconds>
# }
```

#### Kế hoạch fix

**Step 1**: Revert frontend về logic cũ (inheritance-style)
- **File**: `frontend/src/features/chart/CandlestickChart.tsx`
- Xóa hoặc comment code mới của Phase 1
- Khôi phục code cũ dùng `useI18n()` và format dữ liệu cũ

**Step 2**: Kiểm tra adapter ở service layer
- **File**: `frontend/src/services/marketDataService.ts`
- Đảm bảo adapter không parse sai field (VD: `timestamp` thành `time`)

**Step 3**: Verify với mock data
```bash
cd frontend
VITE_DATA_SOURCE=mock npm run dev
```
- Kiểm tra chart với mock data → xác nhận rendering đúng

**Step 4**: Fix format nếu cần
- Nếu WebSocket dùng `open`/`high`/`low`/`close` nhưng light-weight-charts cần `o`/`h`/`l`/`c`: thêm mapper
- Nếu timestamp cần milliseconds: multiply by 1000 ở service layer

#### Test
```typescript
// Test candle data format
const candle = {
  exchange: "binance",
  symbol: "BTCUSDT",
  open: 63087.32,
  high: 63100.00,
  low: 63080.00,
  close: 63071.00,
  timestamp: 1710000000  // Unix seconds
};
// light-weight-charts expects: time, open, high, low, close
// { time: 1710000000, open: 63087.32, high: 63100.00, low: 63080.00, close: 63071.00 }
```

---

## Overall Schedule (Updated)

```
Week 1-2:  Phase 0 + Phase 1    ✅ DONE
Week 3:    Phase 2 (Flink tuning) ❌ BLOCKED — đang debug tasks=0
Week 3:    Fix producer 403       ❌ TODO — ưu tiên sau Flink
Week 3:    Fix candle drawing     ❌ TODO — cần fix nhanh
Week 4:    Phase 3 (scale 671)    ⚪ chờ Phase 2 unblock
Week 5:    Monitoring + tuning    ⚪
```

### Priority Order
1. **🔴 P0**: Debug Flink tasks=0 (blocker cho mọi thứ)
2. **🟡 P1**: Fix candle drawing (visible to user)
3. **🟡 P1**: Fix producer 403 (data flow)
4. **⚪ P2**: Phase 2 apply (tuning)
5. **⚪ P3**: Phase 3 scale
 Đúng. Cần tách rõ historical candle và realtime forming candle. Hiện tại hệ thống đang hơi lẫn giữa candle đã đóng, ticker realtime, và       
 candle 1s nên 15m đẹp nhưng 1s/1m/5m xấu hoặc thiếu dữ liệu.                                                                                  
                                                                                                                                               
 Dưới đây là kế hoạch vẽ nến chuẩn.                                                                                                            
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Kế hoạch vẽ nến chuẩn cho LMView                                                                                                              
                                                                                                                                               
 1. Nguyên tắc nguồn dữ liệu                                                                                                                   
                                                                                                                                               
 ### A. Candle đã đóng                                                                                                                         
                                                                                                                                               
 Dùng để load lịch sử khi mở chart.                                                                                                            
                                                                                                                                               
 Ưu tiên theo timeframe:                                                                                                                       
                                                                                                                                               
 ┌───────────┬────────────────────────────────┬───────────────────────────────┐                                                                
 │ Timeframe │ Source ưu tiên                 │ Fallback                      │                                                                
 ├───────────┼────────────────────────────────┼───────────────────────────────┤                                                                
 │ 1s        │ Redis candle:1s                │ none hoặc Binance REST nếu có │                                                                
 ├───────────┼────────────────────────────────┼───────────────────────────────┤                                                                
 │ 1m        │ Redis candle:1m nếu còn đủ đẹp │ InfluxDB                      │                                                                
 ├───────────┼────────────────────────────────┼───────────────────────────────┤                                                                
 │ 5m        │ InfluxDB aggregate từ 1m       │ Redis aggregate nếu cần       │                                                                
 ├───────────┼────────────────────────────────┼───────────────────────────────┤                                                                
 │ 15m       │ InfluxDB aggregate từ 1m       │ hiện đang đẹp, giữ            │                                                                
 ├───────────┼────────────────────────────────┼───────────────────────────────┤                                                                
 │ 1h+       │ InfluxDB                       │ Lakehouse nếu cần             │                                                                
 └───────────┴────────────────────────────────┴───────────────────────────────┘                                                                
                                                                                                                                               
 Lý do:                                                                                                                                        
                                                                                                                                               
 - Redis tốt cho hot/realtime, nhưng TTL ngắn và dễ gap.                                                                                       
 - InfluxDB tốt cho candle lịch sử, ổn định hơn.                                                                                               
 - 15m đang đẹp vì có thể đang được aggregate từ Influx/1m sạch.                                                                               
 - 1m/5m xấu vì có thể đang lấy Redis/gap-fill/ticker không chuẩn.                                                                             
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 2. Logic load historical candle                                                                                                               
                                                                                                                                               
 Khi user chọn timeframe:                                                                                                                      
                                                                                                                                               
 ```text                                                                                                                                       
   frontend request /klines?symbol=SOLUSDT&interval=1m                                                                                         
 ```                                                                                                                                           
                                                                                                                                               
 Backend xử lý:                                                                                                                                
                                                                                                                                               
 ```text                                                                                                                                       
   if interval == 1s:                                                                                                                          
       lấy Redis candle:1s                                                                                                                     
   elif interval == 1m:                                                                                                                        
       lấy cả Redis candle:1m và Influx 1m                                                                                                     
       chọn source đẹp hơn                                                                                                                     
   elif interval in 5m,15m,1h:                                                                                                                 
       lấy Influx aggregate từ 1m                                                                                                              
 ```                                                                                                                                           
                                                                                                                                               
 ### Tiêu chí “đẹp hơn” cho 1m                                                                                                                 
                                                                                                                                               
 So sánh Redis 1m vs Influx 1m:                                                                                                                
                                                                                                                                               
 Một source được xem là đẹp nếu:                                                                                                               
                                                                                                                                               
 1. Đủ số lượng candle.                                                                                                                        
 2. Timestamp liên tục đúng interval.                                                                                                          
 3. OHLC hợp lệ:                                                                                                                               
    ```text                                                                                                                                    
      high >= max(open, close)                                                                                                                 
      low <= min(open, close)                                                                                                                  
      high >= low                                                                                                                              
    ```                                                                                                                                        
 4. Không có quá nhiều candle volume = 0.                                                                                                      
 5. Candle cuối không quá stale.                                                                                                               
 6. Không có gap lớn.                                                                                                                          
                                                                                                                                               
 Pseudo:                                                                                                                                       
                                                                                                                                               
 ```python                                                                                                                                     
   score = 0                                                                                                                                   
                                                                                                                                               
   score += coverage_ratio * 40                                                                                                                
   score += continuity_ratio * 25                                                                                                              
   score += valid_ohlc_ratio * 20                                                                                                              
   score += nonzero_volume_ratio * 10                                                                                                          
   score += freshness_score * 5                                                                                                                
                                                                                                                                               
   choose source with higher score                                                                                                             
 ```                                                                                                                                           
                                                                                                                                               
 Nếu Redis 1m score thấp hơn InfluxDB thì dùng InfluxDB.                                                                                       
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 3. Logic realtime candle                                                                                                                      
                                                                                                                                               
 Realtime candle không nên lấy thẳng từ Redis candle close. Nó phải được tự form trên frontend hoặc backend từ ticker realtime.                
                                                                                                                                               
 ### Với timeframe 1m                                                                                                                          
                                                                                                                                               
 Giả sử đang ở cây nến 1m:                                                                                                                     
                                                                                                                                               
 ```text                                                                                                                                       
   previous closed candle:                                                                                                                     
   12:00:00                                                                                                                                    
   O=100                                                                                                                                       
   H=110                                                                                                                                       
   L=95                                                                                                                                        
   C=105                                                                                                                                       
                                                                                                                                               
   new realtime candle:                                                                                                                        
   12:01:00 → 12:01:59                                                                                                                         
 ```                                                                                                                                           
                                                                                                                                               
 Cây realtime phải bắt đầu như sau:                                                                                                            
                                                                                                                                               
 ```text                                                                                                                                       
   open = previous.close                                                                                                                       
   high = max(open, live_price)                                                                                                                
   low = min(open, live_price)                                                                                                                 
   close = live_price                                                                                                                          
   time = floor(now / 60s) * 60s                                                                                                               
 ```                                                                                                                                           
                                                                                                                                               
 Sau đó mỗi tick giá:                                                                                                                          
                                                                                                                                               
 ```text                                                                                                                                       
   close = live_price                                                                                                                          
   high = max(high, live_price)                                                                                                                
   low = min(low, live_price)                                                                                                                  
 ```                                                                                                                                           
                                                                                                                                               
 Khi hết timeframe:                                                                                                                            
                                                                                                                                               
 ```text                                                                                                                                       
   nến realtime hiện tại được đóng                                                                                                             
   append vào candle list                                                                                                                      
   tạo nến realtime mới:                                                                                                                       
       open = previous_closed.close                                                                                                            
       high = open                                                                                                                             
       low = open                                                                                                                              
       close = live_price                                                                                                                      
 ```                                                                                                                                           
                                                                                                                                               
 Đây là logic chuẩn để nến “nhảy nhót”, có râu, có body, và đóng đúng timeframe.                                                               
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 4. Không dùng candle 1s làm realtime price source                                                                                             
                                                                                                                                               
 Không nên làm:                                                                                                                                
                                                                                                                                               
 ```text                                                                                                                                       
   live price = candle:1s.close                                                                                                                
 ```                                                                                                                                           
                                                                                                                                               
 Vì với symbol ít giao dịch hoặc stream chậm, candle 1s có thể stale.                                                                          
                                                                                                                                               
 Nên làm:                                                                                                                                      
                                                                                                                                               
 ```text                                                                                                                                       
   live price = ticker:latest.price                                                                                                            
 ```                                                                                                                                           
                                                                                                                                               
 Candle realtime được form từ ticker.                                                                                                          
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 5. Kiến trúc frontend đề xuất                                                                                                                 
                                                                                                                                               
 Frontend nên có 2 layer data:                                                                                                                 
                                                                                                                                               
 ```text                                                                                                                                       
   closedCandles[]     // candles đã đóng, lấy từ Redis/Influx                                                                                 
   formingCandle       // candle đang chạy, build từ ticker realtime                                                                           
 ```                                                                                                                                           
                                                                                                                                               
 Ví dụ:                                                                                                                                        
                                                                                                                                               
 ```ts                                                                                                                                         
   type Candle = {                                                                                                                             
     time: number;                                                                                                                             
     open: number;                                                                                                                             
     high: number;                                                                                                                             
     low: number;                                                                                                                              
     close: number;                                                                                                                            
     volume?: number;                                                                                                                          
     finalized?: boolean;                                                                                                                      
   };                                                                                                                                          
                                                                                                                                               
   type RealtimeState = {                                                                                                                      
     timeframeSec: number;                                                                                                                     
     current: Candle | null;                                                                                                                   
     lastClosed: Candle | null;                                                                                                                
   };                                                                                                                                          
 ```                                                                                                                                           
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 6. Algorithm frontend chuẩn                                                                                                                   
                                                                                                                                               
 ### Khi load chart                                                                                                                            
                                                                                                                                               
 ```ts                                                                                                                                         
   const candles = await fetchCandles(symbol, timeframe);                                                                                      
                                                                                                                                               
   setSeriesData(candles);                                                                                                                     
                                                                                                                                               
   lastClosed = candles[candles.length - 1];                                                                                                   
                                                                                                                                               
   formingCandle = createFormingCandle(lastClosed, livePrice, timeframe);                                                                      
   series.update(formingCandle);                                                                                                               
 ```                                                                                                                                           
                                                                                                                                               
 ### Khi nhận ticker realtime                                                                                                                  
                                                                                                                                               
 ```ts                                                                                                                                         
   function onTicker(price, now) {                                                                                                             
     const bucketTime = floor(now / timeframeSec) * timeframeSec;                                                                              
                                                                                                                                               
     if (!formingCandle) {                                                                                                                     
       formingCandle = {                                                                                                                       
         time: bucketTime,                                                                                                                     
         open: lastClosed?.close ?? price,                                                                                                     
         high: price,                                                                                                                          
         low: price,                                                                                                                           
         close: price,                                                                                                                         
       };                                                                                                                                      
     }                                                                                                                                         
                                                                                                                                               
     // Nếu vẫn trong cùng timeframe                                                                                                           
     if (formingCandle.time === bucketTime) {                                                                                                  
       formingCandle.high = Math.max(formingCandle.high, price);                                                                               
       formingCandle.low = Math.min(formingCandle.low, price);                                                                                 
       formingCandle.close = price;                                                                                                            
       series.update(formingCandle);                                                                                                           
       return;                                                                                                                                 
     }                                                                                                                                         
                                                                                                                                               
     // Nếu sang timeframe mới                                                                                                                 
     lastClosed = formingCandle;                                                                                                               
     appendToCandles(lastClosed);                                                                                                              
                                                                                                                                               
     formingCandle = {                                                                                                                         
       time: bucketTime,                                                                                                                       
       open: lastClosed.close,                                                                                                                 
       high: Math.max(lastClosed.close, price),                                                                                                
       low: Math.min(lastClosed.close, price),                                                                                                 
       close: price,                                                                                                                           
     };                                                                                                                                        
                                                                                                                                               
     series.update(formingCandle);                                                                                                             
   }                                                                                                                                           
 ```                                                                                                                                           
                                                                                                                                               
 Điểm quan trọng:                                                                                                                              
                                                                                                                                               
 ```text                                                                                                                                       
   new candle open = previous candle close                                                                                                     
 ```                                                                                                                                           
                                                                                                                                               
 Không được để:                                                                                                                                
                                                                                                                                               
 ```text                                                                                                                                       
   new candle open = first ticker price                                                                                                        
 ```                                                                                                                                           
                                                                                                                                               
 vì như vậy chart sẽ bị gap giữa hai cây.                                                                                                      
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 7. Timeframe behavior                                                                                                                         
                                                                                                                                               
 ### 1s                                                                                                                                        
                                                                                                                                               
 - Mỗi giây tạo một cây.                                                                                                                       
 - Forming candle sống trong 1 giây.                                                                                                           
 - Nếu không có tick trong giây đó:                                                                                                            
     - hoặc không tạo candle,                                                                                                                  
     - hoặc tạo flat candle từ previous close nếu chart cần continuity.                                                                        
 - Nên ưu tiên không spam flat candle nếu symbol không có trade.                                                                               
                                                                                                                                               
 ### 1m                                                                                                                                        
                                                                                                                                               
 - Historical: lấy Redis/Influx 1m source đẹp hơn.                                                                                             
 - Realtime: build từ ticker.                                                                                                                  
 - Đóng nến mỗi phút.                                                                                                                          
 - Sau khi backend/Flink có candle chính thức, có thể reconcile lại cây vừa đóng.                                                              
                                                                                                                                               
 ### 5m                                                                                                                                        
                                                                                                                                               
 - Historical: lấy Influx aggregate 5m.                                                                                                        
 - Realtime: build từ ticker theo bucket 5 phút.                                                                                               
 - Không cần chờ 5 cây 1m mới vẽ; cây 5m hiện tại vẫn phải nhảy realtime.                                                                      
 - Khi hết 5 phút thì đóng.                                                                                                                    
                                                                                                                                               
 ### 15m                                                                                                                                       
                                                                                                                                               
 - Giữ logic hiện tại nếu đang đẹp.                                                                                                            
 - Nhưng vẫn nên dùng cùng realtime forming logic để thống nhất.                                                                               
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 8. Backend API nên sửa thế nào                                                                                                                
                                                                                                                                               
 ### /api/klines                                                                                                                               
                                                                                                                                               
 Thêm logic source selection:                                                                                                                  
                                                                                                                                               
 ```text                                                                                                                                       
   GET /api/klines?symbol=SOLUSDT&interval=1m&limit=500                                                                                        
 ```                                                                                                                                           
                                                                                                                                               
 Backend:                                                                                                                                      
                                                                                                                                               
 ```python                                                                                                                                     
   if interval == "1m":                                                                                                                        
       redis_rows = get_redis_1m()                                                                                                             
       influx_rows = get_influx_1m()                                                                                                           
       rows = choose_better(redis_rows, influx_rows)                                                                                           
   elif interval in ["5m", "15m", "1h"]:                                                                                                       
       rows = get_influx_aggregate(interval)                                                                                                   
   elif interval == "1s":                                                                                                                      
       rows = get_redis_1s()                                                                                                                   
 ```                                                                                                                                           
                                                                                                                                               
 Response nên thêm metadata debug:                                                                                                             
                                                                                                                                               
 ```json                                                                                                                                       
   {                                                                                                                                           
     "source": "influx",                                                                                                                       
     "quality_score": 92,                                                                                                                      
     "data": [...]                                                                                                                             
   }                                                                                                                                           
 ```                                                                                                                                           
                                                                                                                                               
 Frontend không nhất thiết hiển thị, nhưng giúp debug.                                                                                         
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 9. Backend WebSocket nên sửa thế nào                                                                                                          
                                                                                                                                               
 Nên có stream riêng cho ticker realtime:                                                                                                      
                                                                                                                                               
 ```text                                                                                                                                       
   /ws/ticker/{exchange}/{symbol}                                                                                                              
 ```                                                                                                                                           
                                                                                                                                               
 Payload:                                                                                                                                      
                                                                                                                                               
 ```json                                                                                                                                       
   {                                                                                                                                           
     "type": "ticker",                                                                                                                         
     "symbol": "SOLUSDT",                                                                                                                      
     "price": 69.44,                                                                                                                           
     "event_time": 1781911955743                                                                                                               
   }                                                                                                                                           
 ```                                                                                                                                           
                                                                                                                                               
 Frontend dùng stream này để update:                                                                                                           
                                                                                                                                               
 - live price                                                                                                                                  
 - forming candle                                                                                                                              
 - price line                                                                                                                                  
                                                                                                                                               
 Không dùng candle stream để update giá realtime.                                                                                              
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 10. Reconcile candle đã đóng                                                                                                                  
                                                                                                                                               
 Khi cây realtime vừa đóng, frontend có cây tự build từ ticker:                                                                                
                                                                                                                                               
 ```text                                                                                                                                       
   frontend closed candle                                                                                                                      
 ```                                                                                                                                           
                                                                                                                                               
 Sau vài giây, backend/Flink/Influx có candle chính thức:                                                                                      
                                                                                                                                               
 ```text                                                                                                                                       
   official candle                                                                                                                             
 ```                                                                                                                                           
                                                                                                                                               
 Ta nên reconcile:                                                                                                                             
                                                                                                                                               
 ```text                                                                                                                                       
   if official candle timestamp == lastClosed.time:                                                                                            
       replace lastClosed with official                                                                                                        
 ```                                                                                                                                           
                                                                                                                                               
 Như vậy:                                                                                                                                      
                                                                                                                                               
 - Realtime vẫn mượt.                                                                                                                          
 - Historical sau đó vẫn chuẩn theo data pipeline.                                                                                             
 - Nếu ticker-based forming có sai volume hoặc OHLC nhẹ, sẽ được sửa lại.                                                                      
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Kế hoạch triển khai                                                                                                                           
                                                                                                                                               
 Phase A — Fix data source cho historical candles                                                                                              
                                                                                                                                               
 Mục tiêu: 1m/5m/15m load đẹp.                                                                                                                 
                                                                                                                                               
 1. Sửa backend /api/klines.                                                                                                                   
 2. Với 1m: lấy Redis và Influx, score, chọn source tốt hơn.                                                                                   
 3. Với 5m/15m: ưu tiên Influx aggregate.                                                                                                      
 4. Thêm source và quality_score vào response để debug.                                                                                        
 5. Test BTC/ETH/SOL.                                                                                                                          
                                                                                                                                               
 Kết quả mong muốn:                                                                                                                            
                                                                                                                                               
 ```text                                                                                                                                       
   1m có dữ liệu đều                                                                                                                           
   5m có dữ liệu đều                                                                                                                           
   15m giữ đẹp như hiện tại                                                                                                                    
 ```                                                                                                                                           
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Phase B — Fix realtime forming candle                                                                                                         
                                                                                                                                               
 Mục tiêu: nến hiện tại nhảy realtime chuẩn.                                                                                                   
                                                                                                                                               
 1. Frontend tách:                                                                                                                             
     - closedCandles                                                                                                                           
     - formingCandle                                                                                                                           
     - liveTicker                                                                                                                              
 2. Subscribe ticker realtime.                                                                                                                 
 3. Build candle hiện tại từ ticker.                                                                                                           
 4. Open cây mới = close cây trước.                                                                                                            
 5. Update high/low/close theo ticker.                                                                                                         
 6. Đóng cây khi sang bucket mới.                                                                                                              
                                                                                                                                               
 Kết quả mong muốn:                                                                                                                            
                                                                                                                                               
 ```text                                                                                                                                       
   1m candle nhảy trong 60s                                                                                                                    
   đúng râu nến                                                                                                                                
   đúng body                                                                                                                                   
   không gap giữa hai cây                                                                                                                      
 ```                                                                                                                                           
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Phase C — Reconcile với official candle                                                                                                       
                                                                                                                                               
 Mục tiêu: sau khi Flink/Influx có candle chính thức, thay cây tự build bằng cây official.                                                     
                                                                                                                                               
 1. Khi nhận candle official có timestamp trùng lastClosed.time, replace.                                                                      
 2. Nếu official chưa có, giữ candle frontend tự build.                                                                                        
 3. Nếu sau 5-10s vẫn chưa có official, đánh dấu source = realtime_estimated.                                                                  
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Phase D — Debug panel nội bộ                                                                                                                  
                                                                                                                                               
 Thêm log/debug nhỏ:                                                                                                                           
                                                                                                                                               
 ```text                                                                                                                                       
   symbol: SOLUSDT                                                                                                                             
   timeframe: 1m                                                                                                                               
   historical source: influx                                                                                                                   
   quality score: 94                                                                                                                           
   live price source: ticker                                                                                                                   
   forming candle time: 12:01:00                                                                                                               
   last official candle: 12:00:00                                                                                                              
 ```                                                                                                                                           
                                                                                                                                               
 Cái này giúp biết ngay vì sao BTC đẹp mà SOL xấu.                                                                                             
                                                                                                                                               
 ────────────────────────────────────────────────────────────────────────────────                                                              
                                                                                                                                               
 Kết luận                                                                                                                                      
                                                                                                                                               
 Logic đúng nên là:                                                                                                                            
                                                                                                                                               
 ```text                                                                                                                                       
   Historical candles:                                                                                                                         
     lấy Redis/Influx, source nào đẹp hơn thì dùng                                                                                             
                                                                                                                                               
   Realtime candle:                                                                                                                            
     tự build từ ticker realtime                                                                                                               
                                                                                                                                               
   Candle close:                                                                                                                               
     khi hết timeframe thì đóng                                                                                                                
                                                                                                                                               
   Official candle:                                                                                                                            
     khi Flink/Influx ghi xong thì reconcile lại                                                                                               
 ```                                                                                                                                           
                                                                                                                                               
 Vấn đề hiện tại không phải chỉ data pipeline, mà là chart đang thiếu một lớp “forming candle” chuẩn. Ta cần sửa để candle hiện tại là candle  
 sống, không phải chỉ render lại candle close từ Redis.      
---

## 2026-06-19 Candlestick Rendering Execution Status

### ✅ Phase A — Historical 1m source selection implemented

- `backend/api/klines.py` now treats live `1m` specially.
- For live `1m`, backend fetches both:
  - Redis `candle:1m:{exchange}:{symbol}`
  - InfluxDB `interval == "1m"`
- Backend scores both sources by:
  - coverage
  - timestamp continuity
  - OHLC validity
  - non-zero volume ratio
  - freshness
- Backend returns the cleaner source so sparse/stale Redis candles no longer override cleaner Influx candles.

### ✅ Phase B — Realtime forming candle implemented

- `/stream/all` now includes `_ticker.price` and `_ticker.event_time`.
- `marketDataService.ts` separates ticker updates from candle updates via `onTicker`.
- `CandlestickChart.tsx` now builds the currently forming candle from ticker price:
  - bucket time = floor(event_time / timeframe) * timeframe
  - same bucket: update close/high/low
  - new bucket: open = previous close, then high/low/close follow live price
- This makes 1s/1m/5m/15m active candles move realtime instead of waiting for candle close data.

### ✅ Phase C — Official candle reconciliation implemented

- Candle WebSocket payloads are no longer used as the primary live price source.
- Official candle payload with same timestamp reconciles the current candle while preserving live close/high/low.
- Older official candle payload replaces the matching historical candle in local state.

### Validation

```bash
cd frontend && npm run typecheck
cd frontend && npm run build
PYTHONPYCACHEPREFIX=/tmp/pycache-check python3 -m py_compile backend/api/klines.py backend/api/websocket.py
```

All validation commands passed.

### Remaining follow-up

- Deploy/restart backend and frontend services so the new WebSocket payload and chart logic are active in production.
- After deployment, visually verify BTC/ETH/SOL on 1s, 1m, 5m, and 15m.
- Optional next improvement: expose selected candle source/quality score in `/api/klines` response metadata for debug UI.

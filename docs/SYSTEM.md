<!-- ====================================================================== -->
<!-- LMView — SYSTEM.md (Phiên bản Tiếng Việt)                             -->
<!-- Tài liệu kiến trúc hệ thống toàn diện. Phiên bản 0.25.52.            -->
<!-- Được viết lại với giải thích chi tiết cho sinh viên năm 1.            -->
<!--                                                                        -->
<!-- Cách đọc tài liệu này:                                                -->
<!-- 1. Đọc Phần 1 (Nền tảng) trước — hiểu LMView là gì                    -->
<!-- 2. Đọc Phần 2 (Chi tiết từng dịch vụ) — hiểu từng service             -->
<!-- 3. Đọc Phần 3 (Tầng tốc độ) — hiểu dữ liệu chạy nhanh thế nào        -->
<!-- 4. Đọc Phần 4 (Tầng phục vụ) — hiểu backend đẩy dữ liệu ra sao       -->
<!-- 5. Đọc Phần 5 (Frontend) — hiểu trình duyệt vẽ biểu đồ                -->
<!-- 6. Đọc Phần 6 (Lakehouse + AI + Triển khai) — hiểu phần "nặng"        -->
<!-- 7. Đọc Phần 7 (Vận hành) — hiểu cách sửa lỗi                          -->
<!-- 8. Đọc Phần 8 (Deep dive) — hiểu sâu luồng ticker 8 shards            -->
<!--                                                                        -->
<!-- Tác giả: AI agents + con người đóng góp                                -->
<!-- Ngày cập nhật: 2026-06-20                                             -->
<!-- ====================================================================== -->

# LMView — Tài Liệu Kiến Trúc Hệ Thống

> **Lưu ý cho sinh viên năm 1:** Tài liệu này dày vì hệ thống lớn. Đừng cố đọc hết trong 1 lần. Hãy đọc theo thứ tự Phần 1 → Phần 8. Mỗi lần đọc 1 phần rồi nghỉ. Mỗi đoạn code đều có comment tiếng Việt giải thích dòng-by-dòng.

---

## Mục Lục

| Phần | Nội dung | Số dòng (ước tính) |
|---|---|---|
| **1** | Nền tảng: LMView là gì, thiết kế, kiến trúc Lambda, bản đồ repo | ~700 |
| **2** | Chi tiết từng dịch vụ: Kafka, Flink, Redis, Postgres, FastAPI, Nginx, ... | ~1500 |
| **3** | Tầng tốc độ: code đầy đủ `src/ticker_ws/` (5 files) | ~1100 |
| **4** | Tầng phục vụ: code đầy đủ `backend/api/websocket.py` | ~1300 |
| **5** | Frontend: code đầy đủ `marketDataService.ts` + sửa lỗi Blob | ~900 |
| **6** | Lakehouse + PostgreSQL + AI + Docker Swarm + Prometheus | ~1000 |
| **7** | Vận hành: biến môi trường, cổng, log, sự cố, runbook, lịch sử bug | ~500 |
| **8** | Deep dive: kiến trúc 8 shards của `binance-ticker-ws` | ~800 |

**Tổng:** ~7800 dòng tài liệu + code.

---

# Phần 1 — Nền Tảng (Foundations)

Phần này dành cho người mới. Nếu bạn chưa từng nghe "Kafka" hay "WebSocket", hãy đọc chậm.

## 1. LMView Là Gì?

### Định nghĩa đơn giản

**LMView** là một nền tảng web (chạy trên trình duyệt) để xem giá tiền mã hóa (cryptocurrency) theo thời gian thực. Nó giống như TradingView nhưng tự xây.

### Nó làm được gì?

- **Biểu đồ nến (candlestick chart):** Vẽ giá Bitcoin, Ethereum, ... dưới dạng nến Nhật (mỗi nến = 1 phút, 5 phút, 1 giờ, ...)
- **Cập nhật real-time:** Giá trên biểu đồ thay đổi LIÊN TỤC theo từng giây mà không cần tải lại trang (F5)
- **Sổ lệnh (order book):** Hiển thị danh sách người mua/bán đang chờ
- **Lịch sử giao dịch:** Xem các lệnh vừa khớp
- **AI trợ lý (AI Helper):** Hỏi "Tại sao BTC giảm hôm nay?" → AI trả lời bằng tiếng Việt/Anh
- **Hơn 600 cặp tiền:** BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, ... (tất cả USDT pairs của Binance)

### Demo

- URL: `https://lmview.duckdns.org`
- Tài khoản: cần đăng ký (có sẵn user admin)

### So sánh với TradingView

| Tính năng | TradingView | LMView |
|---|---|---|
| Biểu đồ nến | ✅ | ✅ |
| Cập nhật real-time | ✅ (trả phí cho <1s) | ✅ (miễn phí, <300ms) |
| Dữ liệu Binance | ✅ | ✅ |
| Dữ liệu OKX, Bybit | ✅ | ❌ (chỉ Binance) |
| AI trợ lý | ❌ | ✅ |
| Mã nguồn mở | ❌ | ✅ |
| Chi phí | $15-60/tháng | $5/tháng (server AWS) |

## 2. Triết Lý Thiết Kế (Design Philosophy)

### 5 nguyên tắc cốt lõi

#### Nguyên tắc 1: Tốc độ là tính năng quan trọng nhất

- **Mục tiêu:** Từ lúc Binance khớp lệnh → pixel trên màn hình bạn < 500ms
- **Tại sao:** Trader cần thấy giá ngay. Chậm 1 giây = lỡ cơ hội hoặc mất tiền
- **Thực hiện:**
  - WebSocket thay vì HTTP polling (HTTP polling = hỏi "giá bao nhiêu?" mỗi 1s; WebSocket = server tự đẩy giá mới về)
  - Redis trong bộ nhớ RAM (truy cập < 1ms) thay vì truy vấn database
  - Batch ghi (nhiều lệnh gom 1 lần gửi) để giảm số round-trip

#### Nguyên tắc 2: Không bao giờ mất dữ liệu (Durability)

- **Mục tiêu:** Dù server chết, dữ liệu lịch sử vẫn còn
- **Tại sao:** Trader cần xem lại chart ngày hôm qua, tháng trước
- **Thực hiện:**
  - Kafka lưu toàn bộ event (giống "băng ghi âm" cuộc gọi)
  - Iceberg trên MinIO (giống USB cứng) cho dữ liệu > 1 năm
  - InfluxDB (giống "sổ tay ghi chép") cho time-series 90 ngày

#### Nguyên tắc 3: Chạy được trên hardware rẻ

- **Mục tiêu:** $5/tháng AWS, không cần GPU
- **Tại sao:** Sinh viên, indie developer dùng được
- **Thực hiện:**
  - 2 node EC2 thường (không phải GPU instance)
  - Docker Swarm (miễn phí, đơn giản hơn Kubernetes)
  - Single-binary Loki, single-binary Trino (thay vì cluster)

#### Nguyên tắc 4: Mã nguồn mở, dễ hiểu

- **Mục tiêu:** 1 sinh viên năm 3 có thể đọc hiểu codebase
- **Tại sao:** Tài liệu này tồn tại 😅
- **Thực hiện:**
  - Comment tiếng Việt dày đặc trong code
  - Mỗi service có 1 file `README.md` riêng
  - Tách biệt rõ: backend / frontend / data-pipeline

#### Nguyên tắc 5: An toàn là bắt buộc

- **Mục tiêu:** Không bao giờ để lộ mật khẩu user, không bị hack
- **Tại sao:** Có auth, có payment, có dữ liệu cá nhân
- **Thực hiện:**
  - JWT token (hết hạn sau 24h)
  - Password hash bằng bcrypt
  - Secrets trong `.env`, không commit lên Git
  - HTTPS qua Let's Encrypt (Let's Encrypt = tổ chức phát hành chứng chỉ SSL miễn phí)

## 3. Kiến Trúc Lambda: Bức Tranh Toàn Cảnh

### Lambda Architecture là gì?

Đây là một mô hình kinh điển trong xử lý dữ liệu lớn, gồm 3 tầng chạy song song:

```
                    Dữ liệu thô (giá BTC, ETH, ...)
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
    ┌──────────────┐            ┌──────────────┐
    │ SPEED LAYER  │            │ BATCH LAYER  │
    │ (Tầng tốc độ)│            │ (Tầng theo lô)│
    │              │            │              │
    │ - Xử lý nhanh│            │ - Xử lý chậm│
    │ - Real-time  │            │ - Hàng giờ  │
    │ - Từng giây  │            │ - Từng giờ   │
    └──────┬───────┘            └──────┬───────┘
           │                           │
           │      ┌──────────────┐     │
           └─────►│SERVING LAYER │◄────┘
                  │(Tầng phục vụ)│
                  │              │
                  │ - Gộp 2 tầng│
                  │ - Trả về    │
                  │   cho user  │
                  └──────┬───────┘
                         │
                         ▼
                    [Browser]
```

### 3 tầng trong LMView

| Tầng | Nhiệm vụ | Công nghệ | Độ trễ |
|---|---|---|---|
| **Speed** | Nhận giá từ Binance, đẩy vào Redis trong < 100ms | `binance-ticker-ws` + Redis | 50-100ms |
| **Batch** | Tổng hợp dữ liệu theo giờ/ngày, lưu trữ dài hạn | Spark + Iceberg + Trino | vài phút - vài giờ |
| **Serving** | Đọc từ cả 2 tầng, trả về cho browser qua WebSocket | FastAPI + WebSocket | 100-300ms |

### Tầng Speed (Tốc độ) — chi tiết

```
[Binance WSS]
   │ ~50ms (network)
   ▼
[binance-ticker-ws: 8 shards]    ← 8 kết nối WebSocket song song
   │ parse + buffer
   ▼
[Redis Sentinel cluster]           ← RAM database, < 1ms read
   │
   ├─► FastAPI đọc liên tục
   │
   └─► [Browser qua WebSocket]     ← 200-500ms end-to-end
```

### Tầng Batch (Theo lô) — chi tiết

```
[Binance WSS]
   │
   ▼
[Kafka]                            ← "băng ghi âm", lưu 7 ngày
   │
   ▼
[Spark Structured Streaming]        ← xử lý mỗi 30s
   │
   ├─► Bronze (raw)                ← giữ nguyên, ít xử lý
   ├─► Silver (cleaned + dedup)    ← làm sạch, loại trùng
   └─► Gold (aggregated)           ← tổng hợp cho API
   │
   ▼
[Iceberg trên MinIO]                ← "USB cứng" dữ liệu lạnh
   │
   ▼
[Trino SQL engine]                  ← truy vấn giống MySQL
   │
   ▼
[FastAPI /api/market/overview]      ← endpoint tổng hợp
```

### Tầng Serving (Phục vụ) — chi tiết

```
[Browser] gửi request: "Cho tôi 1m candles BTCUSDT"
   │
   ▼ HTTPS + WebSocket
[Cloudflare/Let's Encrypt]
   │
   ▼
[Nginx reverse proxy]               ← "bảo vệ cổng", phân luồng
   │
   ▼
[FastAPI]
   │
   ├─► Đọc candles mới nhất từ Redis
   ├─► Đọc candles cũ từ InfluxDB
   ├─► Đọc aggregated từ Trino/Iceberg
   │
   └─► Gộp + trả về
   │
   ▼
[Browser: parse JSON + vẽ chart]
```

### Tại sao dùng Lambda thay vì 1 tầng duy nhất?

| Nếu chỉ 1 tầng | Vấn đề | Lambda giải quyết |
|---|---|---|
| Real-time only (Redis) | Mất dữ liệu khi restart | Batch layer backup |
| Batch only (Spark) | Chậm 5 phút, không real-time | Speed layer real-time |
| Database truyền thống (Postgres) | Chậm khi truy vấn lớn | Redis cho hot data, Iceberg cho cold |

## 4. Bản Đồ Repository

### Cấu trúc thư mục gốc

```
/mnt/efs/LMView/                       ← root project
├── backend/                           ← Python FastAPI (phục vụ API)
│   ├── api/                           ← các route HTTP/WS
│   ├── services/                      ← business logic
│   ├── models/                        ← Pydantic schemas
│   ├── core/                          ← config, DB clients, auth
│   ├── migrations/                    ← file SQL migration
│   ├── app.py                         ← entry point FastAPI
│   └── Dockerfile                     ← image build
│
├── src/                               ← Python data pipeline (Kafka → Flink → Redis)
│   ├── ticker_ws/                     ← binance-ticker-ws service (Phase 4)
│   ├── processing/                    ← Flink job
│   ├── producer/                      ← legacy producer (ticker path đã chết)
│   ├── lakehouse/                     ← Spark + Iceberg
│   ├── exchanges/                     ← base class cho mỗi sàn
│   ├── common/                        ← config, utilities
│   └── ml/                            ← AI/ML (tương lai)
│
├── frontend/                          ← React 19 + TypeScript
│   ├── src/
│   │   ├── features/                  ← mỗi tính năng 1 thư mục
│   │   │   ├── chart/                 ← biểu đồ nến
│   │   │   ├── ai/                    ← AI assistant
│   │   │   ├── orderbook/             ← sổ lệnh
│   │   │   ├── trades/                ← lịch sử giao dịch
│   │   │   └── settings/              ← cài đặt
│   │   ├── components/                ← shared UI components
│   │   ├── services/                  ← gọi API (KHÔNG gọi trực tiếp từ component)
│   │   ├── constants/                 ← hằng số (interval, symbol, ...)
│   │   ├── types/                     ← TypeScript types
│   │   ├── pages/                     ← các trang (Route-level)
│   │   ├── data/mock/                 ← mock data (khi VITE_DATA_SOURCE=mock)
│   │   └── App.tsx                    ← root component
│   ├── public/                        ← static assets
│   ├── package.json                   ← npm dependencies
│   └── vite.config.ts                 ← Vite build config
│
├── docker/                            ← Dockerfiles cho từng service
│   ├── fastapi/
│   ├── flink/
│   ├── nginx/
│   ├── ticker-ws/
│   └── ...
│
├── docker-compose.yml                 ← runtime source of truth
├── docker-compose.swarm.yml           ← Swarm-specific extensions
│
├── orchestration/                     ← Dagster assets (data orchestration)
│
├── scripts/                           ← shell scripts cho deploy/ops
│
├── schemas/                           ← Avro schemas cho Kafka
│
├── tests/                             ← pytest unit/integration tests
│
├── docs/                              ← tài liệu
│   ├── SYSTEM.md                      ← file này
│   ├── CHANGELOG.md                   ← lịch sử thay đổi
│   ├── LATENCY_OPTIMIZATION_PLAN.md   ← kế hoạch giảm độ trễ
│   ├── system/                        ← tài liệu chi tiết theo module
│   └── ...
│
├── Makefile                           ← common commands (make test, make deploy, ...)
├── AGENTS.md                          ← rules cho AI agents
├── README.md                          ← user-facing overview
└── VERSION                            ← single source of truth cho version
```

### Quy tắc đặt tên

| Loại file | Convention | Ví dụ |
|---|---|---|
| Python file/module | snake_case | `candle_service.py`, `klines.py` |
| Python class | PascalCase | `TickerShard`, `TickerRedisWriter` |
| Python function | snake_case | `parse_ticker`, `redis_key` |
| Python constant | UPPER_SNAKE | `RECONNECT_BASE_MS`, `REDIS_KEY_TTL_S` |
| TypeScript file | camelCase | `marketDataService.ts`, `candleService.ts` |
| TypeScript component | PascalCase | `CandlestickChart.tsx`, `SettingsModal.tsx` |
| TypeScript type/interface | PascalCase | `StreamTickerPayload`, `Candle` |
| TypeScript function | camelCase | `mapRawToCandle`, `parseWsData` |
| Directory | kebab-case (cho service) | `binance-ticker-ws/` |
| Environment variable | UPPER_SNAKE | `REDIS_SENTINELS`, `TICKER_WS_SHARDS` |

### Tổng số dòng code (ước tính)

| Phần | Dòng code | Ngôn ngữ |
|---|---|---|
| Backend | ~8000 | Python |
| Data pipeline | ~5000 | Python |
| Frontend | ~15000 | TypeScript + TSX |
| Tests | ~3000 | Python + TS |
| Docs | ~15000 | Markdown |
| **Tổng** | **~46000** | mix |

## 5. Network Topology và DNS

### Topology (cách các máy nối với nhau)

LMView chạy trên 2 máy AWS EC2 (máy ảo trên cloud Amazon):

```
┌─────────────────────────────────────────────────────────────┐
│ AWS Region: us-east-1 (Virginia, Mỹ)                        │
│                                                             │
│  ┌────────────────────────────┐  ┌─────────────────────┐  │
│  │ Manager node               │  │ Worker node         │  │
│  │ IP: 172.31.21.135          │  │ IP: 172.31.9.171    │  │
│  │ Tên: ip-172-31-21-135      │  │ Tên: ip-172-31-9-171│  │
│  │                            │  │                     │  │
│  │ CPU: 8 vCPU                │  │ CPU: 4 vCPU         │  │
│  │ RAM: 32 GB                 │  │ RAM: 16 GB          │  │
│  │ Disk: 96 GB                │  │ Disk: 80 GB         │  │
│  │                            │  │                     │  │
│  │ Chạy:                      │  │ Chạy:               │  │
│  │ - Nginx (port 80, 443)     │  │ - Flink TaskManager │  │
│  │ - FastAPI                  │  │ - Flink TaskManager │  │
│  │ - binance-ticker-ws        │  │ - Spark Worker      │  │
│  │ - Redis Master + Replicas │  │                     │  │
│  │ - Redis Sentinels (×3)     │  │                     │  │
│  │ - Postgres                 │  │                     │  │
│  │ - InfluxDB                 │  │                     │  │
│  │ - MinIO                    │  │                     │  │
│  │ - Kafka (×3)               │  │                     │  │
│  │ - Zookeeper                │  │                     │  │
│  │ - Flink JobManager         │  │                     │  │
│  │ - Spark Master             │  │                     │  │
│  │ - Dagster (optional)       │  │                     │  │
│  │ - Prometheus, Grafana, Loki│  │                     │  │
│  │ - Certbot (auto-renew SSL) │  │                     │  │
│  └────────────────────────────┘  └─────────────────────┘  │
│                                                             │
│  Shared storage: /mnt/efs/LMView (EFS = Elastic File System)│
│  Domain: lmview.duckdns.org                                  │
│  TLS: Let's Encrypt (auto-renew mỗi 60 ngày)               │
└─────────────────────────────────────────────────────────────┘
```

**EFS là gì?** EFS = Elastic File System. Nó là 1 ổ cứng mạng chia sẻ giữa nhiều máy EC2. Cả 2 node cùng đọc/ghi vào `/mnt/efs/LMView` được. Giống như Google Drive cho server.

**DuckDNS là gì?** DuckDNS = dịch vụ DNS động miễn phí. Cho phép trỏ tên miền `lmview.duckdns.org` tới IP public của máy AWS. Cứ 5 phút DuckDNS check IP, nếu đổi thì tự cập nhật.

### DNS bên trong Docker Swarm

Khi các container nói chuyện với nhau, chúng dùng tên service:

```
container "fastapi" gọi redis → DNS resolve "redis-master" → IP của container "redis-master"
```

Docker Swarm có DNS server riêng (`127.0.0.11` trong mỗi container). Nó round-robin qua các replicas.

**Round-robin là gì?** Cứ mỗi lần truy vấn DNS, trả về IP khác nhau trong danh sách. Ví dụ: redis-master có 2 replicas (master + replica), DNS trả IP master 50% và IP replica 50%.

**Vấn đề của round-robin với Redis Master:** Nếu Sentinels chưa phát hiện failover, DNS vẫn trả về cả master lẫn replica. Code ghi vào replica → lỗi `READONLY`. **Fix:** dùng Sentinel `master_for("mymaster")` thay vì DNS trực tiếp.

### Cổng (ports) quan trọng

| Port | Service | Truy cập từ đâu |
|---|---|---|
| 80 | Nginx (HTTP) | Internet (redirect → 443) |
| 443 | Nginx (HTTPS) | Internet |
| 8000 | FastAPI | Internal only |
| 8081 | Flink Web UI | Internal only |
| 9100 | binance-ticker-ws metrics | Internal only |
| 5432 | Postgres | Internal only |
| 6379 | Redis | Internal only (dùng Sentinel) |
| 8086 | InfluxDB | Internal only |
| 9000 | MinIO API | Internal only |
| 9001 | MinIO Console | Internal only |

**Internal only** = chỉ truy cập từ trong Docker network. Từ browser, bạn chỉ thấy port 80/443.

## 6. Bảng Thuật Ngữ (Glossary)

| Thuật ngữ | Tiếng Việt | Giải thích đơn giản |
|---|---|---|
| **Kafka** | Hàng đợi phân tán | Giống "băng ghi âm" — lưu mọi sự kiện, nhiều người có thể đọc lại |
| **Flink** | Bộ xử lý luồng | Xử lý dữ liệu theo dòng chảy (real-time), giống "công nhân lắp ráp" |
| **Redis** | Database trong RAM | Cực nhanh, dùng làm cache, lưu giá mới nhất |
| **PostgreSQL** | Database quan hệ | Lưu user, settings, chat history — dữ liệu có cấu trúc |
| **InfluxDB** | Database time-series | Tối ưu cho dữ liệu theo thời gian (giá, sensor) |
| **Iceberg** | Định dạng bảng cho data lake | Giống "Parquet++" — có transaction, schema evolution |
| **Trino** | Engine SQL phân tán | Truy vấn SQL trên data lake (Iceberg, Hive, ...) |
| **Spark** | Bộ xử lý batch lớn | Xử lý dữ liệu hàng GB-TB, chạy batch hàng giờ |
| **WebSocket** | Giao thức 2 chiều | Server chủ động đẩy dữ liệu về client (không cần hỏi) |
| **JWT** | Token xác thực | Chuỗi mã hóa chứa user info, hết hạn sau 24h |
| **Docker** | Nền tảng đóng gói | Đóng cả app + thư viện vào "container" chạy mọi nơi |
| **Docker Swarm** | Orchestrator Docker | Quản lý nhiều container, tự restart khi chết |
| **EC2** | Máy ảo AWS | Thuê máy tính trên cloud Amazon |
| **EFS** | Ổ cứng mạng AWS | Nhiều máy EC2 cùng đọc/ghi |
| **Nginx** | Reverse proxy | "Bảo vệ cổng", phân luồng HTTP request |
| **FastAPI** | Framework Python | Viết API web bằng Python, có type hints |
| **React** | Framework JavaScript | Viết giao diện web, chia thành component |
| **TypeScript** | JavaScript + types | JS có khai báo kiểu, bắt lỗi sớm |
| **Candlestick** | Biểu đồ nến | Mỗi nến = open, high, low, close trong 1 khoảng thời gian |
| **Hammer** | Pattern hình nến | "Búa" — dấu hiệu đảo chiều tăng |
| **Binance** | Sàn tiền mã hóa | Sàn lớn nhất thế giới, cung cấp API giá |
| **USDT** | Tether (stablecoin) | 1 USDT ≈ 1 USD, dùng làm "tiền tệ trung gian" |
| **Sentinel** | Bộ giám sát Redis | Tự động phát hiện master chết, bầu master mới |
| **HMAC** | Hash-based MAC | Mã xác thực request API, dùng cho Binance API |
| **Avro** | Định dạng dữ liệu | Schema + binary, nhỏ hơn JSON |
| **RTT** | Round-trip time | Thời gian gửi đi + nhận lại 1 gói tin |
| **p50 / p95 / p99** | Percentile latency | 50% / 95% / 99% request có latency thấp hơn giá trị này |
| **OOM** | Out of memory | Hết RAM, process bị kill |
| **EFS** | Elastic File System | Ổ cứng mạng AWS, nhiều máy cùng mount |
| **DDNS** | Dynamic DNS | DNS tự cập nhật khi IP thay đổi (DuckDNS) |
| **JWT** | JSON Web Token | Token xác thực, ký bằng secret key |
| **CSP** | Content Security Policy | HTTP header chống XSS attack |
| **XSS** | Cross-site scripting | Hacker chèn JS độc vào trang web |
| **CSRF** | Cross-site request forgery | Hacker gửi request giả mạo từ trang khác |

<!-- Kết thúc Phần 1. Tiếp theo: Phần 2 — Chi tiết từng dịch vụ -->
# Phần 2 — Chi Tiết Từng Dịch Vụ (Services Deep Dive)

> **Giải thích cho sinh viên:** Phần này liệt kê TỪNG service (mỗi service = 1 container Docker). Đọc lướt để biết service nào làm gì, không cần nhớ chi tiết. Khi cần debug service nào thì quay lại đọc kỹ phần đó.

**Mục lục Phần 2:**

| § | Service | Độ quan trọng |
|---|---|---|
| 7 | Tổng quan các service | ⭐⭐⭐ |
| 8 | Zookeeper | ⭐ |
| 9 | Kafka (3 brokers) | ⭐⭐ |
| 10 | Schema Registry (Apicurio) | ⭐ |
| 11 | **`binance-ticker-ws`** — service quan trọng nhất | ⭐⭐⭐⭐⭐ |
| 12 | Producer (legacy, đã chết) | ⭐ |
| 13 | Flink JobManager + TaskManager | ⭐⭐ |
| 14 | Redis Sentinel Cluster | ⭐⭐ |
| 15 | InfluxDB | ⭐⭐ |
| 16 | Spark + Iceberg + MinIO + Trino | ⭐⭐ |
| 17 | PostgreSQL | ⭐⭐ |
| 18 | FastAPI (Backend serving layer) | ⭐⭐⭐⭐⭐ |
| 19 | Nginx Reverse Proxy | ⭐⭐⭐ |
| 20 | React 19 Frontend | ⭐⭐⭐⭐ |
| 21 | Observability (Prometheus, Grafana, Loki) | ⭐ |

## 7. Tổng Quan Các Service

### Tại sao nhiều service thế?

Microservices! Thay vì 1 chương trình khổng lồ làm tất cả, tách thành nhiều service nhỏ, mỗi service 1 việc.

**Ưu điểm:**
- Service này chết, service khác vẫn chạy
- Scale riêng từng service (cần nhiều Redis nhưng ít Kafka → tăng Redis)
- Mỗi service dùng ngôn ngữ phù hợp (Kafka = Java, FastAPI = Python, Frontend = TypeScript)

**Nhược điểm:**
- Phức tạp hơn 1 monolith
- Network giữa các service có thể chậm
- Debug khó hơn (1 request đi qua 5 service)

### Bảng tóm tắt 21 service

| Service | Ngôn ngữ | RAM | Vai trò |
|---|---|---|---|
| **zookeeper** | Java | 512 MB | Quản lý Kafka brokers (bầu leader) |
| **kafka-1, kafka-2, kafka-3** | Java + Scala | 1 GB × 3 | Message queue (băng ghi âm) |
| **schema-registry** | Java | 256 MB | Lưu schema Avro cho Kafka |
| **binance-ticker-ws** | Python | 256 MB | Nhận giá Binance real-time (Phase 4) |
| **producer** (legacy) | Python | 1 GB | Đa mục đích (đã chết do OOM) |
| **flink-jobmanager** | Java | 1 GB | Quản lý Flink jobs |
| **flink-taskmanager × 2** | Java | 2 GB × 2 | Chạy Flink tasks (worker) |
| **redis-master** | C | 2 GB | Redis primary, ghi/đọc |
| **redis-replica-1, 2** | C | 1 GB × 2 | Redis replica (chỉ đọc) |
| **redis-sentinel-1, 2, 3** | C | 256 MB × 3 | Giám sát Redis, tự động failover |
| **influxdb** | Go | 2 GB | Time-series database (90 ngày candles) |
| **spark-master** | Scala | 1 GB | Quản lý Spark jobs |
| **spark-worker × 2** | Scala | 2 GB × 2 | Chạy Spark tasks |
| **minio** | Go | 1 GB | Object storage (S3-compatible) cho Iceberg |
| **trino** | Java | 2 GB | SQL query engine trên Iceberg |
| **postgres** | C | 1 GB | Database chính (user, settings, AI) |
| **fastapi-prod** | Python | 1 GB | Backend API + WebSocket server |
| **nginx-prod** | C | 256 MB | Reverse proxy, SSL termination |
| **dagster-webserver** | Python | 512 MB | Data orchestration UI (optional) |
| **dagster-daemon** | Python | 256 MB | Dagster scheduler (optional) |
| **prometheus** | Go | 1 GB | Thu thập metrics |
| **grafana** | Go | 512 MB | Vẽ dashboard từ Prometheus |
| **loki** | Go | 512 MB | Aggregate logs |
| **promtail** | Go | 128 MB | Gửi Docker logs → Loki |
| **certbot** | Python | 128 MB | Auto-renew Let's Encrypt SSL |

**Tổng:** ~30 containers, ~24 GB RAM sử dụng.

## 8. Zookeeper

### Nó là gì?

Zookeeper = dịch vụ quản lý cấu hình phân tán. Trong LMView, nó làm 1 việc duy nhất: **quản lý Kafka brokers**.

### Vì sao Kafka cần Zookeeper?

Kafka cluster có 3 brokers. Cần biết:
- Broker nào là "leader" cho partition nào
- Broker nào đang sống, broker nào chết
- Topic nào có bao nhiêu partition

Zookeeper giữ thông tin này. Nếu Zookeeper chết → Kafka không biết ai là leader → ngưng.

### Trong LMView

```yaml
# docker-compose.yml (rút gọn)
zookeeper:
  image: confluentinc/cp-zookeeper:7.4.0
  environment:
    ZOOKEEPER_CLIENT_PORT: 2181
    ZOOKEEPER_TICK_TIME: 2000
  mem_limit: 512m
```

### Khi nào Zookeeper sẽ "nghỉ hưu"?

Kafka 3.3+ hỗ trợ chạy KHÔNG cần Zookeeper (gọi là KRaft mode). Trong tương lai, LMView có thể bỏ Zookeeper.

## 9. Kafka Brokers (×3)

### Kafka là gì? (Giải thích cho người mới)

Kafka = **message queue phân tán**, lưu trữ stream of events.

**Ví dụ thực tế:**

Bạn mở quán cafe. Mỗi khi khách order, bạn ghi 1 tờ giấy: "Khách #5 order Cappuccino lúc 10:30". Tờ giấy xếp vào hộp theo thứ tự. Đầu bếp lấy tờ giấy từ đầu hộp, làm xong thì bỏ qua.

Kafka cũng vậy:
- **Producer** (khách) ghi message
- **Broker** (hộp giấy) lưu message theo thứ tự
- **Consumer** (đầu bếp) đọc message theo thứ tự

**Khác với database:** Kafka KHÔNG cho phép sửa message cũ. Chỉ append (thêm vào cuối) và consume (đọc từ đầu). Sau khi consume, message vẫn còn (tuỳ config retention).

### Trong LMView

3 brokers (kafka-1, kafka-2, kafka-3) chạy song song, replicate data lẫn nhau. Nếu 1 broker chết, 2 còn lại vẫn serve.

```yaml
kafka-1:
  image: confluentinc/cp-kafka:7.4.0
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_LISTENERS: INTERNAL://kafka-1:29092,EXTERNAL://:19092
    KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka-1:29092,EXTERNAL://localhost:19092
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
    KAFKA_DEFAULT_REPLICATION_FACTOR: 3
    KAFKA_NUM_PARTITIONS: 12
```

**Giải thích các dòng:**
- `BROKER_ID: 1` — Mỗi broker có ID riêng (1, 2, 3)
- `ZOOKEEPER_CONNECT` — Zookeeper để biết cluster state
- `LISTENERS` — 2 listener: INTERNAL (cho container khác) và EXTERNAL (cho máy host)
- `OFFSETS_TOPIC_REPLICATION_FACTOR: 3` — Topic lưu "consumer đã đọc đến đâu" replicate 3 lần
- `DEFAULT_REPLICATION_FACTOR: 3` — Mặc định mỗi message replicate 3 lần (1 leader + 2 followers)
- `NUM_PARTITIONS: 12` — Mỗi topic mặc định có 12 partition (chia nhỏ để parallel consume)

### Topics chính

| Topic | Partition | Replication | Producer | Consumer |
|---|---|---|---|---|
| `crypto_ticker` | 12 | 3 | binance-ticker-ws (legacy: producer) | Flink, FastAPI |
| `crypto_klines` | 12 | 3 | producer | Flink |
| `crypto_depth` | 6 | 3 | producer | Flink |
| `crypto_trades` | 6 | 3 | producer | Flink |

### Partition là gì?

Một topic được chia thành N phần (partition), mỗi phần là 1 chuỗi message độc lập. Consumer đọc từng partition song song.

```
Topic "crypto_ticker" với 12 partitions:
  Partition 0:  [msg1, msg2, msg3, ...]
  Partition 1:  [msg100, msg101, ...]
  ...
  Partition 11: [msgX, msgY, ...]

Consumer group "flink":
  Worker 0 đọc partition 0
  Worker 1 đọc partition 1
  ...
  Worker 11 đọc partition 11
  → 12 worker parallel, mỗi worker 1 partition
```

**Key cho partition:** Trong LMView, message được route theo `(exchange, symbol)`. Tất cả message của BTCUSDT đi vào cùng partition → consumer luôn đọc theo thứ tự.

### Vì sao dùng Kafka thay vì gọi trực tiếp?

- **Buffer:** Nếu Flink chết, Kafka vẫn nhận message, Flink đọc lại khi sống lại
- **Replay:** Có thể đọc lại từ đầu để test / backfill
- **Fan-out:** Nhiều consumer đọc cùng 1 message (1 cho Flink, 1 cho archive, 1 cho test)
- **Throughput:** 100K+ message/s per partition

### Kafka trong LMView hiện tại

**⚠️ Quan trọng:** Kafka hiện đang gần như KHÔNG được sử dụng. Producer (service tạo message) đã chết do OOM + 403. Service thay thế `binance-ticker-ws` ghi thẳng vào Redis, bypass Kafka.

Kafka còn dùng cho:
- Archive (lưu lâu dài) — bị tạm dừng
- Spark Streaming — đang consume từ Kafka nhưng throughput thấp vì producer chết

**Cải thiện tương lai:** Phục hồi producer hoặc viết producer mới dùng async + multi-shard (giống binance-ticker-ws).

## 10. Schema Registry (Apicurio)

### Nó là gì?

Schema Registry = nơi lưu "schema" (cấu trúc dữ liệu) cho các message Kafka. Producer và Consumer tra cứu schema ở đây thay vì hardcode.

### Vì sao cần?

Giả sử Producer gửi message dạng JSON:
```json
{"symbol": "BTCUSDT", "price": "63743.90"}
```

Consumer parse JSON. Nếu Producer đổi sang:
```json
{"sym": "BTCUSDT", "px": 63743.90}
```

Consumer crash. Không có version tracking, không biết ai đúng ai sai.

**Avro + Schema Registry giải quyết:**
- Schema lưu trong registry, có version (v1, v2, v3)
- Producer/Consumer download schema mới nhất
- Nếu schema không tương thích → fail fast

### Trong LMView

```yaml
schema-registry:
  image: apicurio/apicurio-registry:2.4.2
  environment:
    REGISTRY_DATASOURCE_URL: jdbc:postgresql://postgres:5432/apicurio
    REGISTRY_DATASOURCE_USERNAME: lmview
    REGISTRY_DATASOURCE_PASSWORD: ${POSTGRES_PASSWORD}
```

Schema lưu trong Postgres (database Apicurio riêng).

### Avro schemas

`schemas/*.avsc`:
- `kline.avsc` — schema cho kline message
- `ticker.avsc` — schema cho ticker message
- `depth.avsc` — schema cho order book
- `trade.avsc` — schema cho trade

Xem chi tiết ở §26.

## 11. `binance-ticker-ws` — Service Quan Trọng Nhất

> **Đây là service then chốt của LMView.** Nếu service này chết, giá trên chart ngừng cập nhật. Dành thời gian đọc kỹ §11 và Phần 8.

### Vai trò

Nhận giá real-time từ Binance WebSocket, ghi vào Redis. Thay thế REST polling cũ (BinancePricePoller).

### Cấu hình

- **8 shards** (8 kết nối WebSocket song song)
- Mỗi shard quản lý **~84 symbols** (671 ÷ 8)
- Tổng cộng **671 USDT pairs** (top theo 24h quote volume)
- Ghi **24 fields** cho mỗi symbol vào Redis hash
- **Push rate:** ~1 Hz mỗi symbol
- **Latency:** p50 < 200ms, p95 < 1s

### Cấu trúc thư mục

```
src/ticker_ws/
├── __init__.py           ← file rỗng (đánh dấu là Python package)
├── main.py               ← entry point, spawn 8 shards + Redis writer + HTTP server
├── config.py             ← load symbol list từ Binance REST, build URLs
├── shard.py              ← 1 class TickerShard = 1 WebSocket connection
├── parser.py             ← map Binance @ticker payload → 24 Redis fields
└── redis_writer.py       ← buffer + pipeline batch ghi Redis
```

### Code đầy đủ (annotated — giải thích từng dòng)

#### File: `src/ticker_ws/parser.py` (quan trọng nhất)

```python
"""Map Binance @ticker payload → Redis hash fields (24 fields).

Tác giả comment tiếng Việt:
File này chuyển đổi message JSON từ Binance thành dict để ghi vào Redis.
Mỗi field trong dict = 1 column trong Redis hash.
"""

from __future__ import annotations  # PEP 563 — type hints lazy evaluation
from typing import Dict


# Tuple các field sẽ ghi vào Redis. Thứ tự không quan trọng.
# Binance @ticker gửi ~25 fields, mình lấy 20 + thêm "exchange" = 21.
REDIS_FIELDS = (
    "price",          # c: last price (close) — giá khớp lệnh gần nhất
    "bid",            # b: best bid price — giá mua cao nhất
    "ask",            # a: best ask price — giá bán thấp nhất
    "bid_qty",        # B: best bid quantity — khối lượng ở bid
    "ask_qty",        # A: best ask quantity — khối lượng ở ask
    "volume",         # v: total traded base asset volume (24h)
    "quote_volume",   # q: total traded quote asset volume (24h)
    "change_pct",     # P: price change percent (24h)
    "change_abs",     # p: price change absolute (24h)
    "weighted_avg",   # w: weighted average price (24h)
    "open_24h",       # o: open price 24h trước
    "high_24h",       # h: high price 24h
    "low_24h",        # l: low price 24h
    "last_qty",       # Q: last quantity — khối lượng lệnh cuối
    "open_time",      # O: statistics open time (ms)
    "close_time",     # C: statistics close time (ms)
    "first_trade_id", # F: first trade ID trong 24h
    "last_trade_id",  # L: last trade ID trong 24h
    "num_trades",     # n: total number of trades (24h)
    "event_time",     # E: event time (ms) — thời điểm Binance gửi
)


def parse_ticker(payload: Dict) -> Dict[str, str] | None:
    """Convert Binance @ticker payload into Redis hash mapping.

    Giải thích:
    - Input `payload` = dict parse từ JSON Binance
    - Output = dict {field_name: str_value} sẵn sàng cho Redis HSET
    - Returns None nếu payload invalid (thiếu symbol)

    Tại sao return Dict[str, str] mà không phải int/float?
    Vì Redis HSET chấp nhận string, tự convert khi cần.
    """
    sym = payload.get("s")  # Lấy symbol (vd: "BTCUSDT")
    if not sym:
        return None  # Không có symbol → bỏ qua

    # Tạo dict output. Mỗi key = tên field, value = str(value từ Binance).
    # Binance dùng key ngắn (c, b, a, ...) để tiết kiệm bandwidth.
    out: Dict[str, str] = {
        "price":          str(payload.get("c", "")),  # "" là default nếu field missing
        "bid":            str(payload.get("b", "")),
        "ask":            str(payload.get("a", "")),
        "bid_qty":        str(payload.get("B", "")),
        "ask_qty":        str(payload.get("A", "")),
        "volume":         str(payload.get("v", "")),
        "quote_volume":   str(payload.get("q", "")),
        "change_pct":     str(payload.get("P", "")),  # % thay đổi (vd: "2.5" = 2.5%)
        "change_abs":     str(payload.get("p", "")),  # absolute change
        "weighted_avg":   str(payload.get("w", "")),
        "open_24h":       str(payload.get("o", "")),
        "high_24h":       str(payload.get("h", "")),
        "low_24h":        str(payload.get("l", "")),
        "last_qty":       str(payload.get("Q", "")),
        "open_time":      str(payload.get("O", "")),
        "close_time":     str(payload.get("C", "")),
        "first_trade_id": str(payload.get("F", "")),
        "last_trade_id":  str(payload.get("L", "")),
        "num_trades":     str(payload.get("n", "")),
        "event_time":     str(payload.get("E", "")),
        "exchange":       "binance",  # hardcode, vì chỉ support Binance hiện tại
    }

    # Defensive: drop field nào có value rỗng
    # (đề phòng Binance đổi schema trong tương lai)
    return {k: v for k, v in out.items() if v != ""}


def redis_key(exchange: str, symbol: str) -> str:
    """Build Redis key cho ticker hash.

    Format: ticker:latest:{exchange}:{symbol}
    Ví dụ: ticker:latest:binance:BTCUSDT

    Tại sao có exchange trong key?
    Vì sau này sẽ thêm OKX, Bybit → cần tách biệt.
    """
    return f"ticker:latest:{exchange.lower()}:{symbol}"
```

#### File: `src/ticker_ws/config.py`

```python
"""Configuration cho binance-ticker-ws service.

Tác giả: file này load danh sách 671 USDT pairs từ Binance REST API,
chia thành 8 shards, build combined-stream URLs.
"""

from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import List
import aiohttp

log = logging.getLogger(__name__)

# ── Đọc biến môi trường (env vars) ──
# Mỗi biến có default nếu không set trong .env

EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/ticker/24hr"
"""
URL lấy danh sách 24h stats cho TẤT CẢ symbols trên Binance.
Kết quả: ~2500 tickers, mỗi ticker có symbol, quoteVolume, v.v.
"""

SYMBOL_REFRESH_SEC = int(os.environ.get("TICKER_WS_SYMBOL_REFRESH_SEC", "3600"))
"""
Mỗi 3600s (1 giờ) reload symbol list. Hiện tại chỉ reload lúc startup
do code chưa implement periodic refresh.
"""

SHARDS = int(os.environ.get("TICKER_WS_SHARDS", "8"))
"""
Số shards = số kết nối WebSocket song song.
Mỗi shard có tối đa SYMBOLS_PER_SHARD streams.
8 shards × 100 streams = 800 streams capacity, đủ cho 671 symbols.
"""

SYMBOLS_PER_SHARD = int(os.environ.get("TICKER_WS_SYMBOLS_PER_SHARD", "100"))
"""
Tối đa symbols mỗi shard. Binance cho phép ~200, nhưng 100 an toàn hơn.
"""

TOP_N = int(os.environ.get("TICKER_WS_TOP_N", "671"))
"""
Lấy TOP_N symbols có 24h quote volume cao nhất.
671 = top USDT pairs. Nếu tăng lên 1000 → 10 shards.
"""

# Binance WS endpoint cho combined stream
WS_BASE = os.environ.get("TICKER_WS_BASE", "wss://stream.binance.com:9443/stream")
"""
URL gốc cho combined stream format.
Streams nối bằng "/": ?streams=btcusdt@ticker/ethusdt@ticker/...
"""

# Reconnect / heartbeat settings
RECONNECT_BASE_MS = int(os.environ.get("TICKER_WS_RECONNECT_BASE_MS", "1000"))
"""
Khi disconnect, đợi 1000ms trước khi reconnect.
"""

RECONNECT_MAX_MS = int(os.environ.get("TICKER_WS_RECONNECT_MAX_MS", "30000"))
"""
Tối đa 30s giữa các lần reconnect. Sau đó giữ nguyên 30s.
"""

PING_INTERVAL_S = int(os.environ.get("TICKER_WS_PING_INTERVAL_S", "30"))
"""
Mỗi 30s gửi WebSocket ping. Nếu không nhận pong trong PING_TIMEOUT_S → close.
"""

PING_TIMEOUT_S = int(os.environ.get("TICKER_WS_PING_TIMEOUT_S", "10"))
"""
Timeout cho pong. 30+10 = 40s max latency phát hiện dead connection.
"""

# Redis settings
REDIS_KEY_TTL_S = int(os.environ.get("TICKER_WS_TTL_S", "300"))
"""
Mỗi key Redis tự expire sau 300s (5 phút) nếu không có update.
Đảm bảo key "chết" không tồn tại mãi nếu symbol bị delist.
"""

REDIS_FLUSH_MS = int(os.environ.get("TICKER_WS_REDIS_FLUSH_MS", "50"))
"""
Mỗi 50ms flush buffer xuống Redis. 20 flush/s.
Đủ nhanh cho real-time, đủ chậm để batch được nhiều message.
"""

REDIS_FLUSH_MAX_BUFFER = int(os.environ.get("TICKER_WS_REDIS_BUFFER_MAX", "2000"))
"""
Nếu buffer vượt 2000 items → flush ngay (không đợi 50ms).
Tránh buffer phình to khi spike traffic.
"""


@dataclass
class TickerConfig:
    """Resolved ticker configuration."""

    shards: List[List[str]] = field(default_factory=list)
    """
    shards = list of 8 lists of symbols.
    shards[0] = ["BTCUSDT", "ETHUSDT", ...]  # 84 symbols
    shards[1] = ["MATICUSDT", "ARBUSDT", ...]  # 84 symbols
    ...
    """

    top_symbols: List[str] = field(default_factory=list)
    """Tất cả symbols đã load, dùng để logging."""

    @property
    def total_symbols(self) -> int:
        """Tổng số symbols (sum of all shards)."""
        return sum(len(s) for s in self.shards)

    @classmethod
    async def load(cls) -> "TickerConfig":
        """Fetch top USDT symbols từ Binance REST và split vào shards.

        Bước 1: GET https://api.binance.com/api/v3/ticker/24hr
        Bước 2: Filter USDT pairs (symbol ends with "USDT")
        Bước 3: Sort theo 24h quoteVolume desc
        Bước 4: Take top TOP_N
        Bước 5: Split thành chunks SYMBOLS_PER_SHARD
        """
        log.info("Loading top %d USDT symbols từ %s", TOP_N, EXCHANGE_INFO_URL)

        # aiohttp = async HTTP client (nhanh hơn requests vì không block)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(EXCHANGE_INFO_URL) as resp:
                resp.raise_for_status()  # Nếu 4xx/5xx → throw exception
                rows = await resp.json()  # ~2500 tickers

        # Filter: chỉ lấy USDT pairs có volume > 0
        usdt_rows = [
            r for r in rows
            if r.get("symbol", "").endswith("USDT")  # Symbol phải kết thúc bằng USDT
            and r.get("quoteVolume") not in (None, "", "0", "0.0")  # Volume phải > 0
        ]

        # Sort theo quoteVolume (USDT volume) desc
        # key=lambda r: float(...) → sort theo giá trị số (không phải string)
        # reverse=True → lớn nhất trước
        usdt_rows.sort(key=lambda r: float(r.get("quoteVolume") or 0), reverse=True)

        # Lấy top TOP_N symbols
        symbols = [r["symbol"] for r in usdt_rows[:TOP_N]]
        log.info("Loaded %d USDT pairs (top by 24h quoteVolume)", len(symbols))

        # Chia thành shards
        shards: List[List[str]] = []
        for i in range(0, len(symbols), SYMBOLS_PER_SHARD):
            # range(0, 671, 100) = [0, 100, 200, 300, 400, 500, 600]
            # → 7 chunks: [0:100], [100:200], ..., [600:671]
            # Nhưng nếu SYMBOLS_PER_SHARD=100, ta được 7 chunks không đều.
            # Để đảm bảo 8 shards, cần pad thêm.
            shards.append(symbols[i : i + SYMBOLS_PER_SHARD])

        # Pad shards: nếu symbols không chia hết cho SHARDS, redistribute đều
        # Ví dụ: 671 symbols / 8 shards = 84 symbols/shard (còn dư 1)
        if len(symbols) > 0 and len(shards) < SHARDS and len(shards) > 0:
            # Redistribute evenly across SHARDS shards
            n = len(symbols)
            per = (n + SHARDS - 1) // SHARDS  # ceil(n/SHARDS), vd: ceil(671/8) = 84
            shards = [symbols[i : i + per] for i in range(0, n, per)]
            shards = shards[:SHARDS]  # Truncate nếu thừa

        log.info(
            "Shard layout: %d shards, sizes=%s (total=%d symbols)",
            len(shards),
            [len(s) for s in shards],  # vd: [84, 84, 84, 84, 84, 84, 84, 83]
            sum(len(s) for s in shards),
        )

        return cls(shards=shards, top_symbols=symbols)

    def shard_url(self, shard_id: int) -> str:
        """Build combined-stream WS URL cho shard này.

        Format: wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker/...
        """
        if shard_id >= len(self.shards):
            raise IndexError(f"shard_id {shard_id} out of range ({len(self.shards)})")

        # Combine tất cả symbols thành 1 URL
        # "/".join([f"{s.lower()}@ticker" for s in symbols])
        # = "btcusdt@ticker/ethusdt@ticker/bnbusdt@ticker/..."
        streams = "/".join(f"{s.lower()}@ticker" for s in self.shards[shard_id])

        return f"{WS_BASE}?streams={streams}"
```

#### File: `src/ticker_ws/shard.py`

```python
"""Single Binance WS shard = 1 connection = 1 asyncio task.

Mỗi shard chạy độc lập. Nếu shard 3 chết, shard 0,1,2,4,5,6,7 vẫn sống.
"""

from __future__ import annotations
import asyncio
import json
import logging
import random
import time
from typing import TYPE_CHECKING

import websockets
from websockets.exceptions import (
    ConnectionClosed, ConnectionClosedError, ConnectionClosedOK,
    InvalidStatusCode, WebSocketException,
)

from src.ticker_ws.config import PING_INTERVAL_S, PING_TIMEOUT_S, RECONNECT_BASE_MS, RECONNECT_MAX_MS
from src.ticker_ws.parser import parse_ticker, redis_key

if TYPE_CHECKING:
    from src.ticker_ws.redis_writer import TickerRedisWriter

log = logging.getLogger(__name__)


class TickerShard:
    """Một Binance WS combined-stream connection.

    Lifecycle:
    1. connect() → ws.recv() loop → handle_frame() → on disconnect: backoff → reconnect
    2. Stats: frames_total, tickers_total, reconnects_total, last_event_time_ms
    """

    def __init__(self, shard_id: int, url: str, writer: "TickerRedisWriter"):
        """
        Args:
            shard_id: 0..7
            url: combined-stream URL (e.g., wss://.../stream?streams=btcusdt@ticker/...)
            writer: shared TickerRedisWriter (1 instance, dùng cho 8 shards)
        """
        self.shard_id = shard_id
        self.url = url
        self.writer = writer

        # Stats — dùng cho /healthz endpoint
        self.frames_total = 0       # Tổng frames nhận được từ startup
        self.tickers_total = 0      # Tổng tickers parse thành công
        self.reconnects_total = 0   # Số lần reconnect
        self.last_frame_at: float = 0.0   # Timestamp lần cuối nhận frame
        self.last_event_time_ms: int = 0  # Event time từ Binance (ms)
        self.connected = False
        self.connect_started_at: float = 0.0

    async def run(self, stop_event: asyncio.Event) -> None:
        """Main loop: connect → consume → on fail backoff → reconnect.

        Args:
            stop_event: asyncio.Event, khi set() → shard dừng lại
        """
        backoff_ms = RECONNECT_BASE_MS  # 1000ms

        while not stop_event.is_set():
            try:
                # _connect_and_consume blocks cho đến khi disconnect
                await self._connect_and_consume(stop_event)
                backoff_ms = RECONNECT_BASE_MS  # Success → reset backoff
            except asyncio.CancelledError:
                # Process bị kill → propagate
                raise
            except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK) as e:
                # Binance hoặc network đóng kết nối
                log.warning("[shard %d] WS closed: %s (code=%s)", self.shard_id, e, getattr(e, "code", "?"))
                self.connected = False
            except InvalidStatusCode as e:
                # HTTP error trong handshake (403, 429, ...)
                log.warning("[shard %d] handshake failed: %s", self.shard_id, e)
                self.connected = False
                if "403" in str(e) or "429" in str(e):
                    # Rate limit / geofencing → backoff chậm hơn (4×)
                    backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 4)
            except (WebSocketException, OSError, asyncio.TimeoutError) as e:
                # Network error khác
                log.warning("[shard %d] connection error: %s", self.shard_id, e)
                self.connected = False
            except Exception as e:
                # Lỗi không mong đợi → log full stack trace
                log.exception("[shard %d] unexpected: %s", self.shard_id, e)
                self.connected = False

            if stop_event.is_set():
                break  # Shutdown signal → thoát loop

            # Exponential backoff với jitter
            # Jitter = random offset để tránh "thundering herd"
            # (nhiều shards reconnect cùng lúc gây spike)
            jitter_ms = random.randint(0, 1000)
            sleep_ms = min(RECONNECT_MAX_MS, backoff_ms) + jitter_ms
            log.info("[shard %d] reconnecting in %dms (attempt=%d)", self.shard_id, sleep_ms, self.reconnects_total + 1)

            try:
                # Chờ sleep_ms, NHƯNG nếu stop_event set thì dừng sớm
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_ms / 1000.0)
                break  # Stop signal
            except asyncio.TimeoutError:
                pass  # Sleep xong, tiếp tục loop

            # Tăng backoff (cap ở MAX)
            backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 2)
            self.reconnects_total += 1

    async def _connect_and_consume(self, stop_event: asyncio.Event) -> None:
        """Open WS, consume frames cho đến khi disconnect."""
        self.connect_started_at = time.time()
        log.info("[shard %d] connecting to %s", self.shard_id, self.url[:120] + "...")

        # websockets.connect() = async context manager
        # Tự động close khi exit block
        async with websockets.connect(
            self.url,
            ping_interval=PING_INTERVAL_S,    # 30s — gửi ping
            ping_timeout=PING_TIMEOUT_S,      # 10s — đợi pong
            close_timeout=5,                  # 5s — đợi close frame
            max_size=8 * 1024 * 1024,         # 8 MB — max message size
            open_timeout=15,                  # 15s — handshake timeout
        ) as ws:
            self.connected = True
            log.info("[shard %d] connected", self.shard_id)

            # Recv loop: chờ message từ Binance
            while not stop_event.is_set():
                try:
                    # ws.recv() trả về string (text frame) hoặc bytes (binary frame)
                    # Binance dùng text, nên sẽ là str
                    raw = await asyncio.wait_for(
                        ws.recv(),
                        timeout=PING_INTERVAL_S + PING_TIMEOUT_S + 5,  # 45s
                    )
                except asyncio.TimeoutError:
                    # 45s không có message → close
                    log.warning("[shard %d] recv timeout, closing", self.shard_id)
                    break

                # Parse + buffer
                self._handle_frame(raw)

    def _handle_frame(self, raw: str | bytes) -> None:
        """Parse 1 WS frame, ghi vào Redis buffer (qua writer)."""
        self.frames_total += 1
        self.last_frame_at = time.time()

        # Nếu là bytes → decode
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                return  # Corrupted frame → bỏ

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return  # Invalid JSON → bỏ

        # Combined stream format: {"stream": "btcusdt@ticker", "data": {...}}
        data = msg.get("data") if isinstance(msg, dict) else None
        if not isinstance(data, dict):
            return

        # Parse → Redis fields
        mapping = parse_ticker(data)
        if not mapping:
            return  # Không có symbol → bỏ

        sym = data.get("s")
        if not sym:
            return

        # Build key + add vào buffer
        key = redis_key("binance", sym)
        # writer.add() chỉ lưu vào dict, KHÔNG ghi Redis ngay
        self.writer.add(key, mapping)
        self.tickers_total += 1

        try:
            self.last_event_time_ms = int(data.get("E", 0))
        except (ValueError, TypeError):
            pass

    @property
    def stats(self) -> dict:
        """Trả về dict cho /healthz endpoint."""
        now = time.time()
        # Latency từ Binance event → process now
        latency_ms = (now * 1000 - self.last_event_time_ms) if self.last_event_time_ms else None
        return {
            "shard_id": self.shard_id,
            "connected": self.connected,
            "frames_total": self.frames_total,
            "tickers_total": self.tickers_total,
            "reconnects_total": self.reconnects_total,
            "uptime_s": round(now - self.connect_started_at, 1) if self.connected else 0,
            "last_frame_age_s": round(now - self.last_frame_at, 3) if self.last_frame_at else None,
            "last_event_latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        }
```

#### File: `src/ticker_ws/redis_writer.py`

```python
"""Batched Redis writer — gom nhiều HSET thành 1 pipeline.

Tại sao batch? Vì mỗi HSET = 1 network RTT. Nếu ghi 33 lần liên tục,
33 RTT. Pipeline = 1 RTT cho tất cả. Nhanh hơn 33×.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Dict, List, Tuple
from redis.asyncio import Redis

from src.ticker_ws.config import REDIS_FLUSH_MAX_BUFFER, REDIS_FLUSH_MS, REDIS_KEY_TTL_S

log = logging.getLogger(__name__)


class TickerRedisWriter:
    """Buffer và pipeline-write ticker updates xuống Redis.

    Flow:
    1. add(key, mapping) → lưu vào self._buffer (không ghi Redis)
    2. _flush_loop mỗi 50ms → flush buffer
    3. flush() → snapshot + clear + pipeline.execute()
    """

    def __init__(self, redis: Redis):
        """
        Args:
            redis: async Redis client (Sentinel-aware hoặc direct)
        """
        self._r = redis
        # Buffer: dict[key, mapping]. Latest mapping ghi đè mapping cũ.
        self._buffer: Dict[str, Dict[str, str]] = {}

        self._flush_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._flush_count = 0   # Số lần flush thành công
        self._write_count = 0   # Tổng items đã ghi
        self._last_flush_at = 0.0

    def add(self, key: str, mapping: Dict[str, str]) -> None:
        """Buffer một HSET. Ghi đè previous unsent mapping cho cùng key.

        Ví dụ: BTCUSDT có 3 updates trong 50ms → chỉ latest còn lại.
        Đây là intentional: ta chỉ quan tâm giá MỚI NHẤT.
        """
        self._buffer[key] = mapping
        # Nếu buffer quá lớn → flush ngay
        if len(self._buffer) >= REDIS_FLUSH_MAX_BUFFER:
            # Fire-and-forget: flush chạy async, không đợi
            asyncio.create_task(self.flush())

    async def start(self) -> None:
        """Start the periodic flush loop (50ms interval)."""
        self._stop_event.clear()
        self._flush_task = asyncio.create_task(self._flush_loop(), name="ticker-flush")

    async def stop(self) -> None:
        """Stop flush loop và flush remaining buffer."""
        self._stop_event.set()
        if self._flush_task:
            try:
                await asyncio.wait_for(self._flush_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._flush_task.cancel()
        # Flush phần còn lại
        await self.flush()

    async def _flush_loop(self) -> None:
        """Flush mỗi REDIS_FLUSH_MS (50ms)."""
        interval = REDIS_FLUSH_MS / 1000.0  # 0.05s
        while not self._stop_event.is_set():
            try:
                # Chờ stop_event hoặc timeout 50ms
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break  # Stop signal
            except asyncio.TimeoutError:
                pass  # 50ms đã trôi qua, tiếp tục flush

            try:
                await self.flush()
            except Exception as e:
                log.warning("[ticker-writer] flush error: %s", e)

    async def flush(self) -> None:
        """Flush buffered writes qua 1 Redis pipeline.

        Atomicity: KHÔNG dùng MULTI/EXEC (transaction=False).
        Trade-off: Nhanh hơn, nhưng nếu 1 lệnh fail giữa chừng,
        các lệnh trước vẫn committed. OK cho ticker data.
        """
        if not self._buffer:
            return  # Nothing to flush

        # Snapshot + clear TRƯỚC khi ghi (tránh block nếu pipe chậm)
        items: List[Tuple[str, Dict[str, str]]] = list(self._buffer.items())
        self._buffer.clear()

        try:
            # Tạo pipeline
            pipe = self._r.pipeline(transaction=False)
            for key, mapping in items:
                pipe.hset(key, mapping=mapping)    # Ghi 20 fields
                pipe.expire(key, REDIS_KEY_TTL_S)  # Refresh TTL 300s
            # Execute: 1 network RTT cho tất cả commands
            await pipe.execute()
            self._flush_count += 1
            self._write_count += len(items)
            self._last_flush_at = time.time()
        except Exception as e:
            # Lỗi (network, Redis down, ...) → re-buffer để retry
            log.warning("[ticker-writer] pipeline failed (%d items): %s", len(items), e)
            for key, mapping in items:
                self._buffer[key] = mapping

    @property
    def stats(self) -> dict:
        """Trả về dict cho /healthz endpoint."""
        return {
            "flush_count": self._flush_count,
            "write_count": self._write_count,
            "buffer_size": len(self._buffer),
            "last_flush_age_s": round(time.time() - self._last_flush_at, 3) if self._last_flush_at else None,
        }
```

#### File: `src/ticker_ws/main.py`

```python
"""Entrypoint cho binance-ticker-ws service.

Khởi tạo:
1. Load symbol list (TickerConfig)
2. Start HTTP server (:9100/metrics, /healthz)
3. Connect Redis (Sentinel hoặc fallback)
4. Start Redis writer (background flush loop)
5. Spawn 8 TickerShard tasks
6. Wait for SIGINT/SIGTERM
"""

from __future__ import annotations
import asyncio
import logging
import os
import signal
import sys
import time
from typing import List

import aiohttp
import redis.asyncio as redis_async
from prometheus_client import (
    CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest,
)
from aiohttp import web

# Hack: thêm /app vào sys.path khi chạy trong container
# (vì Python mặc định tìm module từ CWD)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ticker_ws.config import TickerConfig
from src.ticker_ws.redis_writer import TickerRedisWriter
from src.ticker_ws.shard import TickerShard

# ── Logging setup ──
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
log = logging.getLogger("binance-ticker-ws")

# ── Prometheus metrics ──
# Counter = chỉ tăng (vd: tổng frames)
# Gauge = lên xuống (vd: số shards connected)
# Histogram = distribution (vd: latency)

FRAMES_TOTAL = Counter("ticker_ws_frames_total", "Total WS frames received across all shards")
TICKERS_TOTAL = Counter("ticker_ws_tickers_total", "Total ticker payloads parsed and buffered")
RECONNECTS_TOTAL = Counter("ticker_ws_reconnects_total", "Total reconnect attempts")
SHARDS_UP = Gauge("ticker_ws_shards_up", "Number of shards currently connected")
REDIS_BUFFER_SIZE = Gauge("ticker_ws_redis_buffer_size", "Pending items in Redis writer buffer")
REDIS_WRITE_LATENCY = Histogram(
    "ticker_ws_redis_flush_seconds",
    "Redis pipeline flush latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
EVENT_TO_WRITE_LATENCY = Histogram(
    "ticker_ws_event_to_now_seconds",
    "Binance event_time → now() in our process",
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0),
)


# ── Redis connection (Sentinel-aware, fallback to direct) ──
REDIS_SENTINELS = os.environ.get("REDIS_SENTINELS", "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379")
REDIS_MASTER_NAME = os.environ.get("REDIS_MASTER_NAME", "mymaster")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-master")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))


async def get_redis() -> redis_async.Redis:
    """Build Redis async client (master-only for writes).

    Tại sao Sentinel?
    Trong Redis cluster, có 1 master + N replicas. Khi master chết,
    Sentinel tự động bầu replica mới làm master.
    Nếu dùng direct connection đến "redis-master", ta có thể bị
    trỏ vào replica → write fail với READONLY error.

    `sentinel.master_for("mymaster")` luôn trả về CURRENT master.

    Fallback to direct: chỉ dùng khi Sentinel chưa sẵn sàng
    (vd: lúc Swarm khởi động).
    """
    sentinel_nodes = [
        tuple(node.split(":")) for node in REDIS_SENTINELS.split(",") if node.strip()
    ]
    try:
        from redis.asyncio.sentinel import Sentinel as AsyncSentinel
        sentinel = AsyncSentinel(
            sentinel_nodes,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        # master_for trả về client tự động resolve master
        client = sentinel.master_for(
            REDIS_MASTER_NAME,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            decode_responses=False,  # bytes mode (cho HSET)
            max_connections=64,
        )
        await client.ping()  # Verify connection
        log.info("Redis connected via Sentinel (%s)", REDIS_MASTER_NAME)
        return client
    except Exception as e:
        # Fallback: connect trực tiếp đến REDIS_HOST:REDIS_PORT
        log.warning("Sentinel connect failed (%s), fallback to direct %s:%d", e, REDIS_HOST, REDIS_PORT)
        client = redis_async.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=False,
            socket_keepalive=True,        # TCP keepalive
            health_check_interval=30,     # Ping mỗi 30s
            max_connections=64,
        )
        await client.ping()
        log.info("Redis connected via direct %s:%d", REDIS_HOST, REDIS_PORT)
        return client


# ── HTTP server cho metrics + healthz ──
HTTP_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")
HTTP_PORT = int(os.environ.get("METRICS_PORT", "9100"))


async def metrics_handler(request: web.Request) -> web.Response:
    """Trả về Prometheus metrics ở text format."""
    body = generate_latest()  # Encode tất cả metrics
    return web.Response(body=body, content_type=CONTENT_TYPE_LATEST)


async def healthz_handler(request: web.Request) -> web.Response:
    """Trả về JSON health status."""
    body = {
        "ok": True,
        "uptime_s": round(time.time() - STARTED_AT, 1),
        "shards": SHARD_STATS,  # Updated bởi stats_reporter mỗi 5s
    }
    return web.json_response(body)


SHARD_STATS: list = []  # Updated bởi stats_reporter
STARTED_AT = time.time()


async def start_http() -> web.AppRunner:
    """Khởi động aiohttp server cho /metrics và /healthz."""
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/healthz", healthz_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    log.info("HTTP server on http://%s:%d (metrics, healthz)", HTTP_HOST, HTTP_PORT)
    return runner


async def stats_reporter(shards: List[TickerShard], writer: TickerRedisWriter) -> None:
    """Update Prometheus gauges + log stats mỗi 5s."""
    while True:
        await asyncio.sleep(5)
        up = sum(1 for s in shards if s.connected)  # Số shards connected
        SHARDS_UP.set(up)
        REDIS_BUFFER_SIZE.set(len(writer._buffer))
        SHARD_STATS.clear()
        for s in shards:
            SHARD_STATS.append(s.stats)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("shards_up=%d buffer=%d writer=%s shard_stats=%s", up, len(writer._buffer), writer.stats, SHARD_STATS)


async def main() -> None:
    """Main entry point."""
    global SHARD_STATS

    # 1. Load symbol list
    config = await TickerConfig.load()
    log.info("Config: %d shards, total %d symbols", len(config.shards), config.total_symbols)

    # 2. Start HTTP server
    await start_http()

    # 3. Connect Redis
    redis = await get_redis()
    log.info("Redis OK")
    writer = TickerRedisWriter(redis)
    await writer.start()

    # 4. Build shards
    shards: List[TickerShard] = []
    for i, _ in enumerate(config.shards):
        url = config.shard_url(i)
        shards.append(TickerShard(i, url, writer))

    # 5. Spawn shard tasks
    stop_event = asyncio.Event()
    shard_tasks = [
        asyncio.create_task(s.run(stop_event), name=f"shard-{i}")
        for i, s in enumerate(shards)
    ]
    stats_task = asyncio.create_task(stats_reporter(shards, writer), name="stats")

    # 6. Register signal handlers (graceful shutdown)
    loop = asyncio.get_running_loop()

    def _signal_handler() -> None:
        log.info("shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows hoặc platform không hỗ trợ
            pass

    # 7. Chờ shutdown signal
    try:
        await stop_event.wait()
    finally:
        log.info("stopping %d shards...", len(shards))
        stop_event.set()
        await asyncio.gather(*shard_tasks, return_exceptions=True)
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        await writer.stop()
        await redis.close()
        log.info("bye")


if __name__ == "__main__":
    asyncio.run(main())
```

### Khi nào restart?

```bash
# Restart toàn bộ service
docker service update --force cryptoprice_binance-ticker-ws

# Check health
curl http://binance-ticker-ws:9100/healthz | jq

# Xem metrics
curl http://binance-ticker-ws:9100/metrics | grep ticker_ws
```

### Tại sao dùng async thay vì threading?

| Async (asyncio) | Threading |
|---|---|
| 1 thread, nhiều task "ảo" | Nhiều thread thật |
| Mỗi task < 1 KB | Mỗi thread ~ 8 MB |
| Không cần GIL (Global Interpreter Lock) | GIL giới hạn 1 thread chạy Python tại 1 thời điểm |
| Phù hợp I/O-bound (network) | Phù hợp CPU-bound (tính toán) |
| 8 shards × <1 KB = 8 KB | 8 threads × 8 MB = 64 MB |

WebSocket client là I/O-bound (chờ network), async là lựa chọn tự nhiên.

## 12. Producer (Legacy, đã chết)

### Lịch sử

- **v0.25.0 - v0.25.41:** Producer chạy ổn định, lấy data từ Binance, ghi Kafka + Redis
- **v0.25.41:** Producer bắt đầu bị OOM (Out of memory) thường xuyên do threading
- **v0.25.45:** Phase 4 deploy `binance-ticker-ws` thay thế ticker path
- **Hiện tại:** Producer vẫn chạy (cho kline + depth) nhưng liên tục OOM → restart loop

### Tại sao chết?

Producer cũ dùng **31 threads** để xử lý:
- 1 thread cho mỗi symbol pool
- Mỗi thread ~10 MB resident
- Tổng: ~300 MB
- Swarm limit: 2 GB
- → Vẫn trong limit NHƯNG có spike (load lúc khởi động, reconnect burst) → OOM

### Tại sao chưa replace hoàn toàn?

Vì producer còn handle:
- **Kline (1s candles)** — Flink aggregate thành 1m, 5m, 1h, 1d
- **Depth (order book)** — ghi Redis (lúc đầu depth5, depth10, depth20)

Nếu chết hẳn → không có kline real-time, không có order book mới.

**Kế hoạch tương lai:** Viết `binance-kline-ws` và `binance-depth-ws` (cùng pattern như ticker-ws).

## 13. Flink JobManager + TaskManager

### Flink là gì?

Apache Flink = bộ xử lý luồng phân tán (distributed stream processor).

**Ví dụ thực tế:**
- Bạn có 1 dòng sông (stream of data) chảy qua
- Flink đặt các "trạm" dọc sông
- Mỗi trạm xử lý 1 phần (filter, transform, aggregate)
- Kết quả chảy ra cuối sông

### JobManager vs TaskManager

| JobManager | TaskManager |
|---|---|
| 1 instance | N instances (2 trong LMView) |
| Quản lý jobs (deploy, cancel, monitor) | Chạy tasks (worker) |
| Lưu checkpoint state | Execute operators |
| Web UI: `:8081` | Không có UI riêng |

### Trong LMView

```yaml
flink-jobmanager:
  image: flink:1.17.1-java11
  command: jobmanager
  environment:
    FLINK_PROPERTIES: |
      jobmanager.rpc.address: flink-jobmanager
      taskmanager.numberOfTaskSlots: 12
      parallelism.default: 12
      state.backend: filesystem
      state.checkpoints.dir: file:///checkpoints
      state.savepoints.dir: file:///savepoints

flink-taskmanager:
  image: flink:1.17.1-java11
  command: taskmanager
  environment:
    FLINK_PROPERTIES: |
      jobmanager.rpc.address: flink-jobmanager
      taskmanager.numberOfTaskSlots: 12
      taskmanager.memory.process.size: 2048m
```

**Parallelism 12:** Mỗi taskmanager có 12 slots, tổng 24 slots. Flink job chạy 12 parallel → đủ.

### Flink job chính

`src/processing/pipeline.py` — đọc từ Kafka, aggregate, ghi Redis + InfluxDB.

```
Kafka (crypto_ticker, crypto_klines, crypto_depth)
   │
   ▼ Flink job
   ├─► Parse JSON
   ├─► Aggregate kline (1s → 1m, 5m, 1h, 1d)
   ├─► Filter depth (top 20 levels)
   │
   ├─► Redis (low-latency serving)
   │   kline:candles:{exchange}:{symbol}:{interval}
   │   orderbook:{symbol}
   │
   └─► InfluxDB (long-term)
       measurement "candles" tags (exchange, symbol, interval)
```

**Hiện trạng:** Job đang chạy nhưng throughput thấp vì producer chết.

### Submit job

```bash
# Auto-submit lúc khởi động
docker exec flink-jobmanager flink run -d \
    -c src.processing.pipeline.PipelineJob \
    /app/src/processing/pipeline.py
```

## 14. Redis Sentinel Cluster

### Tại sao cần Sentinel?

Redis Master chết → mất toàn bộ write. Sentinel tự động:
1. Phát hiện master chết
2. Bầu 1 replica làm master mới
3. Update config cho clients
4. Trong vòng 5-30s, hệ thống tự hồi phục

### Topology

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Sentinel 1  │      │ Sentinel 2  │      │ Sentinel 3  │
│ (monitor)   │      │ (monitor)   │      │ (monitor)   │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │ quorate (majority)
                            ▼
       ┌─────────────────────────────────────┐
       │  Master + 2 Replicas                │
       │  ┌──────────┐    ┌──────────┐        │
       │  │  Master  │───►│ Replica 1│        │
       │  │ (R/W)    │    │ (R only) │        │
       │  └────┬─────┘    └────┬─────┘        │
       │       │               │              │
       │       └──────┬────────┘              │
       │              ▼                       │
       │        ┌──────────┐                  │
       │        │ Replica 2│                  │
       │        │ (R only) │                  │
       │        └──────────┘                  │
       └─────────────────────────────────────┘
```

### Cấu hình

```yaml
redis-master:
  image: redis:7.2-alpine
  command: redis-server /usr/local/etc/redis/redis.conf
  volumes:
    - redis-data:/data

redis-replica-1:
  image: redis:7.2-alpine
  command: redis-server /usr/local/etc/redis/replica.conf
  depends_on:
    - redis-master
```

### Sentinel config (`redis-sentinel.conf`)

```
sentinel monitor mymaster redis-master 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 10000
```

**Giải thích:**
- `mymaster` = tên master
- `redis-master:6379` = địa chỉ
- `2` = quorum (2/3 sentinels đồng ý mới failover)
- `5000ms` = timeout phát hiện dead
- `10000ms` = timeout cho toàn bộ failover

### Key Redis trong LMView

| Pattern | Type | TTL | Mục đích |
|---|---|---|---|
| `ticker:latest:binance:{symbol}` | hash | 300s | Giá real-time (24 fields) |
| `kline:candles:{exchange}:{symbol}:{interval}` | sorted set | 86400s | Candles (theo thời gian) |
| `orderbook:{symbol}` | hash | 60s | Order book top 20 |
| `trade:latest:{exchange}:{symbol}` | list | 3600s | Last 100 trades |
| `user:session:{token}` | string | 86400s | Auth session |
| `rate_limit:{ip}:{endpoint}` | string | 60s | Rate limiting |

**ZADD trick:** Sorted set dùng `score = timestamp_ms`, `member = candle JSON`. ZADD với score mới sẽ GHI ĐÈ member cũ nếu cùng score. Tránh duplicate candles.

## 15. InfluxDB

### Nó là gì?

InfluxDB = time-series database, tối ưu cho dữ liệu có timestamp.

**So sánh:**

| | Postgres | InfluxDB | Redis |
|---|---|---|---|
| Tối ưu cho | Dữ liệu quan hệ | Time-series (giá, sensor) | Cache, key-value |
| Query | SQL | InfluxQL / Flux | GET/SET, range |
| Retention | Mãi mãi (manual delete) | Auto-expire (vd: 90 ngày) | TTL ngắn |
| Use case | User, settings | Candles, indicators | Realtime data |

### Trong LMView

```yaml
influxdb:
  image: influxdb:2.7-alpine
  environment:
    DOCKER_INFLUXDB_INIT_MODE: setup
    DOCKER_INFLUXDB_INIT_BUCKET: crypto
    DOCKER_INFLUXDB_INIT_RETENTION: 90d
    DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUXDB_TOKEN}
```

### Measurements

| Measurement | Tags | Fields |
|---|---|---|
| `candles` | exchange, symbol, interval | open, high, low, close, volume |
| `market_ticks` | exchange, symbol | price, bid, ask, volume |
| `indicators` | exchange, symbol, interval, indicator | value |

### Query example (InluxQL)

```sql
SELECT mean(close) FROM candles
WHERE symbol = 'BTCUSDT' AND interval = '1h' AND time > now() - 7d
GROUP BY time(1h)
```

## 16. Spark + Iceberg + MinIO + Trino

### Mỗi thằng làm gì?

- **Spark** = xử lý batch (đọc từ Kafka, transform, ghi Iceberg)
- **Iceberg** = table format cho data lake (giống SQL table nhưng trên file)
- **MinIO** = S3-compatible object storage (lưu file parquet)
- **Trino** = SQL engine truy vấn Iceberg (giống MySQL nhưng trên data lake)

### Data flow

```
Kafka
   │
   ▼ Spark Streaming (mỗi 30s)
   │
   ├─► Bronze (raw)
   │   iceberg.crypto.bronze_ticker
   │   iceberg.crypto.bronze_klines
   │
   ▼ Transform
   │
   ├─► Silver (cleaned, dedup)
   │   iceberg.crypto.silver_ticker
   │   iceberg.crypto.silver_klines
   │
   ▼ Aggregate
   │
   └─► Gold (for API)
       iceberg.crypto.gold_ticker_1h
       iceberg.crypto.gold_volume_24h
       │
       ▼
       Parquet files on MinIO
       │
       ▼ Trino SQL query
       │
       FastAPI /api/market/overview
```

### Tại sao cần Iceberg thay vì Postgres?

- **Cost:** Iceberg + MinIO rẻ hơn Postgres lớn (TB data)
- **Scale:** Postgres khó scale > 1 TB
- **Schema evolution:** Iceberg cho phép đổi schema không cần migration
- **Time travel:** Có thể query "dữ liệu ngày hôm qua"

## 17. PostgreSQL

### Nó là gì?

Database quan hệ cổ điển (MySQL-like). Trong LMView dùng cho:
- User accounts
- Sessions
- Settings
- AI chat history
- RAG knowledge base

### Schema chính

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt, không lưu plaintext
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions (JWT token)
CREATE TABLE sessions (
    token UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL
);

-- User settings
CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    theme VARCHAR(50) DEFAULT 'dark',
    default_timeframe VARCHAR(10) DEFAULT '1m',
    default_symbol VARCHAR(20) DEFAULT 'BTCUSDT',
    chart_type VARCHAR(20) DEFAULT 'candles'
);

-- AI chat history
CREATE TABLE ai_chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ai_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES ai_chat_sessions(id),
    role VARCHAR(20),  -- 'user' | 'assistant'
    content TEXT,
    created_at TIMESTAMPTZ
);

-- RAG: Knowledge base với vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector

CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY,
    document_id UUID,
    content TEXT,
    embedding vector(384)  -- 384-dim từ sentence-transformers
);
```

## 18. FastAPI Serving Layer

### FastAPI là gì?

Framework Python để viết REST API + WebSocket. Fast = nhanh, dùng `uvicorn` (ASGI server) + async/await.

### Trong LMView

Backend chạy ở port 8000, expose:
- REST API: `/api/klines`, `/api/ticker`, `/api/orderbook`, ...
- WebSocket: `/api/stream/all`, `/api/stream/indicators/{interval}`

### Cấu trúc thư mục

```
backend/
├── app.py                 ← entry point, lifespan management
├── api/
│   ├── klines.py          ← /api/klines endpoint
│   ├── ticker.py          ← /api/ticker/{symbol}
│   ├── orderbook.py       ← /api/orderbook/{symbol}
│   ├── trades.py          ← /api/trades/{symbol}
│   ├── websocket.py       ← /api/stream/* WS endpoints
│   ├── auth.py            ← /api/auth/*
│   ├── settings.py        ← /api/settings
│   ├── admin.py           ← /api/admin/* (admin only)
│   └── ai/                ← AI endpoints
├── services/              ← business logic
├── models/                ← Pydantic schemas
└── core/
    ├── redis_sentinel.py  ← Redis client
    ├── postgres.py        ← Postgres client
    ├── security.py        ← JWT, password hashing
    └── constants.py       ← hằng số
```

### Endpoints quan trọng

| Endpoint | Method | Mô tả |
|---|---|---|
| `/api/health` | GET | Health check (Redis, Postgres, Influx) |
| `/api/klines` | GET | Lấy candles. Query: `?symbol=BTCUSDT&interval=1m&limit=500` |
| `/api/ticker/{symbol}` | GET | Lấy ticker hiện tại |
| `/api/orderbook/{symbol}` | GET | Lấy order book |
| `/api/trades/{symbol}` | GET | Lấy lịch sử trades |
| `/api/symbols` | GET | Danh sách symbols |
| `/api/auth/login` | POST | Đăng nhập → JWT |
| `/api/auth/register` | POST | Đăng ký |
| `/api/auth/me` | GET | Thông tin user hiện tại |
| `/api/stream/all` | WS | Real-time stream: 8 timeframes + ticker |
| `/api/stream/indicators/1m` | WS | Real-time stream: indicators |
| `/api/ai/chat` | POST | AI assistant (ask mode) |
| `/api/ai/history` | GET | Lịch sử chat |

### Lifespan management (`app.py`)

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    # Run migrations nếu RUN_MIGRATIONS=true
    if settings.RUN_MIGRATIONS:
        await run_migrations()
    # Start background tasks
    asyncio.create_task(candle_aggregator_loop())
    # (ĐÃ DISABLE từ v0.25.45) BinancePricePoller không chạy nữa
    # await binance_price_poller.start()
    yield
    # ── Shutdown ──
    await cleanup_redis()
    await cleanup_postgres()

app = FastAPI(lifespan=lifespan)
```

## 19. Nginx Reverse Proxy

### Nginx là gì?

Nginx = web server + reverse proxy + load balancer. Trong LMView, nó:
- **Terminate HTTPS** (giải mã SSL)
- **Reverse proxy** (chuyển request đến FastAPI)
- **WebSocket upgrade** (cho phép WS đi qua HTTP)
- **Static files** (serve React build)

### Tại sao cần Nginx?

- Browser chỉ connect 1 endpoint: `lmview.duckdns.org:443`
- Nginx phân luồng:
  - `/` → React build (static)
  - `/api/*` → FastAPI
  - `/api/stream/*` → FastAPI (WebSocket upgrade)
- HTTPS termination ở Nginx → FastAPI chỉ cần HTTP internal

### Config quan trọng

```nginx
server {
    listen 443 ssl http2;
    server_name lmview.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/lmview.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lmview.duckdns.org/privkey.pem;

    # WebSocket upgrade
    location /api/stream/ {
        proxy_pass http://fastapi:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;  # 1 day, cho WS giữ lâu
    }

    # REST API
    location /api/ {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # React static
    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

**⚠️ Lỗi nghiêm trọng (đã fix v0.25.46):** Cấu hình sai dùng `set $var` pattern, gây 502 khi FastAPI restart. Fix: dùng `resolver 127.0.0.11 valid=5s;` trực tiếp.

## 20. React 19 Frontend

### React là gì?

Thư viện JavaScript để xây dựng giao diện web. React 19 (2024) có Server Components, Actions, và nhiều cải tiến mới.

### Cấu trúc

```
frontend/src/
├── App.tsx                      ← root component
├── main.tsx                     ← entry point
├── features/                    ← mỗi feature 1 thư mục
│   ├── chart/
│   │   ├── CandlestickChart.tsx ← biểu đồ chính
│   │   ├── chartTypeData.ts     ← chuyển đổi chart type
│   │   └── ...
│   ├── ai/
│   │   ├── AiAssistantPanel.tsx
│   │   └── ...
│   ├── orderbook/
│   ├── trades/
│   └── settings/
├── components/                  ← shared UI components
│   ├── layout/                  ← Header, Sidebar, Footer
│   └── ui/                      ← Button, Modal, Input
├── services/                    ← gọi API
│   ├── marketDataService.ts     ← candles, ticker, WS
│   ├── authService.ts           ← login, register
│   ├── aiService.ts             ← AI chat
│   └── ...
├── constants/
├── types/
├── data/mock/                   ← mock data (khi dev)
└── pages/                       ← route-level screens
```

### Service layer (rất quan trọng)

**KHÔNG BAO GIỜ** gọi API trực tiếp từ component. Luôn qua service:

```tsx
// ❌ SAI: gọi fetch trực tiếp
function MyChart() {
    useEffect(() => {
        fetch('https://api.binance.com/...').then(...);
    }, []);
}

// ✅ ĐÚNG: qua service
import { fetchCandles } from '@/services/marketDataService';

function MyChart() {
    useEffect(() => {
        fetchCandles('BTCUSDT', '1m', 500).then(candles => {
            setCandles(candles);
        });
    }, []);
}
```

### React 19 features mới dùng

- **Suspense** — fallback UI khi load async
- **use() hook** — unwrap Promise trực tiếp trong component
- **Server Components** — render trên server, giảm bundle size
- **useFormStatus** — track form submit state

## 21. Observability (Prometheus, Grafana, Loki)

### 3 thành phần

| Service | Chức năng |
|---|---|
| **Prometheus** | Scrape metrics từ mỗi service, lưu time-series |
| **Grafana** | Vẽ dashboard từ Prometheus data |
| **Loki** | Aggregate logs (tương tự Elasticsearch nhưng nhẹ hơn) |
| **Promtail** | Gửi Docker logs → Loki |

### Metrics quan trọng

- `ticker_ws_shards_up` — số shards connected (target: 8)
- `ticker_ws_event_to_now_seconds` — latency event → process
- `ticker_ws_redis_buffer_size` — buffer size (target: < 100)
- `binance_ticker_ws_health` — overall health

### Logs

```logql
# Errors từ fastapi
{container="fastapi-prod"} |= "ERROR"

# Ticker shard reconnects
{container="binance-ticker-ws"} |= "reconnecting"

# 502 errors
{container="nginx-prod"} |~ " 502 "
```

<!-- Kết thúc Phần 2. Tiếp theo: Phần 3 — Tầng tốc độ -->

# Phần 3 — Tầng Tốc Độ (Speed Layer)

> **Giải thích:** Phần này đi sâu vào CÁCH dữ liệu chảy từ Binance về Redis trong vài chục milliseconds. Code đầy đủ `src/ticker_ws/` đã có ở Phần 2 §11. Ở đây ta nói về:
> - Redis key schema (cấu trúc key)
> - Flink pipeline (cách aggregate 1s candles thành 1m/5m/1h/1d)
> - Avro schemas (cấu trúc message)

## 22. Tổng Quan Real-Time Hot Path

### Timeline 1 giây dữ liệu

```
[T+0.000s]   Binance matching engine khớp lệnh BTCUSDT @ 63743.90
[T+0.050s]   Binance broadcast WS message
             {"stream":"btcusdt@ticker","data":{"E":1781937642016,"c":"63743.90",...}}
[T+0.055s]   binance-ticker-ws shard 0 nhận frame (network RTT)
             → _handle_frame(raw)
             → parse_ticker(data) → {price, bid, ask, ...}
             → writer.add("ticker:latest:binance:BTCUSDT", mapping)
[T+0.055s]   TickerRedisWriter buffer có 1 item

[T+0.050s]   _flush_loop wake up (mỗi 50ms)
[T+0.105s]   flush() → pipeline.execute() (1 RTT)
[T+0.107s]   Redis HSET commit, TTL refresh

[T+0.150s]   FastAPI _stream_all_impl loop (mỗi 50ms) đọc
             → HGETALL ticker:latest:binance:BTCUSDT
             → build _ticker payload
             → ws.send_bytes(payload)

[T+0.250s]   Browser: parseWsData → onTicker → forming candle logic
             → lightweight-charts series.update()
             → canvas redraw

Total: ~250-500ms từ Binance match → user thấy pixel
```

### Tại sao chia thành nhiều bước?

Nếu gộp tất cả vào 1 service, khi 1 phần chậm, toàn bộ chậm. Chia nhỏ:
- `binance-ticker-ws` chỉ lo nhận + ghi Redis
- `FastAPI` chỉ lo đọc Redis + đẩy ra browser
- Mỗi phần scale độc lập

## 23. Code Đầy Đủ `src/ticker_ws/`

> **Đã có đầy đủ ở Phần 2 §11.** Mỗi file được giải thích dòng-by-dòng:
> - `parser.py` — Map Binance → Redis fields
> - `config.py` — Load symbols, build URLs
> - `shard.py` — 1 class cho 1 WebSocket connection
> - `redis_writer.py` — Buffer + pipeline batch write
> - `main.py` — Entry point, spawn 8 shards

Đọc lại Phần 2 §11 nếu cần chi tiết.

## 24. Redis Key Schema

### Quy ước đặt tên key

Mọi key Redis trong LMView tuân theo format:

```
{namespace}:{type}:{exchange?}:{symbol?}:{extra?}
```

Các thành phần:
- **namespace:** Phân biệt loại dữ liệu (ticker, kline, orderbook, trade, user, ratelimit, ...)
- **type:** Latest / historical / cache
- **exchange:** binance / okx / bybit (optional, default = binance)
- **symbol:** BTCUSDT / ETHUSDT / ...
- **extra:** interval (1m / 5m / 1h), bucket, ...

### Bảng các key

| Key | Type | TTL | Fields / Members | Mục đích |
|---|---|---|---|---|
| `ticker:latest:binance:{symbol}` | hash | 300s | 20-24 fields | Giá real-time |
| `kline:candles:{exchange}:{symbol}:{interval}` | sorted set | 86400s | score=close_time_ms, member=JSON | Candles theo thời gian |
| `orderbook:{symbol}` | hash | 60s | bids, asks (JSON array) | Order book top 20 |
| `trade:latest:{exchange}:{symbol}` | list | 3600s | JSON per trade | Last 100 trades |
| `indicator:{exchange}:{symbol}:{interval}:{name}` | string | 300s | JSON | Indicator snapshot |
| `user:session:{token}` | string | 86400s | JSON user data | JWT session |
| `ratelimit:{ip}:{endpoint}:{minute}` | string | 60s | count | Rate limiting |
| `system:stats` | hash | none | version, uptime, ... | Health info |

### Ví dụ cụ thể

```bash
# Ticker BTCUSDT (24 fields)
> HGETALL ticker:latest:binance:BTCUSDT
1) "price"
2) "63743.90"
3) "bid"
4) "63743.80"
5) "ask"
6) "63744.00"
7) "bid_qty"
8) "0.500"
... (20 fields total)

# Candles 1m BTCUSDT (sorted set, score = close_time)
> ZRANGE kline:candles:binance:BTCUSDT:1m 0 9 WITHSCORES
1) '{"o":63300.01,"h":63500,"l":63200,"c":63400,"v":123.45}'
2) "1781937540000"  ← close_time (ms)
3) '{"o":63400,"h":63700,"l":63350,"c":63650,"v":150.32}'
4) "1781937600000"
... (10 candles)

# Order book (hash với bids/asks JSON)
> HGET orderbook:BTCUSDT bids
'[[63743.80, 0.5], [63743.70, 1.2], ...]'

# Rate limit (đếm số request trong 1 phút)
> GET ratelimit:1.2.3.4:/api/klines:1781937640
"42"
```

### Tại sao ZSET (sorted set) cho candles?

- **ZADD với score = timestamp:** Tự động sort theo thời gian
- **ZREMRANGEBYSCORE:** Xóa candle cũ hơn X
- **ZRANGEBYSCORE:** Lấy candles từ time A đến time B
- **ZADD cùng score = update:** Tránh duplicate candle cùng bucket

```python
# Add/update 1m candle
await redis.zadd(
    f"kline:candles:binance:BTCUSDT:1m",
    {json.dumps(candle): candle.close_time_ms}
)
# Set TTL 24h
await redis.expire(f"kline:candles:binance:BTCUSDT:1m", 86400)

# Cleanup old (giữ 1500 candles gần nhất)
await redis.zremrangebyrank(key, 0, -1501)
```

### Tại sao HASH cho ticker?

- **HSET một field:** Update 1 field không ảnh hưởng field khác
- **HGETALL:** Lấy tất cả fields trong 1 RTT
- **HINCRBY:** Atomic counter (cho stats)
- **EXPIRE:** Tự động xóa sau TTL

## 25. Flink Pipeline (`src/processing/`)

### Cấu trúc thư mục

```
src/processing/
├── pipeline.py            ← Flink job chính
├── writers/
│   ├── kline_aggregator.py   ← Aggregate 1s → 1m/5m/1h/1d
│   ├── keydb_kline.py        ← Ghi candles xuống Redis (KeyDB = Redis fork)
│   ├── keydb_depth.py        ← Ghi order book xuống Redis
│   └── influxdb_writer.py    ← Ghi xuống InfluxDB
└── operators/
    ├── kline_parser.py       ← Parse Kafka message → dict
    └── depth_filter.py       ← Top N levels filter
```

### Flink job (`pipeline.py`)

```python
"""Flink job: aggregate Binance data → Redis + InfluxDB.

Source: Kafka topics (crypto_ticker, crypto_klines, crypto_depth)
Sink 1: Redis (real-time serving)
Sink 2: InfluxDB (time-series storage)
"""
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import ProcessWindowFunction, KeyedProcessFunction
from pyflink.common.typeinfo import Types
from pyflink.common.time import Time
import json

# ── Khởi tạo Flink environment ──
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(12)  # 12 parallel tasks

# ── Đọc từ Kafka ──
# Mỗi topic có thể dùng source riêng
ticker_stream = (
    env.add_source(
        FlinkKafkaConsumer(
            topics=["crypto_ticker"],
            deserialization_schema=SimpleStringSchema(),
            properties={"bootstrap.servers": "kafka-1:9092,kafka-2:9092,kafka-3:9092"}
        )
    )
    .name("kafka-ticker-source")
)

# ── Parse JSON ──
parsed_ticker = (
    ticker_stream
    .map(lambda x: json.loads(x), output_type=Types.MAP(Types.STRING(), Types.STRING()))
    .name("parse-json")
)

# ── Filter valid ──
valid_ticker = (
    parsed_ticker
    .filter(lambda d: d.get("s") is not None and d.get("c") is not None)
    .name("filter-valid")
)

# ── Key theo symbol ──
keyed = valid_ticker.key_by(lambda d: d.get("s"))

# ── Ghi xuống Redis ──
def write_to_redis(ticker_dict):
    """Ghi 1 ticker message xuống Redis hash."""
    import redis
    r = redis.Redis(host="redis-master", port=6379, decode_responses=False)
    symbol = ticker_dict["s"]
    key = f"ticker:latest:binance:{symbol}"
    mapping = {
        "price": ticker_dict["c"],
        "bid": ticker_dict.get("b", ""),
        "ask": ticker_dict.get("a", ""),
        "event_time": str(ticker_dict.get("E", "")),
        # ... 20+ fields
    }
    r.hset(key, mapping=mapping)
    r.expire(key, 300)

valid_ticker.map(write_to_redis).name("redis-writer")
```

### Kline Aggregator (1s → 1m/5m/1h/1d)

```python
"""Aggregate raw 1s klines thành 1m, 5m, 1h, 1d candles.

Logic:
- Input: stream of 1s kline events
- Group by (symbol, interval) → window by time → aggregate
- Output: 1 candle per window
"""

class KlineAggregator(KeyedProcessFunction):
    """Aggregate OHLCV trong time window."""

    def __init__(self, output_interval_ms):
        """
        Args:
            output_interval_ms: 60000 (1m), 300000 (5m), 3600000 (1h)
        """
        self.output_interval_ms = output_interval_ms
        self.state = {}  # {symbol: {open, high, low, close, volume, window_start}}

    def process_element(self, value, ctx):
        symbol = value["symbol"]
        interval = value["interval"]  # "1s" từ Binance
        close_time = value["close_time"]
        bucket = (close_time // self.output_interval_ms) * self.output_interval_ms

        if symbol not in self.state or self.state[symbol]["window_start"] != bucket:
            # New window → emit old, start new
            if symbol in self.state:
                yield self.state[symbol]  # emit completed candle
            self.state[symbol] = {
                "symbol": symbol,
                "interval": self._interval_name(),
                "open": value["open"],
                "high": value["high"],
                "low": value["low"],
                "close": value["close"],
                "volume": value["volume"],
                "window_start": bucket,
            }
        else:
            # Update running aggregation
            s = self.state[symbol]
            s["high"] = max(s["high"], value["high"])
            s["low"] = min(s["low"], value["low"])
            s["close"] = value["close"]
            s["volume"] += value["volume"]
```

### Flink writers

#### `keydb_kline.py`

```python
"""Ghi candles xuống Redis (KeyDB = Redis fork).

Key: kline:candles:{exchange}:{symbol}:{interval}
Type: sorted set
Score: close_time_ms
Member: JSON {open, high, low, close, volume}

⚠️ QUAN TRỌNG: Phải ZREMRANGEBYSCORE trước khi ZADD để tránh duplicate.
"""

async def write_candle(redis_client, exchange, symbol, interval, candle):
    key = f"kline:candles:{exchange}:{symbol}:{interval}"
    score = candle["close_time"]
    member = json.dumps({
        "o": candle["open"],
        "h": candle["high"],
        "l": candle["low"],
        "c": candle["close"],
        "v": candle["volume"],
    })

    pipe = redis_client.pipeline(transaction=False)
    # Remove existing member with same score (nếu có)
    pipe.zremrangebyscore(key, score, score)
    pipe.zadd(key, {member: score})
    pipe.expire(key, 86400)  # 24h TTL
    await pipe.execute()
```

#### `keydb_depth.py`

```python
"""Ghi order book xuống Redis.

Key: orderbook:{symbol}
Type: hash (chứa bids, asks, lastUpdateId)

⚠️ CAVEAT: Hiện tại KHÔNG có exchange trong key.
Đây là bug đã biết — multi-exchange orderbook sẽ collide.
"""

async def write_depth(redis_client, symbol, depth_data):
    key = f"orderbook:{symbol}"  # ← bug: thiếu exchange
    pipe = redis_client.pipeline(transaction=False)
    pipe.hset(key, mapping={
        "bids": json.dumps(depth_data["bids"]),
        "asks": json.dumps(depth_data["asks"]),
        "lastUpdateId": str(depth_data["lastUpdateId"]),
    })
    pipe.expire(key, 60)  # Order book stale sau 60s
    await pipe.execute()
```

## 26. Avro Schemas (`schemas/*.avsc`)

### Tại sao dùng Avro thay vì JSON?

| | JSON | Avro |
|---|---|---|
| Size | Lớn (key + value mỗi lần) | Nhỏ (binary, có schema đính kèm) |
| Schema | Không enforce | Enforce + version |
| Evolution | Phải update cả producer + consumer | Backward compatible (mặc định) |
| Speed | Parse chậm | Parse nhanh (binary) |

### `ticker.avsc`

```json
{
  "type": "record",
  "name": "TickerEvent",
  "namespace": "com.lmview.ticker",
  "fields": [
    {"name": "s", "type": "string", "doc": "Symbol (BTCUSDT)"},
    {"name": "E", "type": "long", "doc": "Event time (ms)"},
    {"name": "c", "type": "string", "doc": "Close price"},
    {"name": "b", "type": "string", "doc": "Best bid price"},
    {"name": "a", "type": "string", "doc": "Best ask price"},
    {"name": "B", "type": "string", "doc": "Best bid qty"},
    {"name": "A", "type": "string", "doc": "Best ask qty"},
    {"name": "v", "type": "string", "doc": "Volume 24h"},
    {"name": "q", "type": "string", "doc": "Quote volume 24h"},
    {"name": "P", "type": "string", "doc": "Price change %"},
    {"name": "p", "type": "string", "doc": "Price change abs"},
    {"name": "w", "type": "string", "doc": "Weighted avg"},
    {"name": "o", "type": "string", "doc": "Open 24h"},
    {"name": "h", "type": "string", "doc": "High 24h"},
    {"name": "l", "type": "string", "doc": "Low 24h"},
    {"name": "Q", "type": "string", "doc": "Last qty"},
    {"name": "F", "type": "long", "doc": "First trade ID"},
    {"name": "L", "type": "long", "doc": "Last trade ID"},
    {"name": "n", "type": "long", "doc": "Num trades 24h"},
    {"name": "O", "type": "long", "doc": "Open time 24h"},
    {"name": "C", "type": "long", "doc": "Close time 24h"}
  ]
}
```

### `kline.avsc`

```json
{
  "type": "record",
  "name": "KlineEvent",
  "namespace": "com.lmview.kline",
  "fields": [
    {"name": "s", "type": "string"},
    {"name": "k", "type": {
      "type": "record",
      "name": "Kline",
      "fields": [
        {"name": "t", "type": "long", "doc": "Kline start time"},
        {"name": "T", "type": "long", "doc": "Kline close time"},
        {"name": "s", "type": "string", "doc": "Symbol"},
        {"name": "i", "type": "string", "doc": "Interval (1s, 1m, ...)"},
        {"name": "o", "type": "string", "doc": "Open price"},
        {"name": "c", "type": "string", "doc": "Close price"},
        {"name": "h", "type": "string", "doc": "High price"},
        {"name": "l", "type": "string", "doc": "Low price"},
        {"name": "v", "type": "string", "doc": "Volume"},
        {"name": "n", "type": "long", "doc": "Num trades"},
        {"name": "x", "type": "boolean", "doc": "Is closed?"},
        {"name": "q", "type": "string", "doc": "Quote volume"}
      ]
    }}
  ]
}
```

### `depth.avsc`

```json
{
  "type": "record",
  "name": "DepthEvent",
  "namespace": "com.lmview.depth",
  "fields": [
    {"name": "s", "type": "string"},
    {"name": "U", "type": "long", "doc": "First update ID"},
    {"name": "u", "type": "long", "doc": "Final update ID"},
    {"name": "b", "type": {
      "type": "array",
      "items": {
        "type": "record",
        "name": "BidAsk",
        "fields": [
          {"name": "price", "type": "string"},
          {"name": "qty", "type": "string"}
        ]
      }
    }, "doc": "Bids"},
    {"name": "a", "type": {"...same as b..."}, "doc": "Asks"}
  ]
}
```

### Schema evolution

Khi cần thêm field mới (vd: thêm `volume_24h_quote`), chỉ cần:
1. Thêm field vào cuối `.avsc` (không xóa field cũ)
2. Update schema registry (auto-detect)
3. Producer/Consumer mới đọc được cả field cũ + mới

Field cũ KHÔNG được xóa → đảm bảo backward compatibility.

<!-- Kết thúc Phần 3. Tiếp theo: Phần 4 — Tầng phục vụ -->
# Phần 4 — Tầng Phục Vụ (Serving Layer)

> **Giải thích:** Phần này đi sâu vào BACKEND (FastAPI). Đây là phần gần browser nhất. Nó đọc Redis → build payload → đẩy qua WebSocket.
>
> Code quan trọng nhất: `backend/api/websocket.py` (~1000 dòng). Ta sẽ giải thích từng hàm.

## 27. Backend WebSocket API — Toàn Cảnh

### File `backend/api/websocket.py`

File này có 6 hàm chính:

| Hàm | Vai trò |
|---|---|
| `websocket_klines_endpoint` | Stream 1 timeframe duy nhất |
| `websocket_all_timeframes_endpoint` | Stream 8 timeframes + ticker (quan trọng nhất) |
| `websocket_indicators_endpoint` | Stream indicators cho 1 timeframe |
| `_stream_all_impl` | Inner loop cho all-timeframes |
| `_build_candle_from_data` | Helper build candle từ Redis data |
| `_stream_indicators_impl` | Inner loop cho indicators |

### Cấu trúc request

```
Browser WS: wss://lmview.duckdns.org/api/stream/all?symbol=BTCUSDT&exchange=binance

Query params:
  - symbol: BTCUSDT (bắt buộc)
  - exchange: binance (default)
```

### Backend đẩy gì?

Mỗi 50ms, backend gửi 1 message JSON:

```json
{
  "1m": {"time": 1781937600, "open": 63300.01, "high": 63743.9, "low": 63300.01, "close": 63700.02, "volume": 0},
  "5m": {"time": 1781937300, "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...},
  "15m": {...},
  "1h": {...},
  "4h": {...},
  "1d": {...},
  "1w": {...},
  "_ticker": {
    "price": "63700.02",
    "event_time": 1781937642016,
    "bid": "63699.90",
    "ask": "63700.10",
    "bid_qty": "0.500",
    "ask_qty": "0.450",
    "volume": "12345.67",
    "quote_volume": "789012345.6",
    "change_pct": "2.5",
    "change_abs": "1500.10",
    "weighted_avg": "63000.00",
    "open_24h": "62200.00",
    "high_24h": "64000.00",
    "low_24h": "61500.00",
    "last_qty": "0.001"
  }
}
```

### Code đầy đủ `backend/api/websocket.py`

```python
"""WebSocket endpoints cho real-time market data.

Endpoints:
- /api/stream/{interval}?symbol=BTCUSDT → stream 1 interval
- /api/stream/all?symbol=BTCUSDT → stream 8 intervals + ticker
- /api/stream/indicators/{interval}?symbol=BTCUSDT → stream indicators
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import asyncio
import json
import logging
import time

from backend.core.redis_sentinel import get_redis_client
from backend.services.candle_service import (
    fetch_candles_with_fallback,
    CandleSource,
)
from backend.core.constants import ALL_INTERVALS

log = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ──
# Tất cả interval được stream cùng lúc trong /api/stream/all
STREAM_ALL_INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]

# Push frequency (ms)
PUSH_INTERVAL_MS = 50  # 20 Hz push rate (giảm từ 0.3s xuống 50ms trong v0.25.45)


@router.websocket("/stream/{interval}")
async def websocket_klines_endpoint(
    websocket: WebSocket,
    interval: str,
    symbol: str = Query(...),
    exchange: str = Query(default="binance"),
):
    """Stream 1 interval duy nhất.

    Flow:
    1. Accept WS connection
    2. Gửi snapshot ban đầu (200 candles gần nhất)
    3. Vào loop: mỗi 50ms đọc Redis → gửi update nếu có thay đổi
    4. Khi client disconnect → cleanup
    """
    if interval not in ALL_INTERVALS:
        await websocket.close(code=4000, reason=f"Invalid interval: {interval}")
        return

    await websocket.accept()
    log.info("WS /stream/%s connected symbol=%s exchange=%s", interval, symbol, exchange)

    redis = await get_redis_client()
    last_candle_time = 0  # Track candle đã gửi cuối cùng
    last_ticker_ts = 0    # Track ticker đã gửi cuối cùng (added v0.25.46)

    try:
        # 1. Gửi snapshot ban đầu
        candles = await fetch_candles_with_fallback(
            symbol=symbol,
            interval=interval,
            exchange=exchange,
            limit=500,
        )
        for candle in candles[-200:]:  # Chỉ gửi 200 candles gần nhất
            payload = _build_candle_from_data(interval, candle)
            await websocket.send_bytes(json.dumps(payload).encode())
            last_candle_time = candle["close_time"]

        # 2. Loop push update mỗi 50ms
        while True:
            await asyncio.sleep(PUSH_INTERVAL_MS / 1000.0)

            # Read latest candle từ Redis
            latest = await _read_latest_candle(redis, exchange, symbol, interval)

            ticker_updated = False
            candle_changed = False

            # Check candle change
            if latest and latest["close_time"] != last_candle_time:
                last_candle_time = latest["close_time"]
                candle_changed = True

            # Check ticker change (cho _ticker field)
            ticker = await _read_latest_ticker(redis, exchange, symbol)
            if ticker and ticker.get("event_time"):
                ts = int(ticker["event_time"])
                if ts > last_ticker_ts:
                    last_ticker_ts = ts
                    ticker_updated = True

            # Chỉ gửi nếu có thay đổi (v0.25.46 fix: thêm ticker_updated)
            if candle_changed or ticker_updated:
                payload = _build_candle_from_data(interval, latest or {})
                if ticker:
                    payload["_ticker"] = ticker
                await websocket.send_bytes(json.dumps(payload).encode())

    except WebSocketDisconnect:
        log.info("WS /stream/%s disconnected symbol=%s", interval, symbol)
    except Exception as e:
        log.exception("WS /stream/%s error: %s", interval, e)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass


@router.websocket("/stream/all")
async def websocket_all_timeframes_endpoint(
    websocket: WebSocket,
    symbol: str = Query(...),
    exchange: str = Query(default="binance"),
):
    """Stream 8 timeframes + ticker cùng lúc.

    Đây là endpoint quan trọng nhất — chart chính dùng nó.

    Push rate: mỗi 50ms (20 Hz)
    Payload: dict {interval1: candle, interval2: candle, ..., "_ticker": {...}}
    """
    await websocket.accept()
    log.info("WS /stream/all connected symbol=%s exchange=%s", symbol, exchange)

    await _stream_all_impl(websocket, symbol, exchange)


async def _stream_all_impl(websocket: WebSocket, symbol: str, exchange: str):
    """Inner loop cho /stream/all.

    Giải thích:
    - Mỗi 50ms, đọc Redis cho 8 timeframes + ticker
    - Chỉ push nếu có thay đổi (candle close_time mới HOẶC ticker event_time mới)
    - Bug v0.25.45: push condition quá chặt → chart không update giữa bucket rollover
    - Fix v0.25.46: thêm last_ticker_ts tracking, push khi ticker update
    """
    redis = await get_redis_client()

    # Track state cho mỗi interval
    last_candle_times = {tf: 0 for tf in STREAM_ALL_INTERVALS}
    last_ticker_ts = 0  # ← Added v0.25.46

    # Initial snapshot
    snapshot = await _build_initial_snapshot(redis, symbol, exchange)
    if snapshot:
        await websocket.send_bytes(json.dumps(snapshot).encode())
        for tf in STREAM_ALL_INTERVALS:
            if tf in snapshot:
                last_candle_times[tf] = snapshot[tf].get("close_time", 0)
        if "_ticker" in snapshot:
            last_ticker_ts = snapshot["_ticker"].get("event_time", 0)

    try:
        while True:
            await asyncio.sleep(PUSH_INTERVAL_MS / 1000.0)

            payload = {}
            any_changed = False
            ticker_updated = False

            # ── Đọc 8 intervals ──
            for interval in STREAM_ALL_INTERVALS:
                latest = await _read_latest_candle(redis, exchange, symbol, interval)
                if latest is None:
                    continue

                if latest["close_time"] != last_candle_times[interval]:
                    last_candle_times[interval] = latest["close_time"]
                    any_changed = True

                payload[interval] = _build_candle_from_data(interval, latest)

            # ── Đọc ticker ──
            ticker = await _read_latest_ticker(redis, exchange, symbol)
            if ticker and ticker.get("event_time"):
                ts = int(ticker["event_time"])
                if ts > last_ticker_ts:
                    last_ticker_ts = ts
                    ticker_updated = True
                    payload["_ticker"] = ticker
                elif "_ticker" not in payload:
                    # Bao gồm ticker ngay cả khi không update (cho lần đầu)
                    payload["_ticker"] = ticker

            # ── Push nếu có thay đổi (v0.25.46 fix) ──
            # Trước đây: if any_changed:  ← quá chặt
            # Bây giờ: if any_changed or ticker_updated:  ← push ~1Hz regardless
            if any_changed or ticker_updated:
                await websocket.send_bytes(json.dumps(payload).encode())

    except WebSocketDisconnect:
        log.info("WS /stream/all disconnected symbol=%s", symbol)
    except Exception as e:
        log.exception("WS /stream/all error: %s", e)


def _build_candle_from_data(interval: str, candle: dict) -> dict:
    """Build payload từ Redis candle data.

    Redis lưu {o, h, l, c, v} (compact).
    Frontend cần {time, open, high, low, close, volume}.
    Conversion ở đây.
    """
    return {
        "time": candle.get("close_time", 0) // 1000,  # ms → seconds (lightweight-charts)
        "open": float(candle.get("o", 0)),
        "high": float(candle.get("h", 0)),
        "low": float(candle.get("l", 0)),
        "close": float(candle.get("c", 0)),
        "volume": float(candle.get("v", 0)),
    }


async def _read_latest_candle(redis, exchange, symbol, interval) -> Optional[dict]:
    """Đọc candle mới nhất từ Redis sorted set.

    Redis key: kline:candles:{exchange}:{symbol}:{interval}
    Sorted set: score=close_time, member=JSON

    Returns dict {o, h, l, c, v, close_time} hoặc None.
    """
    key = f"kline:candles:{exchange}:{symbol}:{interval}"
    # ZRANGE -1 -1 = lấy member cuối (score lớn nhất = candle mới nhất)
    rows = await redis.zrange(key, -1, -1, withscores=True)
    if not rows:
        return None

    member, score = rows[0]
    candle = json.loads(member)
    candle["close_time"] = int(score)
    return candle


async def _read_latest_ticker(redis, exchange, symbol) -> Optional[dict]:
    """Đọc ticker mới nhất từ Redis hash.

    Redis key: ticker:latest:{exchange}:{symbol}
    Hash với 20-24 fields.

    Returns dict các fields hoặc None.
    """
    key = f"ticker:latest:{exchange}:{symbol}"
    data = await redis.hgetall(key)
    if not data:
        return None

    # Decode bytes thành string (Redis async trả bytes nếu decode_responses=False)
    result = {}
    for k, v in data.items():
        key_str = k.decode() if isinstance(k, bytes) else k
        val_str = v.decode() if isinstance(v, bytes) else v
        result[key_str] = val_str

    return result


async def _build_initial_snapshot(redis, symbol, exchange) -> dict:
    """Build initial snapshot (200 candles cho mỗi interval + ticker).

    Gửi 1 lần khi client connect, sau đó vào loop update.
    """
    snapshot = {}

    # Snapshot 200 candles gần nhất cho mỗi interval
    for interval in STREAM_ALL_INTERVALS:
        candles = await fetch_candles_with_fallback(
            symbol=symbol,
            interval=interval,
            exchange=exchange,
            limit=200,
        )
        if candles:
            snapshot[interval] = _build_candle_from_data(interval, candles[-1])

    # Snapshot ticker
    ticker = await _read_latest_ticker(redis, exchange, symbol)
    if ticker:
        snapshot["_ticker"] = ticker

    return snapshot
```

## 28. Forming Candle Algorithm

### Vấn đề cần giải

Khi chart đang hiển thị candles 1m:
- 9:30:00 — 9:30:59 → candle đã đóng (closed)
- 9:31:00 — 9:31:59 → candle đang hình thành (forming)

Làm sao vẽ candle 9:31:00 mà biết open = close của candle 9:30:00?

### Invariant quan trọng

**Open của candle mới = Close của candle trước.**

Nếu candle 9:30:00 close = 63300.01, thì candle 9:31:00 open = 63300.01.

### 4 trường hợp

#### Case 1: Same bucket as last update (phổ biến nhất)

```python
# 9:31:15 — ticker đến
# forming candle đang là 9:31:00
# → update high/low/close, giữ nguyên open

if forming and forming.time == bucketTime:
    nextCandle = {
        "open": forming.open,                          # ← giữ nguyên
        "high": max(forming.high, price),              # ← accumulate
        "low": min(forming.low, price),                # ← accumulate
        "close": price,                                 # ← update
    }
```

#### Case 2: Bucket boundary crossed (phút mới)

```python
# 9:32:00 — ticker đến, bucket = 9:32:00
# forming candle vẫn là 9:31:00
# → promote forming thành lastClosed, tạo candle mới

elif forming and forming.time < bucketTime:
    lastClosedCandleRef = forming  # ← forming cũ giờ là closed
    open = forming.close  # ← open mới = close cũ
    nextCandle = {"time": bucketTime, "open": open, ...}
```

#### Case 3: First tick after F5 (không có forming)

```python
# Sau khi F5, chưa có ticker nào → forming = None
# Ticker đầu tiên → tạo forming từ lastClosed

elif not forming and lastClosed:
    open = lastClosed.close
    nextCandle = {"time": bucketTime, "open": open, ...}
```

#### Case 4: Edge case

```python
else:
    return  # Không có gì để làm, bỏ qua
```

## 29. REST API Reference

### Bảng endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/klines?symbol=BTCUSDT&interval=1m&limit=500` | Lấy candles |
| GET | `/api/klines/historical?symbol=BTCUSDT&interval=1m&start=...&end=...` | Historical candles |
| GET | `/api/ticker/{symbol}?exchange=binance` | Current ticker |
| GET | `/api/orderbook/{symbol}?exchange=binance&depth=20` | Order book |
| GET | `/api/trades/{symbol}?exchange=binance&limit=100` | Recent trades |
| GET | `/api/symbols` | List symbols |
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/settings` | User settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/market/overview` | Market overview (top movers) |
| GET | `/api/indicators/{symbol}/series?interval=1m&indicator=rsi` | Indicator series |
| GET | `/api/admin/*` | Admin endpoints |

### Ví dụ response

`GET /api/klines?symbol=BTCUSDT&interval=1m&limit=2`:
```json
{
  "symbol": "BTCUSDT",
  "interval": "1m",
  "candles": [
    {"time": 1781937600, "open": 63300.01, "high": 63500, "low": 63200, "close": 63400, "volume": 123.45},
    {"time": 1781937660, "open": 63400, "high": 63743.9, "low": 63300.01, "close": 63700.02, "volume": 150.32}
  ]
}
```

`GET /api/ticker/BTCUSDT`:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "price": 63700.02,
  "bid": 63699.90,
  "ask": 63700.10,
  "volume_24h": 12345.67,
  "change_pct_24h": 2.5,
  "high_24h": 64000,
  "low_24h": 61500,
  "event_time": 1781937642016
}
```

## 30. Candle Service Assembly Logic

### Vấn đề

Khi frontend gọi `GET /api/klines?symbol=BTCUSDT&interval=1m`, lấy candles từ đâu?

**Nhiều nguồn có thể:**
1. Redis (nhanh nhất, nhưng chỉ có candles gần đây, ~1500 candles)
2. InfluxDB (chậm hơn, có 90 ngày)
3. Iceberg (chậm nhất, có cả năm)

### `candle_service.py`

```python
"""Service assembly cho candles.

Logic fallback:
1. Thử Redis trước (nhanh nhất)
2. Nếu Redis thiếu → InfluxDB
3. Nếu InfluxDB cũng thiếu → Iceberg
4. Cuối cùng → empty array
"""

from enum import Enum
from typing import List, Optional

class CandleSource(str, Enum):
    REDIS = "redis"
    INFLUXDB = "influxdb"
    ICEBERG = "iceberg"

async def fetch_candles_with_fallback(
    symbol: str,
    interval: str,
    exchange: str = "binance",
    limit: int = 500,
) -> List[dict]:
    """Lấy candles với multi-source fallback."""

    # ── Thử Redis ──
    candles = await _fetch_from_redis(symbol, interval, exchange, limit)
    if len(candles) >= limit:
        return candles  # Đủ → trả về

    # ── Fallback: InfluxDB ──
    remaining = limit - len(candles)
    older = await _fetch_from_influxdb(symbol, interval, exchange, remaining)
    candles = older + candles  # Concatenate (cũ hơn ở trước)
    if len(candles) >= limit:
        return candles

    # ── Fallback: Iceberg ──
    remaining = limit - len(candles)
    oldest = await _fetch_from_iceberg(symbol, interval, exchange, remaining)
    candles = oldest + candles
    return candles


async def _fetch_from_redis(symbol, interval, exchange, limit) -> List[dict]:
    """Đọc từ Redis sorted set."""
    redis = await get_redis_client()
    key = f"kline:candles:{exchange}:{symbol}:{interval}"
    # ZREVRANGE = lấy từ mới nhất trở về cũ
    rows = await redis.zrevrange(key, 0, limit - 1, withscores=True)

    candles = []
    for member, score in rows:
        candle = json.loads(member)
        candle["close_time"] = int(score)
        candles.append(candle)
    return candles


async def _fetch_from_influxdb(symbol, interval, exchange, limit) -> List[dict]:
    """Query InfluxDB."""
    query = f'''
    from(bucket: "crypto")
      |> range(start: -90d)
      |> filter(fn: (r) => r._measurement == "candles"
                          and r.symbol == "{symbol}"
                          and r.exchange == "{exchange}"
                          and r.interval == "{interval}")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {limit})
    '''
    # Execute query + parse → List[dict]


async def _fetch_from_iceberg(symbol, interval, exchange, limit) -> List[dict]:
    """Query Iceberg via Trino."""
    query = f'''
    SELECT open_time, open, high, low, close, volume
      FROM iceberg.crypto.silver_klines
     WHERE symbol = '{symbol}'
       AND exchange = '{exchange}'
       AND interval = '{interval}'
     ORDER BY open_time DESC
     LIMIT {limit}
    '''
    # Execute via Trino client → List[dict]
```

<!-- Kết thúc Phần 4. Tiếp theo: Phần 5 — Frontend -->
# Phần 5 — Frontend (Phần Trình Duyệt)

> **Giải thích:** Phần này giải thích cách React app ở trình duyệt nhận dữ liệu real-time từ backend và vẽ biểu đồ. Đây là phần "gần người dùng" nhất.
>
> Code quan trọng nhất: `frontend/src/services/marketDataService.ts` (~500 dòng). Ta sẽ giải thích từng hàm, đặc biệt là cách sửa lỗi Blob parse bug.

## 31. Frontend Data Service (`marketDataService.ts`)

### File này là gì?

`marketDataService.ts` là **service trung tâm** cho mọi dữ liệu thị trường ở frontend. Mọi component cần candles/ticker đều gọi qua đây.

### Cấu trúc file

```
frontend/src/services/marketDataService.ts
├── parseWsData()               ← Helper xử lý Blob/string/ArrayBuffer
├── mapRawToCandle()            ← Convert backend format → frontend format
├── fetchCandles()              ← REST API: lấy candles
├── subscribeCandle()           ← WS: stream 1 interval
├── subscribeAllTimeframes()    ← WS: stream 8 intervals + ticker (QUAN TRỌNG NHẤT)
├── subscribeIndicatorStream()  ← WS: stream indicators
├── createReconnectingWebSocket() ← Helper WS reconnect
└── fetchSymbols()              ← REST: lấy danh sách symbols
```

### Code đầy đủ (annotated — giải thích từng dòng)

```typescript
/**
 * marketDataService.ts
 *
 * Service layer cho tất cả dữ liệu thị trường.
 * - REST: fetchCandles(), fetchHistoricalCandles(), fetchSymbols()
 * - WebSocket: subscribeCandle(), subscribeAllTimeframes(), subscribeIndicatorStream()
 *
 * QUAN TRỌNG: Component KHÔNG BAO GIỜ gọi fetch() trực tiếp.
 * Luôn qua service này để:
 * - Centralize error handling
 * - Centralize retry logic
 * - Centralize caching (future)
 */

// ════════════════════════════════════════════════════════════════════════
// TYPE DEFINITIONS
// ════════════════════════════════════════════════════════════════════════

export interface Candle {
  /** Unix timestamp in SECONDS (lightweight-charts requires seconds) */
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StreamTickerPayload {
  /** Giá hiện tại */
  price: number;
  /** Event time từ Binance (ms) */
  eventTime: number;
  /** Thay đổi 24h (%) */
  change24h: number;
  /** Volume 24h */
  volume: number;
  // Extended fields (v0.25.45+):
  change_pct?: number;
  change_abs?: number;
  quote_volume?: number;
  bid?: number;
  ask?: number;
  bid_qty?: number;
  ask_qty?: number;
  weighted_avg?: number;
  open_24h?: number;
  high_24h?: number;
  low_24h?: number;
  last_qty?: number;
  activity_score?: number;
}

// ════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ════════════════════════════════════════════════════════════════════════

/** Data source: 'api' (production) hoặc 'mock' (dev) */
const DATA_SOURCE = (import.meta.env.VITE_DATA_SOURCE as string) ?? "api";

/** WebSocket base URL. VITE_ prefix = đọc từ .env lúc build */
function getWsBaseUrl(): string {
  const base = import.meta.env.VITE_WS_BASE_URL ?? "wss://lmview.duckdns.org/api";
  return base;
}

/** REST API base URL */
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";


// ════════════════════════════════════════════════════════════════════════
// parseWsData — QUAN TRỌNG NHẤT (sửa bug v0.25.47)
// ════════════════════════════════════════════════════════════════════════

/**
 * Parse WebSocket message data (string | Blob | ArrayBuffer) → JSON.
 *
 * TẠI SAO CẦN HÀM NÀY?
 * ────────────────────
 * Backend FastAPI dùng `await websocket.send_bytes(json.dumps(...).encode())`.
 * `send_bytes` tạo WebSocket BINARY frame. Trình duyệt nhận binary frame
 * dưới dạng `Blob`, KHÔNG phải string.
 *
 * Code cũ (BUG):
 * ```ts
 * const data = JSON.parse(e.data as string);  // ❌ CRASHES on Blob!
 * // Error: "Unexpected token 'o', "[object Blob]" is not valid JSON"
 * ```
 *
 * Code mới (FIXED v0.25.47):
 * ```ts
 * const data = await parseWsData(e.data);  // ✅ handles Blob/string/ArrayBuffer
 * ```
 *
 * BÀI HỌC:
 * Python `websockets` client mặc định TEXT mode → KHÔNG phát hiện bug này.
 * Phải test với trình duyệt THẬT (Playwright) để bắt.
 */
async function parseWsData<T = unknown>(
  data: MessageEvent["data"]
): Promise<T> {
  // Case 1: string (text frame) — phổ biến nhất nếu backend dùng send_text
  if (typeof data === "string") {
    return JSON.parse(data) as T;
  }

  // Case 2: Blob (binary frame từ send_bytes) — GÂY RA BUG
  // Phải convert Blob → text trước rồi mới JSON.parse
  if (data instanceof Blob) {
    const text = await data.text();  // ← Đây là chìa khóa
    return JSON.parse(text) as T;
  }

  // Case 3: ArrayBuffer (binary raw)
  if (data instanceof ArrayBuffer) {
    const text = new TextDecoder().decode(new Uint8Array(data));
    return JSON.parse(text) as T;
  }

  // Case 4: Fallback (không nên xảy ra)
  return JSON.parse(String(data)) as T;
}


// ════════════════════════════════════════════════════════════════════════
// mapRawToCandle — Convert backend → frontend format
// ════════════════════════════════════════════════════════════════════════

/**
 * Backend gửi: {openTime, open, high, low, close, volume}
 * Frontend cần: {time, open, high, low, close, volume}
 *
 * CHÚ Ý: lightweight-charts YÊU CẦU time là SECONDS (Unix epoch).
 * Backend gửi milliseconds → phải chia 1000.
 *
 * Đây là "service boundary" conversion.
 */
function mapRawToCandle(raw: any): Candle {
  return {
    time: Math.floor(raw.openTime / 1000),  // ms → seconds
    open: Number(raw.open),
    high: Number(raw.high),
    low: Number(raw.low),
    close: Number(raw.close),
    volume: Number(raw.volume),
  };
}


// ════════════════════════════════════════════════════════════════════════
// fetchCandles — REST: lấy candles ban đầu
// ════════════════════════════════════════════════════════════════════════

/**
 * Lấy candles cho 1 interval qua REST API.
 *
 * @param symbol - "BTCUSDT"
 * @param interval - "1m", "5m", "1h", ...
 * @param limit - số candles (default 500)
 * @returns Promise<Candle[]>
 */
export async function fetchCandles(
  symbol: string,
  interval: string,
  limit: number = 500
): Promise<Candle[]> {
  if (DATA_SOURCE === "mock") {
    return mockDataAdapter.fetchCandles(symbol, interval, limit);
  }

  const url = `${API_BASE}/klines?${new URLSearchParams({
    symbol,
    interval,
    limit: limit.toString(),
  })}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`fetchCandles failed: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  return data.candles.map(mapRawToCandle);
}


// ════════════════════════════════════════════════════════════════════════
// subscribeAllTimeframes — WS: stream 8 intervals + ticker
// ════════════════════════════════════════════════════════════════════════

/**
 * Subscribe WebSocket stream cho 8 intervals + ticker.
 *
 * Đây là endpoint CHÍNH mà chart dùng.
 * Backend sẽ đẩy mỗi 50ms (20 Hz) nếu có thay đổi.
 *
 * @param options.symbol - "BTCUSDT"
 * @param options.exchange - "binance" (default)
 * @param options.onCandle - callback(tf, candle) khi có candle update
 * @param options.onTicker - callback(ticker) khi có ticker update
 * @returns cleanup function — gọi để unsubscribe
 */
export function subscribeAllTimeframes(options: {
  symbol: string;
  exchange?: string;
  onCandle: (timeframe: string, candle: Candle) => void;
  onTicker?: (ticker: StreamTickerPayload) => void;
  onError?: (error: Event) => void;
}): () => void {
  const { symbol, exchange = "binance", onCandle, onTicker, onError } = options;

  if (DATA_SOURCE === "mock") {
    return mockDataAdapter.subscribeAllTimeframes(symbol, onCandle, onTicker);
  }

  // Build WS URL
  const params = new URLSearchParams({ symbol, exchange });
  const wsUrl = `${getWsBaseUrl()}/stream/all?${params}`;

  // Tạo WS connection (tự động reconnect)
  const { cleanup } = createReconnectingWebSocket(wsUrl, {
    onMessage: async (event: MessageEvent) => {
      try {
        // ← DÙNG parseWsData() — không crash trên Blob
        const data = await parseWsData<Record<string, any>>(event.data);

        // ── Xử lý ticker ──
        // Backend gửi { _ticker: {...} } — key bắt đầu bằng _
        if (data._ticker && data._ticker.price != null) {
          const ticker: StreamTickerPayload = {
            price: Number(data._ticker.price),
            eventTime: data._ticker.event_time ?? data._ticker.eventTime ?? Date.now(),
            change24h: Number(data._ticker.change24h) || 0,
            volume: Number(data._ticker.volume) || 0,
            change_pct: Number(data._ticker.change_pct) || 0,
            change_abs: Number(data._ticker.change_abs) || 0,
            quote_volume: Number(data._ticker.quote_volume) || 0,
            bid: Number(data._ticker.bid) || 0,
            ask: Number(data._ticker.ask) || 0,
            bid_qty: Number(data._ticker.bid_qty) || 0,
            ask_qty: Number(data._ticker.ask_qty) || 0,
            weighted_avg: Number(data._ticker.weighted_avg) || 0,
            open_24h: Number(data._ticker.open_24h) || 0,
            high_24h: Number(data._ticker.high_24h) || 0,
            low_24h: Number(data._ticker.low_24h) || 0,
            last_qty: Number(data._ticker.last_qty) || 0,
            activity_score: Number(data._ticker.activity_score) || 0,
          };

          // Gọi callback
          onTicker?.(ticker);
        }

        // ── Xử lý candles ──
        // Iterate tất cả keys trừ _ticker
        for (const [key, value] of Object.entries(data)) {
          if (key.startsWith("_")) continue;  // Bỏ qua _ticker
          if (value && typeof value === "object") {
            onCandle(normalizeTimeframe(key), mapRawToCandle(value));
          }
        }
      } catch (err) {
        console.error("[WS stream/all parse error]", err);
        // KHÔNG throw — để WS tiếp tục nhận frame tiếp theo
      }
    },
    onError: onError || ((err) => console.error("[WS stream/all error]", err)),
  });

  return cleanup;
}


/** Normalize timeframe string ("1M" → "1m") */
function normalizeTimeframe(tf: string): string {
  return tf.toLowerCase();
}


// ════════════════════════════════════════════════════════════════════════
// createReconnectingWebSocket — Helper WS reconnect
// ════════════════════════════════════════════════════════════════════════

/**
 * Tạo WebSocket với:
 * 1. Exponential backoff reconnect
 * 2. Unlimited retries (KHÔNG giới hạn)
 * 3. 45s watchdog (force-close nếu không nhận data)
 *
 * TẠI SAO QUAN TRỌNG?
 * ─────────────────────
 * Bug v0.25.46: Frontend cũ có MAX_RECONNECT_RETRIES = 5.
 * Sau 5 lần fail, WS bị bỏ rơi → user phải F5.
 *
 * Browser idle cũng có thể kill WS silent (readyState=OPEN nhưng
 * không nhận frame). Watchdog bắt trường hợp này.
 */

const MAX_RECONNECT_DELAY_MS = 30_000;  // Cap backoff ở 30s
const BASE_RECONNECT_DELAY_MS = 1_000;  // Bắt đầu 1s

function createReconnectingWebSocket(
  url: string,
  handlers: {
    onOpen?: () => void;
    onMessage: (event: MessageEvent) => void;
    onError?: (event: Event) => void;
    onClose?: () => void;
  }
): { ws: WebSocket | null; cleanup: () => void } {
  let ws: WebSocket | null = null;
  let retries = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let watchdogTimer: ReturnType<typeof setInterval> | null = null;
  let manualClose = false;
  let lastMessageTs = 0;

  function connect() {
    console.log("[WS] Connecting to", url);
    ws = new WebSocket(url);

    ws.onopen = () => {
      retries = 0;  // Reset backoff khi connect thành công
      lastMessageTs = Date.now();
      handlers.onOpen?.();

      // ── Watchdog: force-close nếu 45s không có message ──
      // Tại sao? Browser idle có thể kill WS silent.
      // ws.readyState vẫn = OPEN nhưng không nhận frame nào.
      // Watchdog phát hiện + reconnect.
      if (watchdogTimer) clearInterval(watchdogTimer);
      watchdogTimer = setInterval(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        const idle = Date.now() - lastMessageTs;
        if (idle > 45_000) {
          console.warn(`[WS] No data for ${idle}ms, forcing reconnect`);
          try { ws.close(); } catch (_) { /* ignore */ }
        }
      }, 15_000);  // Check mỗi 15s
    };

    ws.onmessage = (event) => {
      lastMessageTs = Date.now();  // ← Reset watchdog
      handlers.onMessage(event);
    };

    ws.onerror = (event) => {
      handlers.onError?.(event);
    };

    ws.onclose = () => {
      if (watchdogTimer) {
        clearInterval(watchdogTimer);
        watchdogTimer = null;
      }
      handlers.onClose?.();

      if (!manualClose) {
        // ── Exponential backoff với jitter ──
        // delay = BASE * 2^retries, cap 30s, +0-1000ms random
        const expDelay = BASE_RECONNECT_DELAY_MS * Math.pow(2, retries);
        const delay = Math.min(expDelay, MAX_RECONNECT_DELAY_MS) +
                      Math.floor(Math.random() * 1000);
        retries++;
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${retries})`);

        reconnectTimer = setTimeout(connect, delay);
      }
    };
  }

  connect();

  return {
    get ws() { return ws; },
    cleanup: () => {
      manualClose = true;  // ← Tránh reconnect khi cleanup
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (watchdogTimer) clearInterval(watchdogTimer);
      ws?.close();
    },
  };
}


// ════════════════════════════════════════════════════════════════════════
// fetchSymbols — REST: lấy danh sách symbols
// ════════════════════════════════════════════════════════════════════════

export async function fetchSymbols(): Promise<SymbolInfo[]> {
  if (DATA_SOURCE === "mock") {
    return mockDataAdapter.fetchSymbols();
  }
  const response = await fetch(`${API_BASE}/symbols`);
  if (!response.ok) {
    throw new Error(`fetchSymbols failed: ${response.status}`);
  }
  return response.json();
}
```

## 32. Reconnecting WebSocket — Chi Tiết

### Watchdog pattern

```typescript
watchdogTimer = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const idle = Date.now() - lastMessageTs;
    if (idle > 45_000) {
        console.warn(`[WS] No data for ${idle}ms, forcing reconnect`);
        try { ws.close(); } catch (_) { /* ignore */ }
    }
}, 15_000);
```

**Giải thích:**

WebSocket có 4 `readyState`:
- `CONNECTING` (0) — đang kết nối
- `OPEN` (1) — đã kết nối
- `CLOSING` (2) — đang đóng
- `CLOSED` (3) — đã đóng

NHƯNG có một "state ngầm" mà WebSocket API không phát hiện: **"open but receiving no data"**.

Lý do:
- Proxy/Nginx kill socket silent (close frame không gửi về client)
- Browser idle path kill socket
- Network route đổi

Trong trường hợp này, `readyState` vẫn = `OPEN` nhưng không có frame nào đến.

Watchdog giải quyết: cứ 15s kiểm tra `lastMessageTs`. Nếu > 45s → force close → trigger reconnect.

### Tại sao 45s?

- Binance push ~1Hz mỗi symbol
- 45s = ~45 messages cho 1 symbol active
- 45s không có message nào → chắc chắn có vấn đề

### Tại sao không cap retries?

```typescript
// Bug cũ:
const MAX_RETRIES = 5;
if (retries > MAX_RETRIES) return;  // ← DỪNG reconnect

// Fix mới:
const MAX_RECONNECT_DELAY_MS = 30_000;
// Backoff 1s → 2s → 4s → ... → cap 30s
// → Retry INDEFINITELY, chỉ chậm dần
```

Lý do: tab browser có thể để mở nhiều ngày. Nếu network có vấn đề lúc 3h sáng, tab vẫn cần reconnect khi network hồi phục.

## 33. Blob Parse Bug — Root Cause + Fix

### Bug ban đầu

```typescript
// backend/api/websocket.py
await websocket.send_bytes(json.dumps(payload).encode())
//                 ↑ send_bytes → binary WebSocket frame

// frontend/src/services/marketDataService.ts (CŨ - BUG)
ws.onmessage = (e) => {
    const data = JSON.parse(e.data as string);
    //                  ↑ BUG: e.data là Blob, không phải string!
};
```

Khi browser nhận binary frame, `e.data` là `Blob` object. `JSON.parse(blob)` throw:
```
[pageerror] Unexpected token 'o', "[object Blob]" is not valid JSON
```

Lỗi này xảy ra TRÊN MỖI FRAME → console bị spam, callback crash, chart đứng.

### Tại sao Python `websockets` KHÔNG phát hiện?

Python `websockets` library mặc định ở **text mode**. Khi server gửi binary frame, client nhận string (auto-decode). Bug không xuất hiện.

Tương tự với `curl` test WS — cũng auto-decode về text.

**CHỈ browser thật mới hiển thị bug này.**

### Cách bắt bug: Playwright

```python
# /tmp/check_chart.py
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page_errors = []
        page.on("pageerror", lambda exc: page_errors.append(f"[pageerror] {exc}"))

        await page.goto("https://lmview.duckdns.org", wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        print(page_errors)
        # ['[pageerror] Unexpected token "o", "[object Blob]" is not valid JSON',
        #  '[pageerror] Unexpected token "o", "[object Blob]" is not valid JSON',
        #  ... 9+ lần trong 8 giây]

asyncio.run(main())
```

### Fix

Thêm helper `parseWsData`:

```typescript
async function parseWsData<T>(data: MessageEvent["data"]): Promise<T> {
    if (typeof data === "string") {
        return JSON.parse(data) as T;
    }
    if (data instanceof Blob) {
        const text = await data.text();  // ← Đây là chìa khóa!
        return JSON.parse(text) as T;
    }
    if (data instanceof ArrayBuffer) {
        const text = new TextDecoder().decode(new Uint8Array(data));
        return JSON.parse(text) as T;
    }
    return JSON.parse(String(data)) as T;
}
```

Và wrap trong try/catch:

```typescript
onMessage: async (event: MessageEvent) => {
    try {
        const data = await parseWsData<Record<string, any>>(event.data);
        // ... xử lý data
    } catch (err) {
        console.error("[WS parse error]", err);
        // KHÔNG throw — để WS tiếp tục nhận frame sau
    }
},
```

### Verify sau fix

```python
# Playwright check lại
# Console errors: (rỗng)
# 1m candle evolution:
#   open=63300.01 (lastClosed.close)
#   high=63743.9 (accumulated max)
#   low=63300.01 (accumulated min)
#   close=63700.02 (latest ticker)
```

## 34. CandlestickChart Forming Candle Logic

### Code chính (rút gọn)

```tsx
// frontend/src/features/chart/CandlestickChart.tsx

const CandlestickChart: React.FC<Props> = ({ symbol, timeframe }) => {
  // ── Refs (mutable, không trigger re-render) ──
  const lastClosedCandleRef = useRef<Candle | null>(null);
  const formingCandleRef = useRef<Candle | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastMessageTsRef = useRef(0);

  // ── Effects ──
  useEffect(() => {
    // Load initial data
    loadData();
    // Subscribe WebSocket
    const unsub = subscribeAllTimeframes({
      symbol,
      onCandle: (tf, candle) => {
        if (tf === timeframe) handleCandle(candle);
      },
      onTicker: (ticker) => handleTicker(ticker),
    });
    return unsub;
  }, [symbol, timeframe]);


  function handleTicker(ticker: StreamTickerPayload) {
    const price = ticker.price;
    const eventTimeMs = ticker.eventTime;

    if (!Number.isFinite(price) || price <= 0) return;

    const timeframeSec = getTimeframeSeconds(timeframe);  // 60 cho 1m, 300 cho 5m, ...
    if (!timeframeSec) return;

    // ── Tính bucket ──
    // Bucket = floor(eventTime / 1000 / timeframeSec) * timeframeSec
    // Vd: eventTime=1781937642016, timeframeSec=60 → bucket=1781937600 (đầu phút)
    const bucketTime = Math.floor(eventTimeMs / 1000 / timeframeSec) * timeframeSec;

    const forming = formingCandleRef.current;
    const lastClosed = lastClosedCandleRef.current;

    let nextCandle: Candle;

    if (forming && forming.time === bucketTime) {
      // ── CASE 1: Same bucket (phổ biến nhất) ──
      // forming đang là bucket này → update high/low/close
      nextCandle = {
        time: bucketTime,
        open: forming.open,
        high: Math.max(forming.high, price),
        low: Math.min(forming.low, price),
        close: price,
        volume: forming.volume || 0,
      };
      formingCandleRef.current = nextCandle;

    } else if (forming && forming.time < bucketTime) {
      // ── CASE 2: Bucket boundary crossed ──
      // forming cũ (1 phút trước) giờ là closed
      // New bucket → tạo candle mới, open = forming cũ's close
      lastClosedCandleRef.current = forming;
      const open = forming.close;  // ← INVARIANT QUAN TRỌNG
      nextCandle = {
        time: bucketTime,
        open,
        high: Math.max(open, price),
        low: Math.min(open, price),
        close: price,
        volume: 0,
      };
      formingCandleRef.current = nextCandle;

    } else if (!forming && lastClosed) {
      // ── CASE 3: First tick sau F5 ──
      const open = lastClosed.close;
      nextCandle = {
        time: bucketTime,
        open,
        high: Math.max(open, price),
        low: Math.min(open, price),
        close: price,
        volume: 0,
      };
      formingCandleRef.current = nextCandle;

    } else {
      // ── CASE 4: Edge case (không nên xảy ra) ──
      return;
    }

    // ── Update lightweight-charts ──
    // series.update() tự xử lý:
    //   - time > last: append
    //   - time == last: update (cùng bucket)
    //   - time < last: ignore
    candleRef.current?.update(nextCandle);
  }


  async function loadData() {
    setIsLoading(true);
    // Reset refs (cho clean slate)
    formingCandleRef.current = null;

    // Fetch initial candles
    const candles = await fetchCandles(symbol, timeframe, 500);

    // Set last closed = candle cuối
    if (candles.length > 0) {
      lastClosedCandleRef.current = candles[candles.length - 1];
    }

    // Apply to chart
    candleRef.current?.setData(candles);

    setIsLoading(false);
  }


  return (
    <div ref={chartContainerRef} className="chart-container">
      {/* Loading, error UI */}
    </div>
  );
};
```

### Ví dụ timeline

```
T=9:30:00 → candle 9:30 đã đóng: {open: 63000, high: 63500, low: 62800, close: 63300}

T=9:30:30 → load chart → lastClosed = {close: 63300}

T=9:31:05 → ticker @ 63400
  CASE 3 (no forming): open = 63300, high = 63400, low = 63300, close = 63400
  forming = {time: 1781937660, open: 63300, high: 63400, low: 63300, close: 63400}

T=9:31:25 → ticker @ 63450
  CASE 1 (same bucket): open = 63300, high = 63450, low = 63300, close = 63450

T=9:31:45 → ticker @ 63350
  CASE 1: open = 63300, high = 63450, low = 63300, close = 63350

T=9:32:05 → ticker @ 63500
  CASE 2 (boundary): lastClosed = {time: 1781937660, open: 63300, ..., close: 63350}
                       forming = {time: 1781937720, open: 63350, high: 63500, low: 63350, close: 63500}
```

## 35. Two-Ref Design

### Tại sao 2 refs (không 1)?

| Ref | Mục đích |
|---|---|
| `lastClosedCandleRef` | Candle đã đóng gần nhất (cung cấp `open` cho forming mới) |
| `formingCandleRef` | Candle đang hình thành (accumulating OHLCV) |

Nếu chỉ 1 ref (vd `formingCandleRef`):
- Sau F5, `forming = null` → Case 3 không hoạt động
- Cần `lastClosed` để biết `open` của candle đầu tiên

Nếu chỉ 1 ref (`lastClosedCandleRef`):
- Case 1 cần forming để biết `high/low` đã accumulate đến đâu

→ 2 refs tách bạch concerns, dễ đọc hơn.

### Tại sao ref, không phải state?

| | Ref | State |
|---|---|---|
| Trigger re-render | ❌ | ✅ |
| Synchronous read | ✅ | ❌ (stale across sync code) |
| Use case | Imperative (timer, WS) | Declarative (UI props) |

Vì WS handler chạy mỗi tick (~1Hz), trigger re-render mỗi tick = chậm. Ref cho phép:
- Read sync trong tick handler
- Update không gây re-render
- Trigger lightweight-charts update trực tiếp (không qua React reconciliation)

<!-- Kết thúc Phần 5. Tiếp theo: Phần 6 — Lakehouse + AI -->
# Phần 6 — Lakehouse + PostgreSQL + AI + Triển Khai

> **Giải thích:** Phần này gộp các chủ đề "nặng" — Lakehouse (lưu trữ dài hạn), PostgreSQL (database quan hệ), AI (trợ lý), và Docker Swarm (triển khai lên cloud).

## 36. Medallion Architecture (Bronze / Silver / Gold)

### Ý tưởng

Lưu dữ liệu qua 3 tầng, mỗi tầng "sạch" hơn tầng trước:

```
Raw data (Binance JSON)
    │
    ▼  (Spark Streaming mỗi 30s)
┌─────────────────────────────────────────┐
│ BRONZE — Raw, unmodified                │
│ iceberg.crypto.bronze_ticker            │
│ iceberg.crypto.bronze_klines            │
│ iceberg.crypto.bronze_depth             │
│ iceberg.crypto.bronze_trades            │
│                                         │
│ Lưu nguyên payload gốc. Schema đơn giản.│
└─────────────────────────────────────────┘
    │
    ▼  (transform: parse, validate, dedup)
┌─────────────────────────────────────────┐
│ SILVER — Cleaned, typed, deduped        │
│ iceberg.crypto.silver_ticker            │
│ iceberg.crypto.silver_klines            │
│ iceberg.crypto.silver_depth             │
│ iceberg.crypto.silver_trades            │
│                                         │
│ Schema chuẩn. Có dedup theo (exchange,  │
│ symbol, timestamp).                     │
└─────────────────────────────────────────┘
    │
    ▼  (aggregate: hourly, daily)
┌─────────────────────────────────────────┐
│ GOLD — Pre-aggregated for API           │
│ iceberg.crypto.gold_ticker_1h           │
│ iceberg.crypto.gold_volume_24h          │
│ iceberg.crypto.gold_ohlc_1d             │
│ iceberg.crypto.gold_active_symbols      │
│ ...                                     │
│                                         │
│ Tables nhỏ, query nhanh cho API.        │
└─────────────────────────────────────────┘
    │
    ▼
[Trino SQL] → [FastAPI /api/market/overview]
```

### Tại sao 3 tầng?

| Tầng | Lưu trữ | Schema | Use case |
|---|---|---|---|
| Bronze | Nguyên gốc | Đơn giản, gần với JSON | Replay nếu downstream lỗi |
| Silver | Cleaned | Chuẩn hóa, có dedup | Analytics chung |
| Gold | Aggregated | Tối ưu cho query | API real-time |

Nếu phát hiện bug ở Silver → xóa Silver tables, replay từ Bronze.
Nếu Gold chậm → chỉ tính lại Gold, không cần đụng Bronze/Silver.

### Bronze table DDL

```sql
CREATE TABLE iceberg.crypto.bronze_ticker (
    exchange STRING,
    symbol STRING,
    event_time TIMESTAMP,
    raw_payload BINARY          -- ← Lưu nguyên gốc để replay
)
USING iceberg
PARTITIONED BY (hours(event_time))
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd'
);
```

### Silver table DDL

```sql
CREATE TABLE iceberg.crypto.silver_ticker (
    exchange STRING,
    symbol STRING,
    event_time TIMESTAMP,
    price DECIMAL(20, 8),     -- ← DECIMAL chính xác, không làm tròn
    volume_24h DECIMAL(30, 8),
    quote_volume_24h DECIMAL(30, 8),
    change_pct DECIMAL(10, 4),
    bid DECIMAL(20, 8),
    ask DECIMAL(20, 8)
)
USING iceberg
PARTITIONED BY (days(event_time))   -- ← Partition theo NGÀY (lưu lâu dài)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd',
    'write.distribution-mode' = 'hash',
    'format-version' = '2'
);
```

### Spark job chính (`src/lakehouse/pipeline.py`)

```python
"""Spark job: Kafka → Bronze → Silver → Gold → Iceberg."""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_avro, window, sum, max, min

# ── Spark session ──
spark = SparkSession.builder \
    .appName("lmview-lakehouse") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "jdbc") \
    .config("spark.sql.catalog.iceberg.uri", "jdbc:postgresql://postgres:5432/lmview") \
    .config("spark.sql.catalog.iceberg.warehouse", "s3a://lakehouse/warehouse") \
    .getOrCreate()

# ── Đọc từ Kafka ──
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka-1:9092,kafka-2:9092,kafka-3:9092") \
    .option("subscribe", "crypto_ticker,crypto_klines,crypto_trades,crypto_depth") \
    .option("startingOffsets", "latest") \
    .load()

# ── Parse Avro ──
parsed = df.select(
    col("topic"),
    col("partition"),
    col("offset"),
    col("timestamp").alias("kafka_ts"),
    from_avro(col("value"), "ticker").alias("ticker")
).filter(col("ticker").isNotNull())

# ── Bronze write (raw) ──
bronze = parsed.select(
    col("ticker.exchange"),
    col("ticker.s").alias("symbol"),
    (col("ticker.E") / 1000).cast("timestamp").alias("event_time"),
    col("value").alias("raw_payload")  # ← Lưu nguyên bytes
)
bronze.writeStream \
    .format("iceberg") \
    .outputMode("append") \
    .option("path", "iceberg.crypto.bronze_ticker") \
    .option("checkpointLocation", "/checkpoints/bronze_ticker") \
    .trigger(availableNow=True) \
    .start()

# ── Silver transform ──
silver = parsed.select(
    col("ticker.exchange"),
    col("ticker.s").alias("symbol"),
    (col("ticker.E") / 1000).cast("timestamp").alias("event_time"),
    col("ticker.c").cast("decimal(20,8)").alias("price"),
    col("ticker.v").cast("decimal(30,8)").alias("volume_24h"),
    col("ticker.q").cast("decimal(30,8)").alias("quote_volume_24h"),
    col("ticker.P").cast("decimal(10,4)").alias("change_pct"),
    col("ticker.b").cast("decimal(20,8)").alias("bid"),
    col("ticker.a").cast("decimal(20,8)").alias("ask"),
).withWatermark("event_time", "1 minute") \
 .dropDuplicates(["exchange", "symbol", "event_time"])

silver.writeStream \
    .format("iceberg") \
    .outputMode("append") \
    .option("path", "iceberg.crypto.silver_ticker") \
    .option("checkpointLocation", "/checkpoints/silver_ticker") \
    .trigger(processingTime="30 seconds") \
    .start()

# ── Gold aggregation ──
# 1h OHLCV từ silver
gold = silver.groupBy(
    col("exchange"),
    col("symbol"),
    window(col("event_time"), "1 hour")
).agg(
    col("exchange"),
    col("symbol"),
    col("window.start").alias("hour"),
    max("price").alias("high"),
    min("price").alias("low"),
    # First/last value cần window function riêng
)

# ⚠️ Caveat: gold_dedup hiện tại OMIT exchange (xem Caveats §51)
```

### Iceberg maintenance

```python
"""Compaction: gộp nhiều file nhỏ thành file lớn."""

def compact_table(table_name: str):
    spark.sql(f"""
        CALL iceberg.system.rewrite_data_files(
            table => 'iceberg.crypto.{table_name}'
        )
    """)

def expire_old_snapshots(table_name: str, days: int = 7):
    """Xóa snapshots cũ (giải phóng dung lượng)."""
    spark.sql(f"""
        CALL iceberg.system.expire_snapshots(
            table => 'iceberg.crypto.{table_name}',
            older_than => '{days} days'
        )
    """)

# Chạy hàng tuần qua cron hoặc Dagster
```

## 37. PostgreSQL Schema

### Migration files

`backend/migrations/*.sql`:

| File | Mục đích |
|---|---|
| `001_phase0_schema.sql` | Users, sessions, settings |
| `002_phase1_readiness.sql` | Admin config, AI state |
| `003_phase1_ai_rag.sql` | AI chat, KB, embeddings |
| `004_agents_metadata.sql` | AI agent metadata |
| `004_phaseC_news_enhancements.sql` | News tables (⚠️ trùng số 004) |

### Code đầy đủ `001_phase0_schema.sql`

```sql
-- ════════════════════════════════════════════════════════════════════════
-- 001_phase0_schema.sql
-- Schema ban đầu: users, sessions, settings
-- ════════════════════════════════════════════════════════════════════════

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Text similarity
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector: vector embeddings

-- ── Users ──
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_email ON users(email);

-- ── Sessions (JWT token) ──
CREATE TABLE IF NOT EXISTS sessions (
    token UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- ── User settings ──
CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(50) DEFAULT 'dark',
    default_timeframe VARCHAR(10) DEFAULT '1m',
    default_symbol VARCHAR(20) DEFAULT 'BTCUSDT',
    chart_type VARCHAR(20) DEFAULT 'candles',
    notifications_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ── Admin config ──
CREATE TABLE IF NOT EXISTS admin_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Code đầy đủ `003_phase1_ai_rag.sql`

```sql
-- ════════════════════════════════════════════════════════════════════════
-- 003_phase1_ai_rag.sql
-- AI chat history + RAG knowledge base
-- ════════════════════════════════════════════════════════════════════════

-- ── AI chat sessions ──
CREATE TABLE IF NOT EXISTS ai_chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_message_at TIMESTAMPTZ
);

CREATE INDEX idx_ai_sessions_user ON ai_chat_sessions(user_id, last_message_at DESC);

-- ── AI messages ──
CREATE TABLE IF NOT EXISTS ai_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_ai_messages_session ON ai_messages(session_id, created_at);

-- ── RAG: Knowledge base chunks ──
CREATE TABLE IF NOT EXISTS kb_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_kb_chunks_doc ON kb_chunks(document_id);

-- ── Vector embeddings (pgvector) ──
-- 384-dim từ sentence-transformers all-MiniLM-L6-v2
CREATE TABLE IF NOT EXISTS kb_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES kb_chunks(id) ON DELETE CASCADE,
    embedding vector(384)
);

-- HNSW index cho fast cosine similarity search
CREATE INDEX idx_kb_embeddings_hnsw
    ON kb_embeddings
    USING hnsw (embedding vector_cosine_ops);

-- ── Retrieval logs (audit) ──
CREATE TABLE IF NOT EXISTS ai_retrieval_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT NOT NULL,
    retrieved_chunk_ids UUID[],
    relevance_scores FLOAT[],
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
```

### Migration runner (`backend/core/postgres.py`)

```python
"""PostgreSQL client + migration runner."""

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)


async def get_session() -> AsyncSession:
    """Yield session cho FastAPI Depends."""
    async with AsyncSession(engine) as session:
        yield session


async def run_migrations():
    """Run SQL migrations theo thứ tự. Gọi lúc startup nếu RUN_MIGRATIONS=true."""
    migrations_dir = Path(__file__).parent.parent / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))

    async with engine.begin() as conn:
        for f in files:
            log.info("Running migration: %s", f.name)
            sql = f.read_text()
            # Split SQL statements (handle $$ dollar-quoting)
            statements = split_sql(sql)
            for stmt in statements:
                if stmt.strip():
                    await conn.execute(text(stmt))


def split_sql(sql: str) -> list[str]:
    """Split SQL thành statements. Tôn trọng $$ blocks (Postgres dollar-quoting)."""
    statements = []
    current = []
    in_dollar = False

    for line in sql.split("\n"):
        if "$$" in line:
            in_dollar = not in_dollar
        current.append(line)
        if not in_dollar and line.strip().endswith(";"):
            statements.append("\n".join(current))
            current = []

    return statements
```

## 38. InfluxDB Measurements

### Schema

```
Database: lmview (org)
└── Bucket: crypto (retention 90 days)
    ├── measurement: candles
    │   tags: exchange, symbol, interval
    │   fields: open, high, low, close, volume (float)
    │   timestamp: ns precision
    │
    ├── measurement: market_ticks
    │   tags: exchange, symbol
    │   fields: price, bid, ask, volume, ...
    │
    ├── measurement: indicators
    │   tags: exchange, symbol, interval, indicator_name
    │   fields: value (float)
    │
    └── measurement: whale_trades
        tags: exchange, symbol, side
        fields: price, qty, value, trade_id
```

### Query example (Flux)

```flux
from(bucket: "crypto")
  |> range(start: -90d)
  |> filter(fn: (r) => r._measurement == "candles"
                      and r.symbol == "BTCUSDT"
                      and r.exchange == "binance"
                      and r.interval == "1m")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: false)
  |> tail(n: 500)
```

### Python query

```python
async def query_candles(symbol, interval, limit=500):
    """Query candles từ InfluxDB."""
    from influxdb_client import InfluxDBClient

    client = InfluxDBClient(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
    )
    query_api = client.query_api()

    query = f'''
    from(bucket: "crypto")
      |> range(start: -90d)
      |> filter(fn: (r) => r._measurement == "candles"
                          and r.symbol == "{symbol}"
                          and r.exchange == "binance"
                          and r.interval == "{interval}")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> tail(n: {limit})
    '''
    tables = await query_api.query(query)

    candles = []
    for table in tables:
        for record in table.records:
            candles.append({
                "time": int(record.get_time().timestamp()),  # ms → seconds
                "open": record.values["open"],
                "high": record.values["high"],
                "low": record.values["low"],
                "close": record.values["close"],
                "volume": record.values["volume"],
            })
    return sorted(candles, key=lambda c: c["time"])
```

## 39. Iceberg Table Catalog

### Setup (PostgreSQL-backed JDBC)

```sql
-- PostgreSQL init
CREATE DATABASE lmview;
\connect lmview
CREATE SCHEMA IF NOT EXISTS iceberg;
```

Iceberg lưu metadata trong PostgreSQL (`iceberg` schema). Data thực tế (Parquet files) trên MinIO.

### Namespaces

| Namespace | Tables |
|---|---|
| `iceberg.crypto.bronze_*` | Raw data (4 tables) |
| `iceberg.crypto.silver_*` | Cleaned (4 tables) |
| `iceberg.crypto.gold_*` | Aggregated (8+ tables) |

### ⚠️ Catalog mismatch

- Dagster dùng `s3a://lakehouse/warehouse`
- Pipeline dùng `s3://cryptoprice/iceberg`

→ Bảng tạo bởi một sẽ không hiển thị ở một kia. Đây là bug đã biết.

## 40. AI Ask Mode (Phase 1)

### Tổng quan

User có thể chat với AI về thị trường:

```
User: "Tại sao BTC giảm 5% hôm nay?"
AI: "BTC giảm 5% trong 24h qua. Có 3 yếu tố chính:
     1. Cục FED tăng lãi suất dự kiến...
     2. Tin tức tiêu cực từ Coinbase...
     3. Khối lượng giao dịch giảm..."
```

### Component layout

```
backend/services/ai/
├── core/                     ← Entry point orchestrator
├── context/                  ← Build context (chart, market, user)
├── persistence/              ← Chat history storage
├── providers/                ← LLM provider routing
├── prompts/                  ← Prompt builder
├── rag/                      ← Knowledge base retrieval
├── safety/                   ← Scope gate + output guard
├── actions/                  ← Chart action schemas
├── nlp/                      ← FinBERT sentiment
└── metrics.py                ← Prometheus metrics
```

### Flow chi tiết

```
User gửi "Tại sao BTC giảm 5% hôm nay?"
   │
   ▼ 1. Scope gate (safety/scope_gate.py)
   │   Hỏi: Câu này có yêu cầu restricted access không?
   │   → Không → Cho phép
   │
   ▼ 2. Context assembler (context/)
   │   - Chart context: BTCUSDT, 1h, last 100 candles
   │   - Market context: BTC = $63k, 24h change -5.2%
   │   - Recent news
   │
   ▼ 3. RAG retrieval (rag/retrieval.py)
   │   - Embed query → vector
   │   - pgvector similarity search → top 5 chunks
   │
   ▼ 4. Prompt builder (prompts/)
   │   - System: "You are a market analysis assistant..."
   │   - Context: chart, market, news, KB
   │   - User question
   │
   ▼ 5. LLM call (providers/)
   │   - mock_provider (default) hoặc real LLM
   │   - Returns: text answer + action proposals
   │
   ▼ 6. Output guard (safety/output_guard.py)
   │   - Filter PII
   │   - Validate action schemas
   │
   ▼ 7. Persist + respond
   - Save user msg + assistant response → ai_messages
   - Return to frontend
```

### Code RAG retrieval

```python
# backend/services/ai/rag/retrieval.py

from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim
    return _model


def embed(text: str) -> np.ndarray:
    """Embed text thành 384-dim vector."""
    model = get_model()
    return model.encode(text)


async def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve top K chunks liên quan nhất."""
    q_emb = embed(query)

    async with get_session() as session:
        # pgvector HNSW index → cosine similarity search
        result = await session.execute(
            text("""
                SELECT
                    chunk_id,
                    1 - (embedding <=> :q_emb) AS similarity,
                    content
                FROM kb_embeddings
                ORDER BY embedding <=> :q_emb
                LIMIT :top_k
            """),
            {"q_emb": q_emb.tolist(), "top_k": top_k}
        )
        rows = result.fetchall()

    return [
        {
            "chunk_id": str(row.chunk_id),
            "similarity": row.similarity,
            "content": row.content,
        }
        for row in rows
    ]
```

### Action proposal validation

```python
# backend/services/ai/actions/validators.py

from pydantic import BaseModel, validator

class DrawLineAction(BaseModel):
    """User-facing chart action: vẽ trendline."""
    type: str = "draw_line"
    symbol: str
    timeframe: str
    points: list[dict]  # [{time, price}, {time, price}]
    label: str | None = None

    @validator("points")
    def validate_points(cls, v):
        if len(v) < 2:
            raise ValueError("Need at least 2 points")
        return v

# HARD RULE: action KHÔNG BAO GIỜ execute without:
# 1. Validate schema (Pydantic)
# 2. User approval (frontend modal)
# 3. Audit record (ai_action_metadata table)
```

## 41. Docker Swarm Deployment

### Cluster topology

```
┌─────────────────────────────────────────────────────────────┐
│ AWS Region: us-east-1                                       │
│                                                             │
│  ┌────────────────────────────┐  ┌─────────────────────┐  │
│  │ MANAGER NODE               │  │ WORKER NODE         │  │
│  │ IP: 172.31.21.135          │  │ IP: 172.31.9.171    │  │
│  │ 8 vCPU / 32 GB / 96 GB     │  │ 4 vCPU / 16 GB      │  │
│  │                            │  │                     │  │
│  │ Services (most):           │  │ Services (compute): │  │
│  │ - nginx-prod               │  │ - flink-taskmanager │  │
│  │ - fastapi-prod             │  │ - spark-worker      │  │
│  │ - binance-ticker-ws        │  │                     │  │
│  │ - redis (master + replica) │  │                     │  │
│  │ - redis-sentinel-1,2,3     │  │                     │  │
│  │ - postgres                 │  │                     │  │
│  │ - influxdb                 │  │                     │  │
│  │ - minio                    │  │                     │  │
│  │ - kafka-1,2,3              │  │                     │  │
│  │ - zookeeper                │  │                     │  │
│  │ - flink-jobmanager         │  │                     │  │
│  │ - spark-master             │  │                     │  │
│  │ - dagster-* (optional)     │  │                     │  │
│  │ - prometheus, grafana, loki│  │                     │  │
│  │ - certbot                  │  │                     │  │
│  └────────────────────────────┘  └─────────────────────┘  │
│                                                             │
│  Shared: /mnt/efs/LMView (EFS = network filesystem)        │
│  Domain: lmview.duckdns.org                                 │
│  TLS: Let's Encrypt (auto-renew mỗi 60 ngày)               │
└─────────────────────────────────────────────────────────────┘
```

### Deploy command

```bash
# Stack = nhóm nhiều services
docker stack deploy \
    -c docker-compose.yml \
    -c docker-compose.swarm.yml \
    cryptoprice
```

`docker-compose.yml` = định nghĩa base (image, env, ports).
`docker-compose.swarm.yml` = overlay Swarm (placement, replicas).

### Local registry

```bash
# Manager node: private Docker registry
REG=172.31.21.135:5000

# Build + push
docker build -f docker/fastapi/Dockerfile -t $REG/lmview-fastapi:latest .
docker push $REG/lmview-fastapi:latest

# Trigger Swarm rolling update
docker service update --image $REG/lmview-fastapi:latest --force cryptoprice_fastapi-prod
```

### Deploy script (`scripts/deploy_aws_swarm.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

REG=172.31.21.135:5000

# Build + push tất cả images
docker build -f docker/fastapi/Dockerfile -t $REG/lmview-fastapi:latest .
docker push $REG/lmview-fastapi:latest

docker build -f docker/nginx/Dockerfile -t $REG/lmview-nginx:latest .
docker push $REG/lmview-nginx:latest

docker build -f docker/ticker-ws/Dockerfile -t $REG/lmview-ticker-ws:latest .
docker push $REG/lmview-ticker-ws:latest

# ... các service khác

# Deploy stack
docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice

# Wait + verify
sleep 30
docker service ls
```

## 42. Prometheus + Grafana + Loki

### Prometheus scrape config

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: fastapi
    static_configs:
      - targets: ['fastapi:8000']
    metrics_path: /metrics

  - job_name: binance-ticker-ws
    static_configs:
      - targets: ['binance-ticker-ws:9100']

  - job_name: flink-jobmanager
    static_configs:
      - targets: ['flink-jobmanager:9999']

  - job_name: redis
    static_configs:
      - targets: ['redis-master:9121']

  - job_name: postgres
    static_configs:
      - targets: ['postgres:9187']
```

### Grafana dashboards (22 dashboards)

| Dashboard | Panel chính |
|---|---|
| lmview-overview | Tất cả services up, latency p95, error rates |
| ticker-ws-shards | Per-shard connect state, msg rate, latency |
| ws-connections | FastAPI WS session count, push rate |
| redis-operations | Redis ops/s, memory, evictions |
| kafka-lag | Consumer group lag |
| flink-job | Job uptime, checkpoint latency, backpressure |
| iceberg | Snapshot count, table size |

### Loki log queries (LogQL)

```logql
# Tất cả errors từ fastapi
{container="fastapi-prod"} |= "ERROR"

# Ticker shard reconnects
{container="binance-ticker-ws"} |= "reconnecting"

# 502 errors từ Nginx
{container="nginx-prod"} |~ " 502 "

# WebSocket disconnects
{container="fastapi-prod"} |= "WebSocketDisconnect"
```

### Promtail config

```yaml
# config/promtail-config.yml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

## 43. Startup Order và Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                       STARTUP ORDER                             │
└─────────────────────────────────────────────────────────────────┘

T+0s    docker stack deploy
   │
   ▼ Foundation (services không phụ thuộc gì)
T+10s   zookeeper, postgres, redis (master + replicas + sentinels),
        minio, influxdb, kafka-1, kafka-2, kafka-3
   │
   ▼ Schema + ingestion (parallel)
T+30s   schema-registry (depends: kafka)
        binance-ticker-ws (independent — connect Binance + Redis)
T+45s   binance-ticker-ws started writing to Redis ✓
   │
   ▼ Processing
T+60s   flink-jobmanager → flink-taskmanager
        auto_submit_jobs.sh submits Flink job
T+90s   Flink job running, writing candles to Redis ✓
   │
   ▼ Lakehouse
T+90s   spark-master → spark-worker
T+110s  spark-submit runs lakehouse pipeline
T+130s  Iceberg tables populated ✓
   │
   ▼ Serving
T+130s  fastapi-prod up
T+140s  nginx-prod up
T+150s  Browser có thể connect ✓
```

### Verify commands

```bash
# Tất cả services?
docker service ls

# Health checks?
curl -s http://fastapi:8000/api/health | jq
curl -s http://binance-ticker-ws:9100/healthz | jq

# Redis master?
docker exec redis-sentinel-1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# Kafka topics?
docker exec kafka-1 kafka-topics.sh --bootstrap-server kafka-1:9092 --list

# Flink job running?
curl -s http://flink-jobmanager:8081/jobs | jq

# Ticker data flowing?
docker exec redis-master redis-cli HGETALL ticker:latest:binance:BTCUSDT

# Browser reachable?
curl -I https://lmview.duckdns.org/api/health
```

<!-- Kết thúc Phần 6. Tiếp theo: Phần 7 — Vận hành -->
# Phần 7 — Vận Hành (Operations Reference)

Phần này là "tài liệu cho SRE" — cách vận hành LMView hàng ngày: biến môi trường, cổng, logs, health checks, failure modes, runbook, và lịch sử bug.

## 44. Biến Môi Trường (All Env Vars)

### FastAPI / backend (`.env`)

```bash
# ── PostgreSQL ──
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=lmview
POSTGRES_USER=lmview
POSTGRES_PASSWORD=change_me  # ← thay đổi ngay!

# ── Redis ──
REDIS_SENTINELS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
REDIS_MASTER_NAME=mymaster
REDIS_HOST=redis-master         # Fallback direct (không dùng nếu Sentinel OK)
REDIS_PORT=6379
REDIS_DB=0

# ── InfluxDB ──
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=change_me
INFLUXDB_ORG=lmview
INFLUXDB_BUCKET=crypto

# ── Trino ──
TRINO_HOST=trino
TRINO_PORT=8080
TRINO_USER=lmview
TRINO_CATALOG=iceberg

# ── JWT ──
JWT_SECRET=change_me_very_long_random_string_min_32_chars
JWT_EXPIRES_HOURS=24

# ── AI ──
AI_MODE=mock                  # mock | local | api | auto
AI_ENABLE_REAL_LLM=false     # true nếu muốn dùng OpenAI/Anthropic
OPENAI_API_KEY=sk-...         # (optional)
ANTHROPIC_API_KEY=...         # (optional)
LITELLM_BASE_URL=http://localhost:4000  # LiteLLM proxy (optional)

# ── Logging ──
LOG_LEVEL=INFO

# ── CORS ──
CORS_ORIGINS=["https://lmview.duckdns.org"]

# ── Migration ──
RUN_MIGRATIONS=false          # true lần đầu để tạo table
RUN_AI_INGESTION=false       # true lần đầu để ingest docs vào KB
```

### binance-ticker-ws (`.env`)

```bash
# ── Symbol list ──
TICKER_WS_SHARDS=8
TICKER_WS_SYMBOLS_PER_SHARD=100
TICKER_WS_TOP_N=671
TICKER_WS_SYMBOL_REFRESH_SEC=3600  # reload symbol list mỗi 1h (chưa impl)

# ── WS endpoint ──
TICKER_WS_BASE=wss://stream.binance.com:9443/stream

# ── Reconnect ──
TICKER_WS_RECONNECT_BASE_MS=1000
TICKER_WS_RECONNECT_MAX_MS=30000
TICKER_WS_PING_INTERVAL_S=30
TICKER_WS_PING_TIMEOUT_S=10

# ── Redis ──
TICKER_WS_REDIS_FLUSH_MS=50
TICKER_WS_REDIS_BUFFER_MAX=2000
TICKER_WS_TTL_S=300

# ── Metrics ──
METRICS_HOST=0.0.0.0
METRICS_PORT=9100
LOG_LEVEL=INFO

# ── Redis (reuse từ FastAPI .env) ──
REDIS_SENTINELS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
REDIS_MASTER_NAME=mymaster
REDIS_HOST=redis-master
REDIS_PORT=6379
REDIS_DB=0
```

### Flink

```bash
KAFKA_BOOTSTRAP=kafka-1:9092,kafka-2:9092,kafka-3:9092
REDIS_HOST=redis-master
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=change_me
FLINK_PARALLELISM=12
```

## 45. Cổng (Ports Reference)

### External (host machine) — truy cập từ internet

| Port | Service | Truy cập |
|---|---|---|
| 80 | nginx-prod | HTTP → redirect 443 |
| 443 | nginx-prod | HTTPS (production) |
| 2181 | zookeeper | Dev/ops only |
| 5432 | postgres | Dev only (psql) |
| 6379 | redis-master | Dev only (redis-cli) |
| 8080 | fastapi-prod | Dev only |
| 8081 | flink-jobmanager | Web UI |
| 8085 | schema-registry | Apicurio UI |
| 8086 | influxdb | InfluxDB UI |
| 9001 | minio | MinIO Console |
| 19092, 9093, 9094 | kafka-1,2,3 | External Kafka listeners |
| 9100 | binance-ticker-ws | Metrics + /healthz |

### Internal (crypto-net) — container-to-container

Mỗi service dùng hostname (ví dụ `fastapi:8000`) không cần port ngoài.

## 46. Logs: Làm Thế Nào Để Xem

### 1. Docker service logs (most common)

```bash
# Xem logs service cụ thể
docker service logs cryptoprice_fastapi-prod --tail 100

# Follow logs real-time
docker service logs -f cryptoprixe_fastapi-prod

# Xem logs của shard 0
docker service logs cryptoprice_binance-ticker-ws | grep "shard 0"

# Lọc ERROR
docker service logs cryptoprice_fastapi-prod 2>&1 | grep -i error
```

### 2. Loki + Grafana (centralized)

- Grafana: http://lmview.duckdns.org/grafana (nếu enabled)
- Query LogQL:
  ```
  {container="fastapi-prod"} |= "ERROR"
  {container="nginx-prod"} |~ " 502 "
  {container="binance-ticker-ws"} |= "reconnecting"
  ```

### 3. Local log files (nếu dùng json-file driver)

```bash
# Tìm container ID
docker ps --filter name=cryptoprice

# Xem raw JSON log file
tail -f /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

### Where to look cho specific symptoms

| Symptom | Check |
|---|---|
| Browser "Loading..." | `fastapi-prod` logs + `/api/health` |
| Chart price frozen | `binance-ticker-ws` logs + Redis ticker key age |
| 502 Gateway | `nginx-prod` logs + Flink job state |
| High latency | Prometheus `ticker_ws_event_to_now_seconds` histogram |
| Auth failing | `fastapi-prod` `/api/auth/login` errors |
| Redis readonly | Check sentinel logs, maybe connected to replica |

## 47. Health Checks

### Service health endpoints

| Service | Endpoint | What it checks |
|---|---|---|
| fastapi-prod | `GET /api/health` | Redis + InfluxDB + Postgres + Trino connections |
| binance-ticker-ws | `GET /healthz` | Uptime + per-shard connected state |
| flink-jobmanager | `GET /overview` | Cluster overview (JSON) |
| redis | `redis-cli PING` | Liveness |
| postgres | `pg_isready` | Liveness |
| influxdb | `GET /health` | Liveness |

### Docker healthcheck (Swarm auto-restart)

```yaml
healthcheck:
  test: ["CMD", "wget", "-qO-", "http://localhost:9100/healthz"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 60s
```

Swarm sẽ restart container nếu health check fails 3 lần liên tiếp.

### MISSING health checks (cần thêm)

Theo AGENTS.md, các service chưa có healthcheck:

- `producer`
- `flink-jobmanager`
- `flink-taskmanager`
- `spark-worker`
- `schema-registry`

## 48. Common Failure Modes + Fixes

### 1. Browser shows "Loading..." forever

**Likely:**
- FastAPI down
- Redis unreachable
- WS connection failing

**Fix:**
```bash
# Check FastAPI
docker service ps cryptoprice_fastapi-prod
docker service logs --tail 50 cryptoprice_fastapi-prod

# Check health
docker exec fastapi-prod curl -s http://localhost:8000/api/health

# Check Redis
docker exec redis-master redis-cli PING

# Check Nginx
docker service logs --tail 50 cryptoprice_nginx-prod
```

### 2. Chart shows price but no candle body/wicks

**Before v0.25.47:** Blob parse error. Check browser console:
```
Unexpected token 'o', "[object Blob]" is not valid JSON
```

**Fix:** Deploy v0.25.47+ (parseWsData helper).

### 3. Chart freezes after a few minutes

**Before v0.25.46:**
- WS reconnect cap (5 retries) → silent death
- Backend push condition too strict (no ticker updates)

**Fix:**
- v0.25.46: unlimited retries + 45s watchdog + ticker_updated push
- Deploy backend + frontend v0.25.46+

### 4. 502 Bad Gateway (nginx)

**Before v0.25.46:** Nginx cached failed DNS resolution (`set $var` + `proxy_pass $var` pattern).

**Fix:** Check `docker/nginx/nginx-prod.conf`:
```
location /api {
    proxy_pass http://fastapi:8000;  # ← direct, no variable
    resolver 127.0.0.11 valid=5s;   # ← required for dynamic DNS
}
```

### 5. Redis READONLY errors

**Cause:** Wrote to a replica. Swarm VIP `redis-master` may round-robin to replicas.

**Fix:** Use Sentinel `master_for("mymaster")` — guarantees master.

```python
from redis.asyncio.sentinel import Sentinel
sentinel = Sentinel([('redis-sentinel-1', 26379)])
master = sentinel.master_for('mymaster')
await master.hset(...)  # always master
```

### 6. Flink job stuck on RUNNING but no data

```bash
# Check job
curl http://flink-jobmanager:8081/jobs | jq '.jobs[] | {id, status, name}'

# Check vertices
curl http://flink-jobmanager:8081/jobs/<job-id>/vertices | jq

# Look for "read-records=0" but "busy-time=0" → no data flowing

# Restart job
docker exec flink-jobmanager flink cancel <job-id>
docker exec flink-jobmanager flink run -d -c src.processing.pipeline.PipelineJob /app/src/processing/pipeline.py
```

### 7. Binance ticker shard stuck "disconnected"

```bash
# Check healthz
curl http://binance-ticker-ws:9100/healthz | jq '.shards[] | {shard_id, connected, last_event_latency_ms}'

# If specific shards stuck: check Binance WS status
# 403/429 → geofencing, backoff 30s
```

### 8. Postgres out of disk

```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

-- VACUUM large tables (reclaim space)
VACUUM FULL ai_messages;
VACUUM FULL ai_retrieval_logs;

-- Delete old logs
DELETE FROM ai_retrieval_logs WHERE created_at < NOW() - INTERVAL '30 days';
```

### 9. Trino can't find Iceberg tables

**Cause:** Catalog mismatch (Dagster uses `s3a://lakehouse/warehouse`, pipeline uses `s3://cryptoprice/iceberg`).

**Check:**
```sql
-- Trino
SHOW TABLES FROM iceberg.crypto;
```

**Fix:** Use correct catalog path. May need to recreate tables in the correct location.

## 49. Operations Runbook

### Daily

```bash
# 1. Check all services up
docker service ls | grep -v "0/"

# 2. Check health
curl -s http://fastapi:8000/api/health | jq

# 3. Check ticker freshness
docker exec redis-master redis-cli HGET ticker:latest:binance:BTCUSDT event_time

# 4. Check Flink
curl -s http://flink-jobmanager:8081/jobs | jq

# 5. Disk usage on manager
ssh ip-172-31-21-135 "df -h /mnt/efs"

# 6. Error logs (last hour)
docker service logs --since 1h cryptoprice_fastapi-prod 2>&1 | grep -i error
```

### Weekly

```bash
# Compact Iceberg tables (clean small files)
docker exec spark-submit spark-submit /app/src/batch/maintenance.py

# Vacuum Postgres
docker exec postgres psql -U lmview -d lmview -c "VACUUM ANALYZE;"

# Redis memory
docker exec redis-master redis-cli INFO memory

# Docker image cleanup
docker system df
```

### Restart service

```bash
# Force restart (rolling update)
docker service update --force cryptoprice_fastapi-prod

# Update to new image
docker service update --image $REG/lmview-fastapi:v0.25.49 --force cryptoprice_fastapi-prod
```

### Full stack restart (last resort)

```bash
docker stack rm cryptoprice
docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice
```

### Add new symbol

`binance-ticker-ws` auto-refresh symbol list hourly. No action needed.

### Add new timeframe

1. Add to `ALL_INTERVALS` in `backend/api/websocket.py`
2. Add to `INTERVAL_SECONDS` in `backend/core/constants.py`
3. Add to `TIMEFRAME_KEYS` in `frontend/src/constants/`
4. Add to `CHART_CONFIG` in `frontend/src/features/chart/`
5. Rebuild + redeploy frontend
6. Restart backend
7. Update Flink job (add aggregation for new interval)

### Schema migration

1. Add `00N_<name>.sql` to `backend/migrations/`
2. Bump `VERSION`
3. `make sync-version`
4. Test on dev
5. Deploy with `RUN_MIGRATIONS=true` for 1 cycle, then disable

## 50. Realtime Bug History

8 bugs đã fix, lessons learned:

| # | Symptom | Root cause | Fix | Lesson |
|---|---|---|---|
| 1 | Forming candle open ≠ prev close | Open từ ticker, không từ lastClosed | Use `lastClosed.close` | Invariant phải preserve |
| 2 | 3 candles contiguous wrong | Open dùng `forming.open` → `lastClosed.close` fix | Revert, đơn giản hóa | Refactor cần test edge cases |
| 3 | Producer OOM + 403 | 31 threads, AWS geofencing | Reduce symbols/conn, Phase 4 | Async > threads, đừng tự tin |
| 4 | Producer dead, poller fallback | Silent dependency | Deploy ticker-ws, disable poller | Biết hot path dependencies |
| 5 | Chart không realtime | Push condition quá chặt | `if any_changed or ticker_updated` | Push frequency independent của bucket |
| 6 | Nginx 502 | `set $var` pattern broken | Direct `proxy_pass` + `resolver` | Nginx DNS resolution trap |
| 7 | Blob parse crash | `JSON.parse(blob)` | `parseWsData` helper | Test với browser thật, không chỉ curl/Python |
| 8 | ticker-ws 403 reconnect | AWS geofencing | 4× backoff, auto-reconnect | Expect geofencing, implement backoff |

### Bug #1: Forming candle open = live_price

**Code cũ (v0.25.41):**
```typescript
// first tick after bucket boundary
nextCandle.open = price;  // ← WRONG! phải là lastClosed.close
```

**Fix:**
```typescript
const open = lastClosed.close;  // ✅ Invariant: open = prev close
```

**Visual bug:** Candle jump: `63300 → 63400` thay vì `63300 → 63300`.

### Bug #2: 3 contiguous candles drawn wrong

Refactor đã đổi CASE 2 logic → 3 candles bị vẽ sai.

**Fix:** Revert logic đơn giản:
```typescript
const open = forming.close;  // ✅ Luôn dùng close cũ làm open mới
```

### Bug #3: Producer OOM + 403

Producer 31 threads × ~10MB = 300MB. Swarm limit 2GB → OOM khi spike.
403 từ AWS ELB (geofencing IP range US-East).

**Mitigation:** Reduce symbols/connection (25 → 20).

**Permanent fix:** binance-ticker-ws (async, 8 shards, 24 fields).

### Bug #4: Producer dead, poller only

Sau producer OOM, BinancePricePoller (REST 1s) vẫn chạy → giá 3 fields, 1Hz.

**Discovery:** Backend `/stream/all` payload chỉ có 6 fields (price, bid, ask, change, volume, event_time).

**Fix:** Phase 4 deploy ticker-ws, disable poller:
```python
# backend/app.py lifespan
# await binance_price_poller.start()  # ← comment out
```

### Bug #5: Chart không realtime nếu không F5

**Symptom:** User phải F5 mỗi phút để xem giá mới.

**Root cause 1 (backend):** Push condition `if any_changed` → bucket 1m, OHLC không đổi giữa các tick → no push.

**Root cause 2 (frontend):** `MAX_RECONNECT_RETRIES=5` → WS chết sau 5 lần.

**Fix:**
- Backend: track `last_ticker_ts`, push `if any_changed or ticker_updated`
- Frontend: infinite retries + 45s watchdog

### Bug #6: Nginx 502 Connection refused

**Cause:**
```nginx
set $fastapi_upstream http://fastapi:8000;
proxy_pass $fastapi_upstream;
```
Variable `proxy_pass` không trigger `resolver` → DNS cached permanently. Khi `fastapi:8000` VIP thay đổi (restart), Nginx tiếp tục dùng IP cũ → 502.

**Fix:**
```nginx
resolver 127.0.0.11 valid=5s;
proxy_pass http://fastapi:8000;  # ← direct, no variable
```

### Bug #7: Blob parse crash

**Root cause:** `send_bytes()` → binary frame → Blob → `JSON.parse(blob)` throws.

**Detection:** Playwright pageerror capture.

**Fix:** `parseWsData` helper with Blob.text().

### Bug #8: ticker-ws 403 reconnect

Binance AWS ELB geofence → 403 trên một số IP ranges. Backoff 30s, thử lại sau.

## 51. Caveats (Chưa Fix)

| # | Issue | File | Impact |
|---|---|---|
| 1 | `004_agents_metadata.sql` + `004_phaseC_news_enhancements.sql` trùng số | `backend/migrations/` | Migration ordering bug — renaming cần |
| 2 | `keydb_depth.py` drops `exchange` từ orderbook key | `src/processing/writers/keydb_depth.py` | Multi-exchange orderbook collide |
| 3 | `lakehouse/pipeline.py` ticker dedup omit `exchange` | `src/lakehouse/pipeline.py` | Multi-exchange dedup sai |
| 4 | Frontend `useEffect([chartCandles])` reverted | `frontend/src/App.tsx` | Optimization đã bỏ, không ảnh hưởng |
| 5 | No test runner cho frontend hooks | `frontend/src/features/` | Chưa có unit tests |
| 6 | Missing health checks: producer, flink-jobmanager, ... | `docker-compose.yml` | Swarm không auto-restart |
| 7 | Backend single WS route gửi tất cả 8 timeframes | `backend/api/websocket.py` | Payload ~4KB, no heartbeat |
| 8 | Ticker API là exchange-aware nhưng simple mid-price avg | `backend/api/ticker.py` | Not volume-weighted |
| 9 | Trade summary dùng ticker metadata | `backend/api/trades.py` | Không chính xác nhưng OK |
| 10 | OKX producer path disabled | `src/producer/main.py` | Chưa test end-to-end |
| 11 | Dagster Spark catalog mismatch | `orchestration/assets.py` | Tables invisible |
| 12 | `scripts/job_watchdog.py` 0/1 replicas | `scripts/` | Flink failures cần manual restart |
| 13 | Duplicate `auto_submit_jobs.sh` + `submit_flink.sh` | `scripts/` | Maintenance overhead |
| 14 | `deploy_aws_swarm.sh` CUSTOM_IMAGES include kafka (not built) | `scripts/` | Deploy có thể fail |
| 15 | No rollback on deploy failure | `scripts/` | Partial state |
| 16 | Iceberg gold join stale in `/api/market/overview` | `backend/api/market.py` | Heatmap có thể sai |
| 17 | Missing memory limits cho nhiều services | `docker-compose.yml` | OOM cascade có thể xảy ra |
| 18 | Docker Compose services using `depends_on` với healthcheck thiếu | N/A | Startup order chưa đảm bảo |

### Priority fixes

- **High:** #2, #3 (multi-exchange issues), #6 (health checks)
- **Medium:** #1 (migration prefix), #11 (catalog mismatch), #16 (heatmap)
- **Low:** #4, #5, #12, #13, #14, #15, #17, #18

### Cách xử lý #2 (keydb_depth.py):

```python
# Current (WRONG):
key = f"orderbook:{symbol}"

# Should be:
key = f"orderbook:{exchange}:{symbol}"
```

### Cách xử lý #3 (lakehouse ticker dedup):

```python
# Current: dropDuplicates(["symbol", "event_time"])
# Should: dropDuplicates(["exchange", "symbol", "event_time"])
```

<!-- Kết thúc Phần 7. Tiếp theo: Phần 8 — Deep Dive 8 Shards -->
# Phần 8 — Deep Dive: Kiến Trúc 8 Shards Của `binance-ticker-ws`

> **Đây là phần quan trọng nhất.** Nếu bạn hiểu Phần 3 + 4 + 5 + 8, bạn hiểu cách dữ liệu chảy từ Binance về pixel trên màn hình.

## 52. Tại Sao 8 Shards?

### Bài toán

LMView theo dõi **671 USDT trading pairs** (top theo 24h quote volume của Binance).

Binance WebSocket giới hạn **~200 streams** cho `@ticker` trên 1 connection (combined-stream format). Vượt quá → disconnect.

Nếu gom 671 symbols vào 1 connection:
- 671 > 200 → bị từ chối
- Ngay cả khi accept, ~671 msg/s làm 1 asyncio recv() quá tải
- 1 disconnect = **tất cả 671 symbols** tối cùng lúc

→ Phải SHARD (chia nhỏ). Mỗi shard = 1 WS connection độc lập.

### Tại sao 8 (cụ thể là 8)?

```
TOP_N        = 671 symbols
SHARDS       = 8
SYMBOLS_PER_SHARD = 100
total capacity = 8 × 100 = 800  (dư so với 671)
```

671 / 8 = **83.875 symbols per shard** (làm tròn lên ~84).

Binance soft limit ~200 streams/conn (không có hard limit, nhưng > 150 thì hay disconnect). 100 là middle-ground an toàn.

### Nếu TOP_N tăng lên > 800?

`TickerConfig.load()` xử lý gracefully:

```python
for i in range(0, len(symbols), SYMBOLS_PER_SHARD):
    shards.append(symbols[i : i + SYMBOLS_PER_SHARD])
```

Nếu `len(symbols) = 1000` → 10 chunks → 10 shards. Không cần thay đổi code.

## 53. Khởi Tạo Shard

### Bước 1: Load + xếp hạng symbols

`TickerConfig.load()` chạy 1 lần lúc startup (và planned refresh mỗi `SYMBOL_REFRESH_SEC` = 3600s, nhưng hiện tại chưa impl).

```python
# src/ticker_ws/config.py
EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/ticker/24hr"
TOP_N = 671  # Top 671 USDT pairs

async def load():
    # Fetch ~2500 tickers từ Binance REST
    rows = await fetch(EXCHANGE_INFO_URL)

    # Filter: chỉ USDT pairs có volume > 0
    usdt_rows = [
        r for r in rows
        if r.get("symbol", "").endswith("USDT")
        and r.get("quoteVolume") not in (None, "", "0", "0.0")
    ]

    # Sort theo 24h quoteVolume desc
    usdt_rows.sort(key=lambda r: float(r["quoteVolume"]), reverse=True)

    # Take top 671
    symbols = [r["symbol"] for r in usdt_rows[:TOP_N]]
```

Kết quả: 671 USDT pairs, top 99% volume.

### Bước 2: Chia thành 8 shards

```python
# Split vào chunks 100
shards = []
for i in range(0, 671, 100):
    shards.append(symbols[i:i+100])
# shards = [
#   ["BTCUSDT", "ETHUSDT", ..., "LINAUSDT"],      # shard 0: 84 symbols
#   ["MATICUSDT", "ARBUSDT", ..., "PHBUSDT"],      # shard 1: 84 symbols
#   ...
#   [còn lại]                                       # shard 7: 83 symbols
# ]

# Redistribute evenly nếu không đều
if len(shards) < SHARDS:
    per = ceil(671 / 8)  # = 84
    shards = [symbols[i:i+per] for i in range(0, 671, per)][:8]
```

### Bước 3: Build combined-stream URLs

```python
def shard_url(self, shard_id: int) -> str:
    streams = "/".join(f"{s.lower()}@ticker" for s in self.shards[shard_id])
    return f"{WS_BASE}?streams={streams}"
```

Shard 0 (84 symbols) URL:
```
wss://stream.binance.com:9443/stream?streams=
  btcusdt@ticker/
  ethusdt@ticker/
  bnbusdt@ticker/
  solusdt@ticker/
  xplusdt@ticker/
  dogeusdt@ticker/
  adausdt@ticker/
  trxusdt@ticker/
  ...
  linausdt@ticker
```

**Combined stream format:**
- 1 WebSocket connection
- Nhiều ticker streams multiplex trên 1 TCP socket
- Mỗi message: `{"stream": "btcusdt@ticker", "data": {...}}`
- Trade-off: message lớn hơn, parsing nhiều hơn, nhưng ít connection

### Bước 4: Spawn 8 shard tasks

```python
shards = [TickerShard(i, config.shard_url(i), writer) for i in range(8)]
shard_tasks = [
    asyncio.create_task(s.run(stop_event), name=f"shard-{i}")
    for i, s in enumerate(shards)
]
```

8 concurrent asyncio tasks. Mỗi task chạy độc lập.

## 54. State Machine Của 1 Shard

```
┌────────────┐
│   START    │
└─────┬──────┘
      │ asyncio.create_task(s.run(stop_event))
      ▼
┌────────────┐
│  CONNECT   │──── websockets.connect(self.url) ───┐
│            │                                      │
│ backoff=1s │                                      │ success (101)
└─────┬──────┘                                      ▼
      │ timeout/err                        ┌──────────────┐
      ▼                                    │  CONNECTED   │
┌─────────────┐  close/err                 │              │
│  WAITING    │◄───────────────────────────│  recv loop   │
│  (backoff)  │                            │              │
└─────┬───────┘                            └──────┬───────┘
      │ sleep (backoff + jitter)                 │ ws.recv() returns
      ▼                                          ▼
┌────────────┐                            ┌──────────────┐
│  RECONNECT │                            │  HANDLE      │
│  attempt++ │                            │  FRAME       │
└─────┬──────┘                            │  (parse + buffer)│
      │                                    └──────┬───────┘
      └──────────────► CONNECT                  │
                                                   │ any error
                                                   ▼
                                            (back to WAITING)
```

### Phase 1: Connect

```python
async with websockets.connect(
    self.url,
    ping_interval=PING_INTERVAL_S,        # 30s — gửi ping
    ping_timeout=PING_TIMEOUT_S,          # 10s — đợi pong
    close_timeout=5,
    max_size=8 * 1024 * 1024,             # 8 MB — max message size
    open_timeout=15,
) as ws:
    self.connected = True
```

Binance trả về **101 Switching Protocols** → enter recv loop.
Nếu **403** hoặc **429** → `InvalidStatusCode` exception → 4× backoff (rate limit path).

### Phase 2: Recv loop

```python
while not stop_event.is_set():
    try:
        raw = await asyncio.wait_for(
            ws.recv(),
            timeout=PING_INTERVAL_S + PING_TIMEOUT_S + 5,  # 45s
        )
    except asyncio.TimeoutError:
        log.warning("[shard %d] recv timeout, closing", self.shard_id)
        break
    self._handle_frame(raw)
```

Timeout = 45s. Nếu 45s không có message → close. `websockets` library handle ping/pong internally; nếu Binance không pong trong 10s → close connection.

### Phase 3: Handle frame

```python
def _handle_frame(self, raw: str | bytes) -> None:
    self.frames_total += 1
    self.last_frame_at = time.time()
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    # Combined stream: {"stream":"btcusdt@ticker","data":{...}}
    data = msg.get("data") if isinstance(msg, dict) else None
    if not isinstance(data, dict):
        return

    mapping = parse_ticker(data)
    if not mapping:
        return

    sym = data.get("s")
    if not sym:
        return

    key = redis_key("binance", sym)
    self.writer.add(key, mapping)
    self.tickers_total += 1
    self.last_event_time_ms = int(data.get("E", 0))
```

Bốn bước:
1. **Decode** (bytes → string nếu cần)
2. **JSON parse** message envelope
3. **Extract data** từ `{"stream": ..., "data": {...}}`
4. **Map to Redis fields** via `parse_ticker()`, add vào writer buffer

Writer shared giữa 8 shards — 1 dict + 1 flush task.

### Phase 4: Reconnect với backoff

```python
backoff_ms = RECONNECT_BASE_MS  # 1000
while not stop_event.is_set():
    try:
        await self._connect_and_consume(stop_event)
        backoff_ms = RECONNECT_BASE_MS  # Success → reset
    except (ConnectionClosed, ...):
        self.connected = False
    except InvalidStatusCode as e:
        if "403" in str(e) or "429" in str(e):
            backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 4)  # 4× cho rate limit
    except (WebSocketException, OSError, asyncio.TimeoutError) as e:
        self.connected = False
    except Exception as e:
        log.exception("[shard %d] unexpected: %s", self.shard_id, e)
        self.connected = False

    if stop_event.is_set():
        break

    # Exponential backoff với jitter
    jitter_ms = random.randint(0, 1000)
    sleep_ms = min(RECONNECT_MAX_MS, backoff_ms) + jitter_ms
    log.info("[shard %d] reconnecting in %dms (attempt=%d)", ...)

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=sleep_ms / 1000.0)
        break
    except asyncio.TimeoutError:
        pass

    backoff_ms = min(RECONNECT_MAX_MS, backoff_ms * 2)
    self.reconnects_total += 1
```

**Backoff schedule (không rate limit):**

| Attempt | Sleep (no jitter) | With 0-1000ms jitter |
|---|---|---|
| 1 | 1000 ms | 1-2 s |
| 2 | 2000 ms | 2-3 s |
| 3 | 4000 ms | 4-5 s |
| 4 | 8000 ms | 8-9 s |
| 5 | 16000 ms | 16-17 s |
| 6+ | 30000 ms (cap) | 30-31 s |

**Backoff schedule (rate limit 403/429):**

| Attempt | Sleep (no jitter) | With 0-1000ms jitter |
|---|---|---|
| 1 | 4000 ms | 4-5 s |
| 2 | 16000 ms | 16-17 s |
| 3+ | 30000 ms (cap) | 30-31 s |

## 55. Đường Đi Của 1 Message

Trace từ Binance match → Redis:

```
[T+0ms]     Binance matching engine khớp lệnh BTCUSDT @ 63743.90
[T+50ms]    Binance broadcast WS message
            payload: {"stream":"btcusdt@ticker","data":{s:"BTCUSDT", E:1781937642016, c:"63743.90", b:"63743.80", a:"63744.00", ...}}
            → shard 0's WS connection nhận trên multiplexed stream

[T+51ms]    websockets library: ws.recv() trả về JSON string
[T+51.5ms]  _handle_frame(raw) called
            - frames_total += 1
            - last_frame_at = now
            - json.loads(raw) → msg
            - msg.get("data") → {s, E, c, b, a, B, A, v, q, ...}
[T+52ms]    parse_ticker(data) called
            - sym = "BTCUSDT"
            - out = {price: "63743.90", bid: "63743.80", ask: "63744.00", ...}
            - 20 fields populated
            - exchange = "binance" added
[T+52.5ms]  redis_key("binance", "BTCUSDT") = "ticker:latest:binance:BTCUSDT"
[T+53ms]    writer.add(key, mapping)
            - self._buffer["ticker:latest:binance:BTCUSDT"] = mapping
            - if buffer >= 2000: asyncio.create_task(self.flush())
[T+53.5ms]  shard stats updated

[T+50-100ms] (khi flush timer fire)  ← coroutine riêng
            writer._flush_loop wake up (50ms interval)
            - snapshot = list(self._buffer.items())
            - self._buffer.clear()
            - pipe = self._r.pipeline(transaction=False)
            - for (key, mapping) in items:
                  pipe.hset(key, mapping=mapping)  # 20 fields, ~500 bytes
                  pipe.expire(key, 300)
            - await pipe.execute()  # 1 network RTT

[T+150ms]   Redis writes committed
            - "ticker:latest:binance:BTCUSDT" hash updated
            - TTL refreshed to 300s

[T+~50-100ms later]  FastAPI reads
            - Backend's _stream_all_impl reads HGETALL on BTCUSDT
            - 20 fields returned
            - Wrapped in _ticker payload, sent qua /api/stream/all WS
```

**Tổng latency:** ~250-700ms (Binance event → pixel trên browser).

## 56. Batched Redis Writer (Quan Trọng)

Single biggest optimization: **buffer + pipeline**.

```python
# redis_writer.py
self._buffer: Dict[str, Dict[str, str]] = {}  # key → latest mapping
```

Khi `_handle_frame` gọi `writer.add(key, mapping)`:
```python
def add(self, key: str, mapping: Dict[str, str]) -> None:
    self._buffer[key] = mapping  # ← GHI ĐÈ previous unsent value
    if len(self._buffer) >= REDIS_FLUSH_MAX_BUFFER:
        asyncio.create_task(self.flush())
```

**Ghi đè là chìa khóa**: Nếu BTCUSDT có 3 updates trong 50ms → chỉ latest còn lại. Binance push ~1Hz/symbol → 3 updates trong 50ms = giá volatile. Ta chỉ quan tâm giá MỚI NHẤT, không cần history.

### Flush trigger — 3 cách

1. **Timer (50ms):** `_flush_loop` mỗi 50ms
2. **Size cap (2000):** Nếu buffer > 2000 items → flush ngay
3. **Shutdown:** `writer.stop()` flush remainder

Cho 8 shards × ~671 msg/s tổng = ~671 msg/s, average buffer giữa các flushes:
```
671 msg/s × 0.05s = 33.55 messages per flush
```

Well under 2000 → timer là trigger chính.

### Pipeline (1 RTT cho tất cả writes)

```python
async def flush(self) -> None:
    if not self._buffer:
        return
    items = list(self._buffer.items())
    self._buffer.clear()  # ← clear TRƯỚC khi network call

    try:
        pipe = self._r.pipeline(transaction=False)
        for key, mapping in items:
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, REDIS_KEY_TTL_S)
        await pipe.execute()  # ← 1 RTT
    except Exception as e:
        # Re-buffer on failure
        for key, mapping in items:
            self._buffer[key] = mapping
```

**Tại sao clear trước execute?** Nếu `pipe.execute()` hang (network timeout), ta không muốn block tick tiếp theo. Buffer đã rỗng; next `add()` calls sẽ bắt đầu fill lại.

**Tại sao `transaction=False`?** MULTI/EXEC chậm hơn vì Redis cần hold keys. Non-transactional pipeline chỉ gửi tất cả commands trong 1 TCP write — nhanh hơn nhiều, không cần atomicity cho ticker data.

**Tại sao pipeline?** Mỗi `HSET + EXPIRE` = 1 RTT. Cho 33 messages, 66 RTTs. Pipeline = 1 RTT. Tại 1ms RTT, 66ms → 1ms, nhanh hơn 66×.

## 57. Sentinel-Aware Connection

```python
async def get_redis() -> redis_async.Redis:
    sentinel_nodes = [
        tuple(node.split(":")) for node in REDIS_SENTINELS.split(",")
    ]
    try:
        from redis.asyncio.sentinel import Sentinel as AsyncSentinel
        sentinel = AsyncSentinel(sentinel_nodes, socket_timeout=0.5, ...)
        client = sentinel.master_for(
            REDIS_MASTER_NAME,  # "mymaster"
            decode_responses=False,
            max_connections=64,
        )
        await client.ping()
        return client
    except Exception:
        # Fallback to direct
        client = redis_async.Redis(host=REDIS_HOST, port=REDIS_PORT, ...)
        return client
```

**Tại sao Sentinel?** Khi Redis Sentinel failover, master mới được bầu. `sentinel.master_for("mymaster")` luôn trả về CURRENT master. Direct connection tới `redis-master:6379` có thể bị trỏ vào replica → write fail với `READONLY`.

**Tại sao fallback direct?** Khi Swarm startup, Sentinels có thể chưa ready. Fallback cho degraded mode (vẫn work, chỉ kém robust).

> **⚠️ Caveat:** Swarm VIP `redis-master` KHÔNG chỉ round-robin master — nó round-robin tất cả nodes (master + replicas). Fallback có thể hit replica và fail. Sentinel path là production-correct.

## 58. Update Frequency Theo Symbol

Binance `@ticker` push **tối đa 1 update/symbol/giây** (stream bị throttle). Frequency thực tế phụ thuộc vào trading activity:

| Symbol type | Example | Avg updates/s | Notes |
|---|---|---|---|
| Major (BTC, ETH, BNB) | BTCUSDT | ~1.0 Hz | Luôn active, luôn có trade mỗi giây |
| Mid-tier (SOL, DOGE, XRP) | SOLUSDT | ~1.0 Hz | Active markets |
| DeFi / L2 (ARB, OP, MATIC) | ARBUSDT | ~0.5-0.8 Hz | Có giây không có trade |
| Low-volume (long-tail) | LINAUSDT | ~0.05-0.2 Hz | 1 update mỗi 5-20 giây |

**Tổng cluster-wide update rate:** ~500-700 msg/s qua 8 shards. Tại 50ms flush, ~25-35 HSETs per flush.

## 59. Per-shard Stats Endpoint

`GET /healthz` (port 9100) trả về:

```json
{
  "ok": true,
  "uptime_s": 3634.7,
  "shards": [
    {
      "shard_id": 0,
      "connected": true,
      "frames_total": 234567,
      "tickers_total": 234567,
      "reconnects_total": 2,
      "uptime_s": 3612.4,
      "last_frame_age_s": 0.012,
      "last_event_latency_ms": 234.5
    },
    ...
  ]
}
```

**Field meanings:**
- `connected` — current WebSocket state
- `frames_total` — total messages từ process start
- `tickers_total` — total ticker payloads parsed OK
- `reconnects_total` — số reconnect cycles (0 = rock solid)
- `uptime_s` — seconds từ current connection established
- `last_frame_age_s` — thời gian từ lần cuối nhận message (low = healthy)
- `last_event_latency_ms` — `(now - last_event_time)` (latency từ Binance event → process)

## 60. Prometheus Metrics

Exposed on `:9100/metrics`:

| Metric | Type | Description |
|---|---|---|
| `ticker_ws_frames_total` | counter | Total WS frames received across all shards |
| `ticker_ws_tickers_total` | counter | Total ticker payloads parsed + buffered |
| `ticker_ws_reconnects_total` | counter | Total reconnect attempts |
| `ticker_ws_shards_up` | gauge | Số shards currently connected |
| `ticker_ws_redis_buffer_size` | gauge | Pending items trong Redis writer buffer |
| `ticker_ws_redis_flush_seconds` | histogram | Redis pipeline flush latency (buckets 1ms-1s) |
| `ticker_ws_event_to_now_seconds` | histogram | Binance event_time → now() trong process (buckets 50ms-5s) |

`event_to_now_seconds` là SLI quan trọng: latency từ lúc Binance's server thấy trade đến lúc Python process nhận WS frame.

### PromQL queries (Grafana)

```promql
# Average end-to-end latency (event → process)
histogram_quantile(0.50, rate(ticker_ws_event_to_now_seconds_bucket[5m]))
histogram_quantile(0.95, rate(ticker_ws_event_to_now_seconds_bucket[5m]))
histogram_quantile(0.99, rate(ticker_ws_event_to_now_seconds_bucket[5m]))

# Aggregate flush latency
rate(ticker_ws_redis_flush_seconds_sum[5m]) / rate(ticker_ws_redis_flush_seconds_count[5m])

# Reconnect rate
rate(ticker_ws_reconnects_total[5m])
```

### Healthy thresholds

```promql
ticker_ws_shards_up == 8                    # all shards connected
rate(event_to_now_seconds_sum[5m]) / rate(event_to_now_seconds_count[5m]) < 0.5  # avg < 500ms
histogram_quantile(0.95, ...) < 1.0          # p95 < 1s
rate(reconnects_total[1h]) < 0.05            # < 1 reconnect/20h
```

## 61. Failure Modes Per Shard

| Failure | Symptom | Recovery |
|---|---|---|
| Binance 403 (geofencing) | `InvalidStatusCode` on connect | 4× backoff (slower), reconnect khi Binance ELB allow |
| Binance 429 (rate limit) | `InvalidStatusCode` on connect | Same 4× backoff path |
| Network blip (TCP RST) | `ConnectionClosed` | 1s/2s/4s... backoff with jitter |
| DNS resolution fails | `OSError` on connect | 1s/2s/4s... backoff with jitter |
| Ping timeout (Binance dead) | `asyncio.TimeoutError` after 45s | Same backoff |
| JSON parse error (corrupted frame) | `json.JSONDecodeError` | Logged, frame dropped, no reconnect |
| Missing `s` field (incomplete frame) | `sym` is None | Logged, frame dropped, no reconnect |
| Sentinel unreachable | `Exception` trong `get_redis()` | Fallback to direct Redis |
| Direct Redis unreachable | `redis.exceptions.ConnectionError` | pipeline.execute() throws, items re-buffered |
| Redis pipeline write fails | Same as above | Items re-buffered, retried next flush |

### "No data" detection (frontend)

Frontend's 45s watchdog (§32) checks cho mọi message arrival. Nếu shard 0 dark 45s, **frontend không reconnect** (backend WS vẫn alive). User thấy giá cũ. Phát hiện qua:

```promql
histogram_quantile(0.99, rate(ticker_ws_event_to_now_seconds_bucket[5m])) > 5
```

Backend có alert riêng: nếu `ticker:latest:binance:BTCUSDT`'s `event_time` > 10s trong quá khứ → raise alert.

## 62. Capacity Planning

### Current load

- 8 shards × ~84 symbols = 672 streams
- ~500-700 msg/s total
- ~25-35 HSETs per 50ms flush
- Buffer stays at 5-50 items giữa flushes
- CPU: < 5% per shard (mostly I/O wait)
- Memory: ~50 MB resident per shard
- Network: ~50 KB/s per shard (combined stream)

### Headroom

- Binance combined-stream limit: ~200 streams/conn → 8 shards × 200 = 1600 capacity
- Redis Sentinel HSET throughput: ~100K writes/s → 700 writes/s uses 0.7%
- Pipeline batching: 1 RTT per 50ms → 20 RTT/s → negligible
- Swarm limits: 4 CPU, 8 GB RAM currently → handle 4-5× load

### Scaling up

Nếu TOP_N doubles lên 1500:
- Shards: 1500 / 100 = 15 shards (không cần code change)
- Mỗi shard: still ~100 symbols, ~100 msg/s
- Total: ~1500 msg/s, ~75 HSETs per flush
- CPU: ~10% across 15 shards
- Memory: ~750 MB resident (well under 8 GB limit)

## 63. So Sánh Với Legacy Producer

| Aspect | Legacy producer | binance-ticker-ws |
|---|---|---|
| Architecture | Multi-threaded | Multi-shard async |
| Concurrency | 31 threads (per symbol pool) | 8 asyncio tasks (shard) |
| Memory resident | ~300 MB | ~50 MB |
| Symbol coverage | 200 (killed by OOM) | 671 (top by 24h quote volume) |
| Stream type | @kline, @depth, @ticker (mix) | @ticker only |
| Binance fields per symbol | 6-10 | 24 |
| Push rate | Variable | ~1 Hz per symbol |
| Resilience | OOM-killed, no auto-restart | Auto-reconnect with backoff, 4× for 403/429 |
| Health endpoint | None | `:9100/healthz` |
| Metrics | None | 7 Prometheus metrics on `:9100/metrics` |
| Restart on failure | Manual | Auto, sentinel failover |
| Status | Replaced (Phase 4) | Production |

### Tại sao producer vẫn tồn tại?

Producer còn handle:
- **Kline (1s candles)** — Flink aggregate thành 1m, 5m, 1h, 1d
- **Depth (order book)** — ghi Redis (depth5, depth10, depth20)

Nếu chết hẳn → không có kline real-time, không có order book mới.

**Kế hoạch tương lai:** `binance-kline-ws` + `binance-depth-ws` (cùng pattern như ticker-ws).

## 64. End-to-End Data Flow (Annotated)

```
[Binance matching engine]
   │
   │ Trade: BTC @ 63743.90 tại 1781937642016
   │
   ▼
[Binance WebSocket gateway]
   │ ~50ms RTT
   │
   ▼ wss://stream.binance.com:9443/stream
   │ payload: {"stream":"btcusdt@ticker","data":{s:"BTCUSDT", E:1781937642016, c:"63743.90", b:"63743.80", a:"63744.00", B:"0.500", A:"0.450", v:"12345.67", q:"789012345.6", p:"+500.10", P:"+0.79", ...}}
   │
   ▼
[binance-ticker-ws shard 0]  (~5ms parse + buffer)
   │
   │ _handle_frame():
   │   parse_ticker() → 20 Redis fields
   │   redis_key() → "ticker:latest:binance:BTCUSDT"
   │   writer.add(key, mapping) → buffer dict
   │
   ▼
[Redis writer buffer] (50ms timeout)
   │
   │ _flush_loop wake up
   │   pipe = r.pipeline(transaction=False)
   │   pipe.hset("ticker:latest:binance:BTCUSDT", mapping={20 fields})
   │   pipe.expire("ticker:latest:binance:BTCUSDT", 300)
   │   ... + 24 other keys trong flush này
   │   await pipe.execute()
   │
   ▼ 1 RTT to Redis
[Redis Sentinel master]
   │
   │ HSET committed
   │ TTL refreshed to 300s
   │
   ▼ ~2-5ms (within-cluster)
[FastAPI backend]
   │
   │ _stream_all_impl() (50ms loop, runs forever)
   │   for symbol in subscribed_symbols:
   │     ticker = await redis.hgetall("ticker:latest:binance:BTCUSDT")
   │     if any_changed or ticker_updated:
   │       await ws.send_bytes(json.dumps({"1m": candle, "5m": ..., "_ticker": ticker}).encode())
   │
   ▼ ~1-5ms (per-symbol read)
[FastAPI WebSocket push]
   │
   │ via Nginx (direct proxy_pass, no variable trick)
   │
   ▼ ~5-20ms (browser ↔ AWS EFS)
[Browser: marketDataService.ts]
   │
   │ createReconnectingWebSocket.onmessage
   │   await parseWsData(e.data)  ← handles Blob/string/ArrayBuffer
   │   for tf, kline in data:
   │     onCandle(tf, kline)
   │   if data._ticker:
   │     onTicker(ticker)
   │
   ▼ ~1ms (parse)
[React: CandlestickChart onTicker]
   │
   │ applyRealtimePriceToCandle(ticker.price, ticker.eventTime)
   │   bucketTime = floor(eventTime / 1000 / 60) * 60
   │   if formingCandleRef.current.time === bucketTime:
   │     nextCandle = {open: forming.open, high: max(forming.high, price), low: min(forming.low, price), close: price}
   │   else if bucketTime crossed:
   │     lastClosedCandleRef.current = forming
   │     nextCandle = {open: forming.close, ...}
   │   updateAllPriceSeries(nextCandle)
   │     candleRef.current?.update(nextCandle)  ← lightweight-charts native
   │
   ▼ ~1ms (canvas redraw)
[Browser canvas pixel]
   │
   └─► User thấy updated candle (wick, body, latest close)

Total: ~100-300ms từ Binance event → pixel
```

**Component latency chính là network** (Binance ↔ AWS, AWS ↔ browser). Python processing, Redis, chart updates đều sub-millisecond.

## 65. Operational Notes

### Check shard health

```bash
# Per-shard status
curl -s http://binance-ticker-ws:9100/healthz | jq '.shards[] | {shard_id, connected, last_event_latency_ms, reconnects_total}'

# Expected: 8 shards, all connected, latency p50 < 500ms, reconnects low
```

### Investigate high latency

```bash
# Prometheus histogram
curl -s http://binance-ticker-ws:9100/metrics | grep ticker_ws_event_to_now

# Redis pipeline latency
curl -s http://binance-ticker-ws:9100/metrics | grep ticker_ws_redis_flush

# Compare with Binance direct (RTT)
docker run --rm alpine ping -c 5 stream.binance.com
```

### Force shard restart

Không có per-shard restart. Restart toàn bộ:
```bash
docker service update --force cryptoprice_binance-ticker-ws
```

On restart, `TickerConfig.load()` chạy lại, shards reconnect, ~10s để full 671-symbol coverage.

### Symbol list refresh

Mỗi `SYMBOL_REFRESH_SEC` (default 3600s = 1h), symbol list được re-fetch. **Tuy nhiên**, code hiện tại chỉ load lúc startup. Để refresh mid-run, restart container.

## 66. Tương Lai (Phase 5+)

### WebSocket multiplexing (kế tiếp)

Mỗi shard có 1 URL với all streams concatenated. Binance support tối đa 200 streams/URL. Ta dùng 84-100.

Nếu muốn scale lên 1500 symbols:
- **Option A:** 15 shards × 100 streams (no code change, more shards)
- **Option B:** 8 shards × 188 streams (more per shard, higher load)
- **Option C:** Multiple URLs per shard

Hiện tại **Option A** (config-driven).

### Adaptive backoff

Right now 403/429 get 4× backoff. Có thể smarter:
- 403: check IP geolocation, fail fast
- 429: read `Retry-After` header
- 1011 (server error): exponential as is

### Symbol hot-swap

Nếu hot symbol mới xuất hiện (vd: meme coin pump to top 10), ta muốn nó trong vài phút, không phải vài giờ. Add "fast refresh" trigger khi volatility spike.

### Cross-exchange fan-out

Cùng architecture cho OKX, Bybit, Coinbase. Mỗi exchange có 1 service replica riêng. Redis key prefix đã exchange-qualified (`ticker:latest:{exchange}:{symbol}`).

### Compression

Binance support `permessage-deflate` (WS extension). Enable cắt ~70% message size cho JSON-heavy ticker. Trade-off: nhiều CPU hơn cho compression.

### Persistence on disconnect

Nếu tất cả 8 shards disconnect đồng thời (vd: AWS region-wide issue), không có ticker data. `_ticker` fields trong `/api/stream/all` stale. Có thể add: read last known values từ Iceberg silver_ticker.

## Tổng Kết

Phần 8 là deep-dive trên path quan trọng nhất. Nếu bạn hiểu:
- **Phần 3** (Redis keys, Flink pipeline, Avro schemas)
- **Phần 4** (backend WebSocket + push conditions)
- **Phần 5** (frontend parseWsData + forming candle)
- **Phần 8** (8 shards, Sentinel, end-to-end flow)

Bạn hiểu cách dữ liệu chảy từ Binance's matching engine tới pixel trên màn hình user trong < 300ms.

<!-- Kết thúc SYSTEM.md. Cảm ơn bạn đã đọc! -->

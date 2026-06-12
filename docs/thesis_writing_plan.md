# THESIS WRITING PLAN — LMView
## Kế hoạch viết chi tiết cho 4 chương trọng tâm

**Dự án:** LMView — Real-time Cryptocurrency Technical-Analysis Platform  
**Phiên bản codebase:** 0.23.1  
**Ngày lập kế hoạch:** 2026-06-11  
**Mục tiêu:** Bản thiết kế để AI sinh nội dung từng phần độc lập mà vẫn đảm bảo tính nhất quán.

---

# THÔNG TIN TỔNG QUAN ĐÃ PHÂN TÍCH TỪ CODEBASE

## Kiến trúc tổng thể đã xác nhận

| Tầng | Công nghệ thực tế | Bằng chứng |
|------|-------------------|------------|
| Ingestion | Binance WS + OKX WS (opt-in) → Avro → Kafka | `src/producer/main.py`, `src/exchanges/` |
| Speed | Flink 1.18.1 → Redis Sentinel + InfluxDB | `src/processing/pipeline.py`, 8 writers |
| Batch | Spark + Iceberg/MinIO → Trino | `src/lakehouse/pipeline.py`, `src/batch/` |
| Serving | FastAPI 0.115.6 + WebSocket | `backend/app.py`, `backend/api/` |
| Frontend | React 19.1 + lightweight-charts 5.2 | `frontend/` |
| Auth | PostgreSQL + JWT | `backend/core/security.py`, `backend/api/auth.py` |
| AI Phase 1 | Provider-agnostic LLM + pgvector RAG | `backend/services/ai/`, `backend/api/ai/` |
| Observability | Prometheus + Grafana + Loki | `config/` |
| Orchestration | Dagster | `orchestration/assets.py` |

## Luồng dữ liệu end-to-end đã xác nhận

```
Exchange WS → Producer → Kafka → Flink → Redis/InfluxDB → FastAPI WS → React
                                    → Spark → Iceberg → Trino → FastAPI REST → React
                         → Direct Redis (trade bypass, 50ms latency)
```

## Các quyết định kiến trúc quan trọng

1. Lambda Architecture (Speed + Batch + Serving)
2. Medallion Architecture cho Lakehouse (Bronze → Silver → Gold)
3. Dual Redis write path: Flink batch (500ms) + Producer direct trade (50ms)
4. Redis Sentinel cho HA (1 master + 2 replicas + 3 sentinels)
5. Health-gated failover: auto-switch sang Direct Redis khi Kafka+Flink down 60s+
6. Multi-source fallback chain: Redis → InfluxDB → Trino → REST API
7. Provider-agnostic AI routing: local vLLM → online API → mock fallback
8. pgvector RAG với HNSW index cho knowledge retrieval
9. Defense-in-depth AI safety: scope gate → prompt rules → output guard → action validator

## Điểm nổi bật đủ sức trở thành đóng góp kỹ thuật

1. **Lambda Architecture ứng dụng cho crypto**: Speed layer (Flink) + Batch layer (Spark/Iceberg) + Serving layer (FastAPI) cho real-time crypto TA
2. **Health-gated failover**: Producer tự động phát hiện Kafka+Flink down, chuyển sang Direct Redis write
3. **Multi-source candle fusion**: WebSocket merge trade + candle data từ nhiều nguồn Redis khác nhau
4. **True EMA vs SMA approximation**: Flink real-time indicators dùng true exponential smoothing, Spark batch dùng SMA approximation
5. **Provider-agnostic AI routing**: Hệ thống fallback chain qua nhiều LLM providers
6. **pgvector RAG pipeline**: Heading-aware chunking + cosine similarity + audit logging
7. **Medallion Lakehouse**: Bronze (raw) → Silver (unified + quality scoring) → Gold (9 business metrics tables)
8. **341 pytest test functions + 50 golden AI evaluation questions**: Độ phủ kiểm thử đáng kể

---

# PHẦN 1: KIẾN TRÚC HỆ THỐNG

## Mục tiêu chương
Trình bày kiến trúc tổng thể LMView, giải thích các quyết định thiết kế, và phân tích luồng dữ liệu. Đây là chương nền tảng, các chương khác sẽ tham chiếu lại.

## Dàn ý chi tiết

### 1.1 Tổng quan hệ thống (2 trang)
**Mục tiêu:** Giới thiệu LMView, mục tiêu nghiệp vụ, phạm vi hệ thống.

**Nội dung cần viết:**
- Bảng tóm tắt mục tiêu nghiệp vụ: real-time crypto TA cho trader cá nhân
- Phạm vi: 200+ symbols, 8 timeframes, multi-exchange (Binance+OKX)
- Yêu cầu phi chức năng: latency < 300ms end-to-end, 99.9% availability

**Bằng chứng từ codebase:**
- `README.md` — project description
- `docs/SYSTEM.md` Section 1 — Project Snapshot
- `docker-compose.yml` — 40 services, profiles

**Sơ đồ cần xây dựng:**
- Hình 1.1: Context diagram (LMView ↔ Exchange ↔ User)

**Dung lượng dự kiến:** ~60 dòng nội dung

**Tránh trùng lặp:** Không đi sâu vào implementation, chỉ mô tả "what" và "why"

---

### 1.2 Kiến trúc tổng thể — Lambda Architecture (3 trang)
**Mục tiêu:** Trình bày Lambda Architecture với 3 tầng Speed/Batch/Serving.

**Nội dung cần viết:**
- Tại sao chọn Lambda (không phải Kappa hay đơn giản hơn)
- 3 tầng: Speed (Flink), Batch (Spark), Serving (FastAPI)
- Bảng so sánh Speed vs Batch vs Serving (latency, throughput, storage)
- Ưu/nhược điểm của Lambda trong bối cảnh crypto

**Bằng chứng từ codebase:**
- `docs/SYSTEM.md` Section 2 — Architecture Overview
- `docs/final_data_flow.md` Phần 1.1 — Lambda Architecture
- `src/processing/pipeline.py` — Speed layer
- `src/lakehouse/pipeline.py` — Batch layer
- `backend/app.py` — Serving layer

**Sơ đồ cần xây dựng:**
- Hình 1.2: Lambda Architecture diagram (3 tầng, data flow arrows)

**Luận điểm học thuật:**
- Lambda Architecture cho phép hệ thống xử lý dữ liệu real-time VÀ historical analytics song song
- Trade-off: complexity vs flexibility — Lambda phức tạp hơn Kappa nhưng cho phép batch reprocessing

**Dung lượng dự kiến:** ~100 dòng

**Tránh trùng lặp:** Không mô tả chi tiết từng writer/job — dành cho Chương Backend/Database

---

### 1.3 Microservice vs Modular Monolith (1.5 trang)
**Mục tiêu:** Phân tích quyết định kiến trúc deployment.

**Nội dung cần viết:**
- LMView là **containerized modular monolith** trong Docker Compose
- FastAPI là 1 service duy nhất với modular routing
- Flink, Spark, Kafka là separate services
- Phân tích: khi nào nên tách microservice, khi nào monolith là đủ

**Bằng chứng từ codebase:**
- `docker-compose.yml` — 40 services nhưng FastAPI là 1 app duy nhất
- `backend/app.py` — single app, 17 router modules
- `backend/api/` — modular route handlers

**Luận điểm học thuật:**
- Modular monolith pattern: chia code theo module nhưng deploy đơn giản
- Docker Compose profiles cho phép chọn services cần thiết theo môi trường

**Dung lượng dự kiến:** ~50 dòng

---

### 1.4 Data Flow (3 trang)
**Mục tiêu:** Mô tả luồng dữ liệu từ Exchange đến User, cả Speed path và Batch path.

**Nội dung cần viết:**
- Speed path: Exchange WS → Producer → Kafka → Flink → Redis → FastAPI WS → React
- Batch path: Kafka → Spark → Iceberg → Trino → FastAPI REST → React
- Direct Redis path: Producer → Redis (trade bypass, health-gated)
- Data format: Avro (Kafka), Parquet (Iceberg), JSON (Redis/API)

**Bằng chứng từ codebase:**
- `docs/final_data_flow.md` toàn bộ 7 phần
- `src/producer/main.py` — producer flow
- `src/processing/pipeline.py` — Flink branches
- `src/lakehouse/pipeline.py` — Spark streaming
- `backend/api/websocket.py` — WS serving

**Sơ đồ cần xây dựng:**
- Hình 1.3: End-to-end data flow (speed path, highlighted in red)
- Hình 1.4: End-to-end data flow (batch path, highlighted in blue)

**Luận điểm học thuật:**
- Dual write path đảm bảo availability: primary (Kafka→Flink) + fallback (Direct Redis)
- Avro schema enforcement đảm bảo data contract consistency

**Dung lượng dự kiến:** ~100 dòng

---

### 1.5 Request Flow (2 trang)
**Mục tiêu:** Mô tả một HTTP request từ frontend đến backend và response.

**Nội dung cần viết:**
- REST request: React → Nginx → FastAPI → Redis/InfluxDB/Trino → Response
- WS request: React → Nginx → FastAPI WS → 50ms poll loop → Redis → Push
- Multi-source fallback: Redis → InfluxDB → Trino → REST API fallback

**Bằng chứng từ codebase:**
- `backend/api/klines.py` — klines endpoint với 5-step fallback
- `backend/api/websocket.py` — WS routes
- `frontend/src/services/marketDataService.ts` — API client

**Sơ đồ cần xây dựng:**
- Hình 1.5: REST request flow (sequence diagram)
- Hình 1.6: WebSocket request flow (sequence diagram)

**Dung lượng dự kiến:** ~70 dòng

---

### 1.6 Realtime Flow (2 trang)
**Mục tiêu:** Phân tích riêng real-time data flow (độ trễ thấp nhất).

**Nội dung cần viết:**
- Trade direct path: Binance WS → Producer → Redis `trade:latest` → FastAPI WS → React (~120ms)
- Candle aggregate path: Flink 1s→1m aggregation → Redis ZSET
- WebSocket `/stream/all` optimization: 1 Redis pipeline (6 commands) thay vì 60+ calls
- Change detection: chỉ push khi data thay đổi

**Bằng chứng từ codebase:**
- `src/exchanges/binance/redis_writer.py` — direct Redis writer
- `backend/api/websocket.py` — `_stream_all_impl` với Redis pipeline
- `CHANGELOG.md` v0.23.1 — Redis N+1 fix

**Sơ đồ cần xây dựng:**
- Hình 1.7: Real-time latency chain (tổng ~120-200ms)

**Luận điểm học thuật:**
- Redis pipeline optimization giảm N+1 problem trong WebSocket serving
- Health-gated failover: Graceful degradation khi Kafka/Flink down

**Dung lượng dự kiến:** ~70 dòng

---

### 1.7 Đồng bộ và bất đồng bộ (1.5 trang)
**Mục tiêu:** Phân tích sync vs async trong hệ thống.

**Nội dung cần viết:**
- Async: FastAPI handlers (async/await), Redis pipeline, WebSocket loop
- Sync blocking: Trino queries (wrapped trong `asyncio.to_thread`)
- Event-driven: Kafka pub/sub giữa Producer và Flink
- Batch processing: Spark micro-batch (1-minute trigger)

**Bằng chứng từ codebase:**
- `backend/api/klines.py` — async handlers
- `backend/api/market_overview.py` — `asyncio.to_thread` cho Trino
- `src/lakehouse/pipeline.py` — Spark trigger(processingTime="1 minute")

**Dung lượng dự kiến:** ~50 dòng

---

### 1.8 Caching (2 trang)
**Mục tiêu:** Mô tả chiến lược caching multi-layer.

**Nội dung cần viết:**
- Layer 1: Redis hot cache (ticker, candles, indicators, orderbook)
- Layer 2: InfluxDB warm cache (90 days candles/indicators)
- Layer 3: Iceberg cold storage (365 days)
- Layer 4: FastAPI response cache (200ms-1.5s TTL)
- Layer 5: Frontend in-memory cache (`_livePriceMap`, market/news cache)

**Bằng chứng từ codebase:**
- `backend/api/klines.py` — `klines_cache:{ex}:{sym}:{interval}:{limit}` TTL 200ms-1.5s
- `backend/tasks/market_fetcher.py` — in-memory market cache (300s)
- `frontend/src/services/marketDataService.ts` — `_livePriceMap`
- `docs/SYSTEM.md` Section 7 — Redis key patterns

**Sơ đồ cần xây dựng:**
- Hình 1.8: Multi-layer cache architecture

**Luận điểm học thuật:**
- Cache-aside pattern với TTL phân tầng theo freshness requirement
- Trade-off: consistency vs latency — shorter TTL = fresher data but more Redis load

**Dung lượng dự kiến:** ~70 dòng

---

### 1.9 Logging (1 trang)
**Mục tiêu:** Mô tả logging strategy.

**Nội dung cần viết:**
- Structured logging: `%(asctime)s [%(levelname)s] %(message)s`
- Prometheus metrics instrumentator cho FastAPI
- Producer metrics: `producer_kafka_messages_sent_total`, `producer_ws_reconnects_total`
- **Không bao giờ log credentials, tokens, hoặc API keys**

**Bằng chứng từ codebase:**
- `src/processing/writers/*.py` — logging pattern trong mọi writer
- `backend/app.py` — Prometheus instrumentator
- `src/producer/main.py` — Prometheus metrics

**Dung lượng dự kiến:** ~30 dòng

---

### 1.10 Monitoring (1.5 trang)
**Mục tiêu:** Mô tả monitoring stack.

**Nội dung cần viết:**
- Prometheus scrape jobs: FastAPI, Kafka, Flink, Redis, Spark, MinIO, Trino
- Grafana: 22 dashboards, 18 alert rules
- Loki + Promtail: centralized logging với label extraction
- Alerting: Flink checkpoint failures, Kafka lag, API latency p99

**Bằng chứng từ codebase:**
- `config/prometheus.yml` — scrape configuration
- `config/grafana/dashboards/` — 22 JSON dashboards
- `config/grafana/provisioning/alerting/rules.yml` — 18 alert rules
- `docs/SYSTEM.md` Section 12 — Observability

**Sơ đồ cần xây dựng:**
- Hình 1.9: Monitoring architecture (Prometheus ← exporters → Grafana)

**Dung lượng dự kiến:** ~50 dòng

---

### 1.11 Scaling (1.5 trang)
**Mục tiêu:** Mô tả chiến lược scaling.

**Nội dung cần viết:**
- Horizontal: Kafka partitions (12), Flink parallelism (12), Spark workers, FastAPI pods (K8s HPA)
- Vertical: Redis memory, Spark executor memory
- Data partitioning: Kafka (hash(symbol)), Iceberg (days(timestamp)), Redis (key-based sharding)

**Bằng chứng từ codebase:**
- `src/processing/pipeline.py` — `FLINK_PARALLELISM=12`
- `docker-compose.yml` — memory limits
- `docs/final_data_flow.md` Phần 7.7 — Scaling Patterns

**Dung lượng dự kiến:** ~50 dòng

---

### 1.12 High Availability (1.5 trang)
**Mục tiêu:** Mô tả HA mechanisms.

**Nội dung cần viết:**
- Kafka: 3 brokers, replication factor 3, min.insync.replicas 2
- Redis: Sentinel cluster (1 master + 2 replicas + 3 sentinels)
- Flink: checkpoint-based restart (failure_rate_restart: 5/10min)
- Spark: retry 4 times per task
- Direct Redis failover: health monitor auto-switch khi Kafka+Flink down

**Bằng chứng từ codebase:**
- `docker-compose.yml` — 3 Kafka brokers, 3 Sentinels
- `src/processing/pipeline.py` — restart strategy
- `src/producer/health_monitor.py` — `FAILOVER_THRESHOLD_SEC=60`
- `src/exchanges/binance/redis_writer.py` — direct write path

**Luận điểm học thuật:**
- Multi-layer HA: application-level (health monitor) + infrastructure-level (Sentinel)
- Trade-off: consistency vs availability — eventual consistency trong Flink aggregation

**Dung lượng dự kiến:** ~50 dòng

---

### 1.13 Fault Tolerance (1.5 trang)
**Mục tiêu:** Mô tả cơ chế chịu lỗi.

**Nội dung cần viết:**
- Kafka: at-least-once delivery, checkpoint-based offset commit
- Flink: exactly-once checkpoint, unaligned checkpoints enabled
- Spark: retry with exponential backoff (5 attempts)
- Backend: try/catch trong mọi writer, graceful degradation
- Multi-source fallback: Redis → InfluxDB → Trino → REST

**Bằng chứng từ codebase:**
- `src/processing/pipeline.py` — checkpoint mode EXACTLY_ONCE
- `src/lakehouse/pipeline.py` — `_start_query_with_retry`
- `backend/api/websocket.py` — WebSocketDisconnect + generic exception handling
- `docs/final_data_flow.md` Phần 7.6 — Failure Modes

**Dung lượng dự kiến:** ~50 dòng

---

### 1.14 Backup và Recovery (1 trang)
**Mục tiêu:** Mô tả chiến lược backup.

**Nội dung cần viết:**
- Flink checkpoints: S3 (MinIO) persistent storage
- Spark checkpoints: S3 (MinIO)
- Iceberg: time-travel + snapshot isolation
- PostgreSQL: migrations are idempotent, pgvector data
- Redis: RDB/AOF persistence, Sentinel replication

**Bằng chứng từ codebase:**
- `src/processing/pipeline.py` — `s3://flink-checkpoints/`
- `src/lakehouse/pipeline.py` — `s3://cryptoprice/checkpoints/`
- `backend/migrations/` — 4 idempotent SQL files

**Dung lượng dự kiến:** ~30 dòng

---

## Tổng dung lượng dự kiến Phần 1: ~22 trang (~700 dòng nội dung)

## Danh sách sơ đồ cần xây dựng
1. Hình 1.1: Context diagram
2. Hình 1.2: Lambda Architecture (3 tầng)
3. Hình 1.3: Speed path data flow
4. Hình 1.4: Batch path data flow
5. Hình 1.5: REST request sequence diagram
6. Hình 1.6: WebSocket request sequence diagram
7. Hình 1.7: Real-time latency chain
8. Hình 1.8: Multi-layer cache architecture
9. Hình 1.9: Monitoring architecture

## Rủi ro khi viết
1. **Quá nhiều chi tiết kỹ thuật** → Cần giữ ở mức "why" thay vì "how"
2. **Trùng lặp với chương Backend/Database** → Focus vào architecture decisions, không lặp implementation
3. **Lambda Architecture có thể bị criticize** → Chuẩn bị defense: tại sao Lambda phù hợp hơn Kappa cho use case này

## Chiến lược viết tránh vượt context
- Viết từng section độc lập (1.1 → 1.2 → ... → 1.14)
- Mỗi section chỉ cần: goal, key points (bullet), codebase references
- Không viết prose cho đến khi tất cả sections có outline
- Tái sử dụng sơ đồ từ `docs/final_data_flow.md` thay vì tạo mới

---

# PHẦN 2: AI AGENT

## Mục tiêu chương
Trình bày kiến trúc AI Phase 1 của LMView: Ask Mode với provider-agnostic routing, RAG knowledge base, và multi-layer safety.

## Dàn ý chi tiết

### 2.1 Vai trò AI trong hệ thống (1.5 trang)
**Mục tiêu:** Giới thiệu tại sao cần AI trong crypto TA platform.

**Nội dung cần viết:**
- AI as educational assistant (không phải trading bot)
- Phase 1: Ask Mode (chat-based analysis)
- Phases 2-5 roadmap: Interact Mode, Sentiment, Trade Analysis, Forecasting
- Non-goals: auto-trading, guaranteed predictions, code execution

**Bằng chứng từ codebase:**
- `docs/ai/AI_ROADMAP.md` — Phase 1-5 roadmap
- `docs/ai/AI_SECURITY.md` — "What the AI Cannot Do"
- `docs/ai/AI_ARCHITECTURE.md` — Phase 1 overview

**Luận điểm học thuật:**
- AI trong finance phải là **augmented intelligence** (hỗ trợ quyết định), không phải autonomous agent
- Regulatory compliance: không cung cấp financial advice trực tiếp

**Dung lượng dự kiến:** ~50 dòng

---

### 2.2 Kiến trúc AI Agent (2 trang)
**Mục tiêu:** Trình bày kiến trúc tổng thể AI.

**Nội dung cần viết:**
- AI chạy embedded trong FastAPI (không phải separate microservice)
- Pipeline: Auth → Scope Gate → Session → RAG → Prompt Builder → Provider Router → Output Guard → Store
- Docker Compose AI overlay: optional litellm/vllm services

**Bằng chứng từ codebase:**
- `docs/ai/AI_ARCHITECTURE.md` — architecture diagram
- `backend/api/ai/__init__.py` — router registration
- `backend/api/ai/chat.py` — chat endpoint implementation
- `docker-compose.ai.yml` — AI overlay services

**Sơ đồ cần xây dựng:**
- Hình 2.1: AI pipeline (scope gate → RAG → prompt → provider → output guard)

**Dung lượng dự kiến:** ~70 dòng

---

### 2.3 Workflow — Ask Mode Pipeline (2 trang)
**Mục tiêu:** Mô tả chi tiết Ask Mode workflow.

**Nội dung cần viết:**
- Step 1: Auth + session ownership check
- Step 2: Scope gate (deterministic classification)
- Step 3: Session/message persistence
- Step 4: Chart context assembly + data caveats
- Step 5: RAG retrieval (if enabled)
- Step 6: Prompt builder (system + context + RAG + history + user message)
- Step 7: Provider router → LLM completion
- Step 8: Output guard (financial safety + disclaimer)
- Step 9: Confidence estimation
- Step 10: Assistant message storage

**Bằng chứng từ codebase:**
- `backend/api/ai/chat.py` — full chat endpoint
- `backend/services/scope_gate_service.py` — scope gate
- `backend/services/ai/prompt_builder.py` — prompt construction
- `backend/services/ai/output_guard.py` — output validation
- `docs/ai/AI_API_CONTRACTS.md` — request/response contracts

**Sơ đồ cần xây dựng:**
- Hình 2.2: Ask Mode workflow (flowchart, 10 steps)

**Dung lượng dự kiến:** ~80 dòng

---

### 2.4 Prompt Engineering (2 trang)
**Mục tiêu:** Phân tích prompt construction strategy.

**Nội dung cần viết:**
- System prompt: financial safety rules, educational framing, bilingual guidelines
- Context injection: chart context (symbol, timeframe, indicators, latest candle)
- RAG context: top-K knowledge chunks with citations
- Data caveats: explicit warnings about data limitations
- Conversation history: session messages for context continuity

**Bằng chứng từ codebase:**
- `backend/services/ai/prompt_builder.py` — prompt construction
- `backend/services/ai/context_service.py` — data caveat generation
- `docs/ai/AI_SECURITY.md` — Layer 2: Prompt Safety

**Luận điểm học thuật:**
- Grounded generation: AI chỉ trả lời dựa trên verified knowledge + live data
- Context window management: giới hạn RAG chunks để không vượt model context

**Dung lượng dự kiến:** ~70 dòng

---

### 2.5 Tool Calling (0.5 trang)
**Mục tiêu:** Mô tả tool calling mechanism.

**Trạng thái:** Phase 2 (planned, scaffolded)

**Nội dung cần viết:**
- Chart actions: add_indicator, change_timeframe, set_symbol
- Validation: whitelist + parameter constraints
- User approval flow: AI proposes → user approves → frontend executes
- Audit trail: `ai_tool_actions` table

**Bằng chứng từ codebase:**
- `backend/api/ai/chart_actions.py` — validate + record
- `backend/models/ai/chart_actions.py` — action contracts
- `ai_service/app/tools/` — scaffolded tool registry

**Ghi chú:** Feature chưa hoàn thiện → ghi rõ "đang phát triển, kiến trúc đã scaffold"

**Dung lượng dự kiến:** ~20 dòng

---

### 2.6 MCP — Model Context Protocol (0.5 trang)
**Trạng thái:** **Không áp dụng** — LMView không sử dụng MCP.

**Nội dung cần viết:** Ghi rõ LMView dùng custom RAG pipeline (pgvector) thay vì MCP. Phân tích lý do: MCP phù hợp cho multi-tool orchestration, trong khi LMView chỉ cần knowledge retrieval.

**Dung lượng dự kiến:** ~15 dòng

---

### 2.7 Context Management (1.5 trang)
**Mục tiêu:** Phân tích cách hệ thống quản lý context cho AI.

**Nội dung cần viết:**
- Chart context: symbol, exchange, timeframe, selected indicators, latest candle
- Data caveats: 7 loại warning (placeholder, ticker-derived, stale, etc.)
- Session history: PostgreSQL message persistence
- Knowledge context: RAG chunks với heading-aware retrieval

**Bằng chứng từ codebase:**
- `backend/services/ai/context_service.py` — data caveat list
- `backend/api/ai/chart_context.py` — chart snapshot storage
- `backend/services/ai/chat_service.py` — session/message persistence
- `docs/ai/AI_API_CONTRACTS.md` — chart_context payload

**Dung lượng dự kiến:** ~50 dòng

---

### 2.8 Memory (1 trang)
**Mục tiêu:** Phân tích memory mechanism.

**Nội dung cần viết:**
- Short-term: session messages (PostgreSQL `ai_messages`)
- Long-term: RAG knowledge base (pgvector `ai_knowledge_chunks`)
- No cross-session memory: mỗi session độc lập

**Bằng chứng từ codebase:**
- `backend/migrations/001_phase0_schema.sql` — `ai_messages` table
- `backend/migrations/003_phase1_ai_rag.sql` — knowledge tables

**Dung lượng dự kiến:** ~30 dòng

---

### 2.9 Multi-step Reasoning (0.5 trang)
**Trạng thái:** **Không áp dụng** — Phase 1 chỉ có single-step Ask Mode.

**Nội dung cần viết:** Ghi rõ multi-step reasoning planned cho Phase 2 (LangGraph agent). Phase 1 chỉ là single-turn với session history.

**Bằng chứng từ codebase:**
- `docs/ai/AI_ROADMAP.md` — Phase 2: LangGraph agent orchestration
- `ai_service/app/graph/` — scaffolded LangGraph state

**Dung lượng dự kiến:** ~15 dòng

---

### 2.10 RAG — Retrieval-Augmented Generation (2.5 trang)
**Mục tiêu:** Phân tích chi tiết RAG pipeline.

**Nội dung cần viết:**
- Knowledge sources: 5 curated sources (TA, market structure, risk management, glossary, platform guide)
- Ingestion: Markdown → heading-aware chunking (1200 chars, 200 overlap) → embedding → pgvector
- Retrieval: query embedding → cosine similarity → top-K (default 6) → min score 0.25
- Filters: language, domain, tags, credibility_level, review_status
- Audit: `ai_knowledge_retrieval_logs` table

**Bằng chứng từ codebase:**
- `docs/ai/RAG_KNOWLEDGE_BASE.md` — full RAG documentation
- `backend/services/ai/knowledge_service.py` — ingestion + chunking
- `backend/services/ai/retrieval_service.py` — vector search
- `backend/migrations/003_phase1_ai_rag.sql` — schema
- `docs/ai/knowledge_base/registry.yml` — source registry

**Sơ đồ cần xây dựng:**
- Hình 2.3: RAG pipeline (ingestion → retrieval → enrichment)

**Luận điểm học thuật:**
- Heading-aware chunking giữ semantic coherence tốt hơn fixed-size chunking
- pgvector HNSW index cho efficient approximate nearest neighbor search

**Dung lượng dự kiến:** ~90 dòng

---

### 2.11 Embedding (1.5 trang)
**Mục tiêu:** Phân tích embedding strategy.

**Nội dung cần viết:**
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Lazy import: `sentence_transformers` không có trong requirements.txt mặc định
- Storage: pgvector `vector(384)` type
- Similarity: cosine distance

**Bằng chứng từ codebase:**
- `backend/services/ai/knowledge_service.py` — lazy import `sentence_transformers`
- `backend/migrations/003_phase1_ai_rag.sql` — `vector(384)` column
- `docker/fastapi/requirements.txt` — `litellm` included, `sentence-transformers` NOT included (lazy)

**Luận điểm học thuật:**
- Trade-off: model size vs accuracy — all-MiniLM-L6-v2 là lightweight nhưng đủ cho TA knowledge

**Dung lượng dự kiến:** ~50 dòng

---

### 2.12 Vector Search (1.5 trang)
**Mục tiêu:** Phân tích pgvector search mechanism.

**Nội dung cần viết:**
- HNSW index: m=16, ef_construction=64
- Cosine distance operator: `vector_cosine_ops`
- Query flow: embed query → SELECT with ORDER BY embedding <=> $query_embedding
- Performance: sub-second cho 10K+ vectors

**Bằng chứng từ codebase:**
- `backend/migrations/003_phase1_ai_rag.sql` — HNSW index DDL
- `backend/services/ai/retrieval_service.py` — search implementation

**Sơ đồ cần xây dựng:**
- Hình 2.4: pgvector search architecture

**Dung lượng dự kiến:** ~50 dòng

---

### 2.13 Chi phí vận hành (1 trang)
**Mục tiêu:** Ước tính chi phí vận hành AI.

**Nội dung cần viết:**
- Mock mode: chi phí = 0 (deterministic, no API calls)
- Local vLLM: GPU cost (NVIDIA GPU required)
- Online API: per-token pricing (Qwen, Llama, OpenAI, Gemini, DeepSeek)
- Fallback chain: ưu tiên local → API → mock để giảm cost
- pgvector: storage cost minimal (384-dim vectors)

**Bằng chứng từ codebase:**
- `docs/ai/AI_PROVIDER_ROUTING.md` — provider types và routing modes
- `backend/services/ai/provider_router.py` — fallback logic

**Dung lượng dự kiến:** ~30 dòng

---

### 2.14 Hiệu năng AI (1 trang)
**Mục tiêu:** Phân tích AI performance metrics.

**Nội dung cần viết:**
- Provider latency: mock (0ms), API (1-5s), local vLLM (0.5-2s)
- RAG retrieval: <100ms (pgvector HNSW)
- Scope gate: <1ms (deterministic)
- Output guard: <10ms (regex + pattern matching)
- Evaluation: 50 golden questions across 9 categories

**Bằng chứng từ codebase:**
- `docs/ai/AI_EVALUATION.md` — evaluation framework
- `tests/ai/golden_questions.py` — 50 test questions
- `tests/ai/test_ai_phase1.py` — Phase 1 tests

**Dung lượng dự kiến:** ~30 dòng

---

## Tổng dung lượng dự kiến Phần 2: ~16 trang (~550 dòng)

## Danh sách sơ đồ cần xây dựng
1. Hình 2.1: AI pipeline (scope gate → RAG → prompt → provider → output guard)
2. Hình 2.2: Ask Mode workflow flowchart (10 steps)
3. Hình 2.3: RAG pipeline (ingestion → retrieval → enrichment)
4. Hình 2.4: pgvector search architecture

## Rủi ro khi viết
1. **AI Phase 1 chưa có real LLM deployment** → Focus vào architecture + design, không claim performance numbers không có
2. **litellm/sentence-transformers không trong requirements** → Ghi rõ dependency là optional
3. **Tool calling, multi-step reasoning chưa implement** → Ghi rõ "planned", không viết như đã hoàn thiện
4. **MCP không sử dụng** → Ghi rõ "không áp dụng" thay vì bỏ qua

## Chiến lược viết tránh vượt context
- Mỗi AI service là 1 section độc lập
- Viết theo pattern: "Mục tiêu → Bằng chứng → Phân tích → Kết luận"
- Tái sử dụng architecture diagram từ `docs/ai/AI_ARCHITECTURE.md`
- Không viết code snippets dài — chỉ reference file paths

---

# PHẦN 3: BACKEND

## Mục tiêu chương
Trình bày kiến trúc backend FastAPI, module design, API design, authentication, và service layer.

## Dàn ý chi tiết

### 3.1 Backend Architecture (2.5 trang)
**Mục tiêu:** Tổng quan kiến trúc FastAPI.

**Nội dung cần viết:**
- FastAPI 0.115.6 với async/await
- Lifespan pattern: init PostgreSQL → run migrations → start background tasks
- Router registration order: health, ticker, klines, ..., ai, settings, admin
- Middleware: CORS, Prometheus instrumentator
- Thin route handlers → Service layer → Database clients

**Bằng chứng từ codebase:**
- `backend/app.py` — entry point, lifespan, router registration
- `backend/api/` — 17 route modules
- `backend/services/` — business logic
- `backend/core/` — config, constants, database clients

**Sơ đồ cần xây dựng:**
- Hình 3.1: FastAPI architecture (request → router → service → database)

**Luận điểm học thuật:**
- Layered architecture: separation of concerns giữa route handlers và business logic
- Async-first design: tận dụng Python asyncio cho I/O-bound operations

**Dung lượng dự kiến:** ~80 dòng

---

### 3.2 Module Design (2 trang)
**Mục tiêu:** Mô tả module organization.

**Nội dung cần viết:**
- `api/`: Thin route handlers (17 modules)
- `services/`: Business logic (20+ services)
- `core/`: Config, constants, database clients (8 modules)
- `models/`: Pydantic schemas (12 modules)
- `migrations/`: SQL migrations (4 files)
- `tasks/`: Background tasks (2 fetchers)

**Bằng chứng từ codebase:**
- `backend/` directory structure
- `AGENTS.md` Python Rules — backend architecture guidelines

**Dung lượng dự kiến:** ~70 dòng

---

### 3.3 API Design (3 trang)
**Mục tiêu:** Phân tích REST API + WebSocket API design.

**Nội dung cần viết:**
- REST: 30+ endpoints, grouped by domain (market, auth, ai, admin)
- WebSocket: 3 routes (stream/all, stream/{interval}, stream/indicators/{interval})
- Response format: JSON với DataFreshness metadata
- Error handling: HTTPException với structured error response
- Version: implicit (v0.23.1)

**Bằng chứng từ codebase:**
- `backend/api/*.py` — all route handlers
- `backend/models/common.py` — DataFreshness model
- `docs/SYSTEM.md` Section 9 — API Endpoints table

**Sơ đồ cần xây dựng:**
- Hình 3.2: API endpoint map (grouped by domain)

**Luận điểm học thuật:**
- REST cho request-response, WebSocket cho real-time push
- DataFreshness metadata cho transparent multi-source serving

**Dung lượng dự kiến:** ~100 dòng

---

### 3.4 Authentication (2 trang)
**Mục tiêu:** Phân tích auth mechanism.

**Nội dung cần viết:**
- JWT token-based auth (HS256)
- Registration, login, logout, refresh token
- Session storage: PostgreSQL `users` + `sessions` tables
- Password hashing: bcrypt via passlib
- Token storage: frontend localStorage

**Bằng chứng từ codebase:**
- `backend/core/security.py` — JWT creation/verification
- `backend/api/auth.py` — auth endpoints
- `backend/services/auth_service.py` — business logic
- `backend/migrations/001_phase0_schema.sql` — users/sessions tables
- `frontend/src/services/authService.ts` — frontend auth client

**Dung lượng dự kiến:** ~70 dòng

---

### 3.5 Authorization (1.5 trang)
**Mục tiêu:** Phân tích role-based access control.

**Nội dung cần viết:**
- Roles: user, admin
- Protected routes: `get_current_user` dependency
- Admin routes: `require_admin` dependency
- AI routes: require auth
- Knowledge ingest: admin-only

**Bằng chứng từ codebase:**
- `backend/core/auth_dependencies.py` — auth dependencies
- `backend/api/admin.py` — admin-only routes
- `backend/api/ai/knowledge.py` — admin-only ingest

**Dung lượng dự kiến:** ~50 dòng

---

### 3.6 Exception Handling (1 trang)
**Mục tiêu:** Phân tích error handling strategy.

**Nội dung cần viết:**
- HTTPException cho all API errors
- WebSocket error: log warning, continue (graceful)
- Service layer: try/catch, raise specific exceptions
- No bare `except:` blocks
- Error response format: `{"error": "...", "detail": "..."}`

**Bằng chứng từ codebase:**
- `backend/api/websocket.py` — WS error handling
- `AGENTS.md` Python Rules — "Raise specific exceptions. No bare except:"

**Dung lượng dự kiến:** ~30 dòng

---

### 3.7 Validation (1 trang)
**Mục tiêu:** Phân tích input validation.

**Nội dung cần viết:**
- Pydantic models cho request/response validation
- Symbol validation: uppercase, alphanumeric
- Interval validation: enum check against INTERVAL_SECONDS
- Limit validation: 1-1500
- Type safety: Pydantic strict mode

**Bằng chứng từ codebase:**
- `backend/models/` — Pydantic schemas
- `backend/services/candle_service.py` — validate_symbol, validate_interval
- `backend/core/constants.py` — INTERVAL_SECONDS

**Dung lượng dự kiến:** ~30 dòng

---

### 3.8 Service Layer (2 trang)
**Mục tiêu:** Phân tích business logic layer.

**Nội dung cần viết:**
- `candle_service.py`: aggregate, merge_unique, multi-source collectors
- `indicator_service.py`: snapshot, summary, supported list
- `auth_service.py`: register, login, logout, password change
- `ai_chat_service.py`: session/message CRUD
- `market_overview_service.py`: Trino gold queries
- `settings_service.py`: user preferences CRUD

**Bằng chứng từ codebase:**
- `backend/services/*.py` — all service files
- `AGENTS.md` — "Business logic in services"

**Luận điểm học thuật:**
- Service layer pattern: decouples business logic from HTTP concerns
- Enables testability: services can be unit-tested independently

**Dung lượng dự kiến:** ~70 dòng

---

### 3.9 Repository Layer (0.5 trang)
**Trạng thái:** **Không áp dụng** theo pattern truyền thống.

**Nội dung cần viết:** LMView không có separate repository layer. Database access nằm trong service layer qua utility functions (`get_redis()`, `get_trino_connection()`, PostgreSQL pool). Ghi rõ đây là pragmatic choice cho FastAPI async pattern.

**Dung lượng dự kiến:** ~15 dòng

---

### 3.10 Database Interaction (2 trang)
**Mục tiêu:** Phân tích cách backend tương tác với multi-database.

**Nội dung cần viết:**
- Redis Sentinel: async client, read from replica, write to master
- InfluxDB: Flux query language, write API
- Trino: JDBC connection via `asyncio.to_thread`
- PostgreSQL: asyncpg pool, migrations, pgvector
- Connection management: singleton clients, pool sizing

**Bằng chứng từ codebase:**
- `backend/core/database.py` — all database clients
- `backend/core/redis_sentinel.py` — Redis Sentinel
- `backend/core/postgres.py` — PostgreSQL pool + migrations
- `backend/api/market_overview.py` — Trino queries via `asyncio.to_thread`

**Sơ đồ cần xây dựng:**
- Hình 3.3: Backend database interaction (FastAPI → 4 databases)

**Luận điểm học thuật:**
- Polyglot persistence: mỗi database optimized cho use case riêng
- Redis (hot), InfluxDB (warm), Iceberg/Trino (cold), PostgreSQL (metadata)

**Dung lượng dự kiến:** ~70 dòng

---

## Tổng dung lượng dự kiến Phần 3: ~17 trang (~585 dòng)

## Danh sách sơ đồ cần xây dựng
1. Hình 3.1: FastAPI architecture layers
2. Hình 3.2: API endpoint map
3. Hình 3.3: Backend database interaction

## Rủi ro khi viết
1. **Quá nhiều endpoints (30+)** → Nhóm theo domain, không mô tả từng endpoint chi tiết
2. **Trùng lặp với Chương Database** → Focus vào HOW backend interacts, không mô tả schema
3. **AI endpoints có thể trùng Chương AI** → Chỉ mô tả routing, không phân tích AI logic

## Chiến lược viết tránh vượt context
- Nhóm endpoints theo domain: market, auth, ai, admin, settings
- Mỗi nhóm: table of endpoints + 1-2 representative examples
- Service layer: describe pattern, not every function
- Database interaction: describe client type, not every query

---

# PHẦN 4: DATABASE VÀ TRIỂN KHAI

## Mục tiêu chương
Trình bày thiết kế database (Redis, InfluxDB, Iceberg, PostgreSQL) và chiến lược triển khai (Docker, CI/CD, environments).

## Dàn ý chi tiết — DATABASE

### 4.1 Tổng quan Database (1 trang)
**Mục tiêu:** Giới thiệu polyglot persistence strategy.

**Nội dung cần viết:**
- 4 databases: Redis Sentinel, InfluxDB, Iceberg/MinIO, PostgreSQL
- Mỗi database phục vụ mục đích khác nhau
- Data lifecycle: hot (Redis, 7 days) → warm (InfluxDB, 90 days) → cold (Iceberg, 365 days)

**Bằng chứng từ codebase:**
- `docs/SYSTEM.md` Sections 7, 8
- `docs/final_data_flow.md` Phần 3, 4

**Sơ đồ cần xây dựng:**
- Hình 4.1: Polyglot persistence overview

**Dung lượng dự kiến:** ~30 dòng

---

### 4.2 Redis Sentinel (2 trang)
**Mục tiêu:** Phân tích Redis architecture.

**Nội dung cần viết:**
- Sentinel cluster: 1 master + 2 replicas + 3 sentinels
- Key patterns: 9 families (ticker, candle, indicator, orderbook, trade, cache)
- TTL strategy: 200ms (API cache) → 1 day (1s candles) → 7 days (indicators)
- Data types: Hash (latest), Sorted Set (history/time-series)

**Bằng chứng từ codebase:**
- `docs/SYSTEM.md` Section 7 — Redis key patterns table
- `src/processing/writers/keydb_*.py` — writer implementations
- `backend/core/redis_sentinel.py` — Sentinel client

**Sơ đồ cần xây dựng:**
- Hình 4.2: Redis key families và TTL strategy

**Dung lượng dự kiến:** ~70 dòng

---

### 4.3 InfluxDB (1.5 trang)
**Mục tiêu:** Phân tích time-series storage.

**Nội dung cần viết:**
- 3 measurements: `market_ticks`, `candles`, `indicators`
- Tags: symbol, exchange, interval
- Retention: 90 days
- Flux query language cho analytics

**Bằng chứng từ codebase:**
- `src/processing/writers/influxdb_ticker.py` — market_ticks writer
- `src/processing/writers/influxdb_kline.py` — candles writer
- `backend/services/candle_service.py` — Flux queries

**Dung lượng dự kiến:** ~50 dòng

---

### 4.4 Iceberg Lakehouse (2.5 trang)
**Mục tiêu:** Phân tích Medallion Architecture.

**Nội dung cần viết:**
- Bronze (3 tables): coin_ticker, coin_trades, coin_klines — raw, append-only
- Silver (2 tables): ticker_unified (quality scoring 0/50/100), kline_multi_timeframe (5 intervals)
- Gold (9 tables): market_overview, coin_ticker, momentum_indicators, indicator_history, market_dominance, volatility_ranking, movers_ranking, sector_performance, news_sentiment
- Partition strategy: days(timestamp), interval, exchange
- Write mode: append (Bronze/Silver), dynamic overwrite (Gold)

**Bằng chứng từ codebase:**
- `docs/final_data_flow.md` Phần 4 — full table schemas + transformations
- `src/lakehouse/pipeline.py` — Spark streaming
- `src/batch/unified/*` — batch ETL jobs
- `backend/migrations/` — SQL migrations

**Sơ đồ cần xây dựng:**
- Hình 4.3: Medallion Architecture (Bronze → Silver → Gold)

**Luận điểm học thuật:**
- Quality scoring (0/50/100) cho phép consumers biết data reliability
- Dynamic overwrite cho phép idempotent re-runs

**Dung lượng dự kiến:** ~90 dòng

---

### 4.5 PostgreSQL (2 trang)
**Mục tiêu:** Phân tích PostgreSQL schema.

**Nội dung cần viết:**
- Auth tables: users, sessions, user_settings, notifications
- AI tables: chat_sessions, messages, chart_snapshots, tool_actions
- RAG tables: knowledge_sources, documents, chunks, embeddings (pgvector)
- Retrieval logs: audit trail cho all RAG queries
- Migrations: 4 idempotent SQL files

**Bằng chứng từ codebase:**
- `backend/migrations/001_phase0_schema.sql` — auth + AI base
- `backend/migrations/002_phase1_readiness.sql` — profile, settings, notifications
- `backend/migrations/003_phase1_ai_rag.sql` — RAG tables + pgvector
- `backend/migrations/004_phaseC_news_enhancements.sql` — news

**Sơ đồ cần xây dựng:**
- Hình 4.4: PostgreSQL ERD (auth + AI + RAG tables)

**Dung lượng dự kiến:** ~70 dòng

---

### 4.6 ERD (1 trang)
**Mục tiêu:** Tổng hợp Entity-Relationship Diagram.

**Sơ đồ cần xây dựng:**
- Hình 4.5: Full ERD cho PostgreSQL (users ← sessions ← messages, knowledge_sources → documents → chunks → embeddings)
- Hình 4.6: Iceberg table relationships (Bronze → Silver → Gold lineage)

**Dung lượng dự kiến:** ~30 dòng (mostly diagram)

---

### 4.7 Indexing (1 trang)
**Mục tiêu:** Phân tích indexing strategy.

**Nội dung cần viết:**
- PostgreSQL: HNSW index (pgvector), B-tree (user_id, session_id), created_at DESC
- Redis: inherently indexed (hash fields, sorted set scores)
- Iceberg: partition pruning (days, interval, exchange), manifest files
- InfluxDB: tag-based indexing (symbol, exchange, interval)

**Bằng chứng từ codebase:**
- `backend/migrations/003_phase1_ai_rag.sql` — all CREATE INDEX statements
- `src/lakehouse/pipeline.py` — partition definitions

**Dung lượng dự kiến:** ~30 dòng

---

### 4.8 Query Optimization (1 trang)
**Mục tiêu:** Phân tích query optimization.

**Nội dung cần viết:**
- Redis pipeline: 6 commands trong 1 round-trip (WS optimization)
- InfluxDB: Flux query với pivot + sort + limit
- Trino: partition pruning, dynamic filtering
- PostgreSQL: connection pooling (asyncpg), prepared statements

**Bằng chứng từ codebase:**
- `backend/api/websocket.py` — Redis pipeline optimization
- `backend/services/candle_service.py` — Flux queries
- `backend/api/market_overview.py` — Trino queries

**Dung lượng dự kiến:** ~30 dòng

---

### 4.9 Transaction (0.5 trang)
**Mục tiêu:** Phân tích transaction strategy.

**Nội dung cần viết:**
- PostgreSQL: asyncpg transactions cho user registration, session creation
- Redis: pipeline cho atomic multi-key operations
- Iceberg: ACID transactions (snapshot isolation)
- Flink: exactly-once checkpoint semantics

**Dung lượng dự kiến:** ~15 dòng

---

### 4.10 Concurrency Control (0.5 trang)
**Mục tiêu:** Phân tích concurrency strategy.

**Nội dung cần viết:**
- Redis: single-threaded, atomic operations
- PostgreSQL: MVCC (Multi-Version Concurrency Control)
- Flink: keyed state per partition
- Spark: structured streaming micro-batch (sequential within batch)

**Dung lượng dự kiến:** ~15 dòng

---

## Dàn ý chi tiết — DEPLOYMENT

### 4.11 Docker (2.5 trang)
**Mục tiêu:** Phân tích containerization strategy.

**Nội dung cần viết:**
- 40 concrete services trong docker-compose.yml
- Dockerfiles: FastAPI, Producer, Flink, Spark, Nginx, etc.
- Profiles: dev (29), monitoring (+5), logging (+2), prod (38)
- Memory limits per service
- Health checks cho services accepting connections
- AI overlay: docker-compose.ai.yml (litellm, vllm)

**Bằng chứng từ codebase:**
- `docker-compose.yml` — full service definitions
- `docker/*/Dockerfile` — all Dockerfiles
- `Makefile` — convenience targets

**Sơ đồ cần xây dựng:**
- Hình 4.7: Docker Compose service dependency graph

**Luận điểm học thuật:**
- Profile-based deployment cho phép chọn minimal stack cho mỗi environment
- Memory limits prevent resource contention trong shared development

**Dung lượng dự kiến:** ~80 dòng

---

### 4.12 Kubernetes (0.5 trang)
**Trạng thái:** **Không áp dụng** — LMView dùng Docker Compose, không dùng Kubernetes.

**Nội dung cần viết:** Ghi rõ LMView sử dụng Docker Compose cho cả dev lẫn prod. K8s có thể là future work nhưng hiện tại không áp dụng. Nêu lý do: đơn giản hơn cho single-server deployment.

**Dung lượng dự kiến:** ~15 dòng

---

### 4.13 CI/CD (0.5 trang)
**Trạng thái:** **Không áp dụng** — Không có GitHub Actions, GitLab CI, hoặc CI/CD pipeline.

**Nội dung cần viết:** Ghi rõ LMView hiện không có CI/CD pipeline. Testing chạy local qua `make test`. Build manual qua `make dev-build` / `make prod-build`.

**Dung lượng dự kiến:** ~15 dòng

---

### 4.14 GitOps (0.5 trang)
**Trạng thái:** **Không áp dụng** — Không có ArgoCD, Flux, hoặc GitOps tool.

**Dung lượng dự kiến:** ~10 dòng

---

### 4.15 Development Environment (1 trang)
**Mục tiêu:** Mô tả dev environment setup.

**Nội dung cần viết:**
- Prerequisites: Docker 24+, 32GB RAM, 100GB disk
- `make dev` → 29 services, hot reload
- Nginx dev: plain HTTP port 80
- Frontend: Vite dev server (hot reload)
- Backend: uvicorn with reload

**Bằng chứng từ codebase:**
- `README.md` — Quick Start
- `Makefile` — dev target
- `docker-compose.yml` — dev profile

**Dung lượng dự kiến:** ~30 dòng

---

### 4.16 Testing Environment (1 trang)
**Mục tiêu:** Mô tả testing strategy.

**Nội dung cần viết:**
- 341 pytest test functions across 27 files
- Test categories: unit (211), integration (61), e2e (6), security (18), performance (9), AI (36)
- Frontend: typecheck + build (no test runner yet)
- 50 golden AI evaluation questions
- Coverage: `make test-cov`

**Bằng chứng từ codebase:**
- `tests/` directory structure
- `docs/SYSTEM.md` Section 14 — Testing
- `docs/ai/AI_EVALUATION.md` — evaluation framework

**Dung lượng dự kiến:** ~30 dòng

---

### 4.17 Production Environment (1.5 trang)
**Mục tiêu:** Mô tả production deployment.

**Nội dung cần viết:**
- `make prod` → 38 services (prod + monitoring + logging)
- Nginx prod: HTTPS port 443 + certbot automation
- DuckDNS integration cho dynamic DNS
- Monitoring: Prometheus + Grafana + Loki
- Nginx proxy: `/grafana/`, `/prometheus/`, `/loki/` with Basic Auth
- Resource: 8+ CPU cores, 32GB+ RAM

**Bằng chứng từ codebase:**
- `docker-compose.yml` — prod profile
- `scripts/certbot_auto.sh`, `scripts/duckdns_auto.sh` — SSL/DNS automation
- `config/nginx/` — Nginx configs
- `docs/SYSTEM.md` Section 13 — Setup and Operations

**Dung lượng dự kiến:** ~50 dòng

---

## Tổng dung lượng dự kiến Phần 4: ~20 trang (~665 dòng)

## Danh sách sơ đồ cần xây dựng
1. Hình 4.1: Polyglot persistence overview
2. Hình 4.2: Redis key families và TTL
3. Hình 4.3: Medallion Architecture (Bronze→Silver→Gold)
4. Hình 4.4: PostgreSQL ERD
5. Hình 4.5: Full ERD (PostgreSQL)
6. Hình 4.6: Iceberg table lineage
7. Hình 4.7: Docker Compose service dependency graph

## Rủi ro khi viết
1. **4 databases khác nhau** → Risk of shallow coverage → Focus vào key design decisions
2. **Iceberg schema phức tạp (9 Gold tables)** → Nhóm theo purpose, không mô tả từng column
3. **K8s/CI/CD/GitOps không có** → Ghi rõ "không áp dụng" thay vì bỏ qua
4. **PostgreSQL ERD phức tạp** → Chỉ vẽ main tables, bỏ indexes/constraints chi tiết

## Chiến lược viết tránh vượt context
- Database: mỗi database là 1 section độc lập
- Schema: table-level summary, không list every column
- Deployment: focus vào Docker Compose profiles
- Không viết SQL DDL chi tiết → reference migration files

---

# PHỤ LỤC: TỔNG HỢP

## Tổng dung lượng 4 phần

| Phần | Trang dự kiến | Lines dự kiến | Diagrams |
|------|---------------|---------------|----------|
| 1: Kiến trúc | ~22 | ~700 | 9 |
| 2: AI Agent | ~16 | ~550 | 4 |
| 3: Backend | ~17 | ~585 | 3 |
| 4: Database + Deployment | ~20 | ~665 | 7 |
| **Total** | **~75** | **~2500** | **23** |

## Tổng danh sách sơ đồ (23 hình)

### Phần 1 (9 hình)
1. Context diagram
2. Lambda Architecture 3 tầng
3. Speed path data flow
4. Batch path data flow
5. REST request sequence diagram
6. WebSocket request sequence diagram
7. Real-time latency chain
8. Multi-layer cache architecture
9. Monitoring architecture

### Phần 2 (4 hình)
10. AI pipeline flowchart
11. Ask Mode workflow (10 steps)
12. RAG pipeline (ingestion → retrieval)
13. pgvector search architecture

### Phần 3 (3 hình)
14. FastAPI architecture layers
15. API endpoint map
16. Backend database interaction

### Phần 4 (7 hình)
17. Polyglot persistence overview
18. Redis key families + TTL
19. Medallion Architecture
20. PostgreSQL ERD
21. Full ERD (PostgreSQL)
22. Iceberg table lineage
23. Docker Compose dependency graph

## File tham chiếu chính theo phần

| Phần | Files cần đọc khi viết |
|------|----------------------|
| 1: Architecture | `docs/SYSTEM.md`, `docs/final_data_flow.md` Parts 1,7, `README.md`, `docker-compose.yml` |
| 2: AI | `docs/ai/*` (6 files), `backend/services/ai/*` (10 files), `backend/api/ai/*`, `backend/migrations/003_phase1_ai_rag.sql`, `tests/ai/` |
| 3: Backend | `backend/app.py`, `backend/api/*.py` (17), `backend/services/*.py` (20+), `backend/core/*.py` (8), `backend/models/*.py` (12) |
| 4: Database+Deploy | `backend/migrations/*.sql` (4), `src/lakehouse/pipeline.py`, `src/batch/unified/*`, `docker-compose.yml`, `Makefile`, `docker/*/Dockerfile` |

## Các mục ghi "không áp dụng"

| Mục | Lý do |
|-----|-------|
| MCP (Phần 2.6) | LMView dùng custom RAG pipeline, không dùng MCP |
| Multi-step Reasoning (Phần 2.9) | Phase 1 chỉ single-step, Phase 2 planned |
| Repository Layer (Phần 3.9) | Không có separate repository, DB access trong services |
| Kubernetes (Phần 4.12) | Docker Compose only |
| CI/CD (Phần 4.13) | No CI/CD pipeline |
| GitOps (Phần 4.14) | No GitOps tool |

## Chiến lược tổng thể tránh vượt context

1. **Viết từng section độc lập**: Mỗi section trong kế hoạch này có thể sinh nội dung riêng mà không cần context từ sections khác
2. **Không viết prose liên tục**: Bullet points → prose conversion ở bước cuối
3. **Reuse diagrams**: Sử dụng lại sơ đồ từ `docs/final_data_flow.md` và `docs/ai/AI_ARCHITECTURE.md`
4. **Reference thay vì duplicate**: "Xem chi tiết tại `docs/final_data_flow.md` Phần X" thay vì lặp lại nội dung
5. **Maximum section size**: Mỗi section ≤ 100 dòng prose để fit trong context window
6. **Priority order**: Viết Phần 1 (architecture) trước → cung cấp foundation cho các phần sau

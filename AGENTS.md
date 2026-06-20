# AGENTS.md - LMView

Project rules for AI coding agents.

---

## Project Snapshot

- **Name:** LMView
- **Purpose:** Real-time cryptocurrency technical-analysis platform
- **Architecture:** Lambda Architecture: speed, batch/lakehouse, serving, frontend
- **Core stack:** Kafka, Flink, Spark, Redis Sentinel, InfluxDB, PostgreSQL, Iceberg/MinIO, Trino, FastAPI, React 19
- **Current release:** `0.25.41` in `docs/CHANGELOG.md`
- **Deployment:** 2-node Docker Swarm on AWS EC2 (core: 8/32, worker: 4/16, EFS shared)
- **Current focus:** Production stability, Docker Swarm migration;

---

## Session Startup

Every session starts with:

1. Use `caveman` skill/plugin for agents to cut down output token usage if available.
2. Read `docs/SYSTEM.md` (high-level) and `docs/system/README.md` (per-module index).
3. Read latest `docs/CHANGELOG.md` entries, at least 3.
4. Check `git status --short --branch`.
5. Identify affected modules from `docs/system/*.md` and planned files.
6. For explicit, low-risk requests, proceed after stating intent. Ask first for broad, destructive, ambiguous, or cross-system changes.

Before editing, run `git pull --ff-only` when safe. If worktree is dirty, do not overwrite user changes.

---

## Collaboration Rules

- Do not commit, stage, or push unless explicitly asked.
- Do not touch `.env` or print secrets.
- Update `docs/CHANGELOG.md` for completed feature/fix/refactor/docs work unless user explicitly exempts the session. Resolve version conflicts when 2 users commit their stack of changes by reordering entries on how early they were made and correcting the version number based on the new order.
- Update `README.md` and `docs/SYSTEM.md` when crucial changes were made to the project. Recheck their information every major version update. Only update this file (`AGENTS.md`) if needed.
- Keep batches small: 1-3 files when practical, then verify.
- Prefer repo patterns over new abstractions.
- Never revert changes you did not make.
- Ask before destructive actions: volume deletion, checkpoint deletion, data deletion, `git reset`, schema migration, account/session purge.

---

## Protected Areas

Only touch these when explicitly requested:

- `.env`
- `docker-compose.yml`
- `schemas/*.avsc`
- `backend/migrations/*.sql`
- Flink checkpoints
- Kafka/Redis/InfluxDB/MinIO/PostgreSQL persisted data

Schema changes require producer, Flink, Spark, backend, frontend types where relevant, and tests to change together.

---

## Python Rules

Applies to `backend/`, `src/`, `orchestration/`, `tests/`.

- Use Python 3.11-compatible syntax for backend/producer/backfill code.
- Do not force Python 3.12+ features; Spark/Flink containers must be validated separately.
- Use 4-space indentation, type hints on public functions, and Google-style docstrings for public classes/functions.
- Imports: stdlib, third-party, local.
- Use absolute imports.
- Raise specific exceptions. No bare `except:`.
- Use `Optional[X]` in Pydantic-facing models unless codebase migrates fully.
- Centralize constants in `backend/core/constants.py` or `src/common/config.py`.

Backend architecture:

- `backend/api/`: thin route handlers only.
- `backend/services/`: business logic.
- `backend/models/`: Pydantic schemas.
- `backend/core/`: config, constants, DB clients, Redis Sentinel, auth dependencies.
- Route handlers must not embed Redis/Influx/Trino/PostgreSQL-heavy business logic when service layer is appropriate.
- Auth/settings/admin/AI persistence uses PostgreSQL through `backend/core/postgres.py`; never log credentials or session tokens.
- Ordered SQL migrations run at startup only when `RUN_MIGRATIONS` is true.

Data pipeline architecture:

- New exchanges extend `src/exchanges/base.py`.
- Kafka records must preserve `exchange`, `symbol`, and event timestamps.
- PyFlink writer classes should read worker-specific environment values in `open()` where serialization requires it.
- Preserve candle dedup: remove old sorted-set score before `ZADD`.
- For multi-exchange work, key Flink state, Redis keys, Influx tags, Iceberg DDLs, and API lookups by `(exchange, symbol)`.
- Current caveat: Flink kline aggregation preserves `exchange`, but depth processing still drops/defaults `exchange`; lakehouse ticker dedup also omits `exchange`.
- OKX remains opt-in (`ENABLE_OKX=false` by default); OKX kline Kafka records still need interval normalization before production use.

---

## TypeScript Rules

Applies to `frontend/`.

- React 19 functional components and hooks.
- TypeScript strict mode.
- Components: PascalCase `.tsx`.
- Services/utils: camelCase `.ts`.
- Shared types live in `frontend/src/types/index.ts`.
- Global TypeScript declarations live in `frontend/src/@types/`.
- Shared shell components live in `frontend/src/components/layout/`.
- Shared reusable UI/providers live in `frontend/src/components/ui/`.
- Feature-specific UI lives in `frontend/src/features/<feature>/`.
- Route-level screens live in `frontend/src/pages/`.
- Static/mock data and mock API adapters live in `frontend/src/data/`, especially `frontend/src/data/mock/`.
- Env, timeframe, and market constants live in `frontend/src/constants/`.
- User-facing strings use `useI18n()`.
- Normal-user UI must not expose internal/development labels such as data source, API mode, mock mode, migration phase names, schema phase names, or debug diagnostics. Keep those behind admin-only Debug surfaces.
- API calls belong in `frontend/src/services/*`, not components.
- Use `useApiCall` for fetch flows that need retry/toast/error states.
- Use `useSymbolMeta` for logos/names.
- Auth, settings, notifications, admin, and AI calls must go through their service files.
- Convert backend milliseconds to lightweight-charts seconds at service boundary.
- UI may show `1H`, `4H`, `1D`, `1W`; API interval params must be lowercase.
- `VITE_DATA_SOURCE=mock` uses API-shaped adapters under `frontend/src/data/mock/`; default is API mode.

Frontend verification:

```bash
cd frontend
npm run typecheck
npm run build
```

---

## Docker and Infrastructure Rules

- `docker-compose.yml` is the runtime source of truth, combined with `docker-compose.swarm.yml` for Swarm deployments.
- Every concrete service needs a `profiles` key.
- Template/extension services may use `profiles: ["dont-start"]`.
- Core services use `dev` and/or `prod`.
- Monitoring/logging services stay opt-in.
- Services that accept connections need health checks (currently: producer, flink-jobmanager, flink-taskmanager, spark-worker, schema-registry are MISSING health checks).
- Services need memory limits where Compose supports them.
- Service names use kebab-case.
- Dev Nginx serves plain HTTP on port 80. Production Nginx uses ports 80 and 443 with certbot automation.
- Images are pushed to local registry (`registry:2`, port 5000) and deployed with `--resolve-image never`.
- **Deploy command**: `docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice`

Validate Compose changes with:

```bash
docker compose --profile dev config
docker compose --profile prod --profile monitoring --profile logging config
```

---

## Testing Rules

Python:

```bash
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v
make test
make test-all
make test-cov
```

If local host has no `python` shim, use `python3` or the project virtualenv explicitly.

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

New backend behavior needs unit tests. Endpoint behavior should include integration tests when practical. Data-pipeline changes need focused tests for mapping, dedup, aggregation, or serialization.

---

## Known Hot Spots

Read `docs/system/13-caveats.md` for full bug inventory before changing these:

### Backend hot spots
- `backend/app.py`
- `backend/api/klines.py`
- `backend/services/candle_service.py`
- `backend/api/websocket.py`
- `backend/api/ticker.py`
- `backend/api/orderbook.py`
- `backend/api/trades.py`
- `backend/api/auth.py`
- `backend/api/ai/*`
- `backend/api/ai_legacy.py`
- `backend/api/settings.py`
- `backend/api/admin.py`
- `backend/core/postgres.py`
- `backend/core/security.py`
- `backend/migrations/*.sql`
- `backend/services/ai/*`
- `backend/services/candle_service.py`
- `backend/services/scope_gate_service.py`

### Data pipeline hot spots
- `src/processing/pipeline.py`
- `src/processing/writers/kline_aggregator.py`
- `src/processing/writers/keydb_depth.py` (drops exchange)
- `src/processing/writers/keydb_kline.py`
- `src/producer/main.py`
- `src/exchanges/binance/client.py` (symbol selection)
- `src/exchanges/binance/redis_writer.py`
- `src/exchanges/base.py`
- `src/lakehouse/pipeline.py` (dedup omits exchange)
- `orchestration/assets.py` (catalog mismatch)

### Scripts hot spots
- `scripts/deploy_aws_swarm.sh` (CUSTOM_IMAGES, port sed, no rollback)
- `scripts/auto_submit_jobs.sh` (deps.zip duplicate, Spark URL)
- `scripts/job_watchdog.py` (0/1 replicas)
- `scripts/submit_flink.sh` (duplicate of auto_submit_jobs.sh)
- `scripts/audit_data_coverage.py` (useful but not integrated)
- `scripts/docker-reclaim.sh` (WSL-only, stale)

### Frontend hot spots
- `frontend/src/features/chart/CandlestickChart.tsx`
- `frontend/src/features/ai/AiAssistantPanel.tsx`
- `frontend/src/features/settings/SettingsModal.tsx`
- `frontend/src/services/marketDataService.ts`
- `frontend/src/services/authService.ts`
- `frontend/src/services/aiService.ts`
- `frontend/src/services/settingsService.ts`

Current caveats (detailed bug inventory: `docs/system/13-caveats.md`):

- Backend has one all-timeframe WebSocket route; 50ms poll loop sends all 8 timeframes (large payload). No heartbeat/ping — browser may drop idle connections.
- Ticker API is exchange-aware and can aggregate exchanges, but uses simple mid-price average (not volume-weighted).
- Order book API reads exchange-qualified Redis keys and has ticker/REST fallback metadata.
- Trades API reads true `trade:latest:{exchange}:{symbol}` cache first, then ticker-derived fallback; summary route still reports ticker-derived metadata.
- OKX producer path exists and has unit coverage, disabled by default (`ENABLE_OKX=false`). Kline interval mapping **fixed** in v0.25.41.
- Flink kline aggregation preserves `exchange`; depth processing still drops/defaults `exchange` (keydb_depth.py).
- Spark streaming `coin_*` Iceberg DDLs include `exchange`; ticker streaming dedup still omits `exchange` (lakehouse/pipeline.py).
- `/api/market/overview` tries Trino gold tables, then derives from Redis ticker cache; heatmap helper has stale `iceberg_catalog.gold` join.
- Dagster exposes `defs = Definitions(...)`, but its Spark catalog (`s3a://lakehouse/warehouse`) differs from pipeline's JDBC catalog (`s3://cryptoprice/iceberg`).
- Frontend hook specs exist but no test runner configured.
- **scripts/**: `auto_submit_jobs.sh` and `submit_flink.sh` have duplicated deps.zip build logic. `job_watchdog.py` at 0/1 replicas — Flink job failures require manual re-submit.
- **Deploy**: `deploy_aws_swarm.sh` CUSTOM_IMAGES includes kafka (not built by compose). No rollback on deploy failure.
- **Migration**: `004_agents_metadata.sql` and `004_phaseC_news_enhancements.sql` both use 004 prefix — potential ordering issue.

---

## AI Feature Guidance

Current Phase 1 exists:

- Authenticated AI API routes are modular under `backend/api/ai/`.
- Chat sessions, messages, chart snapshots, action metadata, knowledge chunks/embeddings, and retrieval logs persist in PostgreSQL.
- Scope gate, prompt builder, provider router, RAG retrieval, output guard, and chart-action validator are wired.
- Mock provider remains default/fallback; real provider path needs `AI_ENABLE_REAL_LLM=true`, non-mock `AI_MODE`, provider keys/config, and runtime dependencies.
- `litellm` and `sentence-transformers` are in `docker/fastapi/requirements.txt` and installed in the image. At runtime, they may be pip-installed again if the container uses a different code version (see `backend/app.py` lifespan).
- `docker-compose.ai.yml` starts optional LiteLLM/vLLM support, but `ai-service` is scaffolded and exits after an echo command.
- Frontend AI Helper calls backend Ask Mode in API mode and uses local/mock fallback when needed.

For future AI/ML work:

- Define data contracts first: input window, horizon, target, latency, freshness.
- Store training data and labels in Iceberg, not only Redis.
- Keep online features reproducible from offline feature logic.
- Version model artifacts and model outputs.
- Add model observability: freshness, latency, null rate, drift, model version.
- Keep inference boundaries explicit: backend service for API logic, separate `src/ml` or service module for training/inference.
- Do not mix experimental model code into core candle serving without feature flags.
- Never let AI action execution bypass validation, user approval, or audit recording.

---

## Reference Files

| File | Purpose |
|---|---|
| `docs/SYSTEM.md` | Full current system map and caveats |
| `docs/system/*.md` | Per-module detailed documentation |
| `docs/CHANGELOG.md` | Project history |
| `AGENTS.md` | This file |
| `README.md` | User-facing overview |
| `VERSION` | Single source of truth for version number |
| `docker-compose.yml` | Runtime service graph |
| `docker-compose.swarm.yml` | Docker Swarm overlay config |
| `.env.example` | Env template |
| `Makefile` | Common commands |
| `schemas/*.avsc` | Kafka contracts |

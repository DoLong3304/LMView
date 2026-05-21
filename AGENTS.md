---
trigger: always_on
---

# AGENTS.md - LMView

Project rules for AI coding agents.

---

## Project Snapshot

- **Name:** LMView
- **Purpose:** Real-time cryptocurrency technical-analysis platform
- **Architecture:** Lambda Architecture: speed, batch/lakehouse, serving
- **Core stack:** Kafka, Flink, Spark, Redis Sentinel, InfluxDB, Iceberg/MinIO, Trino, FastAPI, React 19
- **Primary focus:** Data engineering now; AI/ML feature path later

---

## Session Startup

Every session starts with:

1. Read `docs/SYSTEM.md`.
2. Read the latest entries in `docs/CHANGELOG.md` (at least 3).
3. Check `git status --short --branch`.
4. Identify affected modules and planned files.
5. For explicit, low-risk user requests, proceed after stating intent. Ask first for broad, destructive, ambiguous, or cross-system changes.

Before editing, run `git pull --ff-only` when safe. If the worktree is dirty, do not overwrite user changes.

---

## Collaboration Rules

- Do not commit, stage, or push unless explicitly asked.
- Do not touch `.env` or print secrets.
- Update `docs/CHANGELOG.md` for completed feature/fix/refactor work unless the user explicitly exempts the session.
- Keep batches small: 1-3 files when practical, then verify.
- Prefer repo patterns over new abstractions.
- Never revert changes you did not make.
- Ask before destructive actions: volume deletion, checkpoint deletion, data deletion, `git reset`, schema migration.

---

## Protected Areas

Only touch these when explicitly requested:

- `.env`
- `docker-compose.yml`
- `schemas/*.avsc`
- Flink checkpoints
- Kafka/Redis/InfluxDB/MinIO persisted data

Schema changes require producer, Flink, Spark, backend, and tests to change together.

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
- `backend/core/`: config, constants, DB clients, Redis Sentinel.
- Route handlers must not embed Redis/Influx/Trino-heavy business logic when a service layer is appropriate.

Data pipeline architecture:

- New exchanges extend `src/exchanges/base.py`.
- Kafka records must preserve `exchange`, `symbol`, and event timestamps.
- PyFlink writer classes must read environment values in `open()` where serialization requires it.
- Preserve candle dedup: `ZREMRANGEBYSCORE` before `ZADD`.
- For multi-exchange work, key Flink state and Redis keys by `(exchange, symbol)`.

---

## TypeScript Rules

Applies to `frontend/`.

- React 19 functional components and hooks.
- TypeScript strict mode.
- Components: PascalCase `.tsx`.
- Services/utils: camelCase `.ts`.
- Shared types live in `frontend/src/types/index.ts`.
- User-facing strings use `useI18n()`.
- API calls belong in `frontend/src/services/*`, not components.
- Use `useApiCall` for fetch flows that need retry/toast/error states.
- Use `useSymbolMeta` for logos/names.
- Convert backend milliseconds to lightweight-charts seconds at service boundary.
- UI may show `1H`, `4H`, `1D`, `1W`; API interval params must be lowercase.
- `VITE_DATA_SOURCE=mock` uses `frontend/src/mock/mockDataGenerator.ts`; default is API mode.

Frontend verification:

```bash
cd frontend
npm run typecheck
npm run build
```

---

## Docker and Infrastructure Rules

- `docker-compose.yml` is the runtime source of truth.
- Every concrete service needs a `profiles` key.
- Template/extension services may use `profiles: ["dont-start"]`.
- Core services use `dev` and/or `prod`.
- Monitoring/logging services stay opt-in.
- Services that accept connections need health checks.
- Services need memory limits where Compose supports them.
- Service names use kebab-case.

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

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

New backend behavior needs unit tests. Endpoint behavior should include integration tests when practical. Data-pipeline changes need focused tests for mapping, dedup, aggregation, or serialization.

---

## Known Hot Spots

Read `docs/SYSTEM.md` before changing these:

- `backend/api/klines.py`
- `backend/services/candle_service.py`
- `backend/api/websocket.py`
- `src/processing/pipeline.py`
- `src/processing/writers/kline_aggregator.py`
- `src/processing/writers/keydb_*`
- `src/producer/main.py`
- `src/exchanges/*`
- `src/lakehouse/pipeline.py`
- `frontend/src/components/CandlestickChart.tsx`
- `frontend/src/services/marketDataService.ts`

Current caveats to keep in mind:

- Backend exposes `/api/stream/all`; older single-stream helper paths may be stale.
- Ticker API is exchange-aware, but order book/trade API hot paths still need exchange-qualified key alignment.
- OKX support exists but should be treated as experimental until WebSocket subscription flow is verified.
- `/api/market/overview` currently returns placeholder/default data; heatmap/rankings query Trino helpers.

---

## AI Feature Guidance

For future AI/ML work:

- Define data contracts first: input window, horizon, target, latency, freshness.
- Store training data and labels in Iceberg, not only Redis.
- Keep online features reproducible from offline feature logic.
- Version model artifacts and model outputs.
- Add model observability: freshness, latency, null rate, drift, model version.
- Keep inference boundaries explicit: backend service for API logic, separate `src/ml` or service module for training/inference when added.
- Do not mix experimental model code into core candle serving without feature flags.

---

## Reference Files

| File | Purpose |
|---|---|
| `docs/SYSTEM.md` | Full system map and caveats |
| `docs/CHANGELOG.md` | Project history |
| `AGENTS.md` | This file |
| `README.md` | User-facing overview |
| `docker-compose.yml` | Runtime service graph |
| `.env.example` | Env template |
| `Makefile` | Common commands |
| `schemas/*.avsc` | Kafka contracts |

# AI Roadmap — LMView

## Current State: Phase 1 ✅

### Implemented
- Real LLM inference via provider-agnostic routing
- RAG knowledge base with pgvector
- Ask Mode with chart context awareness
- Provider fallback chain (local vLLM → online APIs → mock)
- Financial safety output guard
- Bilingual support (EN/VI)
- 50 golden evaluation questions
- Phase 0 mock mode preserved

## Phase 2: Interact Mode (Planned)

### Goals
- AI-proposed chart actions with user approval flow
- Deterministic frontend chart action dispatcher
- Action execution audit trail
- LangGraph agent orchestration

### Scaffolded
- `ai_service/app/graph/` — LangGraph state and builder
- `ai_service/app/agents/` — Agent role definitions
- `ai_service/app/tools/` — Tool registry
- `backend/models/ai/chart_actions.py` — Action contracts

## Phase 3: News & Sentiment (Planned)

### Goals
- PostgreSQL news persistence
- FinBERT or financial sentiment service
- Vietnamese sentiment/glossary expansion
- News-enriched AI responses

### Scaffolded
- `src/ml/sentiment/` — Sentiment model directory

## Phase 4: Trade & Liquidity Analysis (Planned)

### Goals
- True hot trade cache from `crypto_trades`
- Liquidity/trade-flow analysis
- Real-time trade tape integration
- Order flow analysis in AI responses

## Phase 5: Forecasting (Planned)

### Goals
- TimesFM/Chronos/PatchTST time-series models
- Forecast bands for educational display
- No guaranteed price predictions
- Model versioning and observability

### Scaffolded
- `src/ml/forecasting/` — Forecasting model directory

## Non-Goals (By Design)

These will never be implemented:
- Auto-trading or direct order execution
- Guaranteed price predictions
- Raw SQL/JS/shell execution
- Browser automation
- API-key rotation to bypass quotas
- Bypassing user approval for chart actions

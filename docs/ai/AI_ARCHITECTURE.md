# AI Architecture — LMView Phase 1

## Overview

LMView implements a grounded bilingual AI technical-analysis companion that combines authenticated sessions, live chart context, curated RAG knowledge, provider-agnostic LLM inference, and risk-aware outputs for educational cryptocurrency market analysis.

## Architecture Diagram

```
Frontend AI Helper
  → POST /api/ai/chat (Core FastAPI)
  → Auth + Session ownership
  → Deterministic scope gate
  → Chart context assembly + data caveats
  → RAG knowledge retrieval (pgvector)
  → Prompt builder (system + context + RAG + history + user message)
  → Provider router (local vLLM → online API → mock fallback)
  → LLM completion
  → Output guard (financial safety + disclaimer)
  → Store assistant message + metadata
  → Return AIChatResponse to frontend
```

## Key Contracts

### Provider Interface
All providers implement `BaseProvider`:
- `generate_chat_completion(LLMCompletionRequest) → LLMCompletionResponse`
- `health_check() → ProviderHealthStatus`
- `get_info() → ProviderInfo`

The system does not care whether the underlying model is local vLLM, online API, or deterministic mock.

### Provider Priority Chain
```
Local-first mode:  local_vllm → qwen_api → llama_api → openai → gemini → deepseek → litellm_proxy → mock
API-test mode:     qwen_api → llama_api → local_vllm → openai → gemini → deepseek → litellm_proxy → mock
Mock mode:         mock only
```

### RAG Pipeline
```
Knowledge Markdown → Heading-aware chunking → Sentence-transformers embedding → pgvector storage
User query → Query embedding → Cosine similarity search → Top-K chunks → Prompt enrichment
```

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Provider Router | `backend/services/ai/provider_router.py` | Selects best available LLM provider |
| Base Provider | `backend/services/ai/base_provider.py` | Abstract provider interface |
| Mock Provider | `backend/services/ai/mock_provider.py` | Deterministic Phase 0 fallback |
| LiteLLM Provider | `backend/services/ai/litellm_provider.py` | Unified API provider client |
| Prompt Builder | `backend/services/ai/prompt_builder.py` | Constructs structured prompts |
| Output Guard | `backend/services/ai/output_guard.py` | Financial safety validation |
| Context Service | `backend/services/ai/context_service.py` | Data caveat generation |
| Knowledge Service | `backend/services/ai/knowledge_service.py` | Document ingestion + chunking |
| Retrieval Service | `backend/services/ai/retrieval_service.py` | pgvector similarity search |
| Chat Endpoint | `backend/api/ai/chat.py` | Ask Mode API route |
| Knowledge Endpoints | `backend/api/ai/knowledge.py` | Ingest, search, health |

## Safety Layers

1. **Scope gate** — Blocks out-of-scope requests before RAG/model calls
2. **Prompt builder** — Financial safety rules baked into system prompt
3. **Output guard** — Post-generation validation (flags unsafe claims, removes code, ensures disclaimer)
4. **Chart action validator** — Validates proposed actions against whitelist

## Data Caveats

The AI explicitly states when:
- Market overview is placeholder data
- Trades are ticker-derived, not true trade tape
- Order book is stale/fallback/synthetic
- News context is unavailable or in-memory only
- Indicator data is missing or stale
- OKX exchange data is experimental

## What Is NOT Implemented (Future Phases)

| Feature | Phase | Status |
|---------|-------|--------|
| Interact Mode action execution | Phase 2 | Scaffolded |
| LangGraph agent orchestration | Phase 2 | Scaffolded |
| FinBERT sentiment service | Phase 3 | Scaffolded |
| True hot trade cache | Phase 4 | Scaffolded |
| Time-series forecasting | Phase 5 | Scaffolded |
| Autonomous chart action execution | Phase 2 | Not started |
| Auto-trading | Never | Blocked by design |

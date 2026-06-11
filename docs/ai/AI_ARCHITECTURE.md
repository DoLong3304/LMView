# AI Architecture - LMView 0.24

## Overview

LMView AI is now owned by the importable `ai_service/` package. Backend route modules under `backend/api/ai/*` remain authenticated FastAPI adapters and should not carry production AI logic.

Ask and Interact share one orchestration path:

```text
Frontend AI Panel
-> POST /api/ai/chat
-> auth + user/session ownership
-> ai_service.core.orchestrator
-> scope gate
-> chart/runtime context + temporal sanity notes
-> approved-only RAG retrieval
-> prompt builder
-> provider router: local -> api -> none
-> output guard
-> tool/action proposal
-> persistence + audit metadata
-> AIChatResponse
```

## Package Ownership

| Area | Location | Purpose |
|---|---|---|
| Orchestration | `ai_service/core/orchestrator.py` | Shared Ask/Interact flow |
| Providers | `ai_service/providers/` | `local`, `api`, `none`, and `auto` routing |
| RAG | `ai_service/rag/` | Registry validation, ingestion gates, retrieval, embeddings |
| Actions | `ai_service/actions/` | Function schemas, validation, and chart-action compatibility |
| Prompt/context | `ai_service/prompts/`, `ai_service/context/` | Prompt assembly, live data caveats, temporal grounding |
| Safety | `ai_service/safety/` | Scope gate and output guard |
| Persistence | `ai_service/persistence/` | Chat/session/message helpers |
| API adapters | `backend/api/ai/*` | Authenticated REST endpoints only |

Compatibility wrappers remain under `backend/services/*` for older imports, but new AI logic should be added to `ai_service/`.

## Providers

Public provider choices are:

```text
auto  = local -> api -> none
local = local -> none
api   = api -> none
none  = none
```

`none` is a real production fallback that returns generic LMView/system guidance when no model is usable. Backend production mock fallback has been removed; frontend mock mode remains the mock-data path.

Default API config uses DashScope International OpenAI-compatible `openai/qwen3.5-plus` at `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`. `DASHSCOPE_API_KEY` is primary and `QWEN_API_KEY` is a legacy alias.

## Temporal Grounding

Every shared prompt includes:

- current server UTC time;
- current epoch milliseconds;
- chart timestamp conversion notes;
- data freshness notes;
- instruction that runtime market data can be newer than the model training cutoff.

The output guard and prompt rules prevent the model from rejecting live chart context as impossible only because timestamps are after its training cutoff.

## RAG

Production retrieval requires:

```sql
s.review_status = 'approved'
AND s.allowed_for_rag = TRUE
```

Current bundled AI-generated notes are `pending` and excluded. See `docs/ai/RAG_KNOWLEDGE_BASE.md` for the approval workflow and source-quality policy.

## Actions And Interact Mode

The backend exposes `/api/ai/actions/catalog` and `/api/ai/chart-actions/validate`. The frontend action runtime generates indicator and drawing function definitions from existing chart/drawing registries, then uses the same action template for:

- indicator toggles;
- drawing tool selection;
- page highlights;
- site tours;
- annotation clearing;
- admin debug action testing.

Action execution still stays client-side and validated; AI suggestions do not bypass approval or audit paths.

## Safety Layers

1. Scope gate blocks out-of-scope and prompt-injection attempts before provider calls.
2. Prompt builder adds financial safety, live data freshness, and temporal sanity instructions.
3. RAG retrieval only uses approved sources.
4. Output guard removes unsafe code and adds disclaimers.
5. Action validator enforces a whitelist and parameter schema.

## Not Implemented

| Feature | Status |
|---|---|
| Autonomous trading | Blocked by design |
| Unreviewed KB use in production RAG | Blocked |
| Backend production mock provider | Removed |
| Model-specific business rules outside provider layer | Avoided |

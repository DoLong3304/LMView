# AI Service — ai_service/

AI Ask Mode (Phase 1) — modular AI assistant running inside FastAPI container.

## Architecture

```
User Query → Scope Gate → Intent Router → Context Builder → Provider Router → LLM → Output Guard → Action Validator → Response
                                   ↓
                              RAG Retrieval ← Knowledge Service
                                   ↓
                              Prompt Builder
```

## Structure

```
ai_service/
├── config.py              Settings from env/files, feature flags
├── configs/               YAML configs (ai.api.yaml, ai.local.yaml, litellm.yaml)
├── core/
│   └── orchestrator.py    Main entry point: orchestrates AI query flow
├── providers/
│   ├── router.py           Routes to active provider (auto/local/api/none)
│   ├── litellm_provider.py LiteLLM wrapper (OpenAI, Anthropic, local vLLM)
│   ├── none_provider.py    Stub provider (always returns "not available")
│   ├── base.py             Abstract provider base
│   └── health.py           Provider health check
├── agents/
│   ├── graph.py             LangGraph multi-agent DAG (optional)
│   ├── intent_router.py     Classifies query intent (ask vs interact)
│   ├── synthesis.py         Synthesizes multi-expert responses
│   ├── state.py             Agent state management
│   ├── persistence.py       Agent execution persistence
│   ├── reflection.py        Self-reflection / improvement loop
│   ├── types.py             Type definitions
│   ├── base_expert.py       Base expert class
│   └── experts/
│       ├── chart_interaction.py  Chart manipulation expert
│       ├── general.py            General market knowledge
│       ├── market_data.py        Market data retrieval expert
│       ├── news_sentiment.py     News/sentiment expert
│       ├── rag_knowledge.py      RAG knowledge expert
│       └── technical_analysis.py TA expert
├── context/
│   ├── context_service.py  Chart/market context assembler
│   └── news_context.py     News context assembler
├── persistence/
│   └── chat_store.py       Chat session/message persistence (PostgreSQL)
├── prompts/
│   └── prompt_builder.py   Prompt template builder
├── rag/
│   ├── knowledge_service.py Knowledge base ingestion/management
│   ├── retrieval_service.py  Embedding search + pgvector HNSW
│   └── registry.py           Knowledge doc registry
├── safety/
│   ├── scope_gate.py        Query scope validation (crypto only)
│   └── output_guard.py      Response safety guard
├── actions/
│   ├── executor.py          Action execution (chart, trades, etc.)
│   ├── registry.py          Action type registry
│   ├── validator.py         Action parameter validation
│   ├── undo.py              Action undo support
│   └── tool_definitions.py  Tool/function definitions for LLM
└── nlp/
    ├── entity_extractor.py  Symbol/entity extraction
    ├── finbert.py           FinBERT sentiment analysis
    ├── news_processor.py    News article processing
    └── types.py             NLP type definitions
```

## Provider Routing

| Mode | Description | Requirements |
|---|---|---|
| `none` | Stub — always returns "not available" | None (default) |
| `mock` | Simulated AI responses | None |
| `local` | LiteLLM + local vLLM/Ollama | LiteLLM running, `AI_ENABLE_REAL_LLM=true` |
| `api` | LiteLLM → OpenAI/Anthropic/etc | API keys, LiteLLM running |

- Default: `mock` provider (works without litellm/sentence-transformers)
- Real LLM requires: `AI_ENABLE_REAL_LLM=true` + provider config + API keys
- `AI_MODE` env var selects provider: `mock`, `none`, `local`, `api`

## RAG System

- **Embeddings**: sentence-transformers (pgvector HNSW index)
- **Knowledge base**: PostgreSQL `knowledge_chunks` table with vector embeddings
- **Retrieval**: Cosine similarity search, top-K chunks
- **Scope**: Approved-only knowledge docs in `docs/ai/knowledge_base/approved/`
- **Fallback**: If sentence-transformers not installed → no embeddings, mock retrieval

## Key Data Flow

1. `POST /api/ai/chat` → backend → `orchestrator.process_query()`
2. Scope gate validates query is crypto-related
3. Intent router classifies as "ask" (info) or "interact" (action)
4. Context builder gathers chart data, market data, news
5. RAG retrieval searches knowledge base
6. Prompt builder assembles context + query + instructions
7. Provider router selects LLM or mock
8. Output guard validates response safety
9. Action validator checks for chart actions
10. Response returned to user

## Known Issues

- `litellm` and `sentence-transformers` not in base FastAPI requirements (pip install at runtime)
- Without these deps: providers degrade to mock, RAG returns no embeddings
- `ai-service` in docker-compose.ai.yml is scaffolded (echo command only)
- `docker-compose.ai.yml` starts LiteLLM/vLLM optional services
- Multi-agent LangGraph DAG is scaffolded but not the primary path
- Interact Mode (action execution) is Phase 2 — validation exists, execution is limited

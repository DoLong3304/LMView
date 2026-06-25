# AI Service — ai_service/

The `ai_service` module powers LMView's AI Ask & Interact Modes. It operates
as a modular, multi-agent AI assistant driven by a **LangGraph DAG**.

**Architecture (v0.28.0+):**
- **Standalone container**: `ai_service` runs in its own container
  (`cryptoprice_ai-service`, port 8100), NOT inside the FastAPI container.
- **HTTP proxy mode**: Backend FastAPI proxies AI requests to `ai-service`
  via HTTP (`AI_SERVICE_EMBEDDED=false`, default since v0.28.0).
- **Embedded fallback**: For legacy/local setups, flip
  `AI_SERVICE_EMBEDDED=true` to import `ai_service` directly in the backend
  process.
- **Heavy ML isolation**: `sentence-transformers` (torch), `langgraph`, and
  `litellm` are only installed in the `docker/ai-service` image, keeping
  the backend image slim (~500 MB vs ~3 GB).

See `docker/ai-service/Dockerfile` and `backend/services/ai/ai_proxy.py`.

---

## 1. Core Architecture (LangGraph DAG)

The AI orchestration has migrated away from a linear pipeline to a robust **Multi-Agent Directed Acyclic Graph (DAG)**. This allows for parallel execution of domain experts, ensemble voting, and self-reflective revision loops.

```
User Query 
   ↓
Scope Gate & Knowledge Boundary (Safety Checks)
   ↓
Intent Router (Classifies intent and activates specific experts)
   ↓
Expert Execution (Parallel MoE - Mixture of Experts)
   ├── Technical Analysis Expert
   ├── Market Data Expert
   ├── News & Sentiment Expert
   ├── RAG Knowledge Expert
   ├── Chart Interaction Expert
   └── General Market Expert
   ↓
Ensemble Voting (Cross-validates signals & resolves conflicts)
   ↓
Synthesis (Combines outputs into a coherent LLM response) ↔ Reflection (Validates safety & actions; triggers revision if needed)
   ↓
Output & Action Execution
```

---

## 2. Directory Structure & Key Modules

```text
ai_service/
├── actions/         # Chart action registry, execution, undo, and tool schemas
├── agents/          # LangGraph implementation, state management, and experts
├── config.py        # Settings, feature flags, provider configs
├── configs/         # YAML configs (ai.api.yaml, ai.local.yaml, litellm.yaml)
├── context/         # TA pattern detection, support/resistance, market caveats
├── core/            # Main orchestrator (`orchestrator.py`)
├── nlp/             # FinBERT sentiment analysis, entity extraction, news processing
├── persistence/     # PostgreSQL chat store, execution trace persistence
├── prompts/         # Dynamic prompt building
├── providers/       # LLM provider routing (LiteLLM, mock, none)
├── rag/             # Vector retrieval, pgvector HNSW, knowledge management
└── safety/          # Scope gate, output guard, knowledge boundary checks
```

---

## 3. Multi-Agent Expert System (`agents/experts/`)

The system uses a Mixture of Experts (MoE) pattern. The `Intent Router` determines which experts to activate based on the user's query, saving compute and improving accuracy.

- **Technical Analysis (TA) Expert:** Analyzes chart context, indicators, patterns, and support/resistance levels.
- **Market Data Expert:** Fetches and interprets historical prices, order book data, and recent trades.
- **News & Sentiment Expert:** Leverages `nlp/finbert.py` to analyze sentiment from recent news and social feeds.
- **RAG Knowledge Expert:** Queries the vector database for LMView platform documentation and domain knowledge.
- **Chart Interaction Expert:** Determines if the user wants to manipulate the UI (e.g., add indicators, change timeframe) and issues tool calls.
- **General Market Expert:** Handles general cryptocurrency questions that don't require specific chart data.
- **Tour Planner:** A specialized module that plans user-paced, guided visual tours of the LMView platform.

---

## 4. NLP & Context Subsystems (`nlp/` & `context/`)

To ground the LLM in reality without exposing it to raw, unparsed data, the service uses localized NLP models and contextual algorithms:

- **FinBERT (`nlp/finbert.py`):** Uses `ProsusAI/finbert` (with auto GPU/CPU fallback and lazy loading) to provide robust financial sentiment scores (Positive/Negative/Neutral) on news streams.
- **Entity Extraction (`nlp/entity_extractor.py`):** Identifies cryptocurrency symbols and markets from free-text queries.
- **Context Services (`context/`):** Includes deterministic algorithms like `pattern_detector.py` and `support_resistance.py` to feed mathematically accurate structural data to the TA Expert before LLM synthesis.

---

## 5. Chart Actions & Tools (`actions/`)

The **Interact Mode** allows the AI to manipulate the user's frontend UI using deterministic tool schemas defined in `actions/registry.py`.

- **Action Catalog:** Supports actions like `add_indicator`, `draw_tool`, `highlight_section`, `set_timeframe`, `fetch_historical_prices`, and `start_tour`.
- **Validation & Execution:** The `validator.py` ensures that requested indicators and tools exist in the system. The `executor.py` handles the application of these tools, and `undo.py` provides rollback capabilities.
- **State Persistence:** Chart actions and tool calls are persisted alongside the chat history so that a page reload preserves the interactive UI elements.

---

## 6. Safety & Guardrails (`safety/`)

Before an LLM is ever invoked, and before a response is returned to the user, multiple guardrails ensure the system remains safe and on-topic:

- **Scope Gate (`scope_gate.py`):** Immediately rejects queries that are not related to cryptocurrency, trading, or the LMView platform.
- **Knowledge Boundary (`knowledge_boundary.py`):** Ensures the AI does not hallucinate answers for topics explicitly defined as out-of-bounds.
- **Output Guard (`output_guard.py`):** Scans the synthesized LLM response to prevent financial advice, guarantee disclaimers, and catch unsafe content.

---

## 7. RAG & Knowledge Base (`rag/`)

- **Embeddings:** Uses `sentence-transformers` stored in a PostgreSQL `pgvector` HNSW index.
- **Knowledge Base:** Text chunks are ingested from `docs/ai/knowledge_base/approved/`.
- **Fallback:** If vector dependencies are missing, the system gracefully degrades to mock retrieval.

---

## 8. Provider Routing (`providers/`)

The `provider_router.py` dynamically routes requests based on the `AI_MODE` environment variable:

| Mode | Description | Requirements |
|---|---|---|
| `none` | Stub — always returns "not available" | None (default) |
| `mock` | Simulated deterministic AI responses | None |
| `local` | LiteLLM + local vLLM/Ollama | LiteLLM running, `AI_ENABLE_REAL_LLM=true` |
| `api` | LiteLLM → OpenAI/Anthropic/etc | API keys, LiteLLM running |

---

## 9. Key Data Flow (End-to-End Execution)

1. `POST /api/ai/chat` → backend router calls `orchestrator.run_chat_langgraph()` (or `run_chat_stream`).
2. The user's query and current chart context are persisted in PostgreSQL via `chat_store.py`.
3. **`scope_gate` node** validates that the query is crypto/platform-related.
4. **`intent_router` node** classifies the query intent and activates the necessary domain experts.
5. **`expert_execution` node** runs all activated experts (TA, Market Data, News, RAG, Chart, General) in parallel (`asyncio.gather`).
6. **Ensemble Vote** cross-validates the expert signals, calculates confidence, and resolves conflicting data.
7. **`synthesis` node** uses the dynamic `prompt_builder` to combine expert outputs into a coherent LLM response (supports streaming).
8. **`reflection` node** validates the response safety and checks generated chart actions. If it fails validation, it loops back to the synthesis node for revision.
9. **Tour Planner** (if in Interact Mode) appends an interactive visual tour if requested.
10. The final response (with grounded context, sources, caveats, and action plans) is returned to the user and persisted.

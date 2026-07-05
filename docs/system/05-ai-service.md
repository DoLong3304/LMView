# AI Service — ai_service/

The `ai_service` module powers LMView's AI Ask & Interact Modes. It operates
as a modular, multi-agent AI assistant driven by a **LangGraph DAG** with
parallel expert execution, ensemble voting, streaming support, and a
4-layer response caching hierarchy.

**Architecture (v0.34.0+):**
- **Standalone container**: `ai_service` runs in its own container
  (`cryptoprice_ai-service`, port 8100), NOT inside the FastAPI container.
  See `docker/ai-service/Dockerfile`.
- **HTTP proxy mode**: Backend FastAPI proxies AI requests to `ai-service`
  via HTTP (`AI_SERVICE_EMBEDDED=false`, default since v0.28.0).
  See `backend/services/ai/ai_proxy.py`.
- **Pre-warmed startup**: On container boot, the FastAPI `lifespan` handler
  calls `warmup_all()` on the provider router, sending a minimal `ping`
  completion to each provider to prime LiteLLM connection caches, load
  models, and validate API keys before the first real user request.
- **Heavy ML isolation**: `sentence-transformers` (torch), `langgraph`, and
  `litellm` are only installed in the `docker/ai-service` image, keeping
  the backend image slim (~500 MB vs ~3 GB).

---

## 1. Core Architecture (LangGraph DAG)

The AI orchestration uses a **Multi-Agent Directed Acyclic Graph (DAG)** with
per-node timeouts, parallel expert execution, and revision loops.

```
User Query
   ↓
Scope Gate & Knowledge Boundary ──(out of scope)──→ Early Exit
   ↓                          (in scope)
Intent Router ──(8s timeout)──→ activates domain experts
   ↓
Expert Execution ──(20s per expert, 40s gather)──→ parallel MoE
   ├── Technical Analysis Expert
   ├── Market Data Expert
   ├── News & Sentiment Expert
   ├── RAG Knowledge Expert
   ├── Chart Interaction Expert
   ├── General Market Expert
   └── Tour Planner (Interact mode)
   ↓
Ensemble Voting (cross-validates signals, resolves conflicts, calc confidence)
   ↓
Synthesis ──(45s timeout)──→ single LLM call (batch) or streaming yield
   ↓
Reflection (validates safety, checks actions, triggers revision if needed)
   ↓
Output & Action Execution
```

### Node Timeout Hierarchy

Each node in the DAG has a bounded timeout. If a node exceeds its budget,
a graceful fallback response is returned instead of failing the entire
request.

| Node | Timeout | Fallback |
|------|---------|----------|
| Scope Gate | ~10ms (sync) | N/A — instant |
| Intent Router | **8s** | Use `GENERAL` expert, minimal context needs |
| Expert Execution (per expert) | **20s** | Mark expert as timed out, return partial data |
| Expert Execution (total gather) | **40s** | Return whatever experts completed |
| Synthesis (LLM call) | **45s** | "I couldn't complete the analysis within the time limit." |
| **Total soft max** | **~93s** | |

### Streaming Path

The streaming path follows the same DAG up to and including expert execution,
then switches to `synthesize_response_stream()` which yields SSE-encoded
token events as they arrive from the LLM. After streaming completes, the
output guard is applied asynchronously. The streaming path also has per-node
timeouts (intent router 8s, expert execution 20s per expert / 40s gather).

### Graph Implementation

- **File**: `ai_service/agents/graph.py`
- **Framework**: `langgraph` (`StateGraph`)
- **State type**: `AgentState` (TypedDict in `ai_service/agents/state.py`)
- **Revisions**: Reflection node can trigger up to 1 revision loop back to
  synthesis if the response fails safety validation.

---

## 2. Directory Structure & Key Modules

```text
ai_service/
├── __init__.py
├── config.py            # Settings, feature flags, provider config loaders
├── configs/             # YAML configs (ai.api.yaml, litellm.yaml)
├── app/
│   ├── main.py          # FastAPI app factory, lifespan (pre-warm providers)
│   └── routes.py        # REST endpoints: /ai/chat, /ai/health, /ai/sessions
├── agents/              # LangGraph DAG implementation
│   ├── state.py         # AgentState TypedDict
│   ├── types.py         # Shared types: ExpertOutput, IntentClassification, ContextNeeds, Timer
│   ├── graph.py         # StateGraph compilation, node functions, timeouts
│   ├── intent_router.py # Hybrid (rule-based + LLM fallback) intent classification
│   ├── synthesis.py     # Single LLM call builder (batch + streaming), prompt assembly
│   ├── reflection.py    # Response validation, safety checks, revision routing
│   ├── ensemble.py      # Cross-validation of expert signals
│   ├── persistence.py   # Session memory management
│   ├── base_expert.py   # Abstract base for all experts
│   └── experts/         # Domain expert implementations
│       ├── technical_analysis.py  # Indicators, patterns, support/resistance
│       ├── market_data.py         # Ticker, order book, trades
│       ├── news_sentiment.py      # News fetching, sentiment scoring
│       ├── rag_knowledge.py       # Vector DB retrieval
│       ├── chart_interaction.py   # UI action determination
│       ├── general.py             # Fallback expert
│       └── tour_planner.py        # Interact mode walkthrough generation
├── providers/           # LLM provider routing
│   ├── router.py        # ProviderRouter: auto/local/api/none routing, warmup, health checks
│   ├── litellm_provider.py  # LiteLLM wrapper with key rotation, caching, extra headers
│   ├── none_provider.py # Fallback stub provider
│   ├── base.py          # BaseProvider abstract class
│   └── health.py        # Circuit breaker health monitor
├── core/                # Business logic
│   ├── orchestrator.py  # run_chat() entry point for Ask + Interact modes
│   └── cache.py         # Response cache (normalized key, LRU eviction, TTL-based)
├── safety/              # Guardrails
│   ├── scope_gate.py          # Query scope classification (crypto only)
│   ├── output_guard.py        # Response safety scan
│   └── knowledge_boundary.py  # Hard-coded out-of-bounds topics
├── rag/                 # Knowledge retrieval
│   ├── retrieval_service.py  # Hybrid BM25 + vector search
│   ├── knowledge_service.py  # Chunk management, auto-ingest
│   └── reranker.py           # Cross-encoder re-ranking
├── context/             # Chart context extraction
│   ├── context_service.py    # Data caveats, context assembly
│   ├── support_resistance.py # S/R level calculation
│   └── pattern_detector.py   # Candlestick + trend detection
├── actions/             # Chart action system (Interact mode)
│   ├── registry.py      # Available actions catalog
│   ├── executor.py      # Action execution with rollback
│   ├── validator.py     # Action parameter validation
│   ├── tool_definitions.py   # OpenAI tool schemas
│   └── handlers/        # Action handlers (walkthrough, highlight, navigation)
├── persistence/         # PostgreSQL storage
│   └── chat_store.py    # Session CRUD, message persistence, session memory
├── prompts/             # Prompt templates (legacy)
│   └── prompt_builder.py
└── nlp/                 # NLP utilities
    ├── finbert.py       # Financial sentiment (ProsusAI/finbert)
    └── entity_extractor.py  # Symbol/market entity extraction
```

---

## 3. Multi-Agent Expert System (`agents/experts/`)

The system uses a **Mixture of Experts (MoE)** pattern. The `Intent Router`
determines which experts to activate based on the user's query, saving
compute and improving accuracy. Activated experts run in parallel via
`asyncio.gather()`.

### Expert Catalog

| Expert | File | Purpose | Activates when... |
|--------|------|---------|-------------------|
| **Technical Analysis** | `experts/technical_analysis.py` | Interprets RSI, MACD, SMA, Bollinger Bands, volume, candlestick patterns, S/R levels | Query mentions indicators, trends, support/resistance |
| **Market Data** | `experts/market_data.py` | Fetches ticker, order book, recent trades | Query asks about price, volume, bid/ask |
| **News & Sentiment** | `experts/news_sentiment.py` | Fetches and scores recent news | Query mentions news, sentiment, fundamentals |
| **RAG Knowledge** | `experts/rag_knowledge.py` | Queries vector DB for platform docs | Query asks about LMView features, drawing tools |
| **Chart Interaction** | `experts/chart_interaction.py` | Determines UI tool calls | Interact mode, or query requests chart changes |
| **General** | `experts/general.py` | Baseline context summary | No other expert matches (fallback) |
| **Tour Planner** | `experts/tour_planner.py` | Generates walkthrough JSON (`tour_plan`) | Interact mode with platform walkthrough request |

### Expert Execution Flow

1. Intent router classifies query and produces `activated_experts` list.
2. `expert_execution_node` runs all activated experts in parallel.
3. Each expert wraps its execution in `asyncio.wait_for(..., timeout=20.0)`.
4. Expert outputs include `ExpertOutput` with `content`, `structured_data`,
   `confidence`, `data_sources`, and `warnings`.
5. After all experts complete, `ensemble_vote()` cross-validates signals,
   calculates aggregate confidence, and identifies conflicts.
6. The synthesis node receives all expert outputs and builds the final prompt.

### Candle Fetch Optimization

Data-gathering experts check `context_needs.needs_market_data` before
fetching external data. If the query doesn't need market data (e.g. a
general knowledge question), candle fetches are skipped entirely, avoiding
the "Failed to fetch candles for AI" warning that previously appeared on
every non-chart query.

---

## 4. Request Lifecycle (End-to-End)

### Batch (non-streaming)

```
POST /ai/chat
  │
  ├─ 1. Persist user message + chart context via chat_store.py
  ├─ 2. Load conversation history (last N messages)
  ├─ 3. Check cache.py (normalized key: message+symbol+timeframe)
  │     → HIT: return cached response immediately
  ├─ 4. Check knowledge_boundary.py
  │     → BLOCKED: return boundary refusal
  ├─ 5. Build graph state
  ├─ 6. Execute LangGraph DAG:
  │     a. scope_gate_node          → (~10ms, sync)
  │     b. intent_router_node       → (8s timeout, hybrid rule+LLM)
  │     c. expert_execution_node    → (20s per expert, 40s gather)
  │     d. synthesis_node           → (45s timeout, single LLM call)
  │     e. reflection_node          → (validate, optionally revise)
  ├─ 7. Store response in cache.py
  ├─ 8. Persist assistant response
  └─ 9. Return AIChatResponse
```

### Streaming

```
POST /ai/chat/stream
  │
  ├─ 1-6. Same as batch up to expert execution
  ├─ 7. synthesis_response_stream() → yields SSE token events:
  │     {"content": "...", "done": false}
  │     {"content": "...", "done": false}
  │     ...
  │     {"content": "full text", "done": true}
  └─ 8. Post-stream: output guard check (non-blocking)
```

### Interact Mode Walkthrough

When `mode == "interact"` and the LLM generates a `tour_plan` JSON action:

1. The synthesis node appends `_build_walkthrough_prompt()` to the system
   messages, instructing the LLM to output tool calls for guided tours.
2. The frontend receives `tour_plan` in the response and renders the
   `InteractBoard` overlay.
3. The user navigates through tour steps (prev/next/done/cancel).
4. On completion, recap buttons (Keep / Replay / Revert) appear.
5. The auto-start `useEffect` in `AiAssistantPanel.tsx` uses an
   `autoStartedTourMsgRef` guard to prevent re-triggering the same tour
   plan after completion.

---

## 5. Prompt Assembly System

The synthesis node (`synthesis.py`) builds the prompt from 5 message groups:

### 5.1 System Prompt (compressed, ~1KB)

**Before optimization**: 35KB / 781 lines. Included detailed variable-name
mappings, verbose language rules (repeated 3 ways), response structure
templates, and repetitive safety instructions.

**After optimization**: ~1KB / 19 lines. Compact essential instructions:

```
You are LMView AI, a bilingual (English/Vietnamese) crypto TA assistant.

## Core Rules
1. Respond in user's language. Never mix.
2. Markdown formatting, bold key values.
3. Convert raw variables (sma20 → 20-period SMA).
4. Prefix USD with $.
5. NEVER give buy/sell recs or price predictions.
6. NEVER execute code.
7. Disclaimer appended server-side.

## Synthesis Rules
- Synthesize expert data into coherent response.
- Prioritize relevance to user query.
- Acknowledge data limitations.
- State confidence honestly.

## Response Structure
Market Context → Technical Signals → Order Flow → News/Sentiment → Knowledge → Key Levels → Risk Notes
```

Modern LLMs (Qwen 3.x, GPT-4) already know what SMA, RSI, MACD mean and
naturally structure responses — the compressed prompt preserves all
critical safety instructions without redundant elaboration.

### 5.2 Expert Context Sections

Expert outputs are assembled into a single system message with markdown
headers. **Total content is capped at 2048 characters** (was unbounded,
5-15KB typical). Sections are trimmed from the end if total exceeds this
limit.

### 5.3 Context Needs

A structured data-requirements section tells the LLM what data was requested
vs. what was actually available. If data is missing (e.g., order book not
loaded), the LLM is instructed to use the closest available information.

### 5.4 Session Memory

Previous conversation findings are injected as system context. **Only the
last 3 findings are included** (previously all findings). This prevents
memory from growing unbounded while preserving essential context.

### 5.5 Chat History

Last 10 conversation turns, **capped at 2000 characters total**. Messages
beyond the budget are either truncated (if remaining budget > 100 chars)
or dropped (if budget exhausted). Prevents long sessions from flooding the
LLM with redundant history.

### 5.6 Runtime Context

Injected per-request:
```python
## Runtime Context
- Current server time (UTC): 2026-06-30T12:00:00+00:00
- Current epoch milliseconds: 1759219200000
- Chart times are live runtime data — do not reject timestamps past cutoff.
```

---

## 6. Caching Architecture (4 Layers)

The caching system is designed with 4 independent layers, each targeting a
different scope and TTL. In order of fastest → slowest:

### Layer 0 — Provider-Level Exact-Match Cache

| Property | Value |
|----------|-------|
| **Scope** | In-process Python dict, single `LiteLLMProvider` instance |
| **Max entries** | 50 |
| **TTL** | 15 seconds |
| **Key** | `str(messages)` — exact string of serialized messages |
| **Hit latency** | ~0ms (dict lookup) |
| **File** | `ai_service/providers/litellm_provider.py` |

Catches rapid duplicate calls within the same process — e.g., retries
from the provider router, or identical requests arriving within 15s
of each other. Implemented as module-level `_PROVIDER_CACHE` dict with
timestamp-based expiry and LRU eviction.

### Layer 1 — LiteLLM Library-Level Cache

| Property | Value |
|----------|-------|
| **Scope** | Global `litellm.cache` singleton |
| **Storage** | `diskcache` (preferred) or in-memory fallback |
| **TTL** | 60 seconds |
| **Key** | LiteLLM internal hash of model + messages |
| **Init** | During `warmup()` — first import of litellm |

Enabled on container startup via `litellm.Cache(type="disk", ttl=60)`.
If `diskcache` is not installed (shouldn't happen in the production image),
falls back to `type="local"` (in-memory). Cache namespace is
`litellm_response_cache` for observability.

### Layer 2 — Application-Level Normalized Cache

| Property | Value |
|----------|-------|
| **Scope** | Module-level `OrderedDict` |
| **Max entries** | 500 (was 100) |
| **TTL (price/market)** | 120 seconds (was 30) |
| **TTL (educational)** | 600 seconds (was 300) |
| **Key** | SHA-256 hash of normalized message + symbol + timeframe + indicators + language + mode |
| **File** | `ai_service/core/cache.py` |

The primary semantic cache. Normalizes messages by lowercasing, collapsing
whitespace, and stripping punctuation. Keys include symbol and timeframe
so `"What is RSI?"` for BTCUSDT is cached separately from the same question
for ETHUSDT. Question type classification (price/market vs educational)
determines TTL — the assumption being that price data changes fast while
educational content stays stable.

### Layer 3 — DashScope Server-Side Context Caching

| Property | Value |
|----------|-------|
| **Scope** | DashScope API server (Alibaba Cloud) |
| **Mechanism** | Automatic KV cache of repeated system prompt prefixes |
| **TTL** | ~5 minutes (DashScope managed) |
| **Effect** | ~80% reduction in first-token latency on repeated prompts |
| **Headers** | `X-DashScope-Cache: enable`, `X-DashScope-SSE: enable` |

Enabled via `extra_headers` in every `litellm.acompletion()` call to
DashScope. The DashScope backend detects repeated system prompt prefixes
and reuses the KV cache computation, dramatically reducing first-token
latency for subsequent queries with the same system prompt. This is purely
server-side — no client storage required.

### Layer 4 — LiteLLM Proxy Cache (optional, future)

| Property | Value |
|----------|-------|
| **Scope** | LiteLLM proxy container (port 4000) |
| **Storage** | Redis (when configured) |
| **TTL** | Configurable |
| **Status** | Deactivated — AI service bypasses the proxy |

The LiteLLM proxy config (`ai_service/configs/litellm.yaml`) has caching
parameters defined but is unused because the AI service calls DashScope
directly via the `litellm` Python library. If a future architecture change
routes through the proxy, Redis-backed caching is ready.

### Cache Comparison

| Layer | Scope | TTL | Latency | % of requests hit |
|-------|-------|-----|---------|-------------------|
| 0 — Provider dict | Exact messages | 15s | 0ms | ~2% (retries) |
| 1 — litellm.cache | Exact messages | 60s | ~1ms | ~5% (library duplicates) |
| 2 — Normalized | Semantically same | 30-600s | 0ms | ~30% (common questions) |
| 3 — DashScope KV | System prompt prefix | ~5min server | ~1ms | ~80% reduction in TTFT |
| 4 — Proxy Redis | Exact messages | Configurable | ~2ms | 0% (not in path) |

---

## 7. Provider Routing (`providers/`)

### Provider Modes

| Mode | Description | When Used |
|------|-------------|-----------|
| `api` | DashScope API via LiteLLM | Default production mode |
| `local` | Local vLLM/Ollama via LiteLLM | Development/offline |
| `auto` | Try local → API → none | Fallback when `AI_MODE` unset |
| `none` | Stub — always returns "not available" | Testing/disaster recovery |

### Model Catalog

Models are defined in `ai_service/configs/ai.api.yaml` across 3 tiers:

| Tier | Models | Use Case |
|------|--------|----------|
| **Standard** | `qwen3.7-plus`, `qwen3.6-plus`, `qwen3.6-flash`, `qwen3.5-plus` | Default rotation |
| **Reserved** | `qwen3.7-max`, `qwq-32b`, `deepseek-r1` | Manual/premium user selection |
| **Benchmark** | `qwen3.6-max-preview`, `qwen3.5-flash`, `qwen2.5-72b` | Automated testing |

### Fallback Chain

Within each provider, LiteLLM tries:
1. Primary model with current API key
2. Key rotation (if multiple keys configured via `DASHSCOPE_API_KEYS`)
3. Fallback models (in priority order)
4. If all models + keys exhausted → `QuotaExhaustedError`
5. Provider router falls through to next provider (`none` provider as last resort)

### Circuit Breaker

The health monitor (`providers/health.py`) tracks provider failures and
opens a circuit breaker if a provider fails repeatedly. The provider router
skips tripped providers until the circuit resets.

### DashScope Caching Headers

Every API call to DashScope includes:
- `X-DashScope-Cache: enable` — enables server-side context caching
- `X-DashScope-SSE: enable` — enables streaming support

These headers are added dynamically based on the `base_url` containing
`dashscope` or `aliyuncs`.

### LiteLLM Proxy Configuration

The LiteLLM proxy (`ai_service/configs/litellm.yaml`) mirrors the model
catalog and adds `latency-based-routing` strategy and load balancing. It is
not currently in the request path (the AI service bypasses it), but is
available for future proxy-based deployments.

---

## 8. Safety & Guardrails (`safety/`)

Three independent safety layers, applied at different pipeline stages:

### Scope Gate (`scope_gate.py`)

- **When**: Before any LLM call (first DAG node)
- **What**: Classifies query as in-scope or out-of-scope using keyword +
  LLM hybrid classification
- **Threshold**: LLM fallback if rule-based confidence < 0.45
- **Performance**: ~10ms average (rule-based), ~20s max (LLM fallback with 8s timeout)
- **Out-of-scope examples**: Weather, recipes, code generation, financial advice
- **Prompt injection**: Detected via role-play patterns + instruction override attempts

### Knowledge Boundary (`knowledge_boundary.py`)

- **When**: Before DAG execution, after scope gate
- **What**: Checks against hard-coded out-of-bounds topics
- **Rejects**: Unsolicited financial advice, price predictions, legal opinions

### Output Guard (`output_guard.py`)

- **When**: After LLM response synthesis (post-DAG)
- **What**: Scans the generated response for:
  - Direct buy/sell recommendations
  - Unsafe content (violence, hate speech)
  - Missing disclaimers
  - Language consistency (no mixed languages)
- **If failing**: Triggers reflection node revision

---

## 9. RAG & Knowledge Base (`rag/`)

### Vector Retrieval

- **Embedding model**: `BAAI/bge-small-en-v1.5` (384 dims)
- **Index**: PostgreSQL pgvector HNSW index
- **Search mode**: Hybrid (BM25 + vector) with configurable weight
- **Top-K**: 6 chunks (configurable via `rag_top_k`)
- **Min score**: 0.25 threshold
- **Reranking**: Cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)

### Knowledge Base Ingestion

Text chunks are ingested from `docs/ai/knowledge_base/approved/` at startup.
Content includes:
- LMView platform documentation (drawing tools, indicators, settings)
- Cryptocurrency domain knowledge (market microstructure, on-chain analytics)
- Bilingual glossary (English/Vietnamese)
- Risk management frameworks

### Retrieval Flow

```
User Query
  → LLM-based query rewriting (if needed)
  → Hybrid search (BM25 + vector embedding)
  → Score threshold filter (> 0.25)
  → Cross-encoder reranking
  → Top-K selection
  → Chunk deduplication + source attribution
```

---

## 10. Performance Benchmarks

### Latest Results (v0.34.0)

| Metric | Value |
|--------|-------|
| Total questions | 93 (across 15 categories) |
| Sampled execution | 11 (6 categories) |
| Pass rate | **90.9%** |
| Avg latency (passing) | 23,160 ms |
| Safety refusal rate | **100%** (prompt injection, OOS) |
| Pipeline health | ✅ All experts runnable |

### Token Usage (after optimization)

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| System prompt | 35,299 bytes | 1,022 bytes | **97%** |
| Expert context | 5,000-15,000 bytes | ≤2,048 bytes | 60-86% |
| Chat history | Unlimited (10 msgs) | ≤2,000 bytes | Variable |
| Session memory | All findings | Last 3 | Variable |
| **Total per query** | **~35-50 KB** | **~5 KB** | **85-90%** |

### Latency Breakdown (typical)

| Phase | Duration | Notes |
|-------|----------|-------|
| Scope gate | ~10ms | Synchronous classification |
| Intent router | ~100ms-8s | Fast path (rule-based) or LLM fallback |
| Expert execution | 1-20s | Parallel gather |
| Synthesis (LLM) | 5-45s | Single LLM generation call |
| Reflection | ~10ms-2s | Quick validation scan |
| **Total (typical)** | **~10-30s** | |
| **Total (timeout)** | **~93s** | Soft max before graceful fallback |

---

## 11. Test Suite

### Python Unit Tests

```bash
# All tests (requires ai-service deps installed)
python -m pytest tests/ai/ -v

# Specific test files
python -m pytest tests/ai/test_agent_state.py -v
python -m pytest tests/ai/test_intent_router.py -v
python -m pytest tests/ai/test_chart_safety.py -v
python -m pytest tests/ai/test_experts.py -v
python -m pytest tests/ai/test_provider_health.py -v

# AI grading (requires running ai-service + LLM keys)
python -m pytest tests/ai/test_ai_graded.py -v

# RAG quality tests
python -m pytest tests/ai/test_rag_quality.py -v

# Benchmark suite
python tests/ai/run_benchmark.py --model qwen3.5-flash
```

### End-to-End Playwright Tests

```bash
cd frontend

# Interact mode tests (9 tests, ~5.4 min)
npx playwright test e2e/full-suite/ai-helper-interact.spec.ts \
  --project chromium \
  --config=e2e/full-suite/playwright.config.ts

# Ask mode tests
npx playwright test e2e/full-suite/ai-helper-ask.spec.ts \
  --project chromium \
  --config=e2e/full-suite/playwright.config.ts

# Advanced AI tests
npx playwright test e2e/full-suite/ai-helper-advanced.spec.ts \
  --project chromium \
  --config=e2e/full-suite/playwright.config.ts
```

### Test Caveats

- **AI cold-start**: The first query after container start takes 60-120s
  (LiteLLM warmup + DashScope connection). Subsequent queries are faster
  (10-30s typical).
- **Non-deterministic output**: AI responses vary between runs. Content
  assertions are relaxed (check step count, not specific text).
- **Test 8 timeout**: The last test in the Interact suite takes ~2.9min due
  to accumulated session state + AI latency, but passes within the 240s
  config timeout.

---

## 12. Known Limitations & Caveats

1. **First-query latency**: Despite pre-warming, the very first LLM call
   after container start takes 60-120s due to DashScope quota rotation and
   model loading. Pre-warming primes the connection pool but cannot
   eliminate the cold-start for the first full-sized completion.

2. **No graceful per-expert timeout streaming**: The streaming path's
   synthesis node has a 45s timeout, but if the LLM stalls mid-stream,
   the connection is severed without a fallback response. The batch path
   returns a graceful timeout message.

3. **Non-deterministic tour content**: The `tour_plan` JSON generated by
   the LLM varies per query. Tests verify structure (step count, overlay
   presence) not specific text.

4. **Interact mode session accumulation**: Multiple tour-generated
   messages accumulate in the session. The `clearChat` stability logic
   in Playwright tests waits for the async session load to settle before
   clearing.

5. **RAG knowledge base updates**: Adding new documents to
   `docs/ai/knowledge_base/approved/` requires a container restart to
   re-ingest. Live auto-ingest is planned but not implemented.

6. **LiteLLM proxy unused**: The LiteLLM proxy container (`litellm:4000`)
   is configured but not in the request path — the AI service calls
   DashScope directly via the `litellm` Python library. Proxy caching
   via Redis is available if routing is changed.

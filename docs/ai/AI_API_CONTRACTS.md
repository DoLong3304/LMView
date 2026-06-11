# AI API Contracts - LMView

## Chat Endpoint

### `POST /api/ai/chat`

Request:

```json
{
  "session_id": "uuid or null",
  "mode": "ask",
  "message": "What does the RSI indicate?",
  "language": "en",
  "chart_context": {
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "timeframe": "1h",
    "selected_indicators": ["RSI", "SMA20"],
    "latest_candle": {"close": 67500, "volume": 1200}
  }
}
```

`mode` supports `ask` and `interact`. Both modes use the same backend orchestration pipeline.

Response:

```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "content": "RSI analysis...",
  "provider": "api",
  "model_name": "openai/qwen3.5-plus",
  "is_mock": false,
  "created_at": "2026-06-11T10:00:00Z",
  "warnings": [],
  "tool_calls": [],
  "chart_actions": [],
  "grounded_context_used": true,
  "confidence": 0.75,
  "sources": [],
  "data_caveats": ["Runtime data may be newer than the model training cutoff."],
  "provider_metadata": {
    "provider": "api",
    "model": "openai/qwen3.5-plus",
    "fallback_used": false,
    "latency_ms": 1234
  }
}
```

`provider` is normalized to `local`, `api`, or `none`. `none` means no usable model was available and the response is generic system guidance.

## Health Endpoint

### `GET /api/ai/health`

Response:

```json
{
  "auth_required": true,
  "database_ready": true,
  "mock_mode_available": false,
  "chart_action_schema_version": "1.1.0",
  "action_catalog_version": "2.0.0",
  "supported_modes": ["ask", "interact"],
  "supported_action_types": ["add_indicator", "highlight_region"],
  "ai_mode": "auto",
  "provider_mode": "auto",
  "effective_provider": "api",
  "available_api_models": ["openai/qwen3.5-plus"],
  "local_available": false,
  "rag_enabled": true,
  "pgvector_ready": true,
  "knowledge_source_count": 0
}
```

## Action Catalog

### `GET /api/ai/actions/catalog`

Returns reusable JSON schemas for function calls used by the AI, frontend debug tester, and future action integrations.

## Knowledge Endpoints

### `POST /api/ai/knowledge/search`

Searches approved, RAG-enabled sources only.

```json
{
  "query": "What is RSI?",
  "top_k": 6,
  "min_score": 0.25,
  "language": "en",
  "domain": "technical_analysis"
}
```

### `POST /api/ai/knowledge/ingest`

Admin only. Ingestion skips documents unless their registry entry has `review_status: approved` and `allowed_for_rag: true`.

```json
{
  "source_dir": "docs/ai/knowledge_base/approved/",
  "source_id": "technical-analysis"
}
```

### Other Knowledge Routes

| Endpoint | Purpose |
|---|---|
| `GET /api/ai/knowledge/sources` | List persisted sources |
| `GET /api/ai/knowledge/health` | RAG health |
| `GET /api/ai/knowledge/registry/validate` | Registry metadata validation |

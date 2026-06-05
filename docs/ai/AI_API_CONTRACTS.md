# AI API Contracts — LMView

## Chat Endpoint

### POST /api/ai/chat

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

Response:
```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "role": "assistant",
  "content": "RSI analysis...",
  "provider": "qwen_api",
  "model_name": "openai/qwen-plus",
  "is_mock": false,
  "created_at": "2026-06-05T10:00:00Z",
  "warnings": [],
  "suggested_actions": null,
  "chart_actions": null,
  "grounded_context_used": true,
  "confidence": 0.75,
  "sources": [
    {"chunk_id": "uuid", "title": "TA Fundamentals", "score": 0.92}
  ],
  "data_caveats": ["Trade data is ticker-derived"],
  "provider_metadata": {
    "provider": "qwen_api",
    "model": "openai/qwen-plus",
    "is_local": false,
    "fallback_used": false,
    "latency_ms": 1234
  }
}
```

## Health Endpoint

### GET /api/ai/health

Response:
```json
{
  "auth_required": true,
  "database_ready": true,
  "mock_mode_available": true,
  "chart_action_schema_version": "1.1.0",
  "supported_modes": ["ask", "interact"],
  "supported_action_types": ["add_indicator", "..."],
  "ai_mode": "api",
  "rag_enabled": true,
  "real_llm_enabled": true,
  "available_providers": ["qwen_api", "llama_api", "mock"],
  "pgvector_ready": true,
  "knowledge_source_count": 5
}
```

## Knowledge Endpoints

### POST /api/ai/knowledge/search

Request:
```json
{
  "query": "What is RSI?",
  "top_k": 6,
  "min_score": 0.25,
  "language": "en",
  "domain": "technical_analysis"
}
```

Response:
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "text": "RSI measures momentum...",
      "score": 0.92,
      "document_title": "Technical Analysis Fundamentals",
      "source_title": "Technical Analysis",
      "heading": "RSI (Relative Strength Index)"
    }
  ],
  "query": "What is RSI?",
  "total_results": 3,
  "search_latency_ms": 45
}
```

### POST /api/ai/knowledge/ingest (Admin only)

Request:
```json
{
  "source_dir": "docs/ai/knowledge_base/approved/",
  "source_id": "technical-analysis"
}
```

### GET /api/ai/knowledge/sources

### GET /api/ai/knowledge/health

# AI Provider Routing — LMView

## Overview

LMView uses a provider-agnostic routing system. The AI behavior, prompts, schemas, RAG, risk review, and output contract are identical across all providers.

## Provider Types

| Provider | Type | GPU Required | Notes |
|----------|------|-------------|-------|
| local_vllm | Local vLLM | Yes | Qwen/Llama via vLLM OpenAI-compatible API |
| qwen_api | Online API | No | Qwen-Plus via DashScope |
| llama_api | Online API | No | Llama-4-Maverick via Meta API |
| openai | Online API | No | GPT-4o-mini via OpenAI |
| gemini | Online API | No | Gemini 2.0 Flash via Google |
| deepseek | Online API | No | DeepSeek Chat via DeepSeek API |
| litellm_proxy | Proxy | No | Custom LiteLLM proxy |
| mock | Mock | No | Deterministic Phase 0 fallback |

## Routing Modes

### `AI_MODE=mock` (default)
Only mock provider. No real LLM calls. Safe for development and testing.

### `AI_MODE=api`
Online API providers first: `qwen_api → llama_api → local_vllm → mock`

### `AI_MODE=local`
Local vLLM first: `local_vllm → qwen_api → llama_api → mock`

### `AI_MODE=auto`
Full priority chain: `local_vllm → qwen_api → llama_api → openai → gemini → deepseek → mock`

## Fallback Behavior

1. Router tries providers in configured order
2. On failure, logs warning and tries next provider
3. If `AI_ENABLE_PROVIDER_FALLBACK=false`, stops after first failure
4. Mock is always the final fallback
5. Response metadata indicates which provider was used and if fallback occurred

## Configuration

```bash
# Mode selection
AI_MODE=auto                    # mock|api|local|auto
AI_ENABLE_REAL_LLM=true        # Enable real LLM providers
AI_ENABLE_PROVIDER_FALLBACK=true # Enable automatic fallback

# Provider API keys (set only those you use)
QWEN_API_KEY=...
LLAMA_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...

# Local vLLM
VLLM_BASE_URL=http://vllm:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# LiteLLM proxy
LITELLM_BASE_URL=http://litellm:4000
LITELLM_MASTER_KEY=...
```

## Response Metadata

Every AI response includes provider metadata:
```json
{
  "provider": "qwen_api",
  "model_name": "openai/qwen-plus",
  "is_mock": false,
  "confidence": 0.75,
  "provider_metadata": {
    "provider": "qwen_api",
    "model": "openai/qwen-plus",
    "is_local": false,
    "fallback_used": false,
    "latency_ms": 1234
  }
}
```

## Health Check

`GET /api/ai/health` returns:
- Available providers list
- AI mode
- RAG enabled status
- pgvector readiness
- Knowledge source count

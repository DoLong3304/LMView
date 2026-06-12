# AI Provider Routing - LMView

## Overview

LMView keeps AI behavior provider-agnostic. Ask and Interact use the same orchestration path in `ai_service/core/orchestrator.py`; only the final completion provider changes.

## Public Provider Choices

| Provider | Meaning | Notes |
|---|---|---|
| `local` | Local OpenAI-compatible endpoint, usually vLLM | Preferred by `auto` when healthy |
| `api` | External OpenAI-compatible API model catalog | Defaults to DashScope International Qwen |
| `none` | No model available | Returns generic LMView/system guidance only |

Frontend mock mode remains a frontend data-mode feature. Backend production routing does not include `mock`.

## Routing Modes

| `AI_MODE` | Runtime order |
|---|---|
| `auto` | `local -> api -> none` |
| `local` | `local -> none` |
| `api` | `api -> none` |
| `none` | `none` |

Provider order and model catalogs live in YAML under `ai_service/configs/`. The env surface stays lean.

## Configuration

```bash
AI_MODE=auto
AI_CONFIG_PATH=ai_service/configs/ai.api.yaml
DASHSCOPE_API_KEY=...

# Legacy alias, still accepted if DASHSCOPE_API_KEY is unset.
QWEN_API_KEY=...
```

Default API provider:

| Field | Value |
|---|---|
| Provider | DashScope International OpenAI-compatible API |
| Model | `openai/qwen3.5-plus` |
| Endpoint | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| Primary key env | `DASHSCOPE_API_KEY` |

OpenAI-compatible responses read usage from `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`. Native DashScope references use `input_tokens`, `output_tokens`, and `total_tokens`.

References:

- https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope
- https://www.alibabacloud.com/help/en/model-studio/models
- https://www.alibabacloud.com/help/en/model-studio/model-pricing

## Response Metadata

```json
{
  "provider": "api",
  "model_name": "openai/qwen3.5-plus",
  "is_mock": false,
  "tool_calls": [],
  "chart_actions": [],
  "warnings": [],
  "provider_metadata": {
    "provider": "api",
    "model": "openai/qwen3.5-plus",
    "fallback_used": false,
    "usage": {
      "prompt_tokens": 1200,
      "completion_tokens": 240,
      "total_tokens": 1440
    }
  }
}
```

## Health Check

`GET /api/ai/health` returns provider mode, effective provider, available API models, local health, RAG status, pgvector readiness, and action catalog version.

import os
import sys
import logging

log = logging.getLogger("backend.core.config")

# ─── Redis Sentinel (High Availability) ─────────────────────────────────────
# Redis Sentinel configuration is handled in redis_sentinel.py
# using REDIS_SENTINELS and REDIS_MASTER_NAME environment variables

# ─── InfluxDB ───────────────────────────────────────────────────────────────
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

# ─── Trino (Iceberg query engine) ───────────────────────────────────────────
TRINO_HOST = os.environ.get("TRINO_HOST", "trino")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))

# ─── PostgreSQL (Auth, AI, Session persistence) ─────────────────────────────
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "iceberg")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_LMVIEW_DB = os.environ.get("POSTGRES_LMVIEW_DB", "iceberg_catalog")

# ─── Auth/Session ────────────────────────────────────────────────────────────
SESSION_EXPIRY_HOURS = int(os.environ.get("SESSION_EXPIRY_HOURS", "168"))  # 7 days
RUN_MIGRATIONS = os.environ.get("RUN_MIGRATIONS", "false")

# ─── AI / LLM Provider ──────────────────────────────────────────────────────
# AI_MODE: auto | local | api | none
#   auto  - try local first, then API, then none
#   local - local endpoint only, then none
#   api   - API provider only, then none
#   none  - generic LMView/system answers only
AI_MODE = os.environ.get("AI_MODE", "auto")
AI_CONFIG_PATH = os.environ.get("AI_CONFIG_PATH", "")
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://ai-service:8100")
AI_REQUEST_TIMEOUT_SECONDS = int(os.environ.get("AI_REQUEST_TIMEOUT_SECONDS", "60"))
AI_MAX_CONTEXT_TOKENS = int(os.environ.get("AI_MAX_CONTEXT_TOKENS", "12000"))
AI_ENABLE_RAG = os.environ.get("AI_ENABLE_RAG", "true").lower() in ("1", "true", "yes")

# LiteLLM / provider compatibility knobs (read but never logged)
LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://vllm:8000/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# RAG / Embeddings
AI_EMBEDDING_PROVIDER = os.environ.get("AI_EMBEDDING_PROVIDER", "local")
AI_EMBEDDING_MODEL = os.environ.get("AI_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
AI_RAG_TOP_K = int(os.environ.get("AI_RAG_TOP_K", "6"))
AI_RAG_MIN_SCORE = float(os.environ.get("AI_RAG_MIN_SCORE", "0.25"))
AI_RERANKER_MODEL = os.environ.get("AI_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
AI_KB_APPROVED_ONLY = os.environ.get("AI_KB_APPROVED_ONLY", "true").lower() in ("1", "true", "yes")

# ─── CORS ───────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# ─── Startup validation ────────────────────────────────────────────────────
_missing = []
if not INFLUX_TOKEN:
    _missing.append("INFLUX_TOKEN")
if _missing:
    log.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)

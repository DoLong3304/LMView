# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile for standalone LMView AI service
# ─────────────────────────────────────────────────────────────────────────────
# Runs the ``ai_service.app.main:app`` FastAPI app on port 8100.
#
# The backend FastAPI gateway proxies AI requests here via HTTP.
# This image has ALL the heavy ML libs (torch, sentence-transformers, etc.)
# so the backend stays lean (~500 MB vs ~3 GB).

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH="/app:/app/src"

# Install system deps for building wheels (torch, sentence-transformers, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY docker/fastapi/requirements.txt ./requirements.txt
COPY docker/fastapi/requirements-ai.txt ./requirements-ai.txt

# Install gateway deps + AI deps
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-ai.txt

# Pre-cache embedding model to avoid cold-start download
# BAAI/bge-small-en-v1.5 — lightweight 384-dim model, ~33MB
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')" \
    && python3 -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Copy source — everything the ai-service needs
COPY ai_service/ ./ai_service/
COPY backend/ backend/
COPY src/ src/
COPY schemas/ schemas/

EXPOSE 8100

CMD ["uvicorn", "ai_service.app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "2"]

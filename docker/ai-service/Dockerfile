# Dockerfile for standalone LMView AI service
# ─────────────────────────────────────────────────────────────────────────────
# Runs the ``ai_service.app.main:app`` FastAPI app on port 8100.
#
# Image layers:
#   1. ``requirements.txt``  — base gateway deps (fastapi, uvicorn, httpx…)
#   2. ``requirements-ai.txt`` — heavy ML/LLM libs (litellm, torch, langgraph)
#   3. Source code  — ai_service/ + minimal backend/ for shared models/auth
#
# The backend FastAPI gateway image uses the same base but installs ONLY
# ``requirements.txt`` (no AI libs) and proxies here for AI requests.

FROM python:3.11-slim

WORKDIR /app

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

# Copy only the modules needed at runtime
COPY ai_service/ ./ai_service/
COPY backend/models/ ./backend/models/
COPY backend/core/ ./backend/core/
COPY backend/services/ ./backend/services/
COPY backend/api/ai/ ./backend/api/ai/
COPY backend/api/__init__.py ./backend/api/__init__.py
COPY backend/__init__.py ./backend/__init__.py

EXPOSE 8100

CMD ["uvicorn", "ai_service.app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "2"]

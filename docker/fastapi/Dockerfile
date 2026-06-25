FROM python:3.11-slim

WORKDIR /app

# ─── PYTHONPATH ────────────────────────────────────────────────────────
ENV PYTHONPATH="/app:/app/src"

# ─── Install ONLY gateway deps (NO heavy AI/ML libs) ───────────────────
# The backend is primarily a thin gateways that proxies AI requests to
# the standalone ``ai-service`` container.  In proxy mode
# (``AI_SERVICE_EMBEDDED=false``, the default since v0.27.0) it does not
# import ``torch``, ``sentence-transformers``, ``litellm``, ``langgraph``,
# or any other heavy ML library.
#
# If you flip ``AI_SERVICE_EMBEDDED=true``, install
# ``requirements-ai.txt`` on top of this file.
COPY docker/fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Source code ───────────────────────────────────────────────────────
# ``ai_service/`` is copied for embedded-mode fallback. In proxy mode
# (``AI_SERVICE_EMBEDDED=false``, the default) these modules are imported
# lazily on first AI request.  Heavy AI libs (torch, sqlite-transformers)
# are NOT installed in this image — they live in ``docker/ai-service``.
#
# TODO(v0.28): Convert all remaining ``from ai_service`` imports to lazy
#              and remove this COPY. The backend should proxy 100% via
#              HTTP.  See ``backend/services/ai/ai_proxy.py``.
COPY backend/ backend/
COPY src/ src/
COPY ai_service/ ai_service/
COPY schemas/ schemas/

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

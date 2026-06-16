FROM python:3.11-slim

WORKDIR /app

# Add /app/src to PYTHONPATH so that `from common.logging import ...`,
# `from exchanges.binance.client import ...` (in src/), and other
# top-level packages inside src/ resolve without each module having
# to mutate sys.path.
ENV PYTHONPATH="/app:/app/src"

COPY docker/fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY src/ src/
COPY ai_service/ ai_service/
COPY schemas/ schemas/

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

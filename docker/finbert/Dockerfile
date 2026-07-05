FROM python:3.11-slim

WORKDIR /app

# Install FinBERT dependencies at build time (avoids OOM during startup)
RUN pip install --no-cache-dir --timeout 300 \
    asyncpg \
    transformers \
    torch --extra-index-url https://download.pytorch.org/whl/cpu

COPY src/ /app/src/
COPY ai_service/ /app/ai_service/

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "ai_service.nlp.news_processor"]

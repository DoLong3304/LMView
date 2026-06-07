FROM python:3.11-slim

WORKDIR /app

COPY docker/fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY src/ src/
COPY schemas/ schemas/

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

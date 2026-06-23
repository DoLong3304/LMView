FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "kafka-python==2.0.2" \
    "websockets>=11.0,<13.0" \
    "aiohttp>=3.9.0,<4.0" \
    "avro>=1.11.0,<2.0.0" \
    "fastavro>=1.9.0,<2.0.0" \
    "lz4>=4.0,<5.0" \
    "requests>=2.31.0"

COPY schemas/ /app/schemas/
COPY src/ /app/src/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["python", "-u", "src/combined_stream/main.py"]

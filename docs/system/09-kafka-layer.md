# Kafka Layer

Apache Kafka 3.9.0 message broker for real-time market data.

## Topology

- **3 brokers** (kafka-1/2/3) with 12 partitions per topic
- **Replication factor**: 3
- **Min ISR**: 2
- **Compression**: LZ4
- **Retention**: 48 hours
- **Auto-create topics**: false

## Topics

| Topic | Records | Key |
|---|---|---|
| `crypto_ticker` | 24hr ticker updates (close, bid, ask, volume, change%) | symbol |
| `crypto_klines` | 1s candlestick records (O, H, L, C, V, timestamp) | symbol |
| `crypto_trades` | Aggregated trade data (price, qty, side, timestamp) | symbol |
| `crypto_depth` | Order book snapshots (bids, asks as price-level arrays) | symbol |

## Schema Registry

- **Apicurio Registry** in-memory mode (port 8085)
- Avro schemas in `schemas/*.avsc`
- Producer uses Confluent Avro serializer with 5-byte frame header
- Spark strips the 5-byte header before `from_avro()` decoding

## Kafka Connect / Clients

- **Producer** (`src/producer/main.py`): Confluent Kafka Python producer, Avro-serialized
- **Flink** (`src/processing/pipeline.py`): PyFlink Kafka consumer with Avro deserialization
- **Spark** (`src/lakehouse/pipeline.py`): Spark Structured Streaming Kafka consumer

## Images

- **Custom image**: `cryptoprice/kafka:3.9.0` (based on `apache/kafka:3.9.0`)
- **Dockerfile**: `docker/kafka/Dockerfile` — custom entrypoint, JMX config baked in
- **Entrypoint**: `docker/kafka/entrypoint.sh` — stale ZK node cleanup, ZK session timeout 10s

## Key Configs

- `KAFKA_NUM_PARTITIONS: 12` — default partition count for auto-created topics
- `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3`
- `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3`
- `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2`
- `KAFKA_LOG_SEGMENT_BYTES: 134217728` (128 MB)
- `KAFKA_COMPRESSION_TYPE: lz4`

## Exporter

- `kafka-exporter`: Prometheus metrics exporter (port 9308)
- Running on worker node

## Known Issues

- **Stale ZK nodes**: Entrypoint cleans up stale broker nodes before starting (fix for NodeExistsException on restart)
- **Producer auto-reconnect**: Fixed in v0.25.41 — auto-recreates producer when "RecordAccumulator is closed"
- **Topic provisioning**: Topics must be created manually via `scripts/create_kafka_topics.sh`

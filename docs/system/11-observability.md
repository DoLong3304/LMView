# Observability — Prometheus + Grafana + Loki

## Prometheus

- **State**: 0/1 replicas (stopped) — would run on worker node port 9090
- **Config**: `config/prometheus.yml` — 21 scrape jobs
- **Custom scrape paths**:
  - `/metrics-custom` — WebSocket/source/cache metrics (backend/api/metrics.py)
  - `/metrics-ai` — AI/RAG/cost metrics (backend/services/ai/metrics.py)

## Grafana

- **State**: 1/1 running on worker node, port 3001 (published)
- **Image**: grafana/grafana:10.2.0
- **Dashboards**: 22 provisioned dashboards, 48 alert rules
- **Datasources**: Prometheus, Loki, InfluxDB, PostgreSQL
- **Alert Center**: Dashboard `/d/phase5-alert-center`

## Loki + Promtail

- **State**: 0/1 replicas (stopped) — opt-in logging stack
- Loki port: 3100
- 7-day log retention
- Promtail tails Docker logs via Docker API

## Custom Metrics

### WebSocket / Multi-Source (backend/api/metrics.py)
- Connection lifecycle (connect, disconnect, error)
- Message push count
- Multi-source fallback tracking
- Slow-client buffer warnings
- Source freshness (Redis vs InfluxDB vs Trino)

### AI / RAG (backend/services/ai/metrics.py)
- AI query counts by mode
- Provider call duration/costs
- RAG retrieval counts
- Scope gate hits/rejections
- Output guard statistics

## Exporters Running

| Exporter | Port | State |
|---|---|---|
| kafka-exporter | 9308 | Running |
| node-exporter | 9100 | Stopped |
| redis-exporter | 9121 | Stopped |

## Known Issues

- **Prometheus**: Stopped — no metrics collection currently active
- **Loki**: Stopped — no centralized log aggregation
- **Grafana**: Running but datasources may be unreachable without Prometheus/Loki

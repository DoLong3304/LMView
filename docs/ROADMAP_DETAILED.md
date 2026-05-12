# SYSTEM ROADMAP - Production Readiness Plan

> **Purpose:** Comprehensive roadmap to production-ready enterprise trading platform  
> **Current Status:** MVP Complete (Multi-Exchange HA + Observability)  
> **Target:** Enterprise-grade Trading Platform with 99.9% uptime  
> **Timeline:** 6 phases, 15-21 weeks (4-5 months)  
> **Last updated:** 2026-05-11

---

## 📊 Executive Summary

### Current State (MVP)
- ✅ Multi-Exchange HA (Binance + OKX)
- ✅ News Sentiment Pipeline
- ✅ Observability Stack (Prometheus + Grafana + Loki)
- ✅ Profile-Based Startup (safe for 32GB RAM)
- ✅ Frontend Drawing System (12 tools)
- ✅ Basic 1m candle storage

### Target State (Production)
- 🎯 Medallion Architecture (Bronze/Silver/Gold)
- 🎯 Multi-timeframe storage (1m to 1w)
- 🎯 10K+ concurrent WebSocket connections
- 🎯 Late data handling & backfill
- 🎯 KeyDB failover & TTL management
- 🎯 Kafka optimization (100 partitions)
- 🎯 Cloud-ready (S3 for Iceberg)
- 🎯 99.9% uptime SLA

### Gap Analysis

| Feature | Current | Target | Priority |
|---------|---------|--------|----------|
| Data Lake Structure | Raw files | Medallion (Bronze/Silver/Gold) | HIGH |
| Timeframes | 1m only | 1m, 5m, 15m, 1h, 4h, 1d, 1w | HIGH |
| WebSocket Connections | ~100 | 10,000+ | CRITICAL |
| Late Data | Dropped | Handled & backfilled | CRITICAL |
| KeyDB Failover | Manual | Automatic | CRITICAL |
| Kafka Partitions | 3 | 100 (by symbol) | HIGH |
| Storage Backend | Local disk | S3-compatible | MEDIUM |
| Caching | None | Redis cache layer | HIGH |
| Load Testing | None | 1M req/min | HIGH |

---

## 🎯 Architecture Evolution

### Current Architecture (MVP)
```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  Producer (Binance + OKX) → Kafka (3 partitions)            │
│  Dagster (News) → Kafka                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  Flink (no late data handling)                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  KeyDB: 1m candles (7d TTL)                                 │
│  InfluxDB: 1m candles (90d retention)                       │
│  Iceberg: Raw files (no structure)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVING LAYER                             │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (no caching, ~100 connections)                     │
└─────────────────────────────────────────────────────────────┘
```

### Target Architecture (Production)
```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  Producer (Binance + OKX) → Kafka (100 partitions by symbol)│
│  Dagster (News, 5min) → Kafka                               │
│  Connection Pool: 10K WebSocket connections                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PROCESSING LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  Flink (watermarks, late data handling)                     │
│    ├─ Main output → Storage                                 │
│    └─ Late data output → Backfill topic                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                              │
├─────────────────────────────────────────────────────────────┤
│  KeyDB (Sentinel HA):                                       │
│    ├─ 1s candles (1d TTL)                                   │
│    ├─ 1m candles (7d TTL)                                   │
│    └─ 5m candles (7d TTL)                                   │
│                                                              │
│  InfluxDB (90d retention):                                  │
│    ├─ 1m, 5m, 15m, 1h candles                               │
│    └─ 4h, 1d, 1w candles (downsampled)                      │
│                                                              │
│  Iceberg (S3-backed, Medallion):                            │
│    ├─ Bronze: Raw data (all sources)                        │
│    ├─ Silver: Cleaned & unified                             │
│    └─ Gold: Business metrics                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVING LAYER                             │
├─────────────────────────────────────────────────────────────┤
│  Redis Cache (hot data, top 100 symbols)                    │
│  FastAPI (connection pool, 10K connections)                 │
│  Rate Limiting (per user)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Roadmap Overview

| Phase | Focus | Duration | RAM Impact | Priority | Dependencies |
|-------|-------|----------|------------|----------|--------------|
| **Phase 1** | Medallion Architecture | 3-4 weeks | +1GB | HIGH | None |
| **Phase 2** | Multi-Timeframe Storage | 2-3 weeks | +500MB | HIGH | Phase 1 |
| **Phase 3** | Production Hardening | 3-4 weeks | +200MB | CRITICAL | Phase 2 |
| **Phase 4** | Scalability & Performance | 2-3 weeks | 0 | HIGH | Phase 3 |
| **Phase 5** | Cloud Migration Prep | 2-3 weeks | 0 | MEDIUM | Phase 4 |
| **Phase 6** | Advanced Features | 3-4 weeks | +500MB | LOW | Phase 5 |

**Total Timeline:** 15-21 weeks (4-5 months)  
**Total RAM Impact:** +2.2GB (18.8GB → 21GB, still safe for 32GB)  
**Critical Path:** Phase 1 → 2 → 3 (must complete before production)

---


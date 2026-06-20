# PostgreSQL — Auth, AI, Settings, Iceberg Catalog

PostgreSQL 16 with pgvector serves 4 distinct roles in LMView.

## Connection

- Host: `postgres` (internal), port 5432 (published)
- Image: `pgvector/pgvector:pg16`
- Database: `iceberg_catalog`
- Pool: asyncpg (lazy import, retry pool init)

## Roles

### 1. Iceberg Catalog
Stores Iceberg table metadata (files, partitions, snapshots). Spark and Trino use JDBC catalog → PostgreSQL.

### 2. Application Store (Auth, Settings, AI, News)

**Tables created by migrations:**

| Migration | Tables |
|---|---|
| `001_phase0_schema.sql` | users, sessions, preferences, ai_chat_sessions, ai_chat_messages, ai_chart_snapshots, ai_tool_actions, news_articles, ai_knowledge_docs |
| `002_phase1_readiness.sql` | Profile fields, forced password flag, JSON settings, notifications, app_settings, watchlist activity, AI columns |
| `003_phase1_ai_rag.sql` | pgvector extension, knowledge_sources, knowledge_chunks, knowledge_embeddings, HNSW index, retrieval_audit_logs |
| `004_agents_metadata.sql` | Agent execution tracking, expert runs, chart actions, news sentiment cache |

### 3. AI RAG (pgvector)

- `knowledge_chunks` table with vector embeddings (384d or 768d)
- HNSW index for approximate nearest neighbor search
- Cosine similarity retrieval
- Used by `ai_service/rag/retrieval_service.py`

### 4. Settings & Admin

- User preferences JSON field
- App-wide settings
- Admin user management

## Migration Runner

- SQL files in `backend/migrations/*.sql`
- Run at FastAPI startup when `RUN_MIGRATIONS=true`
- Ordered by filename prefix (001, 002, 003, 004)
- Idempotent: uses `IF NOT EXISTS`, `CREATE OR REPLACE`

## Key backend/core/ modules

- **postgres.py**: init_pg_pool(), close_pg_pool(), run_migration(), pg_health_check()
- **security.py**: Password hashing (bcrypt), JWT tokens, session management
- **auth_dependencies.py**: FastAPI `Depends` for auth-protected routes

## Known Issues

- **Migration order**: `004_agents_metadata.sql` and `004_phaseC_news_enhancements.sql` both use 004 prefix — potential ordering issue
- **Pool retry**: `init_pg_pool()` doesn't retry on first failure, but `get_pg_pool()` does
- **Health check**: Added in v0.25.39 to detect PostgreSQL outages

# RAG Knowledge Base — LMView

## Overview

LMView's RAG (Retrieval-Augmented Generation) system uses PostgreSQL + pgvector for vector similarity search over a curated knowledge base.

## Schema

### Tables (Migration: `003_phase1_ai_rag.sql`)

| Table | Purpose |
|-------|---------|
| `ai_knowledge_sources` | Registry of knowledge collections with metadata |
| `ai_knowledge_documents` | Individual documents (extended from Phase 0) |
| `ai_knowledge_chunks` | Text chunks with heading context |
| `ai_knowledge_embeddings` | 384-dim vectors (all-MiniLM-L6-v2) with HNSW index |
| `ai_knowledge_retrieval_logs` | Audit trail for all retrieval queries |

### Embedding Index
- Type: HNSW (Hierarchical Navigable Small World)
- Distance: Cosine
- Parameters: m=16, ef_construction=64
- Dimension: 384 (matches all-MiniLM-L6-v2)

## Knowledge Sources

| Source ID | Domain | Documents |
|-----------|--------|-----------|
| lmview-platform | platform | LMView Platform Guide |
| technical-analysis | technical_analysis | Technical Analysis Fundamentals |
| crypto-market-structure | market_structure | Cryptocurrency Market Structure |
| risk-management | risk_management | Risk Management Guide |
| bilingual-glossary | glossary | EN/VI Crypto Trading Glossary |

## Ingestion Pipeline

```
Markdown file
→ Frontmatter parsing (title, domain, language, tags)
→ Content hash computation (SHA-256 dedup)
→ Heading-aware semantic chunking (1200 chars, 200 overlap)
→ Embedding generation (sentence-transformers)
→ PostgreSQL storage (document + chunks + embeddings)
```

### Chunking Strategy
1. Split by headings (## or ###) first
2. If section > max_chunk_chars, split by paragraphs
3. If paragraph still too long, split by sentences with overlap

### Deduplication
- Content hash prevents re-ingesting unchanged documents
- Old versions archived, not deleted

## Retrieval

### Filters
- `language` — chunk language
- `domain` — document domain
- `tags` — source tags
- `source_type` — document type
- `credibility_level` — source credibility
- `review_status` — defaults to "approved"

### Return Fields
- chunk_id, text, score
- document_title, source_title
- heading, language, domain
- citation payload

### Quality Warnings
- `no_results` — no relevant chunks found
- `few_results` — fewer than 3 chunks

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/ai/knowledge/ingest` | POST | Admin | Ingest markdown files |
| `/api/ai/knowledge/search` | POST | User | Vector similarity search |
| `/api/ai/knowledge/sources` | GET | User | List knowledge sources |
| `/api/ai/knowledge/health` | GET | User | Knowledge base status |

## Adding New Knowledge

1. Create a markdown file in `docs/ai/knowledge_base/approved/`
2. Add optional YAML frontmatter (title, domain, language, source_type)
3. Register the source in `docs/ai/knowledge_base/registry.yml`
4. Call `POST /api/ai/knowledge/ingest` as admin

## File Layout
```
docs/ai/knowledge_base/
  registry.yml          — Source metadata registry
  approved/             — Production-ready documents
  draft/                — Under review
  deprecated/           — No longer used
```

# RAG Knowledge Base - LMView

## Overview

LMView uses PostgreSQL + pgvector for Retrieval-Augmented Generation (RAG). Production RAG is intentionally conservative: only human-approved sources may be ingested or retrieved.

Current bundled knowledge notes were AI-generated and do not include verified human review metadata. They were moved to `pending/`, marked `review_status: pending`, and set `allowed_for_rag: false`. Production RAG will not use them until a reviewer approves them in `registry.yml`.

## Directory Layout

```text
docs/ai/knowledge_base/
  source_library/       Raw source captures, URLs, PDFs, exported docs, and notes
  canonical/
    project/
    crypto/
    technical_analysis/
    market_microstructure/
    finance_risk/
    news_and_sentiment/
    glossary/
  approved/             Human-reviewed documents allowed for production RAG
  pending/              Awaiting review
  draft/                Work in progress
  deprecated/           Retired and excluded
  manifests/            Source manifests, import logs, review evidence
  registry.yml          Required metadata registry
```

## Registry Metadata

Each source entry in `registry.yml` must include:

| Field | Purpose |
|---|---|
| `source_id` | Stable source identifier |
| `title` | Human-readable title |
| `domain` | Domain such as `project`, `technical_analysis`, or `finance_risk` |
| `language` | Source language |
| `source_type` | System doc, glossary, technical note, external reference, etc. |
| `credibility_level` | `verified`, `reviewed`, `reference`, `ai_generated`, `draft`, or `unknown` |
| `review_status` | `approved`, `pending`, `draft`, or `deprecated` |
| `reviewer` | Human reviewer name or handle; required for approved sources |
| `reviewed_date` | Review date; required for approved sources |
| `lmview_version_scope` | LMView versions the source applies to |
| `source_urls` | Original source URLs, if any |
| `tags` | Retrieval/filter tags |
| `allowed_for_rag` | Must be `true` for production RAG |
| `file_path` | Markdown path relative to `docs/ai/knowledge_base/` |

## Approval Workflow

1. Place raw material in `source_library/` or draft notes in the matching `canonical/<domain>/` folder.
2. Create or update a `registry.yml` entry with `review_status: draft` or `pending` and `allowed_for_rag: false`.
3. Human reviewer checks accuracy, citations, LMView version scope, and source quality.
4. Move the final document to `approved/`.
5. Set `review_status: approved`, `allowed_for_rag: true`, `reviewer`, and `reviewed_date`.
6. Run admin ingestion with `POST /api/ai/knowledge/ingest`.

Documents in `pending/`, `draft/`, and `deprecated/` are excluded by default. Deprecated documents must stay `allowed_for_rag: false`.

## Source Quality Policy

Production RAG should prefer sources in this order:

1. LMView project docs reviewed for the current version.
2. Primary technical references and exchange/API documentation.
3. Human-reviewed educational finance or market-structure notes.
4. AI-generated drafts only after human review and explicit approval.

Every approved source needs enough metadata to explain where it came from, who reviewed it, when it was reviewed, and which LMView versions it applies to.

## Ingestion And Retrieval

Ingestion:

```text
Markdown file
-> registry gate: approved + allowed_for_rag
-> content hash computation
-> heading-aware chunking
-> embedding generation
-> PostgreSQL storage
```

Retrieval SQL requires:

```sql
s.review_status = 'approved'
AND s.allowed_for_rag = TRUE
```

There is no null-source bypass. If no approved source exists, production RAG returns no chunks and the AI answers from live chart/system context only.

## API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/ai/knowledge/ingest` | POST | Admin | Ingest approved markdown files |
| `/api/ai/knowledge/search` | POST | User | Vector similarity search over approved sources |
| `/api/ai/knowledge/sources` | GET | User | List knowledge sources |
| `/api/ai/knowledge/health` | GET | User | Knowledge base status |
| `/api/ai/knowledge/registry/validate` | GET | Admin | Validate registry metadata |

## Tests

Focused tests cover approved-only ingestion, approved-only retrieval, metadata validation, deprecated exclusion, registry consistency, and null-source exclusion.

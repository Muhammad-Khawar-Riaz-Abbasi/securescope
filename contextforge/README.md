# ContextForge

ContextForge is an evidence-backed incident intelligence platform for engineering teams.

It turns noisy alerts, logs, traces, runbooks, architecture notes, and past postmortems into a searchable incident workspace. During an outage, an LLM reconstructs the timeline, ranks likely causes, explains its reasoning with source citations, and proposes safe next actions.

## The problem

Incident responders lose time switching between observability tools and internal documentation. Generic chatbots can summarize text, but they cannot reliably connect a live incident to the correct service, deployment, historical failure, or operational procedure.

ContextForge is designed to answer questions such as:

- What changed shortly before checkout latency increased?
- Which previous incidents look similar, and what fixed them?
- Which runbook step is safe to execute for this service?
- What evidence supports the current root-cause hypothesis?
- What information is still missing before escalating?

## Why this is a strong backend project

The system will exercise production-oriented backend patterns:

- Multi-tenant authentication, RBAC, API keys, and audit logs
- REST API plus webhook and streaming endpoints
- Async ingestion and document-processing jobs
- Hybrid retrieval: vector search, keyword search, metadata filters, and reranking
- RAG with source-grounded answers and citation enforcement
- PostgreSQL with `pgvector` as the initial vector database
- Event-driven processing with retries, idempotency, and dead-letter handling
- Incident timelines built from ordered, time-bounded evidence
- LLM evaluation datasets, answer-quality scoring, and prompt/version tracking
- Rate limits, usage metering, structured logs, tracing, and health checks
- Docker-based local development and CI

## Planned architecture

```text
Clients / integrations
          |
          v
API gateway + auth + rate limits
          |
          +--> Incident service ------> PostgreSQL
          |
          +--> Ingestion API ---------> Job queue
                                      |
                                      v
                         Parse -> chunk -> embed -> index
                                      |
                                      v
                           PostgreSQL + pgvector
                                      |
                                      v
                         Retrieval + reranking + RAG
                                      |
                                      v
                         Cited answer / timeline / actions
```

## Initial implementation target

Build a working vertical slice that can:

1. Create an organization, project, and incident.
2. Ingest a log bundle, runbook, and postmortem document.
3. Process and index those documents asynchronously.
4. Ask an incident question through the API.
5. Return a grounded answer with citations, confidence, retrieved evidence, and an explicit uncertainty section.

## Suggested stack

- Python 3.12
- FastAPI and Pydantic
- PostgreSQL 16 with `pgvector`
- Redis-backed job queue
- OpenAI-compatible LLM and embedding interfaces
- SQLAlchemy and Alembic
- Docker Compose
- Pytest, Ruff, and mypy

The project should keep provider interfaces replaceable so the application can run with hosted models in production and local/mock models during development and testing.

## Runnable MVP

This repository now contains a vertical-slice FastAPI backend under `app/`. It provides:

- tenant and project creation, incident creation, document ingestion, and grounded incident Q&A;
- deterministic local embedding/LLM providers for repeatable tests;
- SHA-256 document deduplication, bounded input validation, request IDs, CORS configuration,
  structured errors, and an API-key authentication seam;
- SQLAlchemy async models and an Alembic migration layout. Embeddings are JSON text for
  extension-free tests and can be promoted to `vector(n)` in PostgreSQL/pgvector deployments;
- a replaceable retrieval interface (deterministic keyword fallback now, hybrid/vector retrieval
  as the production seam);
- an explicit async ingestion queue boundary ready for Redis or a worker.

Run locally:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
pytest
uvicorn app.main:app --reload
```

For PostgreSQL and Redis, copy `.env.example` to `.env`, replace both placeholder secrets,
and use `docker compose up --build`. Never put production credentials in source control.
The local Docker profile requires an API key on every protected endpoint; pass it with
`X-API-Key`. TODOs in `app/main.py` mark the tenant-scoped JWT/API-key and external job
infrastructure seams required before production.

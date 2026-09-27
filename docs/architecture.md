# Architecture

This document is the living record of architectural decisions for the
AI Knowledge Assistant. It's updated at each version checkpoint, not
rewritten from scratch — see the "Decision history" section at the
bottom for how the baseline evolved before implementation began.

## System overview

Modular monolith + separate worker process. One codebase, multiple
runtime processes (`api`, `worker`, `frontend`) — not microservices.

```text
Next.js (frontend) → FastAPI (api) → PostgreSQL (+ pgvector)
                            │              └─ system of record + vectors
                            ├─→ Redis  → Worker process
                            └─→ S3-compatible object storage (MinIO locally)
```

## Locked technology decisions

| Layer              | Choice                                    |
| ------------------ | ------------------------------------------ |
| Frontend            | Next.js 16 + TypeScript, App Router        |
| Backend             | FastAPI + Python 3.12                      |
| API schemas         | Pydantic v2                                |
| Database            | PostgreSQL 16 (via `pgvector/pgvector:pg16`) |
| Vector store         | pgvector                                   |
| Lexical retrieval    | PostgreSQL full-text search                |
| Hybrid fusion         | Reciprocal Rank Fusion (RRF)               |
| Reranking            | Existing cross-encoder approach            |
| Embeddings           | Qwen3-Embedding-0.6B, 1024 dimensions, local |
| LLM                  | API provider, behind an interface          |
| Object storage        | S3-compatible; MinIO for local dev         |
| Background jobs       | Redis + worker process                     |
| ORM                  | SQLAlchemy 2                                |
| Migrations            | Alembic                                    |
| Testing              | pytest (backend), tsc/eslint (frontend)    |
| Containers           | Docker Compose                             |
| CI                    | GitHub Actions                             |
| Observability          | Structured JSON logging + metrics/traces later |
| Auth                  | Application-managed (email + password)     |
| Tenancy                | user → collection isolation, enforced server-side |

## Embedding provider contract (locked at Stage 0 refinement)

Documents and queries are **not interchangeable embedding inputs.**
Qwen3-Embedding-0.6B is instruction-aware: queries carry a task
instruction prefix, documents do not. The `EmbeddingProvider` interface
(introduced in v0.4) therefore exposes two distinct methods rather than
one generic `embed(text)`:

```text
EmbeddingProvider
├── embed_document(text)
└── embed_query(text, instruction)
```

The worker owns document embedding (ingestion time); query-time RAG
orchestration owns query embedding. CPU-only local inference is
supported initially; ingestion throughput on a development machine is
an explicitly documented limitation, not a bug.

## Chunking parameters

Chunk size (~400–700 tokens, ~50–100 token overlap) is treated as an
**evaluation parameter**, not an architectural constant — see
`evals/`. It is deliberately decoupled from the embedding model's 32K
token context ceiling; that ceiling has no bearing on retrieval chunk
granularity.

## Lexical retrieval: BM25Okapi → PostgreSQL FTS

The prototype used BM25Okapi + FAISS. The production application uses
PostgreSQL full-text search + pgvector to reduce infrastructure
complexity and unify persistence under one transactional boundary.
**Retrieval quality is validated empirically** (v0.4 benchmark: BM25Okapi
vs. PostgreSQL FTS on the same evaluation corpus) rather than assumed
equivalent. If PostgreSQL FTS materially degrades retrieval, a
dedicated lexical search engine becomes an evidence-driven addition,
not a default.

## Citation provenance

Citations carry three levels of granularity: source identity
(document → chunk), location (page number), and exact evidence
(character span within a canonical, normalized chunk representation —
not raw parser output, since cleaning/normalization can shift text
positions).

## Why not X

- **Separate vector DB (Pinecone/Weaviate/Qdrant):** would introduce a
  second database to keep in sync with Postgres (deletion consistency,
  retry semantics, credentials, deployment) without a workload that
  actually requires it at this scale.
- **Microservices:** architecture theatre at this project's scope. A
  modular monolith with a separate worker process gives the same
  process-isolation benefits (independent scaling of ingestion vs. API)
  without the operational overhead of N services.
- **LangChain/LlamaIndex:** not introduced merely because this is a RAG
  application. Explicit application-level orchestration keeps ownership
  boundaries, retrieval behavior, evaluation, error handling, citations,
  and observability easier to reason about. A framework can be
  introduced later if a concrete abstraction justifies it.

## Decision history

- **Stage 0 (initial):** Product boundary, architecture, tech stack,
  database model, security model, and versioned roadmap agreed.
- **Stage 0 (refinement):** Embedding model locked to
  Qwen3-Embedding-0.6B (1024-dim); chunking parameters deferred to
  evaluation; BM25→FTS reframed as an evaluated tradeoff rather than an
  assumption; citation schema extended with character-span granularity;
  evaluation moved from v0.8 to start at v0.4 (retrieval baseline).
- **v0.1 (this version):** Runtime skeleton established. No domain
  models, auth, ingestion, or RAG code yet — those begin in v0.2+.
- **v0.1 remediation:** an independent review (never having run against
  a real Docker daemon) found that `backend` was health-gated on
  `redis`/`minio` despite not consuming either yet, and that the MinIO
  healthcheck's `curl` dependency doesn't exist in current MinIO images
  — together these would have prevented `docker compose up` from
  succeeding. Fixed by removing the unused gating (a service should
  only depend on infrastructure it actually consumes; Redis/MinIO
  dependencies return in v0.3 when the worker needs them). Also: split
  `requirements.txt`/`requirements-dev.txt` so the runtime image no
  longer ships pytest/ruff/mypy; replaced the readiness test's
  `status_code in (200, 503)` assertion (which could not fail on a real
  regression) with two deterministic tests using FastAPI dependency
  overrides; made `db/session.py`'s engine/sessionmaker construction
  lazy and cached (mirroring `get_settings`) instead of an import-time
  side effect; added a CI job that builds both Docker images; and fixed
  `frontend/Dockerfile`, which was missing `package-lock.json` in its
  build context and used `npm install` instead of `npm ci` — meaning
  the container build could silently resolve different dependency
  versions than the ones CI validates.
- **v0.2 (Identity + Tenancy):** added `users`/`collections` tables and
  the auth/collections vertical slices (`app/auth/`,
  `app/collections/`), following the vertical-slice layout from the
  original Stage-0 plan rather than a generic api/schemas/services
  split. Key decisions made explicit here rather than left implicit:
  - **Token strategy:** short-lived JWT access token in an HttpOnly,
    `SameSite=Lax` cookie (`auth_cookie_secure` is env-driven — false
    for local HTTP dev, must be true wherever served over HTTPS). No
    refresh-token rotation and no revocation mechanism in v0.2 —
    tokens simply expire (`access_token_expire_minutes`) and the user
    re-logs in; logout only clears the cookie client-side, it does not
    revoke the JWT (a captured token would remain valid until natural
    expiry — see `test_logout_clears_auth_cookie`). Refresh/revocation
    are v0.7-hardening scope, not v0.2.
  - **Password hashing:** Argon2id via `argon2-cffi`, library defaults
    (OWASP's current recommendation), no manual cost tuning.
  - **Anti-enumeration:** `login` returns the identical 401 status and
    message for "no such email" and "wrong password", and always runs
    a real Argon2 verification (against a dummy hash when no user is
    found) so the two cases aren't distinguishable by response timing
    either.
  - **Cross-tenant access is 404, not 403.** A 403 would itself leak
    that a given id belongs to *someone*, letting an attacker enumerate
    valid ids by probing for 403-vs-404. Every single-resource query
    filters by `owner_id == current_user.id` in the same database
    query that filters by `id` — never "fetch by id, then check
    ownership in application code."
  - **Indexing:** a single index on `collections.owner_id`, not a
    composite `(owner_id, id)`. `id` is already the primary key
    (already indexed); the owner_id index covers the "list my
    collections" query pattern, and the point-lookup pattern
    (`owner_id = x AND id = y`) is already efficient via the PK.
  - Verified against a real (non-Docker, locally installed) PostgreSQL
    instance: migration generated via `alembic revision --autogenerate`,
    applied, downgraded, and re-applied cleanly; full auth + tenant
    isolation flow (register, login, generic-failure login, cross-tenant
    404s in both directions, anonymous 401, list scoping, logout
    clearing the auth cookie) exercised end-to-end with curl before the
    automated test suite was written, then codified as 25 passing
    pytest cases.
  - **Not yet fixed, deliberately:** `User.email` uniqueness is
    DB-enforced but unnormalized — `User@example.com` and
    `user@example.com` are currently distinct accounts. An explicit
    normalization policy (strip + lowercase before persistence) is a
    product/security decision to make once, not something to introduce
    silently mid-checkpoint — revisit before v1.0.
- **v0.2 terminology cleanup:** removed the one remaining permissive
  test (`status_code in (200, 503)`) from `test_health.py`; corrected
  `test_logout_invalidates_session` — renamed to
  `test_logout_clears_auth_cookie` — since logout clears the cookie but
  does not revoke the JWT (a captured token stays valid until natural
  expiry; no revocation mechanism exists in v0.2 by design); replaced
  "session cookie" with "JWT access token in an HttpOnly cookie"
  wherever the two were being used interchangeably. No behavior changed.
- **v0.2 real Docker run** surfaced what local-Postgres verification
  couldn't: (1) `backend` had no `healthcheck`, so `docker compose ps`
  reported `Up` even when the uvicorn worker had crashed on startup —
  the reload supervisor process stayed alive while the actual server
  process died, and Compose had no way to tell the difference. Fixed
  by adding a `healthcheck` that hits `/health/live` (not `/health/ready`
  — this check is about "is the process serving," not "is the DB
  reachable," and conflating the two would make an unrelated DB blip
  look like a dead app). Uses `python -c` with `urllib.request`, not
  `curl` — `python:3.12-slim` doesn't reliably ship curl either, same
  category of mistake as the MinIO healthcheck earlier, not repeating
  it. `frontend`'s `depends_on` on `backend` was upgraded from a bare
  dependency to `condition: service_healthy` now that the healthcheck
  makes that condition meaningful. (2) An existing `.env` predating
  v0.2 lacked the new required `SECRET_KEY`, crashing the worker on
  boot — not a code bug (the required-field-with-no-default design is
  intentional), but a real operational gap since `.env` is gitignored
  and nothing updates a person's existing copy when `.env.example`
  gains new variables. Documented in README with the exact symptom and
  fix rather than reintroducing a default value, which would undo the
  deliberate v0.2 security decision.

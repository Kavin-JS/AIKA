# AI Knowledge Assistant

A production-oriented, multi-tenant RAG knowledge platform: create
isolated knowledge collections, ingest documents, ask questions against
those sources, and get grounded answers with traceable citations.

**Status:** v0.2 — Identity + Tenancy. Auth (register/login/me) and
owned collections with enforced tenant isolation are live. No document
ingestion or RAG yet; see `docs/architecture.md` for the full roadmap.

**Verification note:** v0.2 has now been run through a real
`docker compose up`, not just the local-Postgres verification described
below. That run surfaced two real gaps, both now fixed: (1) the
`backend` service had no `healthcheck`, so a crashed uvicorn worker
still showed as `Up` in `docker compose ps` — the one thing that's
supposed to tell you a service is actually working; and (2) an existing
`.env` predating v0.2's new required `SECRET_KEY` caused exactly that
crash. See "If you already have a `.env` from before v0.2" below for
the fix, and `docs/architecture.md` for the healthcheck/`depends_on`
change.

## Architecture

Modular monolith + separate worker process (not microservices):
Next.js frontend → FastAPI backend → PostgreSQL (+pgvector) as the
single system of record, Redis-backed worker for async ingestion,
S3-compatible object storage for original files.

Full rationale and the locked technology decisions: [`docs/architecture.md`](docs/architecture.md).

## Local setup

Requires Docker and Docker Compose.

```bash
cp .env.example .env
docker compose up
```

**If you already have a `.env` from before v0.2:** `.env` is
gitignored, so it's never updated automatically when `.env.example`
gains new variables. v0.2 added a *required* `SECRET_KEY` (no default —
the app won't boot without one, by design; see `docs/architecture.md`).
An existing `.env` missing it will make the `backend` container's
uvicorn worker crash on startup while the container itself keeps
running — `docker compose ps` alone won't show this (see the backend
`healthcheck` in `docker-compose.yml`, added specifically because
`docker compose ps` reporting "Up" was not sufficient to prove the app
was actually serving requests). If `backend` shows `unhealthy`, check
`docker compose logs backend` first — a missing `SECRET_KEY` shows up
there as a clear pydantic `ValidationError`. Fix: diff your `.env`
against `.env.example` and add whatever's missing, most likely:

```bash
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env
```

This starts: `postgres`, `redis`, `minio`, `backend` (FastAPI on
`:8000`), `frontend` (Next.js on `:3000`).

Then, in another terminal, run migrations:

```bash
docker compose exec backend alembic upgrade head
```

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health/live and `/health/ready`
- Backend docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

## Running backend checks locally (without Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # installs requirements.txt too
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ruff check .
mypy app
pytest -q
```

## Running frontend checks locally (without Docker)

```bash
cd frontend
npm install
npx eslint .
npx tsc --noEmit
npm run build
```

## API overview (v0.2)

```text
POST   /api/v1/auth/register    → 201, creates a user
POST   /api/v1/auth/login       → 200, sets a JWT access token in an HttpOnly cookie
POST   /api/v1/auth/logout      → 204, clears the authentication cookie
                                    (does not revoke the JWT itself — see docs/architecture.md)
GET    /api/v1/auth/me          → 200 authenticated / 401 anonymous

POST   /api/v1/collections          → 201, create (owned by caller)
GET    /api/v1/collections          → 200, list caller's own collections
GET    /api/v1/collections/{id}     → 200 own / 404 anyone else's or nonexistent
PATCH  /api/v1/collections/{id}     → 200 own / 404 anyone else's or nonexistent
DELETE /api/v1/collections/{id}     → 204 own / 404 anyone else's or nonexistent
```

Cross-tenant access always returns **404**, not 403 — see
`docs/architecture.md` for why.

## Environment variables

See [`.env.example`](.env.example) for the full list. `.env` is
gitignored — never commit real secrets.

## Repository layout

```text
ai-knowledge-assistant/
├── backend/    # FastAPI application, Alembic migrations, tests
├── frontend/   # Next.js application
├── evals/      # Evaluation harness (populated starting v0.3/v0.4)
├── docs/       # Architecture decision record
├── docker-compose.yml
└── .env.example
```

## Roadmap

v0.1 (this checkpoint) → v0.2 identity/tenancy → v0.3 document
lifecycle → v0.4 retrieval + evaluation baseline → v0.5 grounded QA →
v0.6 conversations/UI → v0.7 hardening → v0.8 evaluation → v1.0.
Full detail in `docs/architecture.md`.

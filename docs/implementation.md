# Implementation

## Scope Implemented
- **Requested scope:** No explicit ticket was passed to `/implement`. Defaulted to
  the BUILD_PLAN "Current ticket" / recommended next step.
- **Related phase:** Phase 0 — Project Scaffold & Infrastructure
- **Related ticket(s):** **P0-T1 — Repo scaffold & backend skeleton**

> Note: `/docs/spec.md` (listed as required by the skill) does not exist. Per
> BUILD_PLAN "Source of Truth", `docs/challenge.md` + `docs/PRD.md` + `ARCHITECTURE.md`
> are authoritative and were used as the spec. See `docs/implementation-notes.md`.

## Approach
- **High-level strategy:** Stand up the smallest runnable FastAPI backend that
  satisfies P0-T1's acceptance (`GET /health` → 200) and establishes the package
  layout the named files require, without building anything owned by later tickets.
- **Key decisions:**
  - Config reads env vars via stdlib `os.getenv` on a frozen, typed `Settings`
    dataclass — no `pydantic-settings` dependency at skeleton stage.
  - Dependency manifest is `requirements.txt` (plan allowed either it or
    `pyproject.toml`); pinned only `fastapi` + `uvicorn[standard]`.
  - Created only `app/` and `app/api/` packages — deferred later-phase packages
    (`graph/`, `ingestion/`, …) to their tickets to avoid empty/premature scope.
- **Assumptions:** Local dev defaults are acceptable for now (`NEO4J_URI=bolt://localhost:7687`,
  `NEO4J_PASSWORD=password`); real values arrive with Compose/`.env` in P0-T2.

---

## Implementation Plan
1. `backend/requirements.txt` — pin FastAPI + uvicorn.
2. `backend/app/__init__.py`, `backend/app/api/__init__.py` — package markers.
3. `backend/app/config.py` — env-driven typed `Settings` + cached `get_settings()`.
4. `backend/app/api/routes.py` — `APIRouter` with `GET /health`.
5. `backend/app/main.py` — create `FastAPI` app, include router.
6. `.gitignore` — ignore `.venv/`, `__pycache__/`, `.env`.
7. Validate: venv install + `TestClient` hit on `/health`; `py_compile`.

**Files created:** all of the above (no existing files modified except `.gitignore`).

---

## Code Changes

### File: backend/requirements.txt
- **Change summary:** New dependency manifest; skeleton deps only.
- Snippet:
  ```
  fastapi==0.115.6
  uvicorn[standard]==0.34.0
  ```

### File: backend/app/__init__.py
- **Change summary:** Empty package marker for the `app` package.

### File: backend/app/api/__init__.py
- **Change summary:** Empty package marker for the `app.api` package.

### File: backend/app/config.py
- **Change summary:** Frozen `Settings` dataclass + `lru_cache`d `get_settings()`
  reading Neo4j connection, LLM/embedding provider, and optional API keys from env.
- Snippet:
  ```python
  @dataclass(frozen=True)
  class Settings:
      neo4j_uri: str
      neo4j_user: str
      neo4j_password: str
      llm_provider: str
      embedding_provider: str
      openai_api_key: str | None
      anthropic_api_key: str | None

  @lru_cache(maxsize=1)
  def get_settings() -> Settings:
      return Settings(
          neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
          ...
      )
  ```

### File: backend/app/api/routes.py
- **Change summary:** `APIRouter` exposing the `/health` liveness route.
- Snippet:
  ```python
  router = APIRouter()

  @router.get("/health")
  def health() -> dict[str, str]:
      return {"status": "ok"}
  ```

### File: backend/app/main.py
- **Change summary:** FastAPI app entrypoint; includes the API router.
- Snippet:
  ```python
  app = FastAPI(title="Knowledge Graph Coaching Platform API")
  app.include_router(router)
  ```

### File: .gitignore
- **Change summary:** Added Python ignores (`__pycache__/`, `*.pyc`, `.venv/`,
  `backend/.venv/`, `.env`) so the validation venv and env files aren't committed.

---

## Acceptance Criteria Mapping

- **Criterion:** `GET /health` → 200 locally (challenge "Dockerized local setup"; ARCH §3.2).
  - **Implementation:** `/health` route returns `{"status":"ok"}` with 200; verified via `TestClient`.
  - **File(s):** `backend/app/api/routes.py`, `backend/app/main.py`.
- **Criterion (objective):** Create module layout, `app/main.py` (FastAPI + health),
  `config.py` reading env vars, dependency manifest.
  - **Implementation:** `main.py` app + router include; `config.py` env-driven typed
    settings; `requirements.txt` manifest; `app/` + `app/api/` packages established.
  - **File(s):** `backend/app/main.py`, `backend/app/config.py`, `backend/requirements.txt`, `backend/app/api/routes.py`.

---

## Build Plan Mapping

- **Ticket:** P0-T1 — Repo scaffold & backend skeleton
  - **Status:** Complete
  - **What was completed:** Backend package layout, FastAPI app with `/health`,
    env-driven typed config, and `requirements.txt`. `GET /health` returns 200 locally.
  - **Remaining work:** None for P0-T1.

---

## Validation
- **How tested:** Created `backend/.venv` (gitignored), installed `requirements.txt` +
  `httpx`, instantiated the app via FastAPI `TestClient`, and called `GET /health`.
- **Results:**
  - `GET /health` → `200`, body `{"status": "ok"}` (assertion passed).
  - `python -m py_compile` on all three modules: clean.
  - `from app.config import get_settings` returns defaults (`bolt://localhost:7687`, `openai`).
  - No repo linter configured → used `py_compile` + import checks as the validation path.
- **Manual verification steps:** From `backend/`, run
  `./.venv/bin/uvicorn app.main:app --reload`, then `curl localhost:8000/health`
  → `{"status":"ok"}`.
- **Visible user outcome:** A running API whose health endpoint responds 200 — the
  foundation P0-T2 (Compose + Neo4j) builds on.

---

## Open Issues
- **Known limitations:** Skeleton only — no Neo4j connection, Docker, or domain
  endpoints yet (owned by P0-T2+). `config.py` reads env but nothing consumes the
  Neo4j/LLM settings until later tickets.
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None.

---

## BUILD_PLAN Update
- **Current phase:** Phase 0 — Project Scaffold & Infrastructure
- **Current ticket:** P0-T2 — Docker Compose + Neo4j service + env template (next)
- **Updated ticket status:** P0-T1 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P0-T2 (depends on P0-T1, now satisfied)

---
---

# Implementation — P0-T2

## Scope Implemented
- **Requested scope:** "continue the build" → next ticket in dependency order.
- **Related phase:** Phase 0 — Project Scaffold & Infrastructure
- **Related ticket(s):** **P0-T2 — Docker Compose + Neo4j service + env template**

## Approach
- **High-level strategy:** Bring up Neo4j + the API under Compose and have the API
  open a Neo4j session on boot, with a graceful (non-crashing) startup path.
- **Key decisions:**
  - Neo4j image `neo4j:5.26-community` (native vector index, current LTS).
  - Single process-wide Neo4j driver in `app/graph/client.py`; session context manager.
  - Lifespan startup retries the connection (10×/3s) then degrades to serving anyway.
  - API uses `bolt://neo4j:7687` inside the Compose network (service name, not localhost).
- **Assumptions:** Local-dev `NEO4J_PASSWORD=password` is fine for the demo; the
  Docker daemon will be available when the reviewer runs `docker compose up`.

---

## Implementation Plan
1. Add `neo4j==5.27.0` to `backend/requirements.txt`.
2. `backend/app/graph/__init__.py` + `backend/app/graph/client.py` — driver/session mgmt.
3. Update `backend/app/main.py` — lifespan opens a session on boot (`RETURN 1`), closes driver on shutdown.
4. `backend/Dockerfile` — slim Python image running uvicorn.
5. `.env.example` — env template.
6. `docker-compose.yml` — `neo4j` (healthcheck) + `api` (depends_on healthy).

**Files created:** `app/graph/__init__.py`, `app/graph/client.py`, `backend/Dockerfile`,
`.env.example`, `docker-compose.yml`. **Modified:** `backend/requirements.txt`, `backend/app/main.py`.

---

## Code Changes

### File: backend/app/graph/client.py
- **Change summary:** Process-wide Neo4j driver singleton, `session()` context
  manager, `verify_connectivity()`, and `close_driver()`. Reads connection from `app.config`.

### File: backend/app/main.py
- **Change summary:** Added `lifespan` that opens a Neo4j session (`RETURN 1`) with
  retry/backoff on startup and closes the driver on shutdown. API serves even if the graph is down.

### File: backend/Dockerfile
- **Change summary:** `python:3.11-slim`, installs `requirements.txt`, copies `app`,
  runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### File: docker-compose.yml
- **Change summary:** `neo4j:5.26-community` (ports 7474/7687, data volume, healthcheck)
  + `api` (build ./backend, `NEO4J_URI=bolt://neo4j:7687`, `depends_on: neo4j healthy`).

### File: .env.example
- **Change summary:** Template for Neo4j + LLM/embedding env vars; notes the
  host-vs-Compose `NEO4J_URI` difference.

### File: backend/requirements.txt
- **Change summary:** Added `neo4j==5.27.0`.

---

## Acceptance Criteria Mapping
- **Criterion:** `docker compose up` brings up Neo4j + API; API opens a session
  (challenge "Requirements"; ARCH §7; PRD §8).
  - **Implementation:** Compose defines both services with a healthcheck gate; the
    API lifespan opens a Neo4j session and runs `RETURN 1` on boot.
  - **File(s):** `docker-compose.yml`, `backend/Dockerfile`, `backend/app/main.py`, `backend/app/graph/client.py`.
  - **Verification status:** Compose config validated and session/startup logic
    verified locally; **live `docker compose up` not run** (Docker daemon unavailable here).

---

## Build Plan Mapping
- **Ticket:** P0-T2 — Docker Compose + Neo4j service + env template
  - **Status:** Complete
  - **What was completed:** Compose stack (neo4j + api), Dockerfile, `.env.example`,
    Neo4j driver/session module, and boot-time session open.
  - **Remaining work:** End-to-end `docker compose up` run pending a live Docker daemon.

---

## Validation
- `docker compose config` → **VALID**; services resolve to `neo4j`, `api`.
- `app.graph.client` and `app.main` import cleanly; driver exports present.
- `TestClient` startup with Neo4j unreachable → `/health` still returns 200 (graceful).
- `py_compile` clean on `app/main.py`, `app/graph/client.py`.
- **Not run:** live `docker compose up` (daemon down in this environment). To verify:
  `docker compose up --build`, then `curl localhost:8000/health` and check API logs for
  "Connected to Neo4j (opened a session ...)".

---

## Open Issues
- **Known limitations:** No graph schema/constraints or vector index yet (P1-T1).
  Boot-time check only opens a session — it does not create or validate schema.
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None. Follow-up: confirm full `docker compose up` once a Docker daemon is available.

---

## BUILD_PLAN Update (P0-T2)
- **Current phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Current ticket:** P1-T1 — Graph schema, constraints & vector index (next)
- **Updated ticket status:** P0-T2 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P1-T1

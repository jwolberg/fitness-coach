# Implementation Notes

Running log of decisions/deviations/tradeoffs during the build. For human review.

## 2026-06-02 — P0-T1 (Repo scaffold & backend skeleton)

- **`/docs/spec.md` is absent.** The `/implement` skill lists it as required, but it
  does not exist in the repo. BUILD_PLAN §"Source of Truth" names `docs/challenge.md`
  + `docs/PRD.md` + `ARCHITECTURE.md` as the authoritative inputs, so I used those
  as the spec equivalents. No scope was inferred beyond P0-T1.
- **Scope chosen:** No ticket was named in the invocation, so I implemented the
  BUILD_PLAN "Current ticket" = **P0-T1** (also the recommended next step).
- **Config uses stdlib `os.getenv`, not `pydantic-settings`.** Avoids adding a
  dependency at skeleton stage. Settings are still typed on a frozen dataclass
  (`app/config.py`), honoring ARCHITECTURE §4 "typed contracts." Reversible — can
  swap to `pydantic-settings` later if env validation grows.
- **Dependency manifest = `requirements.txt`** (not `pyproject.toml`). Plan allows
  either; requirements.txt is the simplest for the Dockerfile in P0-T2. Pinned only
  `fastapi` + `uvicorn[standard]` for now; later tickets add `neo4j`, `langgraph`, etc.
- **Module layout:** created only the packages needed for P0-T1's named files
  (`app/`, `app/api/`). Did NOT pre-create empty packages for later phases
  (`graph/`, `ingestion/`, `retrieval/`, …) to avoid premature/empty scope; they
  land with their tickets.
- **Default `NEO4J_PASSWORD=password`** as a local dev default; the real value comes
  from `.env`/Compose in P0-T2. Documented here so it is not mistaken for a secret.
- **Validation:** created `backend/.venv` (gitignored) to run the app; verified
  `GET /health` → 200 `{"status":"ok"}` via FastAPI `TestClient`. No repo linter
  configured, so ran `py_compile` + import checks instead.

## 2026-06-02 — P0-T2 (Docker Compose + Neo4j service + env template)

- **Neo4j image: `neo4j:5.26-community`.** 5.x ships the native vector index the
  retriever needs (ARCHITECTURE §3.7); 5.26 is the current LTS line. Community
  edition is sufficient for the demo.
- **Neo4j driver pinned `neo4j==5.27.0`** added to `requirements.txt`.
- **API connects to Neo4j by service name inside Compose.** `.env.example` defaults
  `NEO4J_URI=bolt://localhost:7687` (for running the API on the host), but the `api`
  service overrides it to `bolt://neo4j:7687` since localhost won't resolve the DB
  across containers. Documented inline in both files.
- **Graceful startup, not fail-fast.** `app/main.py` lifespan opens a session and
  runs `RETURN 1`, retrying up to 10×/3s. If Neo4j stays unreachable it logs an
  error and the API still serves (so `/health` works for liveness). Under Compose,
  `depends_on: condition: service_healthy` means the DB is already up, so retries
  are just a safety net. Tradeoff: worst-case ~30s startup wait if the DB never
  comes up — acceptable for a demo and avoids a crash loop.
- **Single driver per process** in `app/graph/client.py` (module-level singleton +
  session context manager + `close_driver` on shutdown). This is the only place
  that constructs the driver; later tickets build schema/queries on top.
- **`.gitignore` already covered `.env`** (added in P0-T1), so real env values won't
  be committed; only `.env.example` is tracked.
- **Validation limit:** the Docker daemon was not running in this environment, so a
  live `docker compose up` could not be executed. Validated `docker compose config`
  (VALID; resolves `neo4j` + `api`), import-checked the driver + app, and confirmed
  `/health` → 200 with the graph unreachable. **`docker compose up` itself is
  unverified end-to-end** — should be run once the daemon is available.

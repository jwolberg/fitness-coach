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

---
---

# Implementation — P1-T1

## Scope Implemented
- **Requested scope:** "continue the build" → next ticket in dependency order.
- **Related phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Related ticket(s):** **P1-T1 — Graph schema, constraints & vector index**

## Approach
- **High-level strategy:** Make every PRD §7.1 node/edge type representable and
  create uniqueness constraints + a native vector index, idempotently.
- **Key decisions:**
  - One uniqueness constraint per node label (16); `id` for context nodes, `name`
    for ontology nodes (Joint/MuscleGroup/MovementPattern/Equipment).
  - Single vector index over a shared `:Embeddable` label (cosine), so one index
    spans signals/injuries/goals/exercises.
  - Configurable embedding width (`EMBEDDING_DIM`, default 384).
  - Pure statement builders + idempotent (`IF NOT EXISTS`) execution.
- **Assumptions:** Local embedding model (384 dims) is the default; the embedder
  (P2-T1) must match `EMBEDDING_DIM`.

---

## Implementation Plan
1. Add `embedding_dim` to `app/config.py` + `EMBEDDING_DIM` to `.env.example`.
2. `app/graph/schema.py` — `NODE_KEYS`, `EDGE_TYPES`, `constraint_statements()`,
   `vector_index_statement()`, `apply_schema()`.
3. Wire `apply_schema()` into `app/main.py` startup (idempotent, after connect).

**Files created:** `app/graph/schema.py`. **Modified:** `app/config.py`,
`.env.example`, `app/main.py`.

---

## Code Changes

### File: backend/app/graph/schema.py
- **Change summary:** Node/edge inventory + idempotent constraint and vector-index
  Cypher builders + `apply_schema()`. 16 uniqueness constraints; one `:Embeddable`
  cosine vector index named `embeddable_embedding`.

### File: backend/app/main.py
- **Change summary:** Startup lifespan now calls `apply_schema()` after a successful
  Neo4j connection (schema failure logged, not fatal).

### File: backend/app/config.py
- **Change summary:** Added `embedding_dim` (env `EMBEDDING_DIM`, default 384).

### File: .env.example
- **Change summary:** Documented `EMBEDDING_DIM`.

---

## Acceptance Criteria Mapping
- **Criterion:** All PRD §7.1 node/edge types representable; constraints + vector
  index created idempotently (PRD §7.1; ARCH §3.7, §4).
  - **Implementation:** `NODE_KEYS` covers all 16 labels (constraints), `EDGE_TYPES`
    documents all 14 edges (schemaless in Neo4j), and `vector_index_statement` creates
    the cosine index — all with `IF NOT EXISTS`.
  - **File(s):** `backend/app/graph/schema.py`.
  - **Verification status:** Builders validated (16 idempotent constraints + well-formed
    vector index, dim 384); **live execution against Neo4j pending a Docker daemon**.

---

## Build Plan Mapping
- **Ticket:** P1-T1 — Graph schema, constraints & vector index
  - **Status:** Complete
  - **What was completed:** Schema module with idempotent constraints + vector index,
    embedding-dim config, and boot-time `apply_schema()` wiring.
  - **Remaining work:** Live verification once `docker compose up` can run.

---

## Validation
- `constraint_statements()` → 16 statements, all `IF NOT EXISTS` + `IS UNIQUE`;
  spot-checked `Joint.name` and `Member.id`.
- `vector_index_statement(384)` → well-formed `:Embeddable.embedding` cosine index.
- `EDGE_TYPES` → 14 (matches PRD §7.1). `apply_schema` callable.
- `py_compile` clean; app still boots and serves `/health` 200 (schema apply skipped
  gracefully when Neo4j is down).
- **Not run:** live `apply_schema()` against Neo4j (daemon down). Verify with
  `docker compose up` then check `SHOW CONSTRAINTS` / `SHOW INDEXES` in Neo4j Browser.

---

## Open Issues
- **Known limitations:** Constraints/index unexecuted against a live DB in this env.
  Nodes don't yet get the `:Embeddable` label or `embedding` property — that's P2-T1.
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None. Follow-up: live schema verification under Docker.

---

## BUILD_PLAN Update (P1-T1)
- **Current phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Current ticket:** P1-T2 — Exercise ingestion from `exercises.json` (next)
- **Updated ticket status:** P1-T1 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P1-T2

> **Live validation update:** the Docker daemon later became available, so P0-T2,
> P1-T1, and P1-T2 were verified end-to-end against a real Neo4j (see the P1-T2
> Validation section and implementation-notes). The earlier "pending Docker daemon"
> caveats for P0-T2/P1-T1 are now resolved.

---
---

# Implementation — P1-T2

## Scope Implemented
- **Requested scope:** "continue the build" → next ticket in dependency order.
- **Related phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Related ticket(s):** **P1-T2 — Exercise ingestion from `exercises.json`**

## Approach
- **High-level strategy:** Upsert each exercise as a node and link it to Joint /
  MuscleGroup / Equipment / MovementPattern; link bilateral pairs only when both
  sides exist. All MERGE-based for idempotency.
- **Key decisions:**
  - `FOREACH` over each list builds ontology nodes + edges and tolerates empty lists.
  - `HAS_BILATERAL_PAIR` created only when the target exercise is present (no stub
    nodes); `bilateral_pair_id` preserved as a node property regardless.
  - Exercises tagged `:Embeddable` now (embedding vector written in P2-T1).
  - Pure `load_exercises` / `exercise_params` separated from graph writes for testability.
- **Assumptions:** `exercises.json` at repo root by default; overridable via
  `EXERCISES_PATH` (used by the container seed step in P5-T3).

---

## Implementation Plan
1. `app/ingestion/__init__.py` + `app/ingestion/exercises.py`.
2. Pure loaders (`load_exercises`, `exercise_params`) + `ingest_exercises()` writer.
3. Validate pure parts offline; then validate writes against live Neo4j.

**Files created:** `app/ingestion/__init__.py`, `app/ingestion/exercises.py`.

---

## Code Changes

### File: backend/app/ingestion/exercises.py
- **Change summary:** Loads `exercises.json` and upserts `Exercise` nodes (+`:Embeddable`)
  with `LOADS_JOINT`/`TRAINS_MUSCLE`/`USES_EQUIPMENT`/`HAS_MOVEMENT_PATTERN` edges via
  MERGE+FOREACH; second pass links `HAS_BILATERAL_PAIR` for in-library pairs only.
  Returns the count ingested.

### File: backend/app/ingestion/__init__.py
- **Change summary:** Package marker.

---

## Acceptance Criteria Mapping
- **Criterion:** 50 exercises ingested with LOADS_JOINT/TRAINS_MUSCLE/USES_EQUIPMENT/
  HAS_MOVEMENT_PATTERN edges; re-run idempotent (PRD §7.2, §9 steps 1–4).
  - **Implementation:** `ingest_exercises()` → 50 nodes + edges; MERGE makes re-runs no-ops.
  - **File(s):** `backend/app/ingestion/exercises.py`.
  - **Verification status:** **Verified live** against Neo4j (counts below).

---

## Build Plan Mapping
- **Ticket:** P1-T2 — Exercise ingestion from `exercises.json`
  - **Status:** Complete
  - **What was completed:** Exercise + ontology node/edge ingestion, idempotent,
    verified against a live database.
  - **Remaining work:** None.

---

## Validation
- **Offline:** `load_exercises()` → 50 records; `exercise_params()` well-formed for all
  (lists never None); 0 bilateral pairs resolve within the set; `py_compile` clean.
- **Live (Docker daemon available):** brought up `neo4j` + `api` via Compose; ran
  `apply_schema()` + `ingest_exercises()` twice. Results:
  - Exercise: **50** (all `:Embeddable`); Joint 9, MuscleGroup 19, Equipment 32, MovementPattern 36.
  - Edges: LOADS_JOINT 124, TRAINS_MUSCLE 120, USES_EQUIPMENT 67, HAS_MOVEMENT_PATTERN 93, HAS_BILATERAL_PAIR 0.
  - Counts unchanged after the second run → **idempotent**.
  - `SHOW CONSTRAINTS` = 16; VECTOR indexes = 1.
  - `GET /health` (api container) → 200; logs confirm boot-time connect + schema apply.

---

## Open Issues
- **Known limitations:** No `HAS_BILATERAL_PAIR` edges for this dataset (no pair IDs
  resolve within the 50) — by design, not a bug. Embeddings not written yet (P2-T1).
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None.

---

## BUILD_PLAN Update (P1-T2)
- **Current phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Current ticket:** P1-T3 — Synthetic member data + profile ingestion (Maya) (next)
- **Updated ticket status:** P1-T2 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P1-T3

---
---

# Implementation — P1-T3

## Scope Implemented
- **Requested scope:** "continue the build" / "keep going" → next ticket in order.
- **Related phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Related ticket(s):** **P1-T3 — Synthetic member data + profile ingestion (Maya)**

## Approach
- **High-level strategy:** Author the Maya fixture (PRD §16) and ingest her
  structured profile, linking the member to goals, preferences, equipment access,
  injuries (→ joints), and workout-history sessions.
- **Key decisions:**
  - Equipment/joint names aligned to the `exercises.json` vocabulary so filters match.
  - Adherence as Member properties + per-session status (no Adherence node in §7.1).
  - Workout history = `WorkoutSession` + new `HAS_WORKOUT_SESSION` edge (status-bearing);
    plus new `HAS_EQUIPMENT_ACCESS` edge — both documented extensions beyond §7.1.
  - Goals + injuries tagged `:Embeddable` (vectors in P2-T1).
  - `context_signals` left for P1-T4 (fixture carries raw text + mention hints).
- **Assumptions:** Maya fixture default path `backend/data/members/maya.json`,
  overridable via `MEMBER_PATH`.

---

## Implementation Plan
1. `backend/data/members/maya.json` — fixture per PRD §16.
2. `app/graph/schema.py` — add `HAS_EQUIPMENT_ACCESS`, `HAS_WORKOUT_SESSION` to `EDGE_TYPES`.
3. `app/ingestion/members.py` — `load_member`, `member_properties`, `ingest_member`.
4. Validate offline + live.

**Files created:** `backend/data/members/maya.json`, `app/ingestion/members.py`.
**Modified:** `app/graph/schema.py`.

---

## Code Changes

### File: backend/data/members/maya.json
- **Change summary:** Synthetic Maya fixture — profile, 2 goals, 2 preferences,
  6 equipment, 1 knee injury (affects `knee`), 3 history sessions (1 completed /
  2 missed), 65% adherence, and a chat context signal (for P1-T4).

### File: backend/app/ingestion/members.py
- **Change summary:** Idempotent MERGE-based ingestion of the structured profile:
  `Member` + `HAS_GOAL`/`HAS_PREFERENCE`/`HAS_EQUIPMENT_ACCESS`/`HAS_INJURY`
  (→`AFFECTS_JOINT`→`Joint`)/`HAS_WORKOUT_SESSION`. Goals/injuries tagged `:Embeddable`.

### File: backend/app/graph/schema.py
- **Change summary:** Added the two extension edges to the documented `EDGE_TYPES`.

---

## Acceptance Criteria Mapping
- **Criterion:** Maya present with goals, preferences, equipment, workout history,
  adherence, and `HAS_INJURY → Injury → AFFECTS_JOINT → Joint`; synthetic only
  (PRD §7.3, §16, §9 steps 5–9; §4 non-goal "real data").
  - **Implementation:** `ingest_member()` creates all of the above; adherence on
    Member props + session statuses; fixture is fully synthetic.
  - **File(s):** `backend/app/ingestion/members.py`, `backend/data/members/maya.json`.
  - **Verification status:** **Verified live** (counts + traversal below).

---

## Build Plan Mapping
- **Ticket:** P1-T3 — Synthetic member data + profile ingestion (Maya)
  - **Status:** Complete
  - **What was completed:** Maya fixture + structured-profile ingestion, idempotent,
    verified against a live DB; the contraindication data path already resolves.
  - **Remaining work:** None. (Unstructured chat signal structuring is P1-T4.)

---

## Validation
- **Offline:** fixture loads (member `maya`); `member_properties` flattens name +
  adherence; 2 goals / 6 equipment / 3 sessions; new edges present in `EDGE_TYPES`; `py_compile` clean.
- **Live (Neo4j):** after `apply_schema` + `ingest_exercises` + `ingest_member` (×2):
  - Member 1; HAS_GOAL 2; HAS_PREFERENCE 2; HAS_EQUIPMENT_ACCESS 6; HAS_INJURY 1; HAS_WORKOUT_SESSION 3.
  - `Injury → Joint` = `[knee]`.
  - `Member → Injury → Joint ← Exercise` (contraindication path) = **21** distinct exercises (= all knee-loading exercises).
  - Idempotent: counts unchanged after the second ingest.

---

## Open Issues
- **Known limitations:** Chat signal not yet structured into graph nodes (P1-T4).
  A single seeded member (Maya), by design (depth over breadth).
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None.

---

## BUILD_PLAN Update (P1-T3)
- **Current phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Current ticket:** P1-T4 — Unstructured signal structuring (next)
- **Updated ticket status:** P1-T3 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P1-T4

---
---

# Implementation — P1-T4

## Scope Implemented
- **Requested scope:** "keep going" → next ticket in order.
- **Related phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Related ticket(s):** **P1-T4 — Unstructured signal structuring**

## Approach
- **High-level strategy:** Turn a free-text signal into a `ContextSignal` node and,
  via deterministic keyword extraction, link `MENTIONS_INJURY`/`MENTIONS_GOAL`,
  reconciling against existing member injuries (by joint) and goals (by focus).
- **Key decisions:**
  - Deterministic lexicon-based extraction (no LLM in Phase 1).
  - Reconcile-then-create: link to an existing same-joint injury before making a new one.
  - Goals are linked only if the member already has a matching-focus goal (no fabrication).
  - `ContextSignal` tagged `:Embeddable`.
- **Assumptions:** Signals come from the member fixture's `context_signals`.

---

## Implementation Plan
1. `app/ingestion/signals.py` — `extract_concepts` (pure), `ingest_signal`,
   `structure_member_signals`.
2. Validate offline (extraction) + live (graph linking, reconciliation, idempotency).

**Files created:** `app/ingestion/signals.py`.

---

## Code Changes

### File: backend/app/ingestion/signals.py
- **Change summary:** Keyword lexicons (joints, discomfort cues, goal foci);
  `extract_concepts` derives injuries (joint+discomfort) and goal foci; ingestion
  creates the `ContextSignal` (+`HAS_CONTEXT_SIGNAL`), reconciles/links
  `MENTIONS_INJURY` (creating an `Injury`+`AFFECTS_JOINT` only if none exists), and
  links `MENTIONS_GOAL` to an existing matching-focus goal.

---

## Acceptance Criteria Mapping
- **Criterion:** Given the PRD §7.4 example input, the documented nodes/edges are
  created and linked to the member (PRD §7.4, §9 step 7).
  - **Implementation:** `ContextSignal` with raw text; `MENTIONS_INJURY` → knee injury
    (→ `AFFECTS_JOINT` → `Joint{knee}`); `Member`→`HAS_CONTEXT_SIGNAL`; `MENTIONS_GOAL`
    → lower-body goal.
  - **File(s):** `backend/app/ingestion/signals.py`.
  - **Verification status:** **Verified live** (results below).

---

## Build Plan Mapping
- **Ticket:** P1-T4 — Unstructured signal structuring
  - **Status:** Complete
  - **What was completed:** Deterministic signal structuring with reconciliation,
    verified against a live DB.
  - **Remaining work:** None.

---

## Validation
- **Offline:** `extract_concepts` → `{injury_joints:[knee], goal_foci:[lower_body]}`
  for both the PRD §7.4 example and Maya's text; no injury when no discomfort cue; `py_compile` clean.
- **Live:** after `apply_schema`+`ingest_exercises`+`ingest_member`+`structure_member_signals` (×2):
  - ContextSignal 1; `HAS_CONTEXT_SIGNAL` 1; signal `:Embeddable`.
  - `MENTIONS_INJURY` → `maya-injury-knee` (reconciled — injury count stays **1**, no dup).
  - `MENTIONS_GOAL` → `maya-goal-lower-body-strength`.
  - Idempotent over two runs.

---

## Open Issues
- **Known limitations:** Extraction is lexicon-based (demo-grade); novel phrasings
  outside the lexicon won't be captured. An LLM-assisted extractor could be added
  later behind the same interface.
- **Unresolved edge cases:** None for this scope.
- **Blockers:** None.

---

## BUILD_PLAN Update (P1-T4)
- **Current phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Current ticket:** P1-T5 — Deterministic injury-filter (contraindication) module (next)
- **Updated ticket status:** P1-T4 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P1-T5

---
---

# Implementation — P1-T5

## Scope Implemented
- **Requested scope:** "keep going" → next ticket (completes Phase 1).
- **Related phase:** Phase 1 — Core Graph, Ingestion & Deterministic Safety
- **Related ticket(s):** **P1-T5 — Deterministic injury-filter (contraindication) module**

## Approach
- **High-level strategy:** Package the `Member→Injury→Joint←Exercise` traversal (and
  equipment filtering) as reusable, deterministic, in-graph functions.
- **Key decisions:**
  - All filtering in Cypher (no LLM); contraindicated results include the offending joints.
  - Equipment filter flags exercises needing any unavailable equipment.
  - `safe_exercise_candidates` returns the clean set, ordered by priority tier.
- **Assumptions:** Member equipment via `HAS_EQUIPMENT_ACCESS` (P1-T3); exercise edges (P1-T2).

---

## Implementation Plan
1. `app/safety/__init__.py` + `app/safety/validator.py`.
2. Functions: `contraindicated_exercises`, `contraindicated_exercise_ids`,
   `exercises_requiring_unavailable_equipment`, `safe_exercise_candidates`, `is_contraindicated`.
3. Validate live against Maya.

**Files created:** `app/safety/__init__.py`, `app/safety/validator.py`.

---

## Code Changes

### File: backend/app/safety/validator.py
- **Change summary:** Deterministic contraindication core. `_CONTRAINDICATED`
  traverses Member→Injury→Joint←Exercise (returns offending joints);
  `_UNAVAILABLE_EQUIPMENT` and `_SAFE_CANDIDATES` use `NOT EXISTS {}` subqueries;
  Python wrappers expose ids/sets/lists + `is_contraindicated`.

---

## Acceptance Criteria Mapping
- **Criterion:** For an injured-knee member, all knee-loading exercises are flagged
  contraindicated; computed in-graph, not by LLM (PRD §7.7, §10; ARCH §1, §4).
  - **Implementation:** `contraindicated_exercises('maya')` returns exactly the
    knee-loading set via Cypher.
  - **File(s):** `backend/app/safety/validator.py`.
  - **Verification status:** **Verified live** (set equality with the knee-loading set).

---

## Build Plan Mapping
- **Ticket:** P1-T5 — Deterministic injury-filter (contraindication) module
  - **Status:** Complete
  - **What was completed:** Contraindication + equipment filtering + safe-candidate
    set, deterministic and in-graph, verified live.
  - **Remaining work:** None. **Phase 1 exit criteria met.**

---

## Validation
- **Live (Maya):** contraindicated = **21**, **equals** the knee-loading set (set
  equality True); `affected_joints=[knee]`; 36 exercises need unavailable equipment;
  **9** safe candidates excluding all contraindicated + equipment-blocked; exhaustive
  partition (9 + 41 = 50); `is_contraindicated` True for a knee exercise, False for a safe one.
- `py_compile` clean.

---

## Open Issues
- **Known limitations:** Only 9 safe candidates for Maya — the generator (P3) must
  recover gracefully from a thin candidate pool (PRD §7.6/§10).
- **Unresolved edge cases:** "explicitly marked safe/modified" exceptions (PRD §10)
  not yet modeled; can extend later if needed.
- **Blockers:** None.

---

## Phase 1 Exit Criteria (met)
Graph schema + constraints applied; `exercises.json` (50) and Maya ingested;
unstructured signal produces structured nodes/edges; a deterministic query returns
the contraindicated-exercise set for the injured member. ✔ All verified live.

---

## BUILD_PLAN Update (P1-T5)
- **Current phase:** Phase 2 — GraphRAG Retrieval
- **Current ticket:** P2-T1 — Embedder adapter + embedding of graph nodes (next)
- **Updated ticket status:** P1-T5 → Complete (Phase 1 Complete)
- **Any blockers:** None
- **Recommended next ticket:** P2-T1

---
---

# Implementation — P2-T1

## Scope Implemented
- **Requested scope:** "keep going" → next ticket (starts Phase 2).
- **Related phase:** Phase 2 — GraphRAG Retrieval
- **Related ticket(s):** **P2-T1 — Embedder adapter + embedding of graph nodes**

## Approach
- **High-level strategy:** Add an `Embedder` seam, embed every `:Embeddable` node
  into the Neo4j vector index, and expose a vector-search helper.
- **Key decisions / DEVIATION:** **OpenAI-only embeddings (user-directed)** — no local
  fallback; demo requires `OPENAI_API_KEY`. Overrides ARCH §6 / planning assumption.
  Defaults: `text-embedding-3-small`, 1536-dim.
- **Assumptions:** `:Embeddable` set = exercises, injuries, goals, signals (tagged in P1-T2/T3/T4).

---

## Implementation Plan
1. Config: `EMBEDDING_PROVIDER=openai`, add `EMBEDDING_MODEL`, `EMBEDDING_DIM=1536`; `.env.example`.
2. `requirements.txt`: add `openai`.
3. `app/retrieval/embeddings.py`: `Embedder` protocol, `OpenAIEmbedder`, `get_embedder`,
   `compose_node_text`, `embed_graph_nodes`, `vector_search`.

**Files created:** `app/retrieval/__init__.py`, `app/retrieval/embeddings.py`.
**Modified:** `app/config.py`, `.env.example`, `requirements.txt`.

---

## Code Changes

### File: backend/app/retrieval/embeddings.py
- **Change summary:** `Embedder` protocol + `OpenAIEmbedder` (lazy openai import,
  missing-key guard); `compose_node_text` (pure); `embed_graph_nodes` writes vectors
  via `db.create.setNodeVectorProperty`; `vector_search` via `db.index.vector.queryNodes`.

### File: backend/app/config.py
- **Change summary:** `embedding_provider` default → `openai`; added `embedding_model`
  (`text-embedding-3-small`); `embedding_dim` default → 1536.

### File: .env.example / requirements.txt
- **Change summary:** Documented OpenAI-required embeddings + dim 1536; added `openai==2.40.0`.

---

## Acceptance Criteria Mapping
- **Criterion:** Nodes carry embeddings; vector similarity query returns ranked
  matches (PRD §7.5 step 1–2, §9 Retrieval step 2–3; ARCH §6).
  - **Implementation:** `embed_graph_nodes()` writes a vector onto every `:Embeddable`
    node; `vector_search()` returns ranked nodes via the native index.
  - **File(s):** `backend/app/retrieval/embeddings.py`.
  - **Verification status:** **Verified live with real OpenAI** (key via macOS
    keychain → `.env`): 54 nodes embedded at 1536-d; semantic query "knee hurts after
    lunges/squats" ranks Knee pain (0.891), the knee chat signal (0.826), then lunge
    exercises. Stub run also confirmed index/cosine (exact-text → #1 @ 1.0).

---

## Build Plan Mapping
- **Ticket:** P2-T1 — Embedder adapter + embedding of graph nodes
  - **Status:** Complete (verified live with real OpenAI)
  - **What was completed:** Embedder seam, node embedding into the vector index, vector search.
  - **Remaining work:** Rebuild API image with `openai` (when the API uses embeddings, P2-T3/P3).

---

## Validation
- **Offline:** `compose_node_text` correct; `get_embedder()` raises a clear error
  without a key; `py_compile` clean.
- **Live (real OpenAI):** 54 `:Embeddable` nodes embedded at 1536-d; semantic query
  "my knee hurts after doing lunges and squats" → Knee pain (0.891), knee chat signal
  (0.826), lunge/knee-drive exercises.
- **Live (stub embedder):** query with a node's exact composed text → that node ranks
  **#1 at score 1.0** (index + cosine correct).

---

## Open Issues
- **Known limitations / DEVIATION:** Demo requires `OPENAI_API_KEY` (no local embedder).
  `EMBEDDING_DIM` is now 1536 → any old dim-384 index must be wiped (`down -v`) before re-seed.
- **Blockers:** None (key needed only for a full live run).

---

## BUILD_PLAN Update (P2-T1)
- **Current phase:** Phase 2 — GraphRAG Retrieval
- **Current ticket:** P2-T2 — GraphRAG retriever (vector + traversal + trace) (next)
- **Updated ticket status:** P2-T1 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P2-T2

---
---

# Implementation — P2-T2

## Scope Implemented
- **Requested scope:** "keep going" → next ticket.
- **Related phase:** Phase 2 — GraphRAG Retrieval
- **Related ticket(s):** **P2-T2 — GraphRAG retriever (vector + traversal + trace)**

## Approach
- **Strategy:** Combine vector search (semantic relevance) with graph traversal
  (member neighborhood) and the deterministic safety filter into one focused context
  window + a recorded `graph_trace`.
- **Key decisions:**
  - Safe-candidate set re-ranked by the query's vector scores (true GraphRAG).
  - Hard caps for token efficiency (8 semantic / 8 safe / 5 sessions) — never dump the graph.
  - `graph_trace` = subject-relation-object triples capturing the contraindication path.
  - `CALL {}` subqueries to fetch the neighborhood without a cartesian product.

---

## Implementation Plan
1. `app/retrieval/embeddings.py`: have `vector_search` return `node.id`.
2. `app/retrieval/retriever.py`: `retrieve()` + `_fetch_member_context` + `_build_graph_trace`.
3. Validate live with real OpenAI.

**Files created:** `app/retrieval/retriever.py`. **Modified:** `app/retrieval/embeddings.py`.

---

## Code Changes

### File: backend/app/retrieval/retriever.py
- **Change summary:** `retrieve(member_id, query)` returns member/goals/preferences/
  equipment/injuries/recent_sessions/context_signals/safe_candidates/excluded_exercises/
  semantic_matches/graph_trace. Safe set ranked by semantic score; trace built from
  injuries + contraindicated exercises.

### File: backend/app/retrieval/embeddings.py
- **Change summary:** `_VECTOR_QUERY` now also returns `node.id`.

---

## Acceptance Criteria Mapping
- **Criterion:** For "lower-body session" query on Maya, retrieval surfaces goals,
  recent history, injuries→joints, excluded exercises, and equipment; whole graph is
  **not** dumped (PRD §7.5, §9 Retrieval; ARCH §3.4).
  - **Implementation:** `retrieve('maya', 'Build Maya a lower-body session...')`.
  - **File(s):** `backend/app/retrieval/retriever.py`.
  - **Verification status:** **Verified live** (results below) — 29 exercises in
    context (<50), full neighborhood + trace.

---

## Build Plan Mapping
- **Ticket:** P2-T2 — GraphRAG retriever (vector + traversal + trace)
  - **Status:** Complete
  - **What was completed:** Focused GraphRAG retrieval + graph_trace, verified live.
  - **Remaining work:** None (typed endpoints are P2-T3).

---

## Validation
- **Live (real OpenAI), query "Build Maya a lower-body session for this week":**
  goals (lower-body strength, consistency), preferences, 6 equipment,
  injuries→joint = Knee pain→knee, recent history (completed upper / missed
  lower+conditioning), **21** excluded, 8 focused safe candidates ranked by relevance,
  semantic matches led by the lower-body Goal (0.78), `graph_trace` = 23 triples,
  exercises-in-context = **29 (<50)**.
- `py_compile` clean.

---

## Open Issues
- **Known limitations:** Safe pool skews upper-body for Maya (knee + equipment
  limits); `Jumping Jack` (high-impact) violates her preference — to be handled by
  P3-T2 (preference/validation) and P3-T4 (thin-context recovery), not the retriever.
- **Blockers:** None.

---

## BUILD_PLAN Update (P2-T2)
- **Current phase:** Phase 2 — GraphRAG Retrieval
- **Current ticket:** P2-T3 — `/api/retrieve` + `/api/member/:id/graph` endpoints (next)
- **Updated ticket status:** P2-T2 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P2-T3

---
---

# Implementation — P2-T3

## Scope Implemented
- **Requested scope:** "keep going" → next ticket (completes Phase 2).
- **Related phase:** Phase 2 — GraphRAG Retrieval
- **Related ticket(s):** **P2-T3 — `/api/retrieve` + `/api/member/:id/graph` endpoints & schemas**

## Approach
- **Strategy:** Expose the retriever over typed REST matching PRD §7.9, plus a
  member-graph neighborhood endpoint for viz/debugging.
- **Key decisions:** Explicit Pydantic models for trace/matches/nodes/edges; open
  dicts for variable member data; graph endpoint returns the safety-relevant subgraph
  (incl. excluded exercises) using `elementId` as the stable node id.

---

## Implementation Plan
1. `app/api/schemas.py` — request/response models.
2. `app/retrieval/retriever.py` — add `member_graph()`.
3. `app/api/routes.py` — `POST /api/retrieve`, `GET /api/member/{id}/graph`.

**Files created:** `app/api/schemas.py`. **Modified:** `app/api/routes.py`, `app/retrieval/retriever.py`.

---

## Code Changes

### File: backend/app/api/schemas.py
- **Change summary:** `RetrieveRequest/Response`, `RetrievedContext`, `GraphTraceEntry`,
  `SemanticMatch`, `GraphNode/Edge`, `MemberGraphResponse`.

### File: backend/app/api/routes.py
- **Change summary:** Added `POST /api/retrieve` (404 on unknown member) and
  `GET /api/member/{member_id}/graph` (404 on empty).

### File: backend/app/retrieval/retriever.py
- **Change summary:** Added `member_graph()` returning `{nodes, edges}` for the
  safety-relevant neighborhood.

---

## Acceptance Criteria Mapping
- **Criterion:** Endpoints return the PRD §7.9 response shapes (`retrieved_context`,
  `graph_trace`, `semantic_matches`; `nodes`/`edges`) with typed schemas.
  - **Implementation:** `RetrieveResponse` + `MemberGraphResponse`.
  - **File(s):** `backend/app/api/schemas.py`, `backend/app/api/routes.py`.
  - **Verification status:** **Verified live** (TestClient + real OpenAI).

---

## Build Plan Mapping
- **Ticket:** P2-T3 — endpoints & schemas
  - **Status:** Complete
  - **What was completed:** Typed `/api/retrieve` + `/api/member/:id/graph`, verified live.
  - **Remaining work:** None. **Phase 2 exit criteria met.**

---

## Validation
- **Live (TestClient, real OpenAI):** `/api/retrieve` → 200, top-level keys exactly
  `{member_id, retrieved_context, graph_trace, semantic_matches}`; 21 excluded, 8 safe,
  trace 23, 8 semantic. `/api/member/maya/graph` → 200, 38 nodes / 37 edges across all
  9 node labels + safety edges (AFFECTS_JOINT, LOADS_JOINT). Both → 404 on unknown member.
- `py_compile` clean.

---

## Phase 2 Exit Criteria (met)
`/api/retrieve` returns retrieved context, semantic matches, and a graph trace with
contraindicated exercises excluded; `/api/member/:id/graph` returns the neighborhood. ✔

---

## BUILD_PLAN Update (P2-T3)
- **Current phase:** Phase 3 — Generation, Safety Validation, Explanation & Orchestration
- **Current ticket:** P3-T1 — LLM adapter + workout generator (next)
- **Updated ticket status:** P2-T3 → Complete (Phase 2 Complete)
- **Any blockers:** None
- **Recommended next ticket:** P3-T1

---
---

# Implementation — P3-T1

## Scope Implemented
- **Requested scope:** "keep going" → next ticket (starts Phase 3).
- **Related phase:** Phase 3 — Generation, Safety Validation, Explanation & Orchestration
- **Related ticket(s):** **P3-T1 — LLM adapter + workout generator**

## Approach
- **Strategy:** Add an `LLMClient` seam + a generator that turns retrieved context into
  the structured PRD §7.6 workout JSON.
- **Key decisions:** OpenAI JSON mode; prompt encodes the output schema + hard safety
  rules; generator returns `{workout, retrieved_context}` for downstream reuse;
  graceful recovery when the requested focus can't be trained safely.

---

## Implementation Plan
1. Config: `llm_model` (`LLM_MODEL`, default `gpt-4o-mini`); `.env.example`.
2. `app/llm/client.py` — `LLMClient` + `OpenAILLMClient` + `get_llm_client`.
3. `app/generation/prompts.py` — system + user prompt builders.
4. `app/generation/generator.py` — `generate_workout`.

**Files created:** `app/llm/__init__.py`, `app/llm/client.py`,
`app/generation/__init__.py`, `app/generation/prompts.py`, `app/generation/generator.py`.
**Modified:** `app/config.py`, `.env.example`.

---

## Code Changes

### File: backend/app/llm/client.py
- **Change summary:** Provider-agnostic LLM seam; `OpenAILLMClient.complete_json`
  (JSON mode, temp 0.2); missing-key guard; cached factory.

### File: backend/app/generation/prompts.py
- **Change summary:** `WORKOUT_SYSTEM` (output schema + safety rules + graceful
  recovery) and `build_workout_user` (compact focused context).

### File: backend/app/generation/generator.py
- **Change summary:** `generate_workout(member_id, query)` → `{workout, retrieved_context}`.

---

## Acceptance Criteria Mapping
- **Criterion:** Produces the PRD §7.6 workout structure from retrieved context;
  provider configurable (PRD §7.6, §9 Generation step 1–2; ARCH §6).
  - **Implementation:** `generate_workout` returns the full §7.6 shape via the
    configurable `LLMClient`.
  - **File(s):** `backend/app/generation/*`, `backend/app/llm/client.py`.
  - **Verification status:** **Verified live** (real OpenAI).

---

## Build Plan Mapping
- **Ticket:** P3-T1 — LLM adapter + workout generator
  - **Status:** Complete
  - **What was completed:** LLM seam + structured workout generation, verified live.
  - **Remaining work:** Latency tuning (≈7.5s vs ~5s target) — follow-up.

---

## Validation
- **Live (real OpenAI):** workout has all §7.6 keys; exercises ⊆ safe candidate set;
  no contraindicated exercise in output; `insufficient_safe_options:true` + explanatory
  notes when the requested focus can't be safely trained (graceful recovery).
- `py_compile` clean.

---

## Open Issues
- **Latency:** ≈7.3–7.6s end-to-end (> ~5s PRD target) — candidate optimizations noted
  in implementation-notes.
- **Conservatism:** the model offers a small safe alternative session for Maya's
  knee+equipment-limited case; further repair/expansion is P3-T2/P3-T4.
- **Blockers:** None.

---

## BUILD_PLAN Update (P3-T1)
- **Current phase:** Phase 3 — Generation, Safety Validation, Explanation & Orchestration
- **Current ticket:** P3-T2 — Safety validator: validation + repair + fallback (next)
- **Updated ticket status:** P3-T1 → Complete
- **Any blockers:** None
- **Recommended next ticket:** P3-T2

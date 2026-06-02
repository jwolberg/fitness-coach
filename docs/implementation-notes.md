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

## 2026-06-02 — P1-T5 (Deterministic injury-filter / contraindication module)

- **All safety computed in Cypher, never the LLM** (ARCH §1, PRD §10). The core
  query is the `Member→Injury→Joint←Exercise` traversal; an exercise loading any
  affected joint is contraindicated.
- **Contraindicated results carry the offending joint(s)** (`affected_joints`) so
  the explanation builder (P3-T3) can say *why* without re-querying.
- **Equipment filter** flags any exercise that requires ≥1 piece of equipment the
  member can't access (bodyweight exercises with no equipment are always available).
- **`safe_exercise_candidates`** returns the set that is neither contraindicated nor
  equipment-blocked, ordered by `priority_tier` then name — the candidate pool the
  generator/repair (P3) draws from. Uses `NOT EXISTS { ... }` subqueries for both filters.
- **Validation (live):** for Maya — contraindicated set = **21** and **equals** the
  knee-loading set exactly (set equality); affected joint `[knee]`; 36 exercises need
  unavailable equipment; **9** safe candidates, which exclude every contraindicated
  and every equipment-blocked exercise. The partition is exhaustive (9 + |contra ∪
  unavail|=41 = 50). `is_contraindicated` returns True for a knee exercise and False
  for a safe one.
- **Note for Phase 3:** only 9 safe candidates for Maya — exactly the "few valid
  options" case PRD §7.6/§10 says the generator must recover from gracefully rather
  than hallucinate. Good stress case for P3-T2/P3-T4.

## 2026-06-02 — P1-T4 (Unstructured signal structuring)

- **Deterministic extraction, not LLM.** A small keyword lexicon maps free text to
  (a) injuries — a joint term co-occurring with a discomfort cue — and (b) goal foci.
  Keeps Phase 1 runnable without a provider key; the LLM is reserved for generation
  (P3, never on the safety path per ARCH §6). `extract_concepts` is pure/testable.
- **Reconcile before create (no duplicate concepts).** A derived injury first looks
  for an existing member injury affecting the same joint and links `MENTIONS_INJURY`
  to it; only if none exists does it create a new `Injury (+AFFECTS_JOINT)`. So
  Maya's chat ("knee felt weird...") links to the P1-T3 `maya-injury-knee` rather
  than spawning a second knee injury (verified: injury count stays 1).
- **Goals are linked, never fabricated.** `MENTIONS_GOAL` only attaches to a goal the
  member already has (matched by `focus`); if none matches, it's skipped — honoring
  the PRD's "do not invent" / "possible relationship" wording.
- **ContextSignal tagged `:Embeddable`** (PRD §7.5 embeds signals; vector in P2-T1).
- **Joint/goal lexicons use the canonical vocab** (`exercises.json` joints; the
  `focus` values from the member fixture) so links resolve.
- **Validation:** offline — `extract_concepts` returns `{knee},{lower_body}` for both
  the PRD §7.4 example and Maya's text, and correctly yields no injury when no
  discomfort cue is present. Live — ContextSignal (1) + HAS_CONTEXT_SIGNAL (1);
  MENTIONS_INJURY → `maya-injury-knee`; MENTIONS_GOAL → `maya-goal-lower-body-strength`;
  injury count unchanged (reconciled); idempotent over two runs.

## 2026-06-02 — P1-T3 (Synthetic member data + profile ingestion: Maya)

- **Fixture at `backend/data/members/maya.json`** matching PRD §16 (goal, knee
  injury, equipment, glute preference, recent history, 65% adherence, chat signal).
  Synthetic only.
- **Equipment + joint names aligned to `exercises.json` vocabulary** so the
  contraindication/equipment filters match later: knee → `knee`; equipment mapped
  to real terms (`Dumbbell`, `Resistance Band - Loop`/`- With Handles`,
  `Flat Bench`, `Cable Resistance Machine`, `Handle Attachment`). Maya intentionally
  has **no Barbell**, so barbell squats are excluded by both knee injury and missing
  equipment — convenient for the demo's "why skip barbell squats?".
- **Adherence modeled as Member properties** (`adherence_rate=0.65`,
  `adherence_window`, `adherence_missed_last_week=2`) PLUS per-session status — PRD
  §7.1 has no Adherence node, and properties + session granularity cover the
  "surface adherence trend" story without inventing a node type.
- **DECISION — Workout history uses `WorkoutSession` + new `HAS_WORKOUT_SESSION` edge.**
  History entries need a completed/missed status; §7.1's `COMPLETED_WORKOUT`/`Workout`
  only express completion. So each history slot is a `WorkoutSession {status,date,focus}`
  linked by `HAS_WORKOUT_SESSION`; `COMPLETED_WORKOUT`/`Workout`/`CONTAINS_EXERCISE`
  stay reserved for generated/logged workouts (Phase 3).
- **DECISION — added `HAS_EQUIPMENT_ACCESS` (Member→Equipment).** §7.1 only defines
  `Exercise USES_EQUIPMENT`, but retrieval must know the member's available equipment.
  Both new edges are documented in `schema.EDGE_TYPES` as extensions beyond the §7.1
  minimum (PRD §7.1 says "at minimum").
- **Goals + injuries tagged `:Embeddable`** here (vectors written in P2-T1), matching
  PRD §7.5's embeddable set (signals/injuries/goals/exercises).
- **SCOPE — `context_signals` left for P1-T4.** The fixture carries the raw chat text
  (+ `mentions_injury_id`/`mentions_goal_id` hints), but `members.py` does NOT create
  `ContextSignal`/`MENTIONS_*`; that's P1-T4 (`signals.py`).
- **Validation:** offline (fixture loads; props/edges well-formed) + **live** against
  Neo4j: Maya with 2 goals, 2 preferences, 6 equipment, 1 injury, 3 sessions;
  `Injury→Joint=[knee]`; the `Member→Injury→Joint←Exercise` traversal returns **21**
  contraindicated exercises (= the 21 knee-loading exercises). Idempotent (ingested
  twice, no doubling).
- **Env hiccup:** the harness task temp fs briefly hit 0MB (ENOSPC) mid-run; worked
  around by minimizing stdout and writing results to a file. Shared Docker/temp
  cleanup was (correctly) blocked as out-of-scope; main disk had headroom.

## 2026-06-02 — LIVE validation (closes the "pending Docker daemon" caveats)

The Docker daemon became available, so the deferred end-to-end checks for P0-T2,
P1-T1, and P1-T2 were run for real against `neo4j:5.26-community` via Compose:

- **P0-T2:** `docker compose up neo4j` → healthy; then `--build api` → the API
  container connected on attempt 1 (`bolt://neo4j:7687`), and `GET
  http://localhost:8000/health` → 200. API logs show
  "Connected to Neo4j (opened a session on attempt 1)".
- **P1-T1:** `apply_schema()` created **16 constraints + 1 vector index**
  (`SHOW CONSTRAINTS` = 16, `SHOW INDEXES` VECTOR = 1). Re-running produced no
  errors/changes → idempotent confirmed.
- **P1-T2:** `ingest_exercises()` → **50 Exercise nodes** (all `:Embeddable`),
  9 Joint / 19 MuscleGroup / 32 Equipment / 36 MovementPattern; edges
  LOADS_JOINT 124, TRAINS_MUSCLE 120, USES_EQUIPMENT 67, HAS_MOVEMENT_PATTERN 93,
  HAS_BILATERAL_PAIR 0. Ran twice → counts unchanged (idempotent). The 0
  bilateral edges are expected: none of the 50 `bilateral_pair_id`s resolve within
  the set (verified), and we deliberately don't create stub nodes.

Compose was torn down afterward (`docker compose down`, volume retained). A local
`.env` (copy of `.env.example`, gitignored) was created for the run.

## 2026-06-02 — P1-T1 (Graph schema, constraints & vector index)

- **One uniqueness constraint per node label (16 total).** Context/member-scoped
  nodes keyed by `id`; ontology/library nodes (`Joint`, `MuscleGroup`,
  `MovementPattern`, `Equipment`) keyed by `name` — these are natural singletons,
  so name is the stable key and lets ingestion `MERGE` on it.
- **Single vector index via a shared `:Embeddable` label.** Neo4j vector indexes
  are scoped to one label, but PRD §7.5 embeds several node types (signals,
  injuries, goals, exercises). Putting a secondary `:Embeddable` label + `embedding`
  property on those nodes lets ONE index (`embeddable_embedding`, cosine) span them
  and supports ARCH §3.7's "one Cypher query mixes vector similarity + traversal."
  Embeddings themselves are written in P2-T1.
- **Embedding width is configurable** (`EMBEDDING_DIM`, default 384 for local
  all-MiniLM-L6-v2; 1536 for OpenAI). The vector index is created with this
  dimension; the embedder (P2-T1) must match it. Added to `config.py` + `.env.example`.
- **Edges aren't constrained.** Neo4j relationships are schemaless and relationship
  uniqueness constraints are Enterprise-only; `EDGE_TYPES` is a documented inventory
  (all 14 PRD §7.1 edges) for ingestion + README, not DDL.
- **Statement builders are pure functions** (`constraint_statements`,
  `vector_index_statement`) returning Cypher strings, so they're unit-testable
  without a live DB; `apply_schema()` executes them. All statements use
  `IF NOT EXISTS` → idempotent (acceptance requirement).
- **DEVIATION (file beyond ticket's listed files):** wired `apply_schema()` into the
  `app/main.py` startup lifespan (runs once after a successful Neo4j connect; schema
  failure logs but doesn't crash). The ticket listed only `schema.py`/`client.py`,
  but without a caller the index/constraints are never created. Wiring it at boot is
  the smallest way to satisfy "constraints + vector index created" and keeps the API
  self-bootstrapping; idempotent so re-runs are free. The dedicated seed step
  (P5-T3) can still call `apply_schema()` explicitly.
- **Validation limit (same as P0-T2):** no Docker daemon in the build env, so the
  statements were **not** executed against a live Neo4j. Verified the builders emit
  16 idempotent constraints + a well-formed cosine vector index (dim 384) covering
  all §7.1 labels, and that the app still boots/serves `/health`. Live schema
  creation is pending `docker compose up`.

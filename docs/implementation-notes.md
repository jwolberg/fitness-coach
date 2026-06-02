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

## 2026-06-02 — P3-T5 (/api/generate/workout + /api/explain + structured logging)

- **Endpoints match PRD §7.9:** `/api/generate/workout` → `{workout, explanation,
  safety_validation, status}` (safety_validation = {passed, issues, repaired,
  used_fallback}); `/api/explain` → `{answer, graph_trace}`. Both 404 on unknown member.
- **`workout` left as an open dict in the response envelope** — the LLM output shape
  varies; typing the envelope (and `safety_validation`) gives the typed contract
  without 500s from schema drift. PRD §7.9 shows `workout` as `{}` anyway.
- **`/api/explain` retrieves fresh context** using the question as the query (no
  recommendation store), then runs the deterministic builder. `recommendation_id` is
  accepted per §7.9 but unused (noted) — there's no persistence layer in scope.
- **Structured logging (PRD §13):** `app/observability/logging.py` emits JSON-line
  events; the API logs `generate.request`/`generate.result` (with status, #exercises,
  #safe, #excluded, passed/repaired/used_fallback) and `explain.request`/`explain.result`.
  Retriever/generator/validator also log via their module loggers.
- **Validation (live, TestClient + real OpenAI):** generate → 200 with the full §7.9
  shape, passed=True, status ok; explain → 200 with the exclusion chain + 3-triple
  trace; 404 on unknown member; all four structured events captured. **Phase 3 done.**

## 2026-06-02 — P3-T4 (LangGraph orchestration pipeline + thin-context recovery)

- **Added `langgraph==1.2.4`.** `StateGraph` over a typed `PipelineState` wires
  retrieve → (generate | fallback) → validate → explain, enforcing the fixed ordering
  (validation always after generation, before response — ARCH §5).
- **Conditional edge for thin/empty context.** `_route_after_retrieve`: if there are
  **no safe candidates at all**, route to a deterministic `fallback` node (PRD §10
  safe fallback) and **skip the LLM entirely** — recovers rather than inventing
  (PRD/challenge "Resilience"). Verified the LLM is not called on that branch.
- **Refactor:** split `generate_from_context(ctx, query)` out of `generate_workout`
  so the pipeline reuses the already-retrieved context (one retrieval per request).
- **`run_workout_pipeline(member_id, query)`** invokes the compiled graph and returns
  `{workout, explanation, safety_validation, retrieved_context, status}`.
  `status` ∈ {`ok`, `insufficient_context`}.
- **Validation (live + unit):** normal path (real OpenAI) → status `ok`, all stages
  present, `passed=True`, no contraindicated in final, grounded explanation. Thin path
  (monkeypatched empty safe_candidates, LLM guarded to raise if called) → routed to
  fallback, LLM not invoked, status `insufficient_context`, PRD §10 notes, safe.

## 2026-06-02 — P3-T3 (Explanation builder)

- **Deterministic templating over the recorded `graph_trace` — no LLM, no re-query.**
  This is the strongest reading of "traceable to graph relationships, not a vague LLM
  rationalization" (challenge): the answer literally cannot hallucinate because it's
  assembled from the retrieved context + trace.
- **Intent routing** by keyword: watch-outs / constraints / inclusion / (default)
  exclusion — covering the PRD §7.8 follow-ups and the demo's three asks.
- **Exclusion match is best-effort by name tokens.** "Why skip barbell squats?" →
  picks the highest-token-overlap excluded exercise (here "Barbell Racked Forward
  Lunge"; the dataset has no literal barbell squat) and builds the
  Member→Injury→Joint←Exercise chain. The reasoning shown is always a real
  contraindication; exact-name matching is approximate by design.
- **Validation (live):** all three demo questions produce grounded answers with the
  correct trace — exclusion shows the knee contraindication chain; watch-outs surface
  65% adherence / missed 2 / knee injury / goals / missed sessions; constraints list
  injuries→knee (21 excluded) + equipment + preferences. Fixed a cosmetic "Maya:;"
  join glitch.

## 2026-06-02 — P3-T2 (Safety validator: validation + repair + fallback)

- **Extends `validator.py` (P1-T5).** `validate_workout` flags each exercise as
  `unknown_exercise` / `contraindicated` / `unavailable_equipment` /
  `preference_conflict` / `malformed` (PRD §7.7). All deterministic, in-graph.
- **Preference check is keyword-based and deterministic.** Dislike tags → cue words
  (e.g. `high_impact` → jump/hop/plyo/jack…); flags e.g. "Jumping Jack" for Maya.
- **`validate_and_repair`**: drops bad exercises, backfills from `safe_exercise_candidates`
  (skipping preference conflicts) up to the original count; if nothing safe remains →
  `safe_fallback`. `passed` reflects the ORIGINAL workout; the returned workout is
  always safe. Result carries `{passed, issues, repaired, used_fallback}`.
- **`safe_fallback` = PRD §10 message, joint-aware** ("...coach review before loading
  the knee joint..."), with a few safe candidates at generic 3×10-12 / 60s.
- **LLM is not the only safety layer** (ARCH §1): even if generation emits a bad
  exercise, this layer removes/replaces it before the response leaves the API.
- **Validation (live):** injected a workout with a contraindicated + unknown + malformed
  exercise → all three problems detected; repair produced 3 safe, all-known exercises
  (no contraindicated); "Jumping Jack" → preference_conflict; `safe_fallback` flagged
  insufficient, mentioned knee, all-safe; a clean safe-candidate workout passed.

## 2026-06-02 — P3-T1 (LLM adapter + workout generator)

- **`LLMClient` mirrors the `Embedder` seam** — OpenAI-only for now (`LLM_PROVIDER`,
  `LLM_MODEL` default `gpt-4o-mini`), JSON mode (`response_format=json_object`),
  temperature 0.2. The LLM is never the only safety layer (ARCH §1) — P3-T2 validates.
- **Prompt fixes the output JSON shape + hard safety rules** (use only `safe_candidates`
  by id+name; never `excluded_exercises`; don't invent; respect preferences; recover
  gracefully). The user prompt carries only the focused context, not the graph.
- **Generator returns `{workout, retrieved_context}`** so the validator/explanation/
  orchestration reuse the same trace without re-querying.
- **Tuning — graceful recovery vs. empty output.** First run: for "lower-body session"
  the model correctly judged a knee injury + equipment limits leave too few *lower-body*
  options and returned `insufficient_safe_options:true` with **0 exercises** + an
  explanation (safe, no hallucination — exactly PRD §7.6/§10). But 0 exercises with 8
  safe candidates is a poor demo, so I strengthened the prompt: when the requested
  focus can't be trained safely, still populate `exercises` with the best safe
  alternatives (upper/mobility/hip-dominant) and flag the limitation. Re-run: 1 safe
  exercise (`Resistance Band Reverse Curl`), all ids in the safe set, none
  contraindicated, `insufficient_safe_options:true` + explanatory notes.
- **LATENCY follow-up:** end-to-end generate ≈ 7.3-7.6s (1 embedding call for the
  query + the LLM completion), **above the ~5s PRD target**. Options for later:
  smaller/faster model, trimming the prompt, caching the query embedding, or
  streaming. PRD §12 cares more about the reasoning than the exact number; noted.
- **Validation (live, real OpenAI):** required keys present; exercises ⊆ safe set;
  no contraindicated exercise in output; structured workout matches PRD §7.6.

## 2026-06-02 — P2-T3 (/api/retrieve + /api/member/:id/graph endpoints & schemas)

- **Response matches PRD §7.9 exactly:** `/api/retrieve` → `{member_id,
  retrieved_context, graph_trace, semantic_matches}`. `retrieve()` returns one dict;
  the route pops `graph_trace`/`semantic_matches` to the top level and the rest
  becomes `retrieved_context`.
- **Typed where it matters, open where data varies.** `GraphTraceEntry`,
  `SemanticMatch`, `GraphNode`, `GraphEdge` are explicit Pydantic models; member/
  goal/session objects stay `dict[str, Any]` (synthetic shapes vary) — pragmatic
  typing per ARCH principle 4 without over-constraining.
- **`/api/member/:id/graph` returns a safety-relevant subgraph** (not the whole DB):
  member's direct edges + injury→joint + the excluded exercises that load injured
  joints — so a viewer can *see* why exercises are excluded (PRD §7.10 nice-to-have
  "highlight excluded exercises"). `member_graph()` assembles nodes/edges in Python
  from relationship rows (dedup by element id), using `elementId` as the stable node id.
- **404s** for unknown members on both endpoints (`ValueError`→404 on retrieve;
  empty neighborhood→404 on graph).
- **Validation (live, TestClient + real OpenAI):** `/api/retrieve` 200 with the exact
  top-level keys, 21 excluded / 8 safe / trace 23 / 8 semantic; `/api/member/maya/graph`
  200 with 38 nodes + 37 edges covering all 9 node labels and the safety edge types;
  both endpoints 404 on a bogus member. **Phase 2 exit criteria met.**

## 2026-06-02 — P2-T2 (GraphRAG retriever: vector + traversal + trace)

- **Vector + graph, not one or the other.** `retrieve()` does a graph-wide vector
  search, then graph-traverses the member's safety-relevant neighborhood, then
  applies the deterministic injury/equipment filter (P1-T5). The safe-candidate set
  is re-ranked by the query's semantic scores (vector relevance) — GraphRAG, not
  semantic-search-with-extra-steps.
- **Focused window, never a graph dump.** Caps: 8 semantic matches surfaced, 8 safe
  candidates, 5 recent sessions. For Maya's lower-body query only **29** exercises
  appear in context (8 safe + 21 excluded), never all 50; only the member's
  neighborhood is traversed. `_MEMBER_CONTEXT` uses `CALL {}` subqueries to avoid a
  cartesian blow-up across the OPTIONAL MATCHes.
- **`graph_trace` recorded during traversal** as subject-relation-object triples
  (Member→HAS_INJURY→Injury, Injury→AFFECTS_JOINT→Joint, Exercise→LOADS_JOINT→Joint
  note=contraindicated). 23 triples for Maya — this is what P3-T3 reads to answer
  "why?" without re-querying/re-prompting.
- **Needed `node.id` from the vector index** to intersect semantic hits with the safe
  set — all `:Embeddable` nodes (Exercise/Injury/Goal/ContextSignal) have an `id`, so
  `vector_search` now returns it.
- **Observation for P3:** Maya's safe pool is mostly upper-body (knee injury +
  equipment limits remove most lower-body options), and `Jumping Jack` is high-impact
  — conflicting with her "dislikes high-impact" preference. The retriever's job is
  safety (injury+equipment); **preference conflicts and the thin-pool recovery are
  P3-T2/P3-T4 concerns** (PRD §7.6/§7.7/§10). Good live stress case.
- **Validation (live, real OpenAI):** query "Build Maya a lower-body session" →
  goals/prefs/equipment/injuries→joint(knee)/recent history all surfaced; 21 excluded;
  semantic matches led by the lower-body goal (0.78) + leg-press/split-squat + knee
  signal; trace=23; exercises-in-context=29 (<50).

## 2026-06-02 — P2-T1 (Embedder adapter + node embeddings)

- **DEVIATION (user-directed) — OpenAI-only embeddings, no local fallback.** When
  asked, the user chose "OpenAI only" over fastembed/sentence-transformers. This
  OVERRIDES ARCH §6 and the BUILD_PLAN planning assumption ("local embedding fallback
  so the demo runs without forcing one key"). **Consequence: the demo now REQUIRES
  `OPENAI_API_KEY`** to run retrieval/generation. Config defaults changed:
  `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-small`,
  `EMBEDDING_DIM=1536` (was 384). `.env.example` updated with a prominent note;
  README (P5-T4) must call this out. The vector index is therefore created at dim 1536.
- **`Embedder` protocol keeps the provider behind one seam** (`get_embedder()`),
  so a local provider could be added later without touching the retriever.
- **Node text = name + description/text + muscles + movement patterns** (`compose_node_text`,
  pure) — richer text improves semantic matching. Exercises pull muscles/patterns via
  edges; signals use `text`, injuries/goals use `description`.
- **Vectors written via `db.create.setNodeVectorProperty`** (the idiomatic way to
  populate a Neo4j vector index); `vector_search` uses `db.index.vector.queryNodes`.
- **VALIDATION — now verified live with REAL OpenAI.** The user added the key to the
  macOS keychain (`fitness-OPENAI_API_KEY`), pulled into `.env`. With the real
  `text-embedding-3-small`: all **54** `:Embeddable` nodes embedded at 1536-d, and a
  semantic query "my knee hurts after doing lunges and squats" ranked **Knee pain**
  (injury, 0.891), then the knee/lunge chat signal (0.826), then lunge/knee-drive
  exercises — i.e., the vector search surfaces the right injury + movements. Earlier
  stub run also confirmed the index/cosine path (exact-text → #1 @ 1.0).
  Remaining follow-up: the API Docker image needs a rebuild to include `openai`
  (handled when the API uses embeddings, P2-T3/P3).
- **Note:** `EMBEDDING_DIM` change to 1536 means any pre-existing dim-384 vector index
  must be dropped (wipe the Neo4j volume: `docker compose down -v`) before re-seeding.

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

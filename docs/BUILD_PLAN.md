# Build Plan

## Project
- **Name:** Knowledge Graph Coaching Platform
- **Summary:** An AI coaching assistant that ingests synthetic member context into
  a Neo4j knowledge graph, retrieves the safety-relevant slice via GraphRAG
  (vector + traversal), and generates injury-aware, explainable workout
  recommendations a coach can interrogate ("why?"). Backend: FastAPI + LangGraph.
  Frontend: Expo / React Native Web. One-command Docker Compose demo.

## Source of Truth (authority order)
1. `/docs/challenge.md` — **authoritative** hard requirements & acceptance (used).
2. `/docs/PRD.md` — scope / decisions / per-component requirements / acceptance (used; primary driver; phase structure from §18).
3. `/docs/ARCHITECTURE.md` — module layout, component interfaces, tech-stack decisions, data-flow ordering (used).
- `STRATEGY.md` / `USERS.md` — context only; not a planning input beyond grounding.
- `/docs/ux.md` — **not present**, so not used.

## Planning Assumptions
- **Repo layout** is not mandated verbatim by any doc; the layout in "Architecture
  Notes" below is derived from ARCHITECTURE §3 components + the data flows in
  PRD §9. Reversible.
- **One synthetic member (Maya, PRD §16)** is the seed-data target for the MVP
  (ARCHITECTURE §10 "depth over breadth"); a second member is optional.
- **LLM/embeddings provider** chosen at build time behind the adapter
  (ARCHITECTURE §6). Plan assumes a configurable hosted provider with a local
  embedding fallback so the demo runs without forcing one key.
- **The two required tests** (challenge "test ≥2 critical paths"; PRD §11) are
  scheduled in Phase 5 per PRD §18 Priority 5, but they validate Phase 1/2
  behavior and may be written earlier as those features land.
- Open decision carried from ARCHITECTURE §3.7: Neo4j native vector index is the
  default vector store; Chroma is the documented fallback behind the retriever
  interface.

## Architecture Notes
**Stack** (ARCHITECTURE §3, §6, §7; challenge "Requirements"): Python + FastAPI
(API), LangGraph (orchestration), Neo4j with native vector index (graph +
embeddings), provider-agnostic LLM + embedder adapters, Expo / React Native Web
(frontend), Docker Compose (3 services: `neo4j`, `api`, `frontend`).

**Derived module layout** (maps tickets to files):
```text
backend/
  app/
    main.py                 # FastAPI app + router registration
    config.py               # env config (Neo4j, LLM provider, keys)
    api/
      schemas.py            # Pydantic request/response models (PRD §7.9)
      routes.py             # endpoint handlers
    graph/
      client.py             # Neo4j driver/session mgmt
      schema.py             # node/edge labels, constraints, vector index (PRD §7.1)
    ingestion/
      exercises.py          # exercises.json → nodes/edges (PRD §7.2)
      members.py            # synthetic member profile → graph (PRD §7.3)
      signals.py            # unstructured signal → structured concepts (PRD §7.4)
    retrieval/
      embeddings.py         # Embedder adapter (ARCH §6)
      retriever.py          # GraphRAG: vector + traversal + graph_trace (PRD §7.5)
    generation/
      prompts.py
      generator.py          # LLM workout generation (PRD §7.6)
    safety/
      validator.py          # deterministic validation + repair/fallback (PRD §7.7, §10)
    explain/
      builder.py            # graph_trace → explanation (PRD §7.8)
    orchestration/
      state.py              # typed pipeline state
      pipeline.py           # LangGraph StateGraph: retrieve→generate→validate→explain (ARCH §3.3)
    llm/
      client.py             # LLMClient adapter (ARCH §6)
    observability/
      logging.py            # structured logging (PRD §13)
  data/members/             # synthetic fixtures (Maya, PRD §16)
  tests/                    # critical-path tests (PRD §11)
  Dockerfile
  pyproject.toml (or requirements.txt)
frontend/                   # Expo / RN Web app (ARCH §3.1)
docker-compose.yml
.env.example
README.md
```

**Cross-cutting constraints:**
- **Data-flow ordering is fixed** (ARCHITECTURE §5, PRD §9): retrieve → generate →
  **deterministic validate** → explain. Validation runs *after* generation and
  *before* the response leaves the API.
- **Trust boundary** (ARCHITECTURE §3.1, §3.5): client renders UI and calls the
  API only — no graph, model, or safety logic on the client. All reasoning and
  every safety guarantee live in the backend.
- **Safety is deterministic, not LLM-judged** (ARCHITECTURE §1, PRD §7.7, §10):
  the LLM is never the only safety layer.
- **Explanations read the recorded `graph_trace`** (ARCHITECTURE §3.4, §3.6); they
  do not re-query or re-prompt for rationalization.

**Non-goals affecting implementation** (PRD §4; challenge "Data"): synthetic data
only — no real member/health data; no auth, billing, team admin; no medical
advice; no exercise coverage beyond `exercises.json`; demo-grade frontend only.

## Current Status
- **Overall status:** In Progress
- **Current phase:** Phase 0 — Project Scaffold & Infrastructure
- **Current ticket:** P0-T2 (P0-T1 Complete)
- **Blockers:** None

---

## Phase Breakdown

### Phase 0 — Project Scaffold & Infrastructure
**Goal**
- A runnable skeleton: repo layout, FastAPI app, Neo4j up under Compose, config,
  and a health check — so every later phase is independently testable.

**Exit Criteria**
- `docker compose up` starts `neo4j` and `api`; `GET /health` returns 200; the API
  can open a Neo4j session.

**Tickets**
- **P0-T1 — Repo scaffold & backend skeleton**
  - Objective: Create the module layout (Architecture Notes), FastAPI `app/main.py`
    with a `/health` route, `config.py` reading env vars, and dependency manifest.
  - Modules / files: `backend/app/main.py`, `app/config.py`, `app/api/routes.py`,
    `pyproject.toml`/`requirements.txt`.
  - Depends on: none.
  - Acceptance: `GET /health` → 200 locally (challenge "Dockerized local setup";
    ARCH §3.2).
  - Commit: one commit referencing P0-T1.
  - Status: Complete
- **P0-T2 — Docker Compose + Neo4j service + env template**
  - Objective: `docker-compose.yml` with `neo4j` (with vector-index-capable
    version) and `api`; `.env.example`; API connects to Neo4j on boot.
  - Modules / files: `docker-compose.yml`, `.env.example`, `backend/Dockerfile`,
    `app/graph/client.py`.
  - Depends on: P0-T1.
  - Acceptance: `docker compose up` brings up Neo4j + API; API opens a session
    (challenge "Requirements"; ARCH §7; PRD §8).
  - Commit: one commit referencing P0-T2.
  - Status: Todo

---

### Phase 1 — Core Graph, Ingestion & Deterministic Safety
**Goal**
- The graph exists and is populated; injury-aware filtering works in code over the
  graph. (PRD §18 Priority 1.)

**Exit Criteria**
- Graph schema + constraints applied; `exercises.json` and Maya ingested;
  unstructured signal produces structured nodes/edges; a deterministic query
  returns the contraindicated-exercise set for an injured member.

**Tickets**
- **P1-T1 — Graph schema, constraints & vector index**
  - Objective: Define node/edge labels and uniqueness constraints; create the
    Neo4j vector index for embeddings.
  - Modules / files: `app/graph/schema.py`, `app/graph/client.py`.
  - Depends on: P0-T2.
  - Acceptance: All PRD §7.1 node/edge types representable; constraints + vector
    index created idempotently (PRD §7.1; ARCH §3.7, §4).
  - Commit: one commit referencing P1-T1.
  - Status: Todo
- **P1-T2 — Exercise ingestion from `exercises.json`**
  - Objective: Parse `exercises.json`; create `Exercise` nodes and edges to
    `Joint`, `MuscleGroup`, `Equipment`, `MovementPattern`, and `HAS_BILATERAL_PAIR`.
  - Modules / files: `app/ingestion/exercises.py`.
  - Depends on: P1-T1.
  - Acceptance: 50 exercises ingested with `LOADS_JOINT`/`TRAINS_MUSCLE`/
    `USES_EQUIPMENT`/`HAS_MOVEMENT_PATTERN` edges; re-run is idempotent
    (PRD §7.2, §9 Ingestion steps 1–4; challenge "Data").
  - Commit: one commit referencing P1-T2.
  - Status: Todo
- **P1-T3 — Synthetic member data + profile ingestion (Maya)**
  - Objective: Author Maya fixture (PRD §16); ingest structured profile fields into
    `Member`, `Goal`, `Preference`, `Workout`/`WorkoutSession`, equipment access,
    and injury/adherence nodes/edges.
  - Modules / files: `app/ingestion/members.py`, `backend/data/members/maya.json`.
  - Depends on: P1-T2.
  - Acceptance: Maya present with goals, preferences, equipment, workout history,
    adherence, and `HAS_INJURY → Injury → AFFECTS_JOINT → Joint`; synthetic only
    (PRD §7.3, §16, §9 steps 5–9; §4 non-goal "real data").
  - Commit: one commit referencing P1-T3.
  - Status: Todo
- **P1-T4 — Unstructured signal structuring**
  - Objective: Turn a free-text signal (e.g. "my knee felt weird after lunges…")
    into a `ContextSignal` plus derived `Injury`/`Condition` and `MENTIONS_*` edges.
  - Modules / files: `app/ingestion/signals.py`.
  - Depends on: P1-T3.
  - Acceptance: Given the PRD §7.4 example input, the documented nodes/edges are
    created and linked to the member (PRD §7.4, §9 step 7).
  - Commit: one commit referencing P1-T4.
  - Status: Todo
- **P1-T5 — Deterministic injury-filter (contraindication) module**
  - Objective: Cypher-backed function returning the contraindicated exercise set
    for a member via `Member→Injury→Joint←Exercise`; also equipment filtering.
  - Modules / files: `app/safety/validator.py` (contraindication query core).
  - Depends on: P1-T4.
  - Acceptance: For an injured-knee member, all knee-loading exercises are flagged
    contraindicated; computed in-graph, not by LLM (PRD §7.7, §10; ARCH §1, §4;
    challenge "Generation"/"Safety").
  - Commit: one commit referencing P1-T5.
  - Status: Todo

---

### Phase 2 — GraphRAG Retrieval
**Goal**
- Retrieval combines vector search with graph traversal into a focused context
  window plus a `graph_trace`. (PRD §18 Priority 2.)

**Exit Criteria**
- `/api/retrieve` returns retrieved context, semantic matches, and a graph trace
  with contraindicated exercises excluded; `/api/member/:id/graph` returns the
  neighborhood.

**Tickets**
- **P2-T1 — Embedder adapter + embedding of graph nodes**
  - Objective: `Embedder` adapter (provider/local); embed relevant nodes
    (signals, injuries, goals, exercises) into the Neo4j vector index.
  - Modules / files: `app/retrieval/embeddings.py`, `app/llm/client.py` (shared config).
  - Depends on: P1-T2, P1-T4.
  - Acceptance: Nodes carry embeddings; vector similarity query returns ranked
    matches (PRD §7.5 step 1–2, §9 Retrieval step 2–3; ARCH §6).
  - Commit: one commit referencing P2-T1.
  - Status: Todo
- **P2-T2 — GraphRAG retriever (vector + traversal + trace)**
  - Objective: Embed query → vector search → resolve to graph nodes → traverse
    safety-relevant neighborhood → exclude contraindicated → return compact
    context object + `graph_trace`.
  - Modules / files: `app/retrieval/retriever.py` (uses P1-T5 contraindication core).
  - Depends on: P2-T1, P1-T5.
  - Acceptance: For "lower-body session" query on Maya, retrieval surfaces goals,
    recent history, injuries→joints, excluded exercises, and equipment; whole graph
    is **not** dumped (PRD §7.5, §9 Retrieval; challenge "Retrieval (GraphRAG)";
    ARCH §3.4).
  - Commit: one commit referencing P2-T2.
  - Status: Todo
- **P2-T3 — `/api/retrieve` + `/api/member/:id/graph` endpoints & schemas**
  - Objective: Typed Pydantic request/response models and route handlers.
  - Modules / files: `app/api/schemas.py`, `app/api/routes.py`.
  - Depends on: P2-T2.
  - Acceptance: Endpoints return the PRD §7.9 response shapes (`retrieved_context`,
    `graph_trace`, `semantic_matches`; `nodes`/`edges`) with typed schemas
    (PRD §7.9; challenge "API"; ARCH §3.2).
  - Commit: one commit referencing P2-T3.
  - Status: Todo

---

### Phase 3 — Generation, Safety Validation, Explanation & Orchestration
**Goal**
- The full pipeline produces an injury-aware workout, validates/repairs it
  deterministically, and answers "why?" from the graph trace. (PRD §18 Priority 3.)

**Exit Criteria**
- `/api/generate/workout` returns a structured workout + explanation +
  `safety_validation`; `/api/explain` returns a graph-grounded answer; the
  LangGraph pipeline wires retrieve→generate→validate→explain with a repair loop.

**Tickets**
- **P3-T1 — LLM adapter + workout generator**
  - Objective: `LLMClient` adapter and a generator that produces structured
    workout JSON (title, goal, warm-up, exercises w/ sets·reps·rest, intensity,
    substitutions, notes) from retrieved context.
  - Modules / files: `app/llm/client.py`, `app/generation/prompts.py`,
    `app/generation/generator.py`.
  - Depends on: P2-T2.
  - Acceptance: Produces the PRD §7.6 workout structure from retrieved context;
    provider configurable (PRD §7.6, §9 Generation step 1–2; ARCH §6).
  - Commit: one commit referencing P3-T1.
  - Status: Todo
- **P3-T2 — Safety validator: validation + repair + fallback**
  - Objective: Validate generated workout (unknown IDs, contraindicated joints,
    unavailable equipment, preference conflicts, malformed structure); repair from
    safe candidates or return the safe fallback.
  - Modules / files: `app/safety/validator.py` (extends P1-T5).
  - Depends on: P3-T1, P1-T5.
  - Acceptance: A contraindicated/unknown exercise is caught and repaired or
    replaced by the PRD §10 fallback; LLM is not the only safety layer
    (PRD §7.7, §10; challenge "Generation"/"Resilience").
  - Commit: one commit referencing P3-T2.
  - Status: Todo
- **P3-T3 — Explanation builder**
  - Objective: Turn the recorded `graph_trace` into a human-readable "why?" /
    "what to watch for" answer.
  - Modules / files: `app/explain/builder.py`.
  - Depends on: P3-T2.
  - Acceptance: For "why skip barbell squats?", answer traces
    Member→Injury→Joint←Exercise (matching PRD §7.8 example); grounded in trace,
    not regenerated prose (PRD §7.8; challenge "Explainability").
  - Commit: one commit referencing P3-T3.
  - Status: Todo
- **P3-T4 — LangGraph orchestration pipeline + thin/empty-context recovery**
  - Objective: `StateGraph` with typed state wiring retrieve→generate→validate→
    (repair loop)→explain; handle thin/empty retrieval by asking for more or
    stating uncertainty.
  - Modules / files: `app/orchestration/state.py`, `app/orchestration/pipeline.py`.
  - Depends on: P3-T3.
  - Acceptance: Fixed pipeline ordering enforced (ARCH §5); empty/thin context
    recovers gracefully rather than inventing (PRD §6 stories, §7.6; challenge
    "Resilience"; ARCH §3.3).
  - Commit: one commit referencing P3-T4.
  - Status: Todo
- **P3-T5 — `/api/generate/workout` + `/api/explain` endpoints & schemas**
  - Objective: Typed endpoints invoking the pipeline; structured logging of query,
    retrieved nodes, LLM calls, validation results, repair attempts, final status.
  - Modules / files: `app/api/schemas.py`, `app/api/routes.py`,
    `app/observability/logging.py`.
  - Depends on: P3-T4.
  - Acceptance: Responses match PRD §7.9 shapes incl. `safety_validation`;
    structured logs emitted (PRD §7.9, §13; challenge "API").
  - Commit: one commit referencing P3-T5.
  - Status: Todo

---

### Phase 4 — Frontend Demo UX
**Goal**
- A demo client showing the end-to-end flow. (PRD §18 Priority 4.)

**Exit Criteria**
- From the browser (RN Web build): select Maya, view her context, ask a question,
  see the workout + safety result, ask "why?", and see the explanation trace.

**Tickets**
- **P4-T1 — Expo / RN Web scaffold + API client**
  - Objective: Expo app configured for RN Web; typed API client to the backend.
  - Modules / files: `frontend/` (Expo project), API client module.
  - Depends on: P3-T5.
  - Acceptance: Web build runs and calls the backend successfully (ARCH §3.1;
    challenge "simple frontend").
  - Commit: one commit referencing P4-T1.
  - Status: Todo
- **P4-T2 — Member selector + profile/context view**
  - Objective: Select a synthetic member; show profile, goals, injuries, equipment,
    recent signals (via `/api/member/:id/graph` + ingest data).
  - Modules / files: `frontend/` screens/components.
  - Depends on: P4-T1.
  - Acceptance: Maya's context renders (PRD §7.10 minimum features 1–2).
  - Commit: one commit referencing P4-T2.
  - Status: Todo
- **P4-T3 — Query → workout → safety result + "why?" explanation view**
  - Objective: Coaching question input; render generated workout, safety validation
    result, and "why?" follow-up explanation traces.
  - Modules / files: `frontend/` screens/components.
  - Depends on: P4-T2.
  - Acceptance: The three demo asks (generate / explain / watch-for) work end-to-end
    in the UI (PRD §7.10 features 3–7, §16 demo flow; challenge "The Task" table).
  - Commit: one commit referencing P4-T3.
  - Status: Todo

---

### Phase 5 — Polish: Tests, One-Command Demo, README
**Goal**
- The required tests pass, the whole stack comes up with one command, and the
  README satisfies the brief. (PRD §18 Priority 5.)

**Exit Criteria**
- ≥2 critical-path tests pass; `docker compose up` brings up all 3 services and
  seeds the graph; README includes all PRD §14 sections including the production
  evaluation section.

**Tickets**
- **P5-T1 — Critical-path test: injury filtering**
  - Objective: Test that a generated workout for an injured-knee member contains no
    knee-loading exercise and the validator fails if one appears.
  - Modules / files: `backend/tests/test_injury_filtering.py`.
  - Depends on: P3-T2 (validates Phase 1/3 behavior).
  - Acceptance: Test passes; documents *why chosen* — core safety guarantee
    (PRD §11 Test 1; challenge "test ≥2 critical paths").
  - Commit: one commit referencing P5-T1.
  - Status: Todo
- **P5-T2 — Critical-path test: graph retrieval correctness**
  - Objective: Test that traversal surfaces the `Member→Injury→Joint←Exercise`
    neighborhood and marks the right exercises contraindicated.
  - Modules / files: `backend/tests/test_graph_retrieval.py`.
  - Depends on: P2-T2.
  - Acceptance: Test passes; documents *why chosen* — everything downstream depends
    on correct retrieval (PRD §11 Test 2; challenge "test ≥2 critical paths").
  - Commit: one commit referencing P5-T2.
  - Status: Todo
- **P5-T3 — One-command demo: Compose with frontend + graph seeding**
  - Objective: Add `frontend` service to Compose; seed the graph (exercises + Maya)
    on first boot so the demo works immediately.
  - Modules / files: `docker-compose.yml`, seed entrypoint/command.
  - Depends on: P4-T3.
  - Acceptance: Fresh `docker compose up` yields a working end-to-end demo at a URL
    (challenge "Dockerized local setup"; PRD §8, §15.1; ARCH §7).
  - Commit: one commit referencing P5-T3.
  - Status: Todo
- **P5-T4 — README incl. graph schema, API docs & production-evaluation section**
  - Objective: Write README covering overview, architecture, setup, run, tests,
    graph schema, API, synthetic data, example prompts, limitations, tradeoffs, and
    "How I would evaluate this system in production."
  - Modules / files: `README.md`.
  - Depends on: P5-T3.
  - Acceptance: All 12 PRD §14 items present, including the named production
    evaluation section (PRD §14; challenge "README"; "What We're Looking For").
  - Commit: one commit referencing P5-T4.
  - Status: Todo

---

## Dependency Order
1. P0-T1 — Repo scaffold & backend skeleton
2. P0-T2 — Docker Compose + Neo4j + env
3. P1-T1 — Graph schema, constraints & vector index
4. P1-T2 — Exercise ingestion
5. P1-T3 — Synthetic member (Maya) ingestion
6. P1-T4 — Unstructured signal structuring
7. P1-T5 — Deterministic injury-filter module
8. P2-T1 — Embedder adapter + node embeddings
9. P2-T2 — GraphRAG retriever (+ trace)
10. P2-T3 — `/api/retrieve` + `/api/member/:id/graph`
11. P3-T1 — LLM adapter + workout generator
12. P3-T2 — Safety validator: validation + repair + fallback
13. P3-T3 — Explanation builder
14. P3-T4 — LangGraph orchestration pipeline
15. P3-T5 — `/api/generate/workout` + `/api/explain`
16. P4-T1 — Expo / RN Web scaffold + API client
17. P4-T2 — Member selector + profile view
18. P4-T3 — Query → workout → safety → "why?" view
19. P5-T2 — Test: graph retrieval correctness *(can land right after P2-T2)*
20. P5-T1 — Test: injury filtering *(can land right after P3-T2)*
21. P5-T3 — One-command demo (Compose + frontend + seed)
22. P5-T4 — README + production-evaluation section

## Recommended Next Step
- **Start with:** P0-T2 — Docker Compose + Neo4j service + env template.
- **Why this is next:** P0-T1 (backend skeleton + `/health`) is Complete; P0-T2 is
  its only dependent and the next link in the chain. It brings up Neo4j + the API
  under Compose and connects the API to the graph on boot — the substrate every
  Phase 1 ingestion/retrieval/safety ticket needs in order to be exercised.

## Deferred / Out of Scope
**Non-goals (PRD §4; challenge "Data"):** real member/health data; auth & user
management; billing/subscriptions/team admin; exercise coverage beyond
`exercises.json`; medical diagnosis/advice; perfect ontology coverage; production
infrastructure; frontend polish beyond the demo.

**Stretch goals — only after the core works (PRD §17; challenge "Stretch Goals"):**
graph visualization of member context; multi-agent orchestration (retrieval /
generation / safety-reviewer agents); streaming responses; an evaluation pipeline
for retrieval relevance & recommendation quality; Langfuse / OpenTelemetry
tracing; SNOMED CT grounding; longitudinal reasoning over adherence/progression;
coach feedback loop. (A second synthetic member is also deferred.)

## Update Rules
After each implementation pass:
- Update ticket **Status** only as Todo / In Progress / Complete / Blocked.
- Update **Current Status** (phase, ticket) and the recommended next ticket.
- Record blockers briefly.
- **One ticket = one git commit** (project CLAUDE.md "Commit per ticket"); the
  message references the ticket ID/title. Commit locally; do not push unless asked.
- Run relevant lint/tests before each commit (CLAUDE.md Validation).
- Log off-spec decisions / deviations / tradeoffs in
  `docs/implementation-notes.md` (project CLAUDE.md "Running implementation notes").
- Do **not** add new scope unless the docs change.

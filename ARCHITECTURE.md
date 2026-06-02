# Architecture

How the Knowledge Graph Coaching Platform is built and why. This document makes
the concrete technical decisions the challenge brief leaves open
([`docs/challenge.md`](docs/challenge.md)), grounded in the requirements in
[`docs/PRD.md`](docs/PRD.md) and the strategy in [`STRATEGY.md`](STRATEGY.md).

> **Decisions are flagged with _[Decision]_ and a rationale.** Where the PRD says
> "any" or "preferred," a default was chosen and explained. These are reversible —
> override any of them before the build hardens.

---

## 1. Guiding principles

These follow directly from the strategy ("explainable and safe by structure"):

1. **The graph does real work.** Safety, retrieval scope, and explanation all
   derive from explicit graph relationships — not from prompt text or vibes.
2. **Safety is deterministic, not learned.** Injury filtering is enforced in
   code over graph data. The LLM is never the only safety layer.
3. **Every recommendation is traceable.** Each output carries a graph trace that
   answers "why?" without re-asking the model.
4. **Typed contracts at every boundary.** Pydantic on the backend, TypeScript on
   the frontend, a documented graph schema in between.
5. **Runnable in one command.** The whole stack comes up with Docker Compose.

---

## 2. System overview

```text
                ┌─────────────────────────────────────────┐
                │      Frontend (React Native + Expo,       │
                │        RN Web build served as web)        │
                │  member select · query · workout · why?  │
                └───────────────────┬─────────────────────┘
                                    │ HTTPS / JSON
                ┌───────────────────▼─────────────────────┐
                │            API (FastAPI, Python)         │
                │   typed REST · request/response schemas  │
                └───────────────────┬─────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────┐
                │      Orchestration (LangGraph)           │
                │  ingest → retrieve → generate → validate │
                │                     → explain            │
                └───┬───────────┬──────────┬───────────┬───┘
                    │           │          │           │
            ┌───────▼──┐  ┌─────▼────┐ ┌───▼─────┐ ┌───▼──────┐
            │ Retriever│  │  LLM     │ │ Safety  │ │Explanation│
            │ graph +  │  │ provider │ │validator│ │ builder   │
            │ vector   │  │ (pluggable)│(deterministic)│(graph trace)│
            └────┬─────┘  └──────────┘ └─────────┘ └───────────┘
                 │
        ┌────────▼─────────────────────────┐
        │   Neo4j  (graph + native vector)  │
        │  nodes · edges · embeddings index │
        └───────────────────────────────────┘
```

The orchestration layer is the spine: each coach request flows through a fixed
pipeline of retrieve → generate → validate → explain, with the graph as the
source of truth at every step.

---

## 3. Components

### 3.1 Frontend
_[Decision] React Native + Expo, with a React Native Web build served as the demo
web app._ Satisfies the PRD's "TypeScript/JavaScript" requirement from a single
React Native codebase that renders both in the browser (via `react-native-web`)
and, later, on iOS/Android — without a second codebase. For this submission the
**web build is the demo target**: it's served as static assets from a container
(§7) so `docker compose up` still brings up the full stack and a reviewer opens a
URL. Renders the member selector, query box, workout view, safety result, and
"why?" explanation traces (PRD §7.10).

_Tradeoff:_ Expo + RN Web adds a small abstraction tax versus plain web React
(react-native-web shims, Metro/Expo build) in exchange for a native-mobile path
that needs no rewrite. The demo and Docker story are unchanged because the web
build is plain static assets behind a web server.

### 3.2 API
_[Decision] FastAPI (Python)._ Pydantic-native, so the PRD's "typed
request/response schemas" (§7.9) come for free, with automatic OpenAPI docs for
the reviewer. Async fits the I/O-bound LLM + graph calls. Endpoints map 1:1 to
PRD §7.9: `/api/ingest/member`, `/api/retrieve`, `/api/generate/workout`,
`/api/explain`, `/api/member/:id/graph`.

### 3.3 Orchestration
_[Decision] LangGraph over plain LangChain._ The request lifecycle is a
multi-step stateful pipeline (retrieve → generate → validate → repair → explain)
with a conditional repair loop — that maps naturally onto a `StateGraph` with
typed state and explicit edges. It also leaves a clean seam for the stretch-goal
multi-agent split (retrieval agent / generation agent / safety reviewer) without
restructuring.

### 3.4 Retriever (GraphRAG)
Combines two signals into one focused context window (PRD §7.5):
- **Vector search** — embed the coach query, find semantically relevant nodes
  (signals, injuries, goals, exercises).
- **Graph traversal** — expand from the resolved member node across the
  safety-relevant neighborhood (injuries → joints → contraindicated exercises;
  equipment; recent history).

The retriever returns a compact context object **plus** a `graph_trace` —
traversal is recorded as it happens so explanation never re-queries.

### 3.5 Safety validator
A **deterministic** module (PRD §7.7, §10) that runs *after* generation and
*before* the response leaves the API. It rejects/repairs:
unknown exercise IDs, contraindicated movements that slipped through, unavailable
equipment, preference violations, malformed structures. On failure it either
repairs from safe candidates or returns a safe fallback explaining the gap.

### 3.6 Explanation builder
Turns the recorded `graph_trace` into a human-readable "why?" answer
(PRD §7.8). Because it reads the trace, explanations are grounded in actual
relationships, not regenerated prose.

### 3.7 Datastore
_[Decision] Neo4j with its native vector index — single datastore for both graph
and embeddings._ The PRD lists Chroma/FAISS as alternatives, but co-locating
vectors with the graph keeps Docker Compose to one stateful service, avoids a
sync problem between two stores, and lets a single Cypher query mix vector
similarity with traversal. _Fallback:_ if the native index proves limiting,
swap in Chroma behind the retriever's interface — the retriever is the only
component that touches vector search.

---

## 4. Knowledge graph schema

The full node and edge inventory lives in [`docs/PRD.md`](docs/PRD.md) §7.1. The
load-bearing safety path is:

```text
Member ─HAS_INJURY─▶ Injury ─AFFECTS_JOINT─▶ Joint ◀─LOADS_JOINT─ Exercise
```

A traversal from a member's injuries to the joints they affect, intersected with
the joints each exercise loads, yields the contraindicated set — computed in the
graph, not inferred by the model. Exercise nodes and their relationships
(`LOADS_JOINT`, `TRAINS_MUSCLE`, `USES_EQUIPMENT`, `HAS_MOVEMENT_PATTERN`,
`HAS_BILATERAL_PAIR`) are built by ingesting `exercises.json`.

---

## 5. Data flows

Detailed step lists are in `docs/PRD.md` §9. In brief:

- **Ingestion** — load `exercises.json` → exercise/joint/muscle/equipment nodes;
  load synthetic members → parse structured fields; extract structured concepts
  from unstructured signals (chat snippets, logged injuries) into nodes + edges.
- **Retrieval** — embed query → vector search → resolve matches to graph nodes →
  traverse safety-relevant neighborhood → exclude contraindicated → return
  context window + graph trace.
- **Generation** — build prompt from retrieved context → generate structured
  workout JSON → **deterministic validation** → repair or fallback → build
  explanation trace → respond.

---

## 6. LLM & embeddings

_[Decision] Provider-agnostic behind a thin interface._ The PRD allows "any
provider." A small adapter (`LLMClient` / `Embedder`) isolates the rest of the
system from the choice, configured by environment variable.
_[Decision] Default to a hosted provider (OpenAI or Anthropic) for generation,
with the embedding model from the same provider — or a local
`sentence-transformers` model_ to keep the demo runnable without a key if
desired. The provider is never on the safety-critical path (§3.5).

---

## 7. Deployment

_[Decision] Docker Compose with three services_ (PRD §8): `neo4j` (graph +
vector), `api` (FastAPI), `frontend` (the Expo **web build** — static assets
served by a lightweight web server such as nginx or `serve`). `docker compose up`
brings up the stack; an ingestion step (entrypoint or one-shot command) seeds the
graph from `exercises.json` and synthetic members so the demo works on first
boot. Native iOS/Android targets run outside Compose via the Expo dev tooling and
are out of scope for the dockerized demo.

---

## 8. Observability

Structured logging at minimum (PRD §13): incoming query, retrieved
nodes/edges, semantic matches, LLM calls, validation results, repair attempts,
final status. _Stretch:_ Langfuse / OpenTelemetry tracing with graph-query timing
and token counts — wired through the same orchestration layer.

---

## 9. Testing strategy

Two critical-path tests are required (PRD §11); both target the differentiator:

1. **Injury filtering** — given a member with a knee injury, a generated workout
   must contain no knee-loading exercise, and the validator must fail if one
   appears. _Chosen because it is the core safety guarantee — if this breaks, the
   product's central promise breaks._
2. **Graph retrieval correctness** — the `Member → Injury → Joint ← Exercise`
   traversal surfaces the right contraindicated set. _Chosen because every
   downstream safety and explanation behavior depends on retrieval returning the
   correct neighborhood._

Optional: unknown-ID validation, empty-retrieval fallback, equipment filtering,
explanation-trace correctness.

---

## 10. Tradeoffs & what's cut

- **Single datastore (Neo4j vector index)** over a dedicated vector DB — simpler
  ops, one fewer service, at the cost of best-in-class ANN tuning. Reversible
  behind the retriever interface.
- **Deterministic safety in code** over LLM-judged safety — more upfront schema
  work, but the guarantee is auditable and testable.
- **One strong synthetic member (Maya)** over broad seed data (PRD §16) — depth
  over breadth, matching the brief's stated preference.
- **Demo-grade frontend** — enough to show the end-to-end flow, not production UI.
- **Expo + RN Web** over plain web React — a small build/abstraction tax now in
  exchange for a no-rewrite path to native iOS/Android. The web build remains the
  dockerized demo target.
- **Out of scope** (PRD §4): real data, auth, billing, medical advice,
  full exercise coverage.

---

## 11. Where this maps to strategy

The four [`STRATEGY.md`](STRATEGY.md) tracks correspond directly to the
component groups above: **Knowledge graph & ingestion** (§3.7, §4, §5),
**GraphRAG retrieval** (§3.4), **Safety & explainability** (§3.5, §3.6), and
**Demo & developer experience** (§3.1, §3.2, §7).

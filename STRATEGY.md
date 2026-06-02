---
name: Knowledge Graph Coaching Platform
last_updated: 2026-06-02
---

# Knowledge Graph Coaching Platform Strategy

## Target problem

A fitness coach programming for many members can't reliably hold every member's
injuries, goals, equipment, preferences, and recent history in their head — so
safety constraints (this injury → avoid these movements) get applied
inconsistently, and once a program is built, nobody can explain *why* it was
built that way. The hard part is that this context is scattered across notes,
logs, and conversations, and the relationships between it are exactly what
determines a safe, defensible recommendation.

## Our approach

Model the member's world as an explicit knowledge graph and make the graph do
the reasoning — combining graph traversal with semantic search (GraphRAG) so
that recommendations are injury-aware by construction and every "why?" traces
back to concrete graph relationships, not an after-the-fact LLM rationalization.
We win by being *explainable and safe by structure*, not by generating
plausible-sounding workouts.

## Who it's for

**Primary:** Fitness coaches managing multiple members — they're hiring the
platform to generate safe, personalized sessions in seconds and to instantly
recall and justify the context behind any recommendation.

**Secondary:** Technical reviewers evaluating the system — they're hiring it to
judge whether the graph does real work, the safety filtering holds, and the
architecture is sound.

## Key metrics

- **Injury-filter precision** — share of generated workouts containing zero
  contraindicated exercises (the safety floor; should never regress). Measured
  via the safety validator + test suite.
- **Explanation faithfulness** — share of "why?" answers traceable to an actual
  graph path vs. ungrounded LLM prose. Measured by sampled review.
- **Retrieval relevance** — does the retrieved neighborhood contain the context
  needed for a correct decision (precision/recall on safety-relevant nodes).
- **Invalid-recommendation rate** — share of generations caught/repaired by
  validation (unknown IDs, equipment violations, schema errors). From logs.
- **AI response latency** — end-to-end generation time; target under ~5s.

## Tracks

### Knowledge graph & ingestion

The graph schema and the pipeline that turns raw member context (profiles, chat
snippets, logged injuries) into structured nodes and edges.

_Why it serves the approach:_ The graph is the substrate everything else reasons
over — if it isn't right, retrieval, safety, and explanation all fail.

### GraphRAG retrieval

Combining vector/semantic search with graph traversal to assemble a focused,
token-efficient context window around the safety-relevant neighborhood.

_Why it serves the approach:_ This is what makes the graph "do real work" rather
than be semantic search with extra steps.

### Safety & explainability

Deterministic injury-aware filtering, validation/repair of invalid outputs, and
graph-grounded explanation traces for every recommendation.

_Why it serves the approach:_ "Safe and explainable by structure" is the core
bet — this track is where it's enforced rather than hoped for.

### Demo experience & developer experience

The end-to-end runnable slice: typed REST API, simple frontend, one-command
Docker setup, and clear README.

_Why it serves the approach:_ The approach only persuades if a coach (or
reviewer) can see the full flow work end-to-end with minimal friction.

## Not working on

- Real member/health data — synthetic only.
- Auth, billing, team administration, and other production-platform surface.
- Medical diagnosis or treatment advice.
- Exhaustive exercise coverage beyond the provided `exercises.json`.

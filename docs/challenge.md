# AI Engineering — Take-Home Project: Knowledge Graph Coaching Platform

**Time:** 1–2 days | **Stack:** Python, TypeScript/JavaScript, LangChain or LangGraph, a graph database (Neo4j preferred), any LLM provider

A working system that runs end-to-end is the goal. Depth beats breadth — a focused slice that ingests real context, reasons over a graph, and explains itself is worth more than a wide system that does each part shallowly. Stub or mock anything that isn't core to the architecture.

## The Task

Build an AI coaching assistant that ingests a member's context into a knowledge graph, retrieves the relevant slice of that graph, and generates safe, personalized, explainable workout and coaching recommendations.

A coach should be able to ask things like:

| Ask | Expected behavior |
| --- | --- |
| "Build this member a lower-body session for this week." | Generates a workout that respects their injuries, goals, equipment, and recent history |
| "Why did you skip barbell squats for her?" | Explains the reasoning by pointing at graph relationships (e.g. a knee injury → joints loaded → contraindicated movement) |
| "What should I watch for with this member?" | Surfaces context: adherence trends, flagged injuries, stated goals, relevant chat history |

The differentiator is **reasoning over relationships**, not just semantic search. The graph is what lets the system explain *why*.

## The Knowledge Graph

Model the member's world as a graph. At minimum, represent:

- **Member** — profile, goals, preferences
- **Exercise** — from `exercises.json` (muscle groups, joints loaded, movement patterns, equipment, bilateral pairing)
- **Injury / condition** — what's affected and how it constrains exercise selection
- **Workout history** — what they've done, when, adherence
- **Context signals** — chat history, transcripts, biometrics, longitudinal data (mock/synthetic is fine)

You should be able to traverse, for example: `Member → has injury → Knee → maps to joint → joints_loaded → Exercise` to filter out contraindicated movements.

You're encouraged to ground health/anatomy relationships in a real ontology (e.g. SNOMED CT concepts for injuries/joints) where it adds value, but a clean hand-rolled ontology is perfectly acceptable for this scope.

## Ingestion

Ingest member context (use synthetic data — **do not use real member data**) and build the graph relationships. Show how a raw profile + a few unstructured signals (a chat snippet, a logged injury) become structured nodes and edges.

## Retrieval (GraphRAG)

Retrieval should combine graph traversal with vector / semantic search — not one or the other:

- Use vector embeddings to find semantically relevant context (e.g. matching a free-text complaint to an injury concept or exercise)
- Use graph traversal to expand from a node to its safety-relevant neighborhood
- Assemble a focused context window — be deliberate about token efficiency

## Generation

Generate a workout or coaching recommendation from the retrieved context. The output must be injury-aware: an exercise that loads an injured joint should never appear, and the system should recover gracefully when filtering leaves few valid options (recommend alternatives, not crash or hallucinate).

## Explainability

Every recommendation must be explainable. The coach should be able to ask "why?" and get an answer traceable to graph relationships, not a vague LLM rationalization.

## Resilience

Handle failure gracefully. At minimum:

- If retrieval returns thin or empty context, the system recovers — it asks for more, falls back, or says what it doesn't know rather than inventing it
- If the LLM produces an invalid recommendation (unknown exercise ID, contraindicated movement that slipped through), the system catches it and corrects

## Requirements

- Knowledge graph in a graph database (Neo4j preferred; others fine) with a documented schema — node types, edge types, and what they mean
- Ingestion pipeline that turns member context into graph nodes/edges
- GraphRAG retrieval combining graph traversal and vector search
- Generation of injury-aware, personalized recommendations with explainable reasoning
- API — REST endpoints for retrieval and generation, with typed request/response schemas
- A simple frontend — a dashboard or chat interface is enough to demo the flow end-to-end
- Dockerized local setup — `docker compose up` (or equivalent) should bring up the stack
- Test at least 2 critical paths — pick the ones that matter most (e.g. injury filtering, graph retrieval correctness) and explain why you chose them
- In your README, include a section: "How I would evaluate this system in production" — retrieval quality, safety/failure modes to monitor, latency, and how you'd know it's working. A few paragraphs is fine.
- Performance: aim for AI responses under ~5 seconds and be reasonable about prompt/token efficiency. We care more about how you reason about these than hitting an exact number.

## Stretch Goals

- Graph visualization of a member's context
- Agent workflows / multi-agent orchestration (e.g. a retrieval agent + a generation agent + a safety reviewer)
- Streaming responses
- Evaluation pipeline — measure retrieval relevance and recommendation quality
- Observability — tracing LLM calls, tool invocations, and graph queries (Langfuse, OpenTelemetry, or structured logging)
- SNOMED CT (or similar) grounding for injuries and anatomy
- Longitudinal reasoning — adherence trends and progression over time

## What We're Looking For

There's no single right architecture — we want to see how you think. We pay attention to:

- **Graph + retrieval design** — is the graph doing real work, or is it semantic search with extra steps?
- **Safety** — injury-aware filtering that actually holds up
- **Explainability** — can a coach trust and understand the output?
- **System design & API** — clean boundaries, typed contracts, sane data flow
- **Developer experience** — does it run with one command? Is the README clear?
- **Tradeoff thinking** — tell us what you cut, what you'd do with more time, and why

Working comfortably in ambiguity is part of the exercise. Where the spec is open, make a decision and explain it.

## Data

See `exercises.json` (50 exercises). Key fields: `muscle_groups`, `joints_loaded`, `movement_patterns`, `equipment_required`, `priority_tier`, `is_bilateral`, `bilateral_pair_id`. Generate synthetic members, injuries, and context signals yourself — **do not use any real member or personal data**.

## How to Submit

- Build in a public GitHub repo.
- Include the Dockerized setup, a runnable demo or recorded walkthrough, and a clear README.
- Send us the link.

Good luck — we're excited to see how you think.

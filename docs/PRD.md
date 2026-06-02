# PRD: Knowledge Graph Coaching Platform

## 1. Project Overview

Build an AI coaching assistant that helps a fitness coach generate safe, personalized, and explainable workout recommendations for a member.

The system ingests synthetic member context into a knowledge graph, retrieves the relevant graph neighborhood using GraphRAG, and generates injury-aware coaching recommendations. The key differentiator is that recommendations are not based only on semantic search or prompt context. The system must reason over explicit relationships between members, injuries, joints, exercises, workout history, goals, preferences, and context signals.

The final product should run end-to-end locally and demonstrate how a coach can ask natural language questions such as:

* “Build this member a lower-body session for this week.”
* “Why did you skip barbell squats for her?”
* “What should I watch for with this member?”

## 2. Problem & Context

Fitness coaches often need to personalize programming based on fragmented information: goals, injuries, preferences, prior workouts, adherence patterns, equipment access, chat history, and subjective feedback. This context is usually scattered across notes, workout logs, forms, and conversations.

LLMs can generate plausible workouts, but without structured reasoning they may miss safety constraints, ignore injury history, or provide explanations that sound reasonable but are not traceable. For coaching recommendations to be trusted, the system must be able to explain why a movement was included, excluded, modified, or substituted.

A knowledge graph is a strong fit because exercise safety and personalization depend on relationships:

Member → has injury → Knee
Knee → maps to joint → joints_loaded
Exercise → loads joint → Knee
Therefore: exclude or modify exercises that load the injured joint.

The goal is to demonstrate a focused, high-quality slice of a production-grade AI coaching system.

## 3. Goals

### Primary Goals

1. Build an end-to-end AI coaching assistant that ingests synthetic member data into a knowledge graph.
2. Model relationships among members, injuries, exercises, joints, equipment, goals, workout history, and context signals.
3. Use GraphRAG to combine semantic search with graph traversal.
4. Generate personalized workout and coaching recommendations that respect injuries, goals, preferences, equipment, and recent workout history.
5. Provide traceable explanations for every recommendation and exclusion.
6. Catch unsafe or invalid model outputs before returning them to the user.
7. Expose the system through typed REST APIs and a simple frontend.
8. Provide a Dockerized local setup and clear README.

### Secondary Goals

1. Demonstrate thoughtful failure handling when retrieval context is thin or incomplete.
2. Keep response latency reasonable, aiming for under roughly 5 seconds.
3. Show how this system would be evaluated and monitored in production.
4. Include at least two meaningful tests covering the most important failure modes.

## 4. Non-Goals

The system does not need to be a full production fitness platform.

Out of scope:

* Real member data.
* Authentication and user management.
* Billing, subscriptions, or coach/team administration.
* Full exercise library beyond the provided `exercises.json`.
* Medical diagnosis or treatment advice.
* Perfect ontology coverage.
* Full production-grade infrastructure.
* Exhaustive frontend polish.

Synthetic data is required. Any real health or member data should be avoided.

## 5. Target Users

### Primary User: Fitness Coach

A coach uses the system to understand a member’s context, generate workouts, and ask follow-up questions about recommendation logic.

The coach needs:

* Safe workout generation.
* Fast context recall.
* Explainable exercise selection.
* Visibility into risks, injuries, adherence, and recent member signals.

### Secondary User: Reviewer / Evaluator

A technical reviewer evaluates the architecture, implementation quality, graph design, safety behavior, API boundaries, and tradeoff thinking.

The reviewer needs:

* One-command local setup.
* Clear README.
* Demonstrable end-to-end flow.
* Tests for critical safety and retrieval paths.
* Evidence that the graph is doing meaningful reasoning.

## 6. Core User Stories

### Story 1: Generate an Injury-Aware Workout

As a coach, I want to ask for a workout for a specific member so that I can quickly generate a session that respects their goals, injuries, equipment, and recent history.

Example prompt:

> Build this member a lower-body session for this week.

Expected behavior:

* Retrieves the member’s goals, preferences, available equipment, injuries, workout history, and relevant context signals.
* Traverses the graph to identify contraindicated exercises.
* Generates a session using safe exercises only.
* Provides substitutions or regressions if many exercises are filtered out.
* Explains the reasoning behind key selections.

### Story 2: Explain an Exercise Exclusion

As a coach, I want to ask why an exercise was skipped so that I can understand and trust the system’s recommendation.

Example prompt:

> Why did you skip barbell squats for her?

Expected behavior:

* Identifies the excluded exercise.
* Traces relevant graph relationships.
* Explains the decision using concrete graph evidence.
* Avoids vague LLM rationalization.

Example explanation:

> Barbell squats were skipped because the member has a logged knee injury. The knee injury maps to the knee joint, and barbell squats load the knee joint heavily. Because this member’s injury constraint excludes knee-loaded bilateral squatting patterns this week, the system substituted hip-dominant and lower-load alternatives.

### Story 3: Surface Coaching Watchouts

As a coach, I want to ask what to watch for with a member so that I can proactively manage risk, motivation, and adherence.

Example prompt:

> What should I watch for with this member?

Expected behavior:

* Surfaces injuries, adherence trends, recent complaints, stated goals, relevant chat history, and biometric or longitudinal signals if available.
* Separates safety concerns from coaching opportunities.
* States uncertainty when evidence is thin.

## 7. Functional Requirements

### 7.1 Knowledge Graph

The system must use a graph database. Neo4j is preferred, but another graph database is acceptable if justified.

At minimum, the graph must represent:

#### Node Types

* `Member`
* `Goal`
* `Preference`
* `Exercise`
* `MuscleGroup`
* `Joint`
* `MovementPattern`
* `Equipment`
* `Injury`
* `Condition`
* `Workout`
* `WorkoutSession`
* `ContextSignal`
* `ChatSnippet`
* `Transcript`
* `BiometricSignal`

#### Core Edge Types

* `Member HAS_GOAL Goal`
* `Member HAS_PREFERENCE Preference`
* `Member HAS_INJURY Injury`
* `Injury AFFECTS_JOINT Joint`
* `Exercise LOADS_JOINT Joint`
* `Exercise TRAINS_MUSCLE MuscleGroup`
* `Exercise USES_EQUIPMENT Equipment`
* `Exercise HAS_MOVEMENT_PATTERN MovementPattern`
* `Member COMPLETED_WORKOUT Workout`
* `Workout CONTAINS_EXERCISE Exercise`
* `Member HAS_CONTEXT_SIGNAL ContextSignal`
* `ContextSignal MENTIONS_INJURY Injury`
* `ContextSignal MENTIONS_GOAL Goal`
* `Exercise HAS_BILATERAL_PAIR Exercise`

The graph schema must be documented in the README, including what each node and edge type means.

### 7.2 Exercise Ingestion

The system must ingest the provided `exercises.json` file.

Exercise fields should include:

* Exercise ID
* Name
* Muscle groups
* Joints loaded
* Movement patterns
* Equipment required
* Priority tier
* Bilateral status
* Bilateral pair ID, if applicable

The ingestion process should create exercise nodes and relationship edges to muscles, joints, movement patterns, and equipment.

### 7.3 Synthetic Member Data

The system must generate or include synthetic members.

Each synthetic member should include:

* Profile information
* Goals
* Preferences
* Equipment access
* Injury or condition history
* Workout history
* Adherence information
* Unstructured context signals, such as chat snippets or transcripts
* Optional biometrics or longitudinal signals

No real member or personal data should be used.

### 7.4 Unstructured Signal Structuring

The system must demonstrate how raw unstructured context becomes structured graph data.

Example input:

> “My knee has been bothering me after lunges, but I still want to train legs this week.”

Expected structured output:

* `ContextSignal` node containing the raw text.
* `Injury` or `Condition` node related to knee discomfort.
* Relationship from member to injury.
* Relationship from injury to affected joint.
* Possible relationship from context signal to goal or training intent.

### 7.5 GraphRAG Retrieval

Retrieval must combine semantic search and graph traversal.

The system should:

1. Use vector embeddings to identify semantically relevant context.
2. Map free-text questions or complaints to relevant graph nodes.
3. Traverse graph relationships to retrieve safety-relevant neighborhoods.
4. Assemble a focused context window for generation.
5. Avoid dumping the entire graph into the prompt.

Example retrieval flow:

1. Coach asks: “Build this member a lower-body session.”
2. Semantic search finds relevant member goals, recent lower-body complaints, and workout history.
3. Graph traversal expands from the member to injuries, joints, excluded exercises, available equipment, and recent workouts.
4. Retrieval returns a compact context object for generation.

### 7.6 Workout Generation

The system must generate personalized coaching recommendations.

Workout output should include:

* Session title
* Session goal
* Warm-up
* Exercise list
* Sets and reps
* Intensity guidance
* Rest guidance
* Substitutions or regressions
* Notes for the coach
* Explanation trace

The workout must be injury-aware.

An exercise that loads an injured or contraindicated joint should not appear in the final recommendation. If too few valid exercises remain, the system should recover by:

* Recommending safer alternatives.
* Reducing intensity or range of motion.
* Suggesting upper-body, mobility, recovery, or coach follow-up options.
* Stating that it does not have enough safe options rather than hallucinating.

### 7.7 Safety Validation

The system must validate generated recommendations before returning them.

Validation should catch:

* Unknown exercise IDs.
* Exercises not present in the exercise library.
* Exercises that violate injury constraints.
* Exercises requiring unavailable equipment.
* Exercises that conflict with explicit member preferences.
* Empty or malformed workout structures.

If validation fails, the system should either:

1. Automatically repair the recommendation using safe alternatives, or
2. Return a safe fallback explaining what failed and what information is needed.

The LLM should not be the only safety layer. Safety rules should be deterministic where possible.

### 7.8 Explainability

Every recommendation must be explainable.

The system should support follow-up questions such as:

* “Why did you include this?”
* “Why did you exclude that?”
* “What constraints affected this workout?”
* “What should I watch for?”

Explanations must refer to graph relationships.

Example trace:

* Member has injury: knee discomfort.
* Knee discomfort affects joint: knee.
* Barbell squat loads joint: knee.
* Therefore barbell squat was excluded.
* Goblet box squat or hip bridge was selected because it better matches available equipment, lower joint load, and the member’s goal.

The explanation should be human-readable but grounded in graph evidence.

### 7.9 API

The system must expose typed REST endpoints.

Recommended endpoints:

#### `POST /api/ingest/member`

Ingest a synthetic member profile and context signals.

Request:

```json
{
  "member": {},
  "context_signals": []
}
```

Response:

```json
{
  "member_id": "member_001",
  "nodes_created": 12,
  "edges_created": 28,
  "status": "success"
}
```

#### `POST /api/retrieve`

Retrieve graph and semantic context for a coach query.

Request:

```json
{
  "member_id": "member_001",
  "query": "Build a lower-body session for this week"
}
```

Response:

```json
{
  "member_id": "member_001",
  "retrieved_context": {},
  "graph_trace": [],
  "semantic_matches": []
}
```

#### `POST /api/generate/workout`

Generate an injury-aware workout.

Request:

```json
{
  "member_id": "member_001",
  "query": "Build this member a lower-body session for this week"
}
```

Response:

```json
{
  "workout": {},
  "explanation": {},
  "safety_validation": {
    "passed": true,
    "issues": []
  }
}
```

#### `POST /api/explain`

Answer a why-question using graph evidence.

Request:

```json
{
  "member_id": "member_001",
  "question": "Why did you skip barbell squats for her?",
  "recommendation_id": "rec_001"
}
```

Response:

```json
{
  "answer": "Barbell squats were skipped because...",
  "graph_trace": []
}
```

#### `GET /api/member/:member_id/graph`

Return the member’s relevant graph neighborhood for debugging or visualization.

Response:

```json
{
  "nodes": [],
  "edges": []
}
```

### 7.10 Frontend

Build a simple frontend sufficient to demo the end-to-end flow.

Minimum frontend features:

* Select a synthetic member.
* View member profile, goals, injuries, equipment, and recent signals.
* Ask a coaching question.
* Generate a workout.
* View safety validation result.
* Ask “why?” follow-up questions.
* Display explanation traces.

Nice-to-have:

* Graph visualization of the member context.
* Highlight excluded exercises and reasons.
* Streaming generation.
* Debug panel showing retrieval results.

## 8. Technical Requirements

### Required Stack

* Backend: Python preferred.
* Frontend: TypeScript or JavaScript.
* Orchestration: LangChain or LangGraph.
* Graph database: Neo4j preferred.
* LLM provider: any.
* Embeddings: any provider or local embedding model.
* Local setup: Docker Compose or equivalent.

### Suggested Architecture

```text
Frontend
  ↓
REST API
  ↓
Application Service Layer
  ↓
Retriever
  ├── Vector Search
  └── Graph Traversal
  ↓
Prompt / Generation Layer
  ↓
Safety Validator
  ↓
Explanation Builder
  ↓
Response
```

### Suggested Services

* `api`: Backend REST server.
* `frontend`: Demo UI.
* `neo4j`: Graph database.
* `vector-store`: Can be built into Neo4j, local FAISS, Chroma, or another lightweight option.

## 9. Data Flow

### Ingestion Flow

1. Load `exercises.json`.
2. Create exercise nodes.
3. Create joints, muscles, equipment, and movement pattern nodes.
4. Link exercises to relevant graph entities.
5. Load synthetic member profiles.
6. Parse structured profile fields.
7. Extract structured concepts from unstructured context signals.
8. Create member, injury, goal, preference, workout, and signal nodes.
9. Create edges among member context, anatomy, constraints, and exercise library.

### Retrieval Flow

1. Receive coach query.
2. Embed query.
3. Search vector index for relevant signals, injuries, goals, and exercises.
4. Resolve semantic matches to graph nodes.
5. Traverse graph from member to constraints, recent history, goals, preferences, equipment, and relevant exercise candidates.
6. Exclude contraindicated exercises.
7. Return focused context window and graph trace.

### Generation Flow

1. Build prompt from focused retrieved context.
2. Generate structured workout JSON.
3. Validate workout deterministically.
4. Repair or fallback if validation fails.
5. Generate explanation trace.
6. Return final response.

## 10. Safety Requirements

The system must enforce injury-aware filtering before returning a workout.

Hard safety rules:

* Do not recommend exercises that load an injured joint unless explicitly marked as safe or modified.
* Do not recommend exercises requiring unavailable equipment.
* Do not recommend unknown exercises.
* Do not hide uncertainty.
* Do not provide medical diagnosis.
* Do not invent member history.
* Do not claim a graph relationship exists unless it was retrieved or derived from ingested data.

Recommended safety response when context is insufficient:

> I do not have enough safe lower-body options based on the current injury context. I recommend a coach review before loading the knee joint. Safe alternatives may include low-load hip-dominant work, mobility, or upper-body training until more information is available.

## 11. Testing Requirements

Include at least two tests for critical paths.

Recommended tests:

### Test 1: Injury Filtering

Purpose:

Ensure that exercises loading an injured joint are excluded from recommendations.

Example:

* Member has knee injury.
* Barbell squat loads knee.
* Generated workout should not contain barbell squat.
* Validator should fail if a knee-loaded exercise appears.

### Test 2: Graph Retrieval Correctness

Purpose:

Ensure graph traversal returns the relevant safety neighborhood.

Example:

* Member → has injury → knee injury.
* Knee injury → affects joint → knee.
* Exercise → loads joint → knee.
* Retrieval should surface this relationship and mark the exercise as contraindicated.

Additional optional tests:

* Unknown exercise ID validation.
* Empty retrieval fallback.
* Equipment filtering.
* Explanation trace correctness.
* Thin context recovery.

## 12. Performance Requirements

Target response time:

* Aim for AI responses under roughly 5 seconds.

The system should be reasonable about:

* Token usage.
* Number of graph queries.
* Size of retrieved context.
* Avoiding unnecessary full-graph retrieval.
* Caching static exercise relationships.

Exact latency is less important than demonstrating thoughtful design and clear tradeoffs.

## 13. Observability

At minimum, use structured logging for:

* Incoming query.
* Retrieved graph nodes and edges.
* Semantic matches.
* LLM calls.
* Safety validation results.
* Repair attempts.
* Final recommendation status.

Stretch observability:

* Langfuse tracing.
* OpenTelemetry.
* Graph query timing.
* Token usage tracking.
* Retrieval relevance scores.

## 14. README Requirements

The README must include:

1. Project overview.
2. Architecture diagram or explanation.
3. Local setup instructions.
4. How to run the app.
5. How to run tests.
6. Graph schema documentation.
7. API documentation.
8. Synthetic data explanation.
9. Example prompts to try.
10. Known limitations.
11. Tradeoffs and what was intentionally cut.
12. Section titled: “How I would evaluate this system in production.”

### Production Evaluation Section Should Cover

* Retrieval quality.
* Safety failure modes.
* Injury filtering accuracy.
* Invalid recommendation rate.
* Explanation faithfulness.
* Latency.
* Token usage.
* Coach satisfaction.
* Member outcome proxies.
* Human review workflows.
* Monitoring and alerting.

## 15. Success Criteria

A successful submission should demonstrate:

1. The app runs locally with one command.
2. Exercise data is ingested into a graph.
3. Synthetic member context is ingested into a graph.
4. Unstructured context is transformed into structured nodes and edges.
5. Graph traversal is used for real decision-making.
6. Vector search is used for semantic matching.
7. The system generates a safe, personalized workout.
8. Injury constraints are enforced.
9. Invalid LLM outputs are caught.
10. Explanations are traceable to graph relationships.
11. REST APIs are typed and documented.
12. Frontend demonstrates the end-to-end flow.
13. Tests cover important safety and retrieval behavior.
14. README explains architecture, setup, tradeoffs, and production evaluation.

## 16. Suggested Demo Scenario

Use one strong synthetic member instead of trying to support many shallow examples.

Example member:

* Name: Maya
* Goal: Build lower-body strength and return to consistent training.
* Injury: Recent knee pain aggravated by lunges and deep squats.
* Equipment: Dumbbells, resistance bands, bench, cable machine.
* Preference: Enjoys glute-focused workouts, dislikes high-impact movements.
* Recent history: Missed two workouts last week; completed upper-body session three days ago.
* Chat signal: “My knee felt weird after lunges, but I still want to train legs this week.”
* Adherence signal: 65% completion over the past month.

Demo flow:

1. Ingest Maya’s profile and signals.
2. Show generated graph relationships.
3. Ask: “Build Maya a lower-body session for this week.”
4. Show safe workout.
5. Ask: “Why did you skip barbell squats?”
6. Show graph-grounded explanation.
7. Ask: “What should I watch for?”
8. Surface adherence trend, knee pain, lower-body goal, and suggested coach follow-up.

## 17. Stretch Goals

Stretch goals should only be attempted after the core system works.

Potential stretch goals:

* Graph visualization of member context.
* Multi-agent workflow with retrieval agent, generation agent, and safety reviewer.
* Streaming responses.
* Evaluation pipeline for retrieval relevance and recommendation quality.
* Observability with Langfuse or OpenTelemetry.
* SNOMED CT or similar grounding for injuries and anatomy.
* Longitudinal reasoning over adherence and progression.
* Coach feedback loop to improve future recommendations.

## 18. Recommended Implementation Priorities

### Priority 1: Core Graph and Safety

* Ingest exercises.
* Ingest one or two synthetic members.
* Model injuries, joints, equipment, and exercise constraints.
* Implement deterministic injury filtering.

### Priority 2: GraphRAG

* Add vector search.
* Combine semantic matches with graph traversal.
* Build focused retrieval context.

### Priority 3: Generation and Validation

* Generate structured workout JSON.
* Validate and repair unsafe outputs.
* Produce graph-grounded explanations.

### Priority 4: Demo UX

* Build simple frontend.
* Add member selector.
* Add coach query input.
* Show workout, safety result, and explanation trace.

### Priority 5: Polish

* Docker Compose.
* Tests.
* README.
* Production evaluation section.
* Optional graph visualization.

## 19. Key Product Principle

The graph must do real work.

This project should not be a chatbot with a graph database attached. The graph should directly influence recommendation safety, retrieval, filtering, and explanation. The strongest version of this project will make it obvious that the system can answer “why?” because it has explicit relationships to reason over.

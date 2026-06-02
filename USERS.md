# Users

Who this product is for, what they're trying to do, and what they need from it.
Grounded in [`STRATEGY.md`](STRATEGY.md) and [`docs/PRD.md`](docs/PRD.md).

A note on terminology: the **coach** is the user — they operate the product. The
**member** is the subject the coach is programming for. Members are modeled in
the knowledge graph but do not use the system directly in this scope.

---

## Primary user: the fitness coach

A coach managing multiple members who needs to program safe, personalized
sessions quickly and justify the reasoning behind them.

**Job to be done:** "Generate a safe, personalized session for this member in
seconds, and let me instantly recall and explain the context behind any
recommendation."

**Situation:** Programming for many members at once. Each member's injuries,
goals, equipment, preferences, and recent history live in scattered notes, logs,
and chat threads. The coach can't hold it all in their head, so safety
constraints get applied inconsistently and prior decisions are hard to justify
after the fact.

**Goals:**

- Produce a workout that respects injuries, goals, equipment, and recent history.
- Trust that contraindicated movements never slip through.
- Understand *why* an exercise was included, excluded, or substituted.
- See risks and watch-outs (injuries, adherence trends, recent complaints) at a glance.

**Pain points today:**

- Context is fragmented across notes, forms, logs, and conversations.
- Safety reasoning lives in the coach's head and isn't applied consistently.
- Generic AI tools produce plausible workouts but can't explain or defend them.
- No traceable record of *why* a program was built a certain way.

**What they need from the product:**

- Fast, injury-aware workout generation.
- Graceful recovery when few safe options remain (alternatives, not crashes or hallucinations).
- "Why?" answers grounded in graph relationships, not vague rationalization.
- A quick read on what to watch for with a given member.

**Key scenarios** (see the Maya demo in `docs/PRD.md` §16):

1. *Generate* — "Build this member a lower-body session for this week."
2. *Explain* — "Why did you skip barbell squats for her?"
3. *Watch-outs* — "What should I watch for with this member?"

---

## Secondary user: the technical reviewer / evaluator

A reviewer assessing the system's architecture, safety behavior, and quality —
the audience for the take-home submission.

**Job to be done:** "Judge quickly whether the graph does real work, the safety
filtering actually holds, and the system is well-built."

**Goals:**

- Run the whole thing end-to-end with minimal friction.
- Confirm the graph drives real reasoning, not semantic search with extra steps.
- Verify injury-aware filtering holds up under test.
- Understand the tradeoffs the builder made and why.

**What they need from the product:**

- One-command local setup (`docker compose up` or equivalent).
- A clear README: architecture, schema, API, example prompts, limitations, tradeoffs.
- Tests covering the critical safety and retrieval paths.
- A runnable demo or recorded walkthrough.

---

## Subject (not a user): the member

The person the coach programs for — e.g. **Maya** in the demo scenario. Members
are represented in the knowledge graph (profile, goals, preferences, injuries,
workout history, adherence, context signals) and are the subject of every
recommendation, but they do not interact with the system in this scope.

**Why they matter here:** the richness and accuracy of the member's graph is
what makes a recommendation safe and explainable. Modeling the member well is a
product concern even though the member is not a user.

> Members use **synthetic data only** — no real member or personal health data.
> See `docs/PRD.md` §4 and §7.3.

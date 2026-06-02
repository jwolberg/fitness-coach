# Runbook — Running Locally

Operational guide for running the Knowledge Graph Coaching Platform on your machine.
For architecture and design, see [`../README.md`](../README.md) and
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).

---

## 0. Prerequisites

| For | Need |
| --- | --- |
| One-command demo (recommended) | Docker + Docker Compose |
| Local dev (no Docker) | Python 3.11+, Node 22+, a running Neo4j 5.x |
| Either way | An **OpenAI API key** (embeddings + generation are OpenAI-only) |

> **The OpenAI key is required.** Without it the graph still seeds, but retrieval and
> generation will fail (there is no local embedding/LLM fallback — a deliberate
> tradeoff; see README §11).

---

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```ini
OPENAI_API_KEY=sk-...
```

Defaults that usually need no change:

| Var | Default | Notes |
| --- | --- | --- |
| `NEO4J_USER` / `NEO4J_PASSWORD` | `neo4j` / `password` | local dev only |
| `LLM_MODEL` | `gpt-4o-mini` | generation model |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `text-embedding-3-small` / `1536` | **must match each other** and the vector index |
| `CORS_ALLOW_ORIGINS` | `*` | browser origins allowed to call the API |
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000` | baked into the web build |

> Never commit `.env` — it's git-ignored.

---

## 2. Run the full stack (one command)

```bash
docker compose up --build
```

Boot order (Compose handles it): **neo4j** (waits until healthy) → **seed**
(one-shot: schema + exercises + Maya + embeddings, then exits) → **api** → **frontend**.

| Service | URL | Notes |
| --- | --- | --- |
| frontend | **http://localhost:8081** | the demo UI — start here |
| api | http://localhost:8000 | OpenAPI docs at `/docs` |
| neo4j | http://localhost:7474 | Neo4j Browser (user `neo4j`, pass from `.env`) |
| seed | — | runs once and exits with code 0 |

First build takes a few minutes (installs deps + builds the Expo web bundle). Stop with
`Ctrl-C`, or run detached with `docker compose up -d --build`.

### Verify it's up

```bash
curl localhost:8000/health                      # {"status":"ok"}
docker compose logs seed | grep -E "Seeded|Embedded"   # "Seeded graph: 50 exercises" + "Embedded 54 nodes"
docker compose ps                               # api/frontend Up, neo4j healthy, seed Exited (0)
```

### Try the demo

Open **http://localhost:8081**, then:
1. Maya is selected — review her profile (knee injury, 21 excluded exercises, goals, equipment).
2. "Ask the coach" → keep the default query → **Generate workout** (a safe, injury-aware session).
3. "Ask why?" → **Why did you skip barbell squats for her?** → see the graph-evidence trace.
4. Try **What should I watch for with this member?**

### Stop / reset

```bash
docker compose down            # stop containers, keep the graph (named volume)
docker compose down -v         # ALSO wipe the Neo4j volume (full reset / re-seed next up)
```

---

## 3. Run locally without Docker (dev loop)

Useful for fast iteration on the backend or frontend.

### 3a. Neo4j (still via Docker — simplest)

```bash
docker compose up -d neo4j
```

### 3b. Backend API

```bash
cd backend
python -m venv .venv
./.venv/bin/pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
export NEO4J_URI=bolt://localhost:7687        # localhost, not the compose hostname

./.venv/bin/python -m app.seed                # seed schema + data + embeddings (idempotent)
./.venv/bin/uvicorn app.main:app --reload     # API on http://localhost:8000
```

### 3c. Frontend

```bash
cd frontend
npm install
EXPO_PUBLIC_API_URL=http://localhost:8000 npm run web   # web on http://localhost:8081
```

---

## 4. Run the tests

Two critical-path tests over the deterministic graph layer. They need Neo4j running but
**no OpenAI key** (they skip with a clear message if Neo4j is unreachable).

```bash
docker compose up -d neo4j
cd backend
PYTHONPATH=. NEO4J_URI=bolt://localhost:7687 ./.venv/bin/pytest tests/ -v
```

Expected: `7 passed`. (`test_injury_filtering.py` = injury filtering; `test_graph_retrieval.py` = retrieval correctness.)

---

## 5. Re-seeding the graph

The seed step is **idempotent** — safe to re-run any time:

```bash
# in Docker
docker compose run --rm seed
# local dev
cd backend && OPENAI_API_KEY=sk-... NEO4J_URI=bolt://localhost:7687 ./.venv/bin/python -m app.seed
```

You must re-seed (or wipe the volume) if you change `EMBEDDING_DIM`/`EMBEDDING_MODEL`,
because the vector index dimension is fixed at creation (see Troubleshooting).

---

## 6. Troubleshooting

| Symptom | Cause / Fix |
| --- | --- |
| Frontend shows **"backend: error" / Failed to fetch** | API not up, or CORS. Confirm `curl localhost:8000/health`; ensure `CORS_ALLOW_ORIGINS` allows the UI origin (default `*`). |
| `/api/retrieve` or `/api/generate/workout` → 500 | Missing/invalid `OPENAI_API_KEY`, or the graph has no embeddings. Set the key and re-seed (§5). |
| Seed logs **"OPENAI_API_KEY not set — skipped embeddings"** | Graph seeded but vectors absent → retrieval fails. Set the key and re-run the seed. |
| **Vector dimension mismatch** after changing `EMBEDDING_DIM` | The index was created at the old dimension. `docker compose down -v` (wipe volume), then `up` to recreate at the new dim. |
| `api` exits / never starts | It waits for `seed` to finish successfully. Check `docker compose logs seed` — a failed seed (e.g., bad key, neo4j down) blocks the API. |
| Port already in use (8000 / 8081 / 7474 / 7687) | Another process/stack is bound. Stop it, or change the host port mappings in `docker-compose.yml`. |
| neo4j stuck "starting" / unhealthy | Give it ~20–40s on first boot; check `docker compose logs neo4j`. Low disk can stall it. |
| Generation feels slow (~7–8s) | Expected — embedding + LLM round-trips (above the ~5s target; see README §10). |
| Editing frontend code shows no change | Metro caches the bundle; restart the web server (`npm run web`), or rebuild the image (`docker compose up --build frontend`). |

### Handy checks

```bash
docker compose logs -f api          # follow API + structured event logs (generate.request, etc.)
docker compose ps                   # service health/status
# In Neo4j Browser (http://localhost:7474):
#   MATCH (e:Exercise) RETURN count(e)                 // expect 50
#   SHOW INDEXES YIELD name, type WHERE type='VECTOR'  // expect 1
#   MATCH (:Member {id:'maya'})-[:HAS_INJURY]->(:Injury)-[:AFFECTS_JOINT]->(j) RETURN j.name  // 'knee'
```

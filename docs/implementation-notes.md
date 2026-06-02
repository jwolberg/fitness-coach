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

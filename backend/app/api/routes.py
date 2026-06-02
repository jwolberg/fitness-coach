"""API route handlers.

`/health` is the liveness check (P0-T1). P2-T3 adds the typed GraphRAG endpoints
`POST /api/retrieve` and `GET /api/member/:id/graph` (PRD §7.9). Generation/explain
endpoints land in P3-T5.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    ExplainRequest,
    ExplainResponse,
    GenerateWorkoutRequest,
    GenerateWorkoutResponse,
    MemberGraphResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.explain.builder import explain
from app.observability.logging import log_event
from app.orchestration.pipeline import run_workout_pipeline
from app.retrieval.retriever import member_graph, retrieve

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns 200 so Compose / the reviewer can confirm the API is up."""
    return {"status": "ok"}


@router.post("/api/retrieve", response_model=RetrieveResponse)
def api_retrieve(req: RetrieveRequest) -> RetrieveResponse:
    """Return the focused GraphRAG context + graph trace + semantic matches (PRD §7.9)."""
    try:
        result = retrieve(req.member_id, req.query)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    graph_trace = result.pop("graph_trace")
    semantic_matches = result.pop("semantic_matches")
    return RetrieveResponse(
        member_id=req.member_id,
        retrieved_context=result,
        graph_trace=graph_trace,
        semantic_matches=semantic_matches,
    )


@router.get("/api/member/{member_id}/graph", response_model=MemberGraphResponse)
def api_member_graph(member_id: str) -> MemberGraphResponse:
    """Return the member's safety-relevant graph neighborhood for viz/debugging (PRD §7.9)."""
    graph = member_graph(member_id)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"Member '{member_id}' not found")
    return MemberGraphResponse(**graph)


@router.post("/api/generate/workout", response_model=GenerateWorkoutResponse)
def api_generate_workout(req: GenerateWorkoutRequest) -> GenerateWorkoutResponse:
    """Run the full pipeline and return workout + explanation + safety_validation (PRD §7.9)."""
    log_event("generate.request", member_id=req.member_id, query=req.query)
    try:
        result = run_workout_pipeline(req.member_id, req.query)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    sv = result["safety_validation"]
    ctx = result.get("retrieved_context") or {}
    log_event(
        "generate.result",
        member_id=req.member_id,
        status=result.get("status"),
        exercises=len((result.get("workout") or {}).get("exercises", []) or []),
        safe_candidates=len(ctx.get("safe_candidates", [])),
        excluded=len(ctx.get("excluded_exercises", [])),
        passed=sv.get("passed"),
        repaired=sv.get("repaired"),
        used_fallback=sv.get("used_fallback"),
    )
    return GenerateWorkoutResponse(
        workout=result["workout"],
        explanation=result["explanation"],
        safety_validation=sv,
        status=result.get("status"),
    )


@router.post("/api/explain", response_model=ExplainResponse)
def api_explain(req: ExplainRequest) -> ExplainResponse:
    """Answer a why-question from graph evidence (PRD §7.9)."""
    log_event("explain.request", member_id=req.member_id, question=req.question)
    try:
        ctx = retrieve(req.member_id, req.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    answer = explain(req.question, req.member_id, ctx)
    log_event("explain.result", member_id=req.member_id, trace_len=len(answer.get("graph_trace", [])))
    return ExplainResponse(answer=answer["answer"], graph_trace=answer["graph_trace"])

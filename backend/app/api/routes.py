"""API route handlers.

`/health` is the liveness check (P0-T1). P2-T3 adds the typed GraphRAG endpoints
`POST /api/retrieve` and `GET /api/member/:id/graph` (PRD §7.9). Generation/explain
endpoints land in P3-T5.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import MemberGraphResponse, RetrieveRequest, RetrieveResponse
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

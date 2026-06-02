"""LangGraph orchestration: retrieve → generate → validate → explain (ARCH §3.3, §5).

A `StateGraph` enforces the fixed pipeline ordering — validation always runs after
generation and before the response. A conditional edge after retrieval handles
thin/empty context: if there are no safe candidates at all, the pipeline skips the
LLM and routes to a deterministic safe fallback rather than inventing exercises
(PRD resilience; challenge "Resilience").

    START → retrieve → ┌─ generate ─┐ → validate → explain → END
                       └─ fallback ─┘
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.explain.builder import explain
from app.generation.generator import generate_from_context
from app.orchestration.state import PipelineState
from app.retrieval.retriever import retrieve
from app.safety.validator import safe_fallback, validate_and_repair

logger = logging.getLogger(__name__)


def _retrieve_node(state: PipelineState) -> dict[str, Any]:
    ctx = retrieve(state["member_id"], state["query"])
    return {"retrieved_context": ctx}


def _route_after_retrieve(state: PipelineState) -> str:
    """Thin/empty context → fallback; otherwise generate."""
    ctx = state["retrieved_context"]
    if not ctx.get("safe_candidates"):
        logger.info("Thin context for '%s' — routing to safe fallback", state["member_id"])
        return "fallback"
    return "generate"


def _generate_node(state: PipelineState) -> dict[str, Any]:
    workout = generate_from_context(state["retrieved_context"], state["query"])
    return {"workout": workout, "status": "ok"}


def _fallback_node(state: PipelineState) -> dict[str, Any]:
    return {"workout": safe_fallback(state["member_id"]), "status": "insufficient_context"}


def _validate_node(state: PipelineState) -> dict[str, Any]:
    """Deterministic safety gate — always runs before the response (ARCH §5)."""
    result = validate_and_repair(state["member_id"], state["workout"])
    return {"workout": result["workout"], "safety_validation": result["safety_validation"]}


def _explain_node(state: PipelineState) -> dict[str, Any]:
    exp = explain("what constraints affected this workout", state["member_id"],
                  state["retrieved_context"])
    return {"explanation": exp}


@lru_cache(maxsize=1)
def _compiled_graph():
    g = StateGraph(PipelineState)
    g.add_node("retrieve", _retrieve_node)
    g.add_node("generate", _generate_node)
    g.add_node("fallback", _fallback_node)
    g.add_node("validate", _validate_node)
    g.add_node("explain", _explain_node)

    g.add_edge(START, "retrieve")
    g.add_conditional_edges("retrieve", _route_after_retrieve,
                            {"generate": "generate", "fallback": "fallback"})
    g.add_edge("generate", "validate")
    g.add_edge("fallback", "validate")
    g.add_edge("validate", "explain")
    g.add_edge("explain", END)
    return g.compile()


def run_workout_pipeline(member_id: str, query: str) -> dict[str, Any]:
    """Run retrieve→generate→validate→explain and return the assembled result."""
    final: PipelineState = _compiled_graph().invoke({"member_id": member_id, "query": query})
    return {
        "workout": final.get("workout"),
        "explanation": final.get("explanation"),
        "safety_validation": final.get("safety_validation"),
        "retrieved_context": final.get("retrieved_context"),
        "status": final.get("status"),
    }

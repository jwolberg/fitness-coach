"""Typed request/response schemas (PRD §7.9; ARCH §3.2, principle 4).

Pydantic models for the retrieval + member-graph endpoints. Inner member/goal/etc.
objects are kept as open dict maps (synthetic-data shapes vary); the load-bearing
structures (graph_trace, semantic_matches, graph nodes/edges) are explicitly typed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --- /api/retrieve ---------------------------------------------------------------


class RetrieveRequest(BaseModel):
    member_id: str
    query: str


class GraphTraceEntry(BaseModel):
    subject: str
    relation: str
    object: str
    note: str | None = None


class SemanticMatch(BaseModel):
    id: str | None = None
    label: str | None = None
    type: str | None = None
    score: float


class RetrievedContext(BaseModel):
    member: dict[str, Any]
    goals: list[dict[str, Any]] = Field(default_factory=list)
    preferences: list[dict[str, Any]] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    injuries: list[dict[str, Any]] = Field(default_factory=list)
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)
    context_signals: list[dict[str, Any]] = Field(default_factory=list)
    safe_candidates: list[dict[str, Any]] = Field(default_factory=list)
    excluded_exercises: list[dict[str, Any]] = Field(default_factory=list)


class RetrieveResponse(BaseModel):
    member_id: str
    retrieved_context: RetrievedContext
    graph_trace: list[GraphTraceEntry] = Field(default_factory=list)
    semantic_matches: list[SemanticMatch] = Field(default_factory=list)


# --- /api/member/:id/graph -------------------------------------------------------


class GraphNode(BaseModel):
    id: str            # stable element id
    type: str | None = None  # primary label
    label: str | None = None  # human-readable display name
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str


class MemberGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# --- /api/generate/workout -------------------------------------------------------


class GenerateWorkoutRequest(BaseModel):
    member_id: str
    query: str


class SafetyValidation(BaseModel):
    passed: bool
    issues: list[dict[str, Any]] = Field(default_factory=list)
    repaired: bool = False
    used_fallback: bool = False


class GenerateWorkoutResponse(BaseModel):
    # workout content is left open (LLM output shape varies); the envelope is typed.
    workout: dict[str, Any]
    explanation: dict[str, Any]
    safety_validation: SafetyValidation
    status: str | None = None


# --- /api/explain ----------------------------------------------------------------


class ExplainRequest(BaseModel):
    member_id: str
    question: str
    recommendation_id: str | None = None  # accepted per PRD §7.9; not persisted (no rec store)


class ExplainResponse(BaseModel):
    answer: str
    graph_trace: list[GraphTraceEntry] = Field(default_factory=list)

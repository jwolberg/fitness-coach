"""Typed state for the LangGraph generation pipeline (ARCH §3.3)."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Inputs
    member_id: str
    query: str
    # Stage outputs
    retrieved_context: dict[str, Any]
    workout: dict[str, Any]
    safety_validation: dict[str, Any]
    explanation: dict[str, Any]
    # 'ok' (generated) | 'insufficient_context' (thin retrieval -> safe fallback)
    status: str

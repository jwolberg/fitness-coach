"""Workout generation (PRD §7.6, §9 Generation steps 1-2).

Retrieves the focused GraphRAG context, prompts the LLM, and returns the structured
workout JSON plus the retrieved context (so the validator (P3-T2), explanation
builder (P3-T3), and orchestration (P3-T4) can use the same trace without re-querying).
"""

from __future__ import annotations

import logging
from typing import Any

from app.generation.prompts import WORKOUT_SYSTEM, build_workout_user
from app.llm.client import get_llm_client
from app.retrieval.retriever import retrieve

logger = logging.getLogger(__name__)


def generate_workout(member_id: str, query: str) -> dict[str, Any]:
    """Generate a structured workout from retrieved context.

    Returns ``{"workout": <dict>, "retrieved_context": <dict>}``. The workout is the
    raw LLM output — it is NOT yet safety-validated (that is P3-T2).
    """
    ctx = retrieve(member_id, query)
    user = build_workout_user(ctx, query)
    workout = get_llm_client().complete_json(WORKOUT_SYSTEM, user)
    logger.info(
        "Generated workout for '%s' (%d exercises, insufficient_safe_options=%s)",
        member_id,
        len(workout.get("exercises", []) or []),
        workout.get("insufficient_safe_options"),
    )
    return {"workout": workout, "retrieved_context": ctx}

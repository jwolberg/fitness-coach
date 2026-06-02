"""Deterministic injury-filter / contraindication core (PRD §7.7, §10; ARCH §1, §4).

Safety is computed **in the graph**, never by the LLM. The load-bearing rule is:

    Member ─HAS_INJURY─▶ Injury ─AFFECTS_JOINT─▶ Joint ◀─LOADS_JOINT─ Exercise

Any exercise loading a joint affected by one of the member's injuries is
contraindicated. This module also flags exercises that require equipment the member
lacks, and exposes the resulting safe-candidate set. P3-T2 (validation/repair) and
P2-T2 (retrieval) build on these functions.
"""

from __future__ import annotations

import logging
from typing import Any

from app.graph.client import session

logger = logging.getLogger(__name__)

# Exercises loading a joint affected by the member's injuries, with the offending
# joint(s) attached for explanation (P3-T3).
_CONTRAINDICATED = """
MATCH (:Member {id: $member_id})-[:HAS_INJURY]->(:Injury)-[:AFFECTS_JOINT]->(j:Joint)
      <-[:LOADS_JOINT]-(e:Exercise)
RETURN e.id AS id, e.name AS name, collect(DISTINCT j.name) AS affected_joints
ORDER BY e.name
"""

# Exercises that require at least one piece of equipment the member cannot access.
_UNAVAILABLE_EQUIPMENT = """
MATCH (e:Exercise)-[:USES_EQUIPMENT]->(eq:Equipment)
WHERE NOT EXISTS {
  MATCH (:Member {id: $member_id})-[:HAS_EQUIPMENT_ACCESS]->(eq)
}
RETURN DISTINCT e.id AS id, e.name AS name
ORDER BY e.name
"""

# Safe set: not contraindicated AND every required equipment is available.
_SAFE_CANDIDATES = """
MATCH (e:Exercise)
WHERE NOT EXISTS {
        MATCH (:Member {id: $member_id})-[:HAS_INJURY]->(:Injury)-[:AFFECTS_JOINT]->(j:Joint)
        WHERE (e)-[:LOADS_JOINT]->(j)
      }
  AND NOT EXISTS {
        MATCH (e)-[:USES_EQUIPMENT]->(eq:Equipment)
        WHERE NOT EXISTS { MATCH (:Member {id: $member_id})-[:HAS_EQUIPMENT_ACCESS]->(eq) }
      }
RETURN e.id AS id, e.name AS name, e.priority_tier AS priority_tier
ORDER BY coalesce(e.priority_tier, 999), e.name
"""


def contraindicated_exercises(member_id: str) -> list[dict[str, Any]]:
    """Return exercises that load an injured joint (id, name, affected_joints)."""
    with session() as s:
        return [dict(r) for r in s.run(_CONTRAINDICATED, member_id=member_id)]


def contraindicated_exercise_ids(member_id: str) -> set[str]:
    """Return just the set of contraindicated exercise ids."""
    return {row["id"] for row in contraindicated_exercises(member_id)}


def exercises_requiring_unavailable_equipment(member_id: str) -> set[str]:
    """Return ids of exercises needing equipment the member can't access."""
    with session() as s:
        return {r["id"] for r in s.run(_UNAVAILABLE_EQUIPMENT, member_id=member_id)}


def safe_exercise_candidates(member_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Return exercises that are neither contraindicated nor equipment-blocked.

    Ordered by priority tier (lower = higher priority) then name.
    """
    query = _SAFE_CANDIDATES + ("\nLIMIT $limit" if limit is not None else "")
    params: dict[str, Any] = {"member_id": member_id}
    if limit is not None:
        params["limit"] = limit
    with session() as s:
        return [dict(r) for r in s.run(query, **params)]


def is_contraindicated(member_id: str, exercise_id: str) -> bool:
    """True if the given exercise loads a joint affected by the member's injuries."""
    return exercise_id in contraindicated_exercise_ids(member_id)

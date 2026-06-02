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


# --- P3-T2: validate generated workouts, repair, or fall back --------------------

_ALL_EXERCISES = "MATCH (e:Exercise) RETURN e.id AS id, e.name AS name"
_DISLIKE_PREFS = (
    "MATCH (:Member {id: $member_id})-[:HAS_PREFERENCE]->(p:Preference {kind: 'dislike'}) "
    "RETURN p.tag AS tag, p.description AS description"
)
_INJURED_JOINTS = (
    "MATCH (:Member {id: $member_id})-[:HAS_INJURY]->(:Injury)-[:AFFECTS_JOINT]->(j:Joint) "
    "RETURN collect(DISTINCT j.name) AS joints"
)

# Keyword cues for known dislike tags (deterministic preference check).
_DISLIKE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "high_impact": ("jump", "jumping", "hop", "plyo", "jack", "bound", "skip"),
}


def known_exercise_ids() -> set[str]:
    """Return all exercise ids in the library."""
    with session() as s:
        return {r["id"] for r in s.run(_ALL_EXERCISES)}


def _dislike_tags(member_id: str) -> list[str]:
    with session() as s:
        return [r["tag"] for r in s.run(_DISLIKE_PREFS, member_id=member_id) if r["tag"]]


def _injured_joints(member_id: str) -> list[str]:
    with session() as s:
        rec = s.run(_INJURED_JOINTS, member_id=member_id).single()
    return rec["joints"] if rec else []


def _violates_preference(name: str, tags: list[str]) -> str | None:
    lowered = (name or "").lower()
    for tag in tags:
        for kw in _DISLIKE_KEYWORDS.get(tag, ()):
            if kw in lowered:
                return tag
    return None


def validate_workout(member_id: str, workout: dict[str, Any]) -> dict[str, Any]:
    """Validate a generated workout deterministically (PRD §7.7).

    Returns ``{"passed": bool, "issues": [...]}``. Each issue is
    ``{exercise_id, name, problem}`` where problem ∈ {unknown_exercise,
    contraindicated, unavailable_equipment, preference_conflict, malformed}.
    """
    exercises = workout.get("exercises")
    if not isinstance(exercises, list):
        return {"passed": False, "issues": [{"problem": "malformed",
                                             "detail": "workout has no 'exercises' list"}]}

    known = known_exercise_ids()
    contra = contraindicated_exercise_ids(member_id)
    unavailable = exercises_requiring_unavailable_equipment(member_id)
    dislikes = _dislike_tags(member_id)

    issues: list[dict[str, Any]] = []
    for ex in exercises:
        eid = ex.get("exercise_id")
        name = ex.get("name")
        if not eid or not name or ex.get("sets") is None or not ex.get("reps"):
            issues.append({"exercise_id": eid, "name": name, "problem": "malformed"})
            continue
        if eid not in known:
            issues.append({"exercise_id": eid, "name": name, "problem": "unknown_exercise"})
        elif eid in contra:
            issues.append({"exercise_id": eid, "name": name, "problem": "contraindicated"})
        elif eid in unavailable:
            issues.append({"exercise_id": eid, "name": name, "problem": "unavailable_equipment"})
        tag = _violates_preference(name, dislikes)
        if tag:
            issues.append({"exercise_id": eid, "name": name,
                           "problem": "preference_conflict", "detail": tag})

    return {"passed": len(issues) == 0, "issues": issues}


def _is_clean(ex: dict[str, Any], bad_ids: set[str], dislikes: list[str]) -> bool:
    eid = ex.get("exercise_id")
    if not eid or not ex.get("name") or ex.get("sets") is None or not ex.get("reps"):
        return False
    return eid not in bad_ids and _violates_preference(ex.get("name", ""), dislikes) is None


def safe_fallback(member_id: str, limit: int = 5) -> dict[str, Any]:
    """Build the deterministic safe-fallback workout (PRD §10)."""
    dislikes = _dislike_tags(member_id)
    candidates = [c for c in safe_exercise_candidates(member_id)
                  if _violates_preference(c["name"], dislikes) is None][:limit]
    joints = _injured_joints(member_id)
    joint_phrase = (" before loading the " + "/".join(joints) + " joint") if joints else ""
    exercises = [
        {"exercise_id": c["id"], "name": c["name"], "sets": 3, "reps": "10-12",
         "rest": "60s", "intensity": "low-moderate", "substitution": "",
         "notes": "Deterministic safe fallback selection."}
        for c in candidates
    ]
    return {
        "title": "Safe alternative session",
        "goal": "Train safely within the current injury and equipment constraints",
        "warm_up": ["5 min easy cardio", "dynamic mobility for available joints"],
        "exercises": exercises,
        "intensity_guidance": "Keep load low to moderate; stop if any pain appears.",
        "rest_guidance": "60-90s between sets.",
        "notes": (
            "I do not have enough safe options based on the current injury context. "
            f"I recommend a coach review{joint_phrase}. Safe alternatives may include "
            "low-load hip-dominant work, mobility, or upper-body training until more "
            "information is available."
        ),
        "insufficient_safe_options": True,
    }


def validate_and_repair(member_id: str, workout: dict[str, Any]) -> dict[str, Any]:
    """Validate, then repair from safe candidates or fall back (PRD §7.7, §10).

    Returns ``{"workout": <dict>, "safety_validation": {passed, issues, repaired,
    used_fallback}}``. ``passed`` reflects the ORIGINAL workout; the returned workout
    is always safe.
    """
    result = validate_workout(member_id, workout)
    if result["passed"]:
        return {"workout": workout,
                "safety_validation": {"passed": True, "issues": [],
                                      "repaired": False, "used_fallback": False}}

    dislikes = _dislike_tags(member_id)
    bad_ids = contraindicated_exercise_ids(member_id) | exercises_requiring_unavailable_equipment(member_id)
    unknown = {ex.get("exercise_id") for ex in (workout.get("exercises") or [])
               if ex.get("exercise_id") not in known_exercise_ids()}
    bad_ids |= {u for u in unknown if u}

    kept = [ex for ex in (workout.get("exercises") or []) if _is_clean(ex, bad_ids, dislikes)]

    # Backfill from safe candidates (excluding ones already kept / preference conflicts).
    kept_ids = {ex["exercise_id"] for ex in kept}
    target = max(len(workout.get("exercises") or []), 1)
    for cand in safe_exercise_candidates(member_id):
        if len(kept) >= target:
            break
        if cand["id"] in kept_ids or _violates_preference(cand["name"], dislikes):
            continue
        kept.append({"exercise_id": cand["id"], "name": cand["name"], "sets": 3,
                     "reps": "10-12", "rest": "60s", "intensity": "low-moderate",
                     "substitution": "", "notes": "Added during safety repair."})
        kept_ids.add(cand["id"])

    if not kept:
        return {"workout": safe_fallback(member_id),
                "safety_validation": {"passed": False, "issues": result["issues"],
                                      "repaired": False, "used_fallback": True}}

    repaired = {**workout, "exercises": kept}
    return {"workout": repaired,
            "safety_validation": {"passed": False, "issues": result["issues"],
                                  "repaired": True, "used_fallback": False}}

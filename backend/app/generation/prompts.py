"""Prompt construction for workout generation (PRD §7.6).

Builds a compact system + user prompt from the focused retrieved context. The system
prompt fixes the output JSON shape and the hard safety rules (use only safe
candidates; never contraindicated; recover gracefully when options are thin). The
user prompt carries only the focused context — never the whole graph.
"""

from __future__ import annotations

import json
from typing import Any

WORKOUT_SYSTEM = """\
You are a fitness coaching assistant that writes safe, personalized, injury-aware workouts.

HARD RULES (a deterministic validator also enforces these — do not rely on yourself alone):
- Use ONLY exercises from the provided "safe_candidates" list, referenced by their exact "id" and "name".
- NEVER include any exercise from "excluded_exercises" (they load an injured joint or need unavailable equipment).
- Do not invent exercises, ids, member history, or graph relationships.
- Respect the member's stated preferences (e.g. avoid disliked movement types).
- If the requested focus can't be trained safely (e.g. a knee injury blocks most lower-body work),
  set "insufficient_safe_options": true, explain the limitation in "notes", AND STILL populate
  "exercises" with the best safe alternatives you can from safe_candidates (mobility, upper-body,
  hip-dominant, recovery). Only leave "exercises" empty if safe_candidates is itself empty.
  Never pad with unsafe or invented exercises.

Return ONLY a JSON object with this shape:
{
  "title": string,
  "goal": string,
  "warm_up": [string],
  "exercises": [
    {"exercise_id": string, "name": string, "sets": integer, "reps": string,
     "rest": string, "intensity": string, "substitution": string, "notes": string}
  ],
  "intensity_guidance": string,
  "rest_guidance": string,
  "notes": string,
  "insufficient_safe_options": boolean
}
"""


def build_workout_user(ctx: dict[str, Any], query: str) -> str:
    """Assemble the compact user prompt from the focused retrieved context."""
    member = ctx.get("member", {})
    payload = {
        "coach_query": query,
        "member": {
            "name": member.get("name"),
            "adherence_rate": member.get("adherence_rate"),
            "notes": member.get("notes"),
        },
        "goals": [g.get("description") for g in ctx.get("goals", [])],
        "preferences": [
            {"kind": p.get("kind"), "description": p.get("description")}
            for p in ctx.get("preferences", [])
        ],
        "equipment_available": ctx.get("equipment", []),
        "injuries": [
            {"name": i.get("name"), "joint": i.get("joint"), "status": i.get("status")}
            for i in ctx.get("injuries", [])
        ],
        "recent_sessions": [
            {"title": s.get("title"), "status": s.get("status"), "date": s.get("date")}
            for s in ctx.get("recent_sessions", [])
        ],
        "safe_candidates": [
            {"id": e.get("id"), "name": e.get("name")} for e in ctx.get("safe_candidates", [])
        ],
        "excluded_exercises": [
            {"name": e.get("name"), "reason": e.get("reason")}
            for e in ctx.get("excluded_exercises", [])
        ],
    }
    return (
        "Build a workout for this coach request using only the safe candidates.\n\n"
        + json.dumps(payload, indent=2)
    )

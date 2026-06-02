"""Explanation builder (PRD §7.8): turn the recorded graph_trace into a "why?" answer.

Explanations are **deterministic templating over graph evidence** — they read the
retrieved context + `graph_trace` (recorded during P2-T2 retrieval) and never
re-query the graph or re-prompt the LLM. This guarantees the answer is traceable to
real relationships, not a vague rationalization (challenge "Explainability").

Handles the demo's follow-ups: "why did you skip X?", "why include X?",
"what should I watch for?", and "what constraints affected this workout?".
"""

from __future__ import annotations

import re
from typing import Any

_STOP = {
    "why", "did", "you", "the", "for", "her", "him", "them", "this", "that", "these",
    "skip", "skipped", "exclude", "excluded", "leave", "out", "not", "include",
    "included", "with", "and", "was", "were", "would", "should", "what", "watch",
    "constraints", "affected", "workout", "exercise", "exercises", "have", "does",
    "his", "she", "are", "any", "use",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2 and t not in _STOP]


def _injured_joints(ctx: dict[str, Any]) -> list[str]:
    return sorted({i["joint"] for i in ctx.get("injuries", []) if i.get("joint")})


def _injury_names(ctx: dict[str, Any]) -> list[str]:
    return [i["name"] for i in ctx.get("injuries", []) if i.get("name")]


def _best_match(name_tokens: list[str], items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the exercise whose name shares the most query tokens (>=1)."""
    best, best_score = None, 0
    for item in items:
        score = sum(1 for t in name_tokens if t in (item.get("name") or "").lower())
        if score > best_score:
            best, best_score = item, score
    return best if best_score > 0 else None


def _trace_for_exclusion(member_id: str, ctx: dict[str, Any], exercise: dict[str, Any]) -> list[dict]:
    """Build the Member→Injury→Joint←Exercise chain for one excluded exercise."""
    injured = set(_injured_joints(ctx))
    offending = [j for j in (exercise.get("joints") or []) if j in injured]
    trace: list[dict[str, Any]] = []
    for inj in ctx.get("injuries", []):
        if inj.get("joint") in offending:
            trace.append({"subject": f"Member:{member_id}", "relation": "HAS_INJURY",
                          "object": f"Injury:{inj['name']}"})
            trace.append({"subject": f"Injury:{inj['name']}", "relation": "AFFECTS_JOINT",
                          "object": f"Joint:{inj['joint']}"})
    for joint in offending:
        trace.append({"subject": f"Exercise:{exercise['name']}", "relation": "LOADS_JOINT",
                      "object": f"Joint:{joint}", "note": "contraindicated"})
    return trace


def _explain_exclusion(question: str, member_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    excluded = ctx.get("excluded_exercises", [])
    match = _best_match(_tokens(question), excluded)
    injured = _injured_joints(ctx)
    injuries = _injury_names(ctx)
    name = ctx.get("member", {}).get("name", "the member")

    if not match:
        return {
            "answer": (
                f"No excluded exercise in this session matches that name. "
                f"{name}'s active constraints are: injuries {injuries or 'none'} affecting "
                f"joint(s) {injured or 'none'}; any exercise loading those joints is excluded."
            ),
            "graph_trace": [],
        }

    offending = [j for j in (match.get("joints") or []) if j in set(injured)]
    safe_names = [c.get("name") for c in ctx.get("safe_candidates", [])[:3]]
    answer = (
        f"{match['name']} was excluded because it loads the {', '.join(offending) or 'an injured'} "
        f"joint. {name} has {', '.join(injuries) or 'an injury'} affecting the "
        f"{', '.join(injured)} joint, so any exercise loading that joint is contraindicated "
        f"(computed from the graph, not the model). Safer alternatives in this session include "
        f"{', '.join(n for n in safe_names if n) or 'low-load mobility / upper-body work'}."
    )
    return {"answer": answer, "graph_trace": _trace_for_exclusion(member_id, ctx, match)}


def _explain_inclusion(question: str, member_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    match = _best_match(_tokens(question), ctx.get("safe_candidates", []))
    injured = _injured_joints(ctx)
    name = ctx.get("member", {}).get("name", "the member")
    if not match:
        return {"answer": "No included exercise matches that name in this session.",
                "graph_trace": []}
    answer = (
        f"{match['name']} was included because it does not load any of {name}'s injured "
        f"joint(s) ({', '.join(injured) or 'none'}) and fits the available equipment, so it "
        f"passed the deterministic safety filter."
    )
    trace = [{"subject": f"Exercise:{match['name']}", "relation": "SAFE_FOR",
              "object": f"Member:{member_id}", "note": "not contraindicated"}]
    return {"answer": answer, "graph_trace": trace}


def _explain_watchouts(member_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    member = ctx.get("member", {})
    name = member.get("name", "the member")
    rate = member.get("adherence_rate")
    window = member.get("adherence_window", "recent period")
    missed = member.get("adherence_missed_last_week")
    injuries = _injury_names(ctx)
    injured = _injured_joints(ctx)
    goals = [g.get("description") for g in ctx.get("goals", [])]
    missed_sessions = [s.get("title") for s in ctx.get("recent_sessions", []) if s.get("status") == "missed"]

    parts = [f"What to watch for with {name}:"]
    if rate is not None:
        pct = f"{round(rate * 100)}%" if rate <= 1 else f"{rate}%"
        miss = f", missed {missed} last week" if missed else ""
        parts.append(f"adherence is {pct} over the {window}{miss}")
    if injuries:
        parts.append(f"active injury: {', '.join(injuries)} (affects {', '.join(injured)})")
    if goals:
        parts.append(f"goals: {', '.join(g for g in goals if g)}")
    if missed_sessions:
        parts.append(f"recently missed: {', '.join(missed_sessions)}")
    parts.append(f"consider a coach review before loading the {', '.join(injured) or 'affected'} joint")
    answer = parts[0] + " " + "; ".join(parts[1:]) + "."
    return {"answer": answer, "graph_trace": ctx.get("graph_trace", [])}


def _explain_constraints(member_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    injured = _injured_joints(ctx)
    injuries = _injury_names(ctx)
    equipment = ctx.get("equipment", [])
    likes = [p.get("description") for p in ctx.get("preferences", []) if p.get("kind") == "like"]
    dislikes = [p.get("description") for p in ctx.get("preferences", []) if p.get("kind") == "dislike"]
    excluded_n = len(ctx.get("excluded_exercises", []))
    answer = (
        f"This workout was shaped by: injuries {', '.join(injuries) or 'none'} affecting "
        f"joint(s) {', '.join(injured) or 'none'} (which excluded {excluded_n} exercises); "
        f"available equipment ({', '.join(equipment) or 'none'}); "
        f"preferences (likes: {', '.join(likes) or 'none'}; dislikes: {', '.join(dislikes) or 'none'})."
    )
    return {"answer": answer, "graph_trace": ctx.get("graph_trace", [])}


def explain(question: str, member_id: str, retrieved_context: dict[str, Any]) -> dict[str, Any]:
    """Answer a follow-up question from graph evidence. Returns {answer, graph_trace}."""
    q = (question or "").lower()
    if "watch" in q or "watch out" in q or "look out" in q:
        return _explain_watchouts(member_id, retrieved_context)
    if any(w in q for w in ("constraint", "shaped", "affect")):
        return _explain_constraints(member_id, retrieved_context)
    if any(w in q for w in ("include", "included", "why this", "why is")):
        return _explain_inclusion(question, member_id, retrieved_context)
    # default: exclusion ("why skip / why did you skip / why not / why exclude")
    return _explain_exclusion(question, member_id, retrieved_context)

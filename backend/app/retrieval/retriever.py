"""GraphRAG retriever: vector search + graph traversal + trace (PRD §7.5, §9 Retrieval).

Combines the two signals into one *focused* context window (never the whole graph):
  1. Vector search finds semantically relevant nodes for the coach query.
  2. Graph traversal expands from the member across the safety-relevant neighborhood
     (goals, preferences, equipment, injuries→joints, recent history, signals).
  3. Contraindicated exercises are excluded (deterministic, P1-T5); the safe
     candidate set is ranked by semantic relevance to the query.
A ``graph_trace`` records the Member→Injury→Joint←Exercise reasoning so the
explanation builder (P3-T3) never re-queries or re-prompts.

``retrieve`` returns a plain dict; P2-T3 wraps it in typed Pydantic schemas.
"""

from __future__ import annotations

import logging
from typing import Any

from app.graph.client import session
from app.retrieval.embeddings import vector_search
from app.safety import validator

logger = logging.getLogger(__name__)

# Focused-window caps (token efficiency — we never dump the whole graph/library).
_SEMANTIC_K = 25          # how many vector hits to pull for ranking
_SEMANTIC_KEEP = 8        # how many semantic matches to surface in the result
_MAX_SAFE_CANDIDATES = 8  # focused exercise candidate set handed to generation
_MAX_RECENT_SESSIONS = 5

# Member neighborhood in one query; CALL{} subqueries avoid a cartesian blow-up.
_MEMBER_CONTEXT = """
MATCH (m:Member {id: $member_id})
CALL { WITH m MATCH (m)-[:HAS_GOAL]->(g:Goal) RETURN collect(g{.*}) AS goals }
CALL { WITH m OPTIONAL MATCH (m)-[:HAS_PREFERENCE]->(p:Preference)
       RETURN collect(p{.*}) AS preferences }
CALL { WITH m OPTIONAL MATCH (m)-[:HAS_EQUIPMENT_ACCESS]->(e:Equipment)
       RETURN collect(DISTINCT e.name) AS equipment }
CALL { WITH m OPTIONAL MATCH (m)-[:HAS_INJURY]->(i:Injury)
       OPTIONAL MATCH (i)-[:AFFECTS_JOINT]->(j:Joint)
       RETURN collect(DISTINCT {id: i.id, name: i.name, description: i.description,
                                status: i.status, joint: j.name}) AS injuries }
CALL { WITH m OPTIONAL MATCH (m)-[:HAS_WORKOUT_SESSION]->(ws:WorkoutSession)
       RETURN collect(ws{.*}) AS sessions }
CALL { WITH m OPTIONAL MATCH (m)-[:HAS_CONTEXT_SIGNAL]->(cs:ContextSignal)
       RETURN collect(cs{.id, .text, .kind, .date}) AS signals }
RETURN m{.*} AS member, goals, preferences, equipment, injuries, sessions, signals
"""


def _fetch_member_context(member_id: str) -> dict[str, Any]:
    with session() as s:
        record = s.run(_MEMBER_CONTEXT, member_id=member_id).single()
    if record is None:
        raise ValueError(f"Member '{member_id}' not found")
    return dict(record)


def _build_graph_trace(member_id: str, injuries: list[dict], contraindicated: list[dict]) -> list[dict]:
    """Record the safety reasoning path as subject-relation-object triples."""
    trace: list[dict[str, Any]] = []
    for inj in injuries:
        if not inj.get("name"):
            continue
        trace.append({"subject": f"Member:{member_id}", "relation": "HAS_INJURY",
                      "object": f"Injury:{inj['name']}"})
        if inj.get("joint"):
            trace.append({"subject": f"Injury:{inj['name']}", "relation": "AFFECTS_JOINT",
                          "object": f"Joint:{inj['joint']}"})
    for ex in contraindicated:
        for joint in ex.get("affected_joints", []):
            trace.append({"subject": f"Exercise:{ex['name']}", "relation": "LOADS_JOINT",
                          "object": f"Joint:{joint}", "note": "contraindicated"})
    return trace


def retrieve(member_id: str, query: str) -> dict[str, Any]:
    """Assemble the focused GraphRAG context window + graph trace for a coach query."""
    # 1. Semantic signal (graph-wide vector search).
    matches = vector_search(query, k=_SEMANTIC_K)
    score_by_id = {m["id"]: m["score"] for m in matches if m.get("id") is not None}
    semantic_matches = [
        {"id": m["id"], "label": m["label"], "type": _primary_label(m["labels"]),
         "score": m["score"]}
        for m in matches[:_SEMANTIC_KEEP]
    ]

    # 2. Graph traversal of the member's safety-relevant neighborhood.
    ctx = _fetch_member_context(member_id)
    injuries = ctx["injuries"]
    sessions = sorted(ctx["sessions"], key=lambda s: s.get("date") or "", reverse=True)
    recent_sessions = sessions[:_MAX_RECENT_SESSIONS]

    # 3. Deterministic safety: exclude contraindicated, rank safe set by query relevance.
    contraindicated = validator.contraindicated_exercises(member_id)
    safe = validator.safe_exercise_candidates(member_id)
    safe.sort(key=lambda e: (-score_by_id.get(e["id"], 0.0), e.get("priority_tier") or 999))
    safe_candidates = safe[:_MAX_SAFE_CANDIDATES]

    graph_trace = _build_graph_trace(member_id, injuries, contraindicated)

    logger.info(
        "Retrieved for '%s' q=%r: %d semantic, %d safe candidates, %d excluded, trace=%d",
        member_id, query, len(semantic_matches), len(safe_candidates),
        len(contraindicated), len(graph_trace),
    )

    return {
        "member": ctx["member"],
        "goals": ctx["goals"],
        "preferences": ctx["preferences"],
        "equipment": ctx["equipment"],
        "injuries": injuries,
        "recent_sessions": recent_sessions,
        "context_signals": ctx["signals"],
        "safe_candidates": safe_candidates,
        "excluded_exercises": [{"id": e["id"], "name": e["name"],
                                "reason": "contraindicated", "joints": e["affected_joints"]}
                               for e in contraindicated],
        "semantic_matches": semantic_matches,
        "graph_trace": graph_trace,
    }


def _primary_label(labels: list[str]) -> str | None:
    """Pick the meaningful label (ignore the shared :Embeddable tag)."""
    for label in labels:
        if label != "Embeddable":
            return label
    return labels[0] if labels else None

"""Structure unstructured context signals into graph nodes/edges (PRD §7.4, §9 step 7).

Turns a free-text signal (e.g. "my knee felt weird after lunges...") into a
``ContextSignal`` node plus, when the text implies them, ``MENTIONS_INJURY`` /
``MENTIONS_GOAL`` edges — reconciling against the member's *existing* injuries
(by affected joint) and goals (by focus) so we don't duplicate the structured
nodes ingested in P1-T3. A derived injury with no existing match is created and
linked to its joint (PRD §7.4 "Injury ... → affected joint").

Extraction is deterministic (a small keyword lexicon), so Phase 1 runs without an
LLM/provider key; the LLM path is reserved for generation (P3). ``extract_concepts``
is pure and testable; ``ingest_signal`` / ``structure_member_signals`` write the graph.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from app.graph.client import session
from app.ingestion.members import load_member

logger = logging.getLogger(__name__)

# Free-text term -> canonical Joint name (matches the exercises.json joint vocabulary).
_JOINT_LEXICON: dict[str, str] = {
    "knee": "knee",
    "shoulder": "shoulder",
    "hip": "hip",
    "ankle": "ankle",
    "elbow": "elbow",
    "wrist": "wrist",
    "lower back": "lumbar spine",
    "low back": "lumbar spine",
    "lumbar": "lumbar spine",
    "upper back": "thoracic spine",
    "neck": "cervical spine",
}

# Words signalling discomfort/injury (co-occurrence with a joint => derived injury).
_DISCOMFORT_CUES: tuple[str, ...] = (
    "pain", "painful", "hurt", "sore", "ache", "aching", "weird", "off",
    "bother", "tweak", "strain", "sprain", "discomfort", "stiff", "injured", "injury",
)

# Free-text term -> Goal focus (matches the focus values used in member fixtures).
_GOAL_FOCUS_LEXICON: dict[str, str] = {
    "legs": "lower_body",
    "leg": "lower_body",
    "lower body": "lower_body",
    "squat": "lower_body",
    "lunge": "lower_body",
    "glute": "lower_body",
    "quad": "lower_body",
    "hamstring": "lower_body",
    "upper body": "upper_body",
    "chest": "upper_body",
    "press": "upper_body",
    "pull": "upper_body",
}


def extract_concepts(text: str) -> dict[str, Any]:
    """Derive injuries (joint + discomfort) and goal foci from free text.

    Returns ``{"injury_joints": [...], "goal_foci": [...]}`` (both de-duplicated,
    order-preserving).
    """
    lowered = text.lower()
    has_discomfort = any(cue in lowered for cue in _DISCOMFORT_CUES)

    injury_joints: list[str] = []
    if has_discomfort:
        for term, joint in _JOINT_LEXICON.items():
            if term in lowered and joint not in injury_joints:
                injury_joints.append(joint)

    goal_foci: list[str] = []
    for term, focus in _GOAL_FOCUS_LEXICON.items():
        if term in lowered and focus not in goal_foci:
            goal_foci.append(focus)

    return {"injury_joints": injury_joints, "goal_foci": goal_foci}


_UPSERT_SIGNAL = """
MATCH (m:Member {id: $member_id})
MERGE (cs:ContextSignal {id: $id})
SET cs.text = $text, cs.kind = $kind, cs.date = $date, cs:Embeddable
MERGE (m)-[:HAS_CONTEXT_SIGNAL]->(cs)
"""

_FIND_EXISTING_INJURY = """
MATCH (:Member {id: $member_id})-[:HAS_INJURY]->(i:Injury)-[:AFFECTS_JOINT]->(:Joint {name: $joint})
RETURN i.id AS injury_id
LIMIT 1
"""

_LINK_SIGNAL_TO_INJURY = """
MATCH (cs:ContextSignal {id: $signal_id})
MATCH (i:Injury {id: $injury_id})
MERGE (cs)-[:MENTIONS_INJURY]->(i)
"""

_CREATE_DERIVED_INJURY = """
MATCH (m:Member {id: $member_id})
MERGE (j:Joint {name: $joint})
MERGE (i:Injury {id: $injury_id})
SET i.name = $name, i.status = 'reported', i.source = 'context_signal', i:Embeddable
MERGE (m)-[:HAS_INJURY]->(i)
MERGE (i)-[:AFFECTS_JOINT]->(j)
WITH i
MATCH (cs:ContextSignal {id: $signal_id})
MERGE (cs)-[:MENTIONS_INJURY]->(i)
"""

_LINK_SIGNAL_TO_GOAL = """
MATCH (:Member {id: $member_id})-[:HAS_GOAL]->(g:Goal {focus: $focus})
WITH g LIMIT 1
MATCH (cs:ContextSignal {id: $signal_id})
MERGE (cs)-[:MENTIONS_GOAL]->(g)
RETURN g.id AS goal_id
"""


def ingest_signal(member_id: str, signal: dict[str, Any]) -> dict[str, Any]:
    """Create the ContextSignal and its derived/linked edges. Returns a summary."""
    signal_id = signal["id"]
    concepts = extract_concepts(signal.get("text", ""))
    linked_injuries: list[str] = []
    linked_goals: list[str] = []

    with session() as s:
        s.run(
            _UPSERT_SIGNAL,
            member_id=member_id,
            id=signal_id,
            text=signal.get("text"),
            kind=signal.get("kind", "chat"),
            date=signal.get("date"),
        ).consume()

        for joint in concepts["injury_joints"]:
            existing = s.run(_FIND_EXISTING_INJURY, member_id=member_id, joint=joint).single()
            if existing:  # reconcile with the structured injury from P1-T3
                injury_id = existing["injury_id"]
                s.run(_LINK_SIGNAL_TO_INJURY, signal_id=signal_id, injury_id=injury_id).consume()
            else:  # derive a new injury from the signal
                injury_id = f"{signal_id}-injury-{joint.replace(' ', '-')}"
                s.run(
                    _CREATE_DERIVED_INJURY,
                    member_id=member_id,
                    joint=joint,
                    injury_id=injury_id,
                    name=f"Reported {joint} discomfort",
                    signal_id=signal_id,
                ).consume()
            linked_injuries.append(injury_id)

        for focus in concepts["goal_foci"]:
            record = s.run(
                _LINK_SIGNAL_TO_GOAL, member_id=member_id, focus=focus, signal_id=signal_id
            ).single()
            if record:  # only link to a goal the member actually has (no fabrication)
                linked_goals.append(record["goal_id"])

    logger.info(
        "Structured signal '%s' for '%s': injuries=%s goals=%s",
        signal_id,
        member_id,
        linked_injuries,
        linked_goals,
    )
    return {"signal_id": signal_id, "injuries": linked_injuries, "goals": linked_goals}


def structure_member_signals(path: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    """Structure every ``context_signals`` entry in a member fixture."""
    member = load_member(path)
    member_id = member["id"]
    return [ingest_signal(member_id, sig) for sig in (member.get("context_signals") or [])]

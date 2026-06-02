"""Ingest a synthetic member's structured profile into the graph (PRD §7.3, §16).

Creates the ``Member`` and links goals, preferences, equipment access, injuries
(``HAS_INJURY → Injury → AFFECTS_JOINT → Joint``), and workout-history sessions.
Adherence is stored as Member properties plus per-session status. All writes use
MERGE, so re-running is idempotent.

Scope note: the fixture's ``context_signals`` (unstructured text) are intentionally
NOT ingested here — turning them into ``ContextSignal`` + ``MENTIONS_*`` nodes is
P1-T4 (``signals.py``). Goals and injuries are tagged ``:Embeddable`` for P2-T1.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.graph.client import session

logger = logging.getLogger(__name__)

# Maya is the seeded demo member (PRD §16). Overridable via MEMBER_PATH for seeding.
_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "members" / "maya.json"

_UPSERT_MEMBER = """
MERGE (m:Member {id: $id})
SET m += $props
"""

_UPSERT_GOALS = """
MATCH (m:Member {id: $member_id})
UNWIND $goals AS goal
  MERGE (g:Goal {id: goal.id})
  SET g += goal, g:Embeddable
  MERGE (m)-[:HAS_GOAL]->(g)
"""

_UPSERT_PREFERENCES = """
MATCH (m:Member {id: $member_id})
UNWIND $preferences AS pref
  MERGE (p:Preference {id: pref.id})
  SET p += pref
  MERGE (m)-[:HAS_PREFERENCE]->(p)
"""

_UPSERT_EQUIPMENT = """
MATCH (m:Member {id: $member_id})
UNWIND $equipment AS name
  MERGE (e:Equipment {name: name})
  MERGE (m)-[:HAS_EQUIPMENT_ACCESS]->(e)
"""

_UPSERT_INJURIES = """
MATCH (m:Member {id: $member_id})
UNWIND $injuries AS injury
  MERGE (i:Injury {id: injury.id})
  SET i.name = injury.name, i.description = injury.description,
      i.status = injury.status, i:Embeddable
  MERGE (m)-[:HAS_INJURY]->(i)
  FOREACH (j IN injury.affects_joints |
    MERGE (joint:Joint {name: j})
    MERGE (i)-[:AFFECTS_JOINT]->(joint))
"""

_UPSERT_SESSIONS = """
MATCH (m:Member {id: $member_id})
UNWIND $sessions AS s
  MERGE (ws:WorkoutSession {id: s.id})
  SET ws += s
  MERGE (m)-[:HAS_WORKOUT_SESSION]->(ws)
"""


def load_member(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load and return the raw member fixture."""
    resolved = Path(path) if path is not None else Path(os.getenv("MEMBER_PATH", _DEFAULT_PATH))
    with open(resolved, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "id" not in data:
        raise ValueError("Member fixture must be a JSON object with an 'id'")
    return data


def member_properties(member: dict[str, Any]) -> dict[str, Any]:
    """Flatten the member's scalar profile + adherence fields onto Member props."""
    profile = member.get("profile") or {}
    adherence = member.get("adherence") or {}
    props: dict[str, Any] = {"name": member.get("name")}
    props.update(profile)
    if adherence:
        props["adherence_rate"] = adherence.get("rate")
        props["adherence_window"] = adherence.get("window")
        props["adherence_missed_last_week"] = adherence.get("missed_last_week")
    # Drop None values so we don't overwrite with nulls on re-ingest.
    return {k: v for k, v in props.items() if v is not None}


def ingest_member(path: str | os.PathLike[str] | None = None) -> str:
    """Ingest the member's structured profile. Returns the member id."""
    member = load_member(path)
    member_id = member["id"]
    with session() as s:
        s.run(_UPSERT_MEMBER, id=member_id, props=member_properties(member)).consume()
        s.run(_UPSERT_GOALS, member_id=member_id, goals=member.get("goals") or []).consume()
        s.run(
            _UPSERT_PREFERENCES, member_id=member_id, preferences=member.get("preferences") or []
        ).consume()
        s.run(
            _UPSERT_EQUIPMENT, member_id=member_id, equipment=member.get("equipment_access") or []
        ).consume()
        s.run(_UPSERT_INJURIES, member_id=member_id, injuries=member.get("injuries") or []).consume()
        s.run(
            _UPSERT_SESSIONS, member_id=member_id, sessions=member.get("workout_history") or []
        ).consume()
    logger.info(
        "Ingested member '%s': %d goals, %d preferences, %d equipment, %d injuries, %d sessions",
        member_id,
        len(member.get("goals") or []),
        len(member.get("preferences") or []),
        len(member.get("equipment_access") or []),
        len(member.get("injuries") or []),
        len(member.get("workout_history") or []),
    )
    return member_id

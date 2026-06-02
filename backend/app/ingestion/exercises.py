"""Ingest ``exercises.json`` into the graph (PRD §7.2, §9 ingestion steps 1-4).

Creates an ``Exercise`` node per record and edges to ``Joint`` (LOADS_JOINT),
``MuscleGroup`` (TRAINS_MUSCLE), ``Equipment`` (USES_EQUIPMENT), and
``MovementPattern`` (HAS_MOVEMENT_PATTERN), plus ``HAS_BILATERAL_PAIR`` between
exercises that are both present. All writes use MERGE, so re-running is idempotent.

``load_exercises`` / ``exercise_params`` are pure (testable without a DB);
``ingest_exercises`` performs the graph writes.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.graph.client import session

logger = logging.getLogger(__name__)

# exercises.json lives at the repo root. Overridable via EXERCISES_PATH (e.g. the
# path it's mounted/copied to inside the container for seeding, P5-T3).
_DEFAULT_PATH = Path(__file__).resolve().parents[3] / "exercises.json"

# Scalar fields copied verbatim onto the Exercise node.
_SCALAR_FIELDS = (
    "name",
    "priority_tier",
    "is_bilateral",
    "bilateral_pair_id",
    "side",
    "supports_weight",
    "is_duration",
    "is_reps",
    "estimated_rep_duration",
)

# One MERGE per exercise; FOREACH creates ontology nodes + edges and tolerates
# empty lists. Exercises are embeddable (P2-T1 writes the vector), so tag the label.
_UPSERT_EXERCISE = """
MERGE (e:Exercise {id: $id})
SET e += $props
SET e:Embeddable
FOREACH (j IN $joints | MERGE (n:Joint {name: j}) MERGE (e)-[:LOADS_JOINT]->(n))
FOREACH (m IN $muscles | MERGE (n:MuscleGroup {name: m}) MERGE (e)-[:TRAINS_MUSCLE]->(n))
FOREACH (q IN $equipment | MERGE (n:Equipment {name: q}) MERGE (e)-[:USES_EQUIPMENT]->(n))
FOREACH (p IN $patterns | MERGE (n:MovementPattern {name: p}) MERGE (e)-[:HAS_MOVEMENT_PATTERN]->(n))
"""

# Second pass: only link bilateral pairs where BOTH exercises exist (no stub nodes).
_LINK_BILATERAL = """
MATCH (a:Exercise {id: $a})
MATCH (b:Exercise {id: $b})
MERGE (a)-[:HAS_BILATERAL_PAIR]->(b)
RETURN count(*) AS linked
"""


def load_exercises(path: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    """Load and return the raw exercise records from JSON."""
    resolved = Path(path) if path is not None else Path(os.getenv("EXERCISES_PATH", _DEFAULT_PATH))
    with open(resolved, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list of exercises, got {type(data).__name__}")
    return data


def exercise_params(record: dict[str, Any]) -> dict[str, Any]:
    """Map a raw record to the parameters for the upsert statement."""
    return {
        "id": record["id"],
        "props": {f: record.get(f) for f in _SCALAR_FIELDS},
        "joints": record.get("joints_loaded") or [],
        "muscles": record.get("muscle_groups") or [],
        "equipment": record.get("equipment_required") or [],
        "patterns": record.get("movement_patterns") or [],
    }


def ingest_exercises(path: str | os.PathLike[str] | None = None) -> int:
    """Upsert all exercises and their edges. Returns the number of exercises ingested."""
    records = load_exercises(path)
    ids = {r["id"] for r in records}
    with session() as s:
        for record in records:
            s.run(_UPSERT_EXERCISE, **exercise_params(record)).consume()

        # Link bilateral pairs only when the target is also in the library.
        linked = 0
        for record in records:
            pair_id = record.get("bilateral_pair_id")
            if pair_id and pair_id in ids:
                s.run(_LINK_BILATERAL, a=record["id"], b=pair_id).consume()
                linked += 1

    logger.info(
        "Ingested %d exercises; %d HAS_BILATERAL_PAIR edges (pairs present in library)",
        len(records),
        linked,
    )
    return len(records)

"""Graph schema: node labels, uniqueness constraints, and the vector index.

P1-T1 scope: make every PRD §7.1 node/edge type representable and create the
uniqueness constraints + the Neo4j native vector index, idempotently. The Cypher
is built by pure functions (``constraint_statements`` / ``vector_index_statement``)
so it can be unit-tested without a live database; ``apply_schema`` executes them.

Edges are schemaless in Neo4j (no DDL needed); ``EDGE_TYPES`` is the documented
inventory ingestion (P1-T2+) and the README rely on.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.client import session

logger = logging.getLogger(__name__)

# Node label -> the property that uniquely identifies an instance.
# Context/member-scoped nodes are keyed by an `id`; ontology/library nodes
# (joints, muscles, movement patterns, equipment) are keyed by their `name`.
NODE_KEYS: dict[str, str] = {
    "Member": "id",
    "Goal": "id",
    "Preference": "id",
    "Exercise": "id",
    "MuscleGroup": "name",
    "Joint": "name",
    "MovementPattern": "name",
    "Equipment": "name",
    "Injury": "id",
    "Condition": "id",
    "Workout": "id",
    "WorkoutSession": "id",
    "ContextSignal": "id",
    "ChatSnippet": "id",
    "Transcript": "id",
    "BiometricSignal": "id",
}

# Documented edge inventory. Relationship types need no constraints in Neo4j; this
# list is the source of truth ingestion and the README reference.
EDGE_TYPES: list[str] = [
    # --- PRD §7.1 core edges ---
    "HAS_GOAL",
    "HAS_PREFERENCE",
    "HAS_INJURY",
    "AFFECTS_JOINT",
    "LOADS_JOINT",
    "TRAINS_MUSCLE",
    "USES_EQUIPMENT",
    "HAS_MOVEMENT_PATTERN",
    "COMPLETED_WORKOUT",
    "CONTAINS_EXERCISE",
    "HAS_CONTEXT_SIGNAL",
    "MENTIONS_INJURY",
    "MENTIONS_GOAL",
    "HAS_BILATERAL_PAIR",
    # --- Extensions beyond the §7.1 minimum (PRD §7.1 is "at minimum") ---
    # Member's available equipment (challenge/PRD retrieval expands to "available
    # equipment"); §7.1 only defines Exercise USES_EQUIPMENT.
    "HAS_EQUIPMENT_ACCESS",
    # Member's scheduled/performed sessions with a status (completed/missed), the
    # basis for adherence/recent-history retrieval. COMPLETED_WORKOUT/Workout stay
    # reserved for generated/logged workouts (Phase 3).
    "HAS_WORKOUT_SESSION",
]

# Embeddable nodes carry a shared secondary label so one vector index spans them
# (signals, injuries, goals, exercises per PRD §7.5). Embeddings are written in P2-T1.
EMBEDDABLE_LABEL = "Embeddable"
EMBEDDING_PROPERTY = "embedding"
VECTOR_INDEX_NAME = "embeddable_embedding"


def _constraint_name(label: str, key: str) -> str:
    return f"constraint_{label.lower()}_{key.lower()}"


def constraint_statements() -> list[str]:
    """Return idempotent uniqueness-constraint statements for every node label."""
    return [
        f"CREATE CONSTRAINT {_constraint_name(label, key)} IF NOT EXISTS "
        f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
        for label, key in NODE_KEYS.items()
    ]


def vector_index_statement(dimensions: int) -> str:
    """Return the idempotent native vector-index statement for embeddable nodes."""
    return (
        f"CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS "
        f"FOR (n:{EMBEDDABLE_LABEL}) ON (n.{EMBEDDING_PROPERTY}) "
        f"OPTIONS {{ indexConfig: {{ "
        f"`vector.dimensions`: {int(dimensions)}, "
        f"`vector.similarity_function`: 'cosine' }} }}"
    )


def apply_schema() -> None:
    """Create all constraints and the vector index. Safe to run repeatedly."""
    settings = get_settings()
    statements = constraint_statements()
    statements.append(vector_index_statement(settings.embedding_dim))
    with session() as s:
        for stmt in statements:
            s.run(stmt).consume()
    logger.info(
        "Applied graph schema: %d constraints + 1 vector index (dim=%d)",
        len(NODE_KEYS),
        settings.embedding_dim,
    )

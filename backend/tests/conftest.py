"""Shared test fixtures.

The two critical-path tests are INTEGRATION tests over the deterministic graph layer
(no LLM / no embeddings needed). They require a running Neo4j (``docker compose up
neo4j``). If Neo4j is unreachable the whole session is skipped with a clear message,
so ``pytest`` is friendly when the stack isn't up.
"""

from __future__ import annotations

import pytest

from app.graph.client import close_driver, verify_connectivity
from app.graph.schema import apply_schema
from app.ingestion.exercises import ingest_exercises
from app.ingestion.members import ingest_member
from app.ingestion.signals import structure_member_signals


@pytest.fixture(scope="session", autouse=True)
def seeded_graph():
    """Ensure schema + Maya + exercises are present (idempotent). Skip if no DB."""
    try:
        verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j not reachable ({exc}); run `docker compose up -d neo4j` first")
    apply_schema()
    ingest_exercises()
    ingest_member()
    structure_member_signals()
    yield
    close_driver()


@pytest.fixture
def member_id() -> str:
    return "maya"

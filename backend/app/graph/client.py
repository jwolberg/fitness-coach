"""Neo4j driver and session management.

P0-T2 scope: own the single Neo4j driver for the process, expose a session
context manager, and verify connectivity on boot. Connection settings come from
``app.config`` (env-driven). Later tickets (P1-T1+) add schema/constraints and
queries on top of this; this module is the only place that constructs the driver.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from neo4j import Driver, GraphDatabase, Session

from app.config import get_settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the process-wide Neo4j driver, creating it on first use."""
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Created Neo4j driver for %s", settings.neo4j_uri)
    return _driver


def verify_connectivity() -> None:
    """Verify the driver can reach Neo4j; raises if it cannot."""
    get_driver().verify_connectivity()


@contextmanager
def session() -> Iterator[Session]:
    """Yield a Neo4j session bound to the shared driver."""
    with get_driver().session() as s:
        yield s


def close_driver() -> None:
    """Close and drop the shared driver (called on app shutdown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Closed Neo4j driver")

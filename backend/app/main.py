"""FastAPI application entrypoint.

Creates the app, registers the API router (currently ``/health``), and on startup
opens a Neo4j session to confirm the graph is reachable (P0-T2 acceptance). Run
locally with ``uvicorn app.main:app --reload`` from ``backend/``.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.graph.client import close_driver, session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Neo4j can take a few seconds to accept connections after `docker compose up`,
# so retry briefly before giving up. The API still serves if the graph is down.
_STARTUP_RETRIES = 10
_STARTUP_DELAY_SECONDS = 3


def _connect_to_graph() -> None:
    """Open a Neo4j session and run a trivial query, retrying on failure."""
    for attempt in range(1, _STARTUP_RETRIES + 1):
        try:
            with session() as s:
                s.run("RETURN 1").consume()
            logger.info("Connected to Neo4j (opened a session on attempt %d)", attempt)
            return
        except Exception as exc:  # noqa: BLE001 - log and retry any driver/connection error
            logger.warning(
                "Neo4j not ready (attempt %d/%d): %s", attempt, _STARTUP_RETRIES, exc
            )
            time.sleep(_STARTUP_DELAY_SECONDS)
    logger.error("Could not reach Neo4j after %d attempts; API will serve anyway", _STARTUP_RETRIES)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _connect_to_graph()
    yield
    close_driver()


app = FastAPI(title="Knowledge Graph Coaching Platform API", lifespan=lifespan)
app.include_router(router)

"""API route handlers.

P0-T1 scope: just the ``/health`` liveness check (challenge "Dockerized local
setup"; ARCHITECTURE §3.2). Later tickets register the PRD §7.9 endpoints on this
same router.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns 200 so Compose / the reviewer can confirm the API is up."""
    return {"status": "ok"}

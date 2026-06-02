"""FastAPI application entrypoint.

P0-T1 scope: create the app and register the API router (currently just
``/health``). Run locally with ``uvicorn app.main:app --reload`` from ``backend/``.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Knowledge Graph Coaching Platform API")
app.include_router(router)

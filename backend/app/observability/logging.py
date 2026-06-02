"""Structured logging (PRD §13).

A tiny JSON-line event logger so each coach request emits machine-readable records:
incoming query, retrieved counts, validation results, repair attempts, final status.
The retriever/generator/validator also log via their own module loggers; this adds
the request-level events the API emits.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("coaching.events")


def log_event(event: str, **fields: Any) -> None:
    """Emit one structured JSON log line for an event."""
    try:
        payload = json.dumps({"event": event, **fields}, default=str)
    except (TypeError, ValueError):
        payload = json.dumps({"event": event, "fields_repr": repr(fields)})
    logger.info(payload)

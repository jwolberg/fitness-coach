"""LLM adapter (ARCH §6): provider-agnostic behind a thin interface.

The LLM generates recommendations but is **never** the only safety layer (ARCH §1,
PRD §7.7) — the deterministic validator (P3-T2) checks every output. Configured by
env (`LLM_PROVIDER`, `LLM_MODEL`); OpenAI is the implemented provider.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Minimal LLM interface (one provider seam)."""

    def complete_json(self, system: str, user: str) -> dict: ...


class OpenAILLMClient:
    """OpenAI chat completions in JSON mode."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for generation. Set it in your env / .env.")
        from openai import OpenAI  # lazy import

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.llm_model

    def complete_json(self, system: str, user: str) -> dict:
        """Return the model's JSON object response as a dict."""
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """Return the configured LLM client (OpenAI only for now)."""
    provider = get_settings().llm_provider
    if provider == "openai":
        return OpenAILLMClient()
    raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'. Only 'openai' is implemented.")

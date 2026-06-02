"""Environment-driven configuration.

P0-T1 scope: read the settings later tickets will need (Neo4j connection, LLM
provider, API keys) from the environment with safe local defaults, so the app is
configurable without forcing any provider key at skeleton stage. Uses stdlib
``os.getenv`` to avoid an extra dependency at this stage; the values are typed on
a small dataclass per ARCHITECTURE §4 "typed contracts at every boundary".
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Resolved application settings (immutable snapshot of the environment)."""

    # Neo4j connection (used from P0-T2 onward).
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # LLM / embeddings provider selection (used from Phase 2/3). Provider-agnostic
    # behind the adapter per ARCHITECTURE §6; keys are optional at skeleton stage.
    llm_provider: str
    embedding_provider: str
    openai_api_key: str | None
    anthropic_api_key: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings read once from the process environment."""
    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "local"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

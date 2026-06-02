"""Embedder adapter + embedding of graph nodes into the Neo4j vector index (PRD §7.5
steps 1-2; ARCH §6).

Embeddings are OpenAI-only by project decision (no local fallback) — running
retrieval/generation requires ``OPENAI_API_KEY``. The ``Embedder`` protocol keeps
that choice behind one seam so a different provider could be added later.

``compose_node_text`` is pure/testable. ``embed_graph_nodes`` writes vectors onto
the ``:Embeddable`` nodes (signals, injuries, goals, exercises); ``vector_search``
runs the native vector index query and returns ranked matches.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings
from app.graph.client import session

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Minimal embedding interface (one provider seam)."""

    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbedder:
    """OpenAI embeddings (default: text-embedding-3-small, 1536 dims)."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for embeddings (no local fallback). "
                "Set it in your environment / .env."
            )
        from openai import OpenAI  # lazy import so the package only loads when used

        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self.dimension = settings.embedding_dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Return the configured embedder (OpenAI only for now)."""
    provider = get_settings().embedding_provider
    if provider == "openai":
        return OpenAIEmbedder()
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER '{provider}'. Only 'openai' is implemented "
        "(no local embedder by project decision)."
    )


def compose_node_text(name: str, desc: str, muscles: list[str], patterns: list[str]) -> str:
    """Build the text representation embedded for a node (richer = better matching)."""
    parts: list[str] = []
    if name:
        parts.append(name)
    if desc:
        parts.append(desc)
    if muscles:
        parts.append("muscles: " + ", ".join(muscles))
    if patterns:
        parts.append("movement: " + ", ".join(patterns))
    return " | ".join(parts)


# Fetch every embeddable node with the fields used to build its text. Exercises pick
# up their muscle groups / movement patterns; other nodes leave those empty.
_FETCH_EMBEDDABLE = """
MATCH (n:Embeddable)
OPTIONAL MATCH (n)-[:TRAINS_MUSCLE]->(mg:MuscleGroup)
OPTIONAL MATCH (n)-[:HAS_MOVEMENT_PATTERN]->(mp:MovementPattern)
WITH n, collect(DISTINCT mg.name) AS muscles, collect(DISTINCT mp.name) AS patterns
RETURN elementId(n) AS eid,
       coalesce(n.name, '') AS name,
       coalesce(n.text, n.description, '') AS desc,
       muscles, patterns
"""

_WRITE_EMBEDDING = """
UNWIND $rows AS row
MATCH (n) WHERE elementId(n) = row.eid
CALL db.create.setNodeVectorProperty(n, 'embedding', row.embedding)
"""

_VECTOR_QUERY = """
CALL db.index.vector.queryNodes('embeddable_embedding', $k, $vec) YIELD node, score
RETURN score,
       labels(node) AS labels,
       coalesce(node.name, node.text, node.description) AS label,
       elementId(node) AS eid
ORDER BY score DESC
"""


def embed_graph_nodes(batch_size: int = 128) -> int:
    """Embed every ``:Embeddable`` node and store the vector. Returns nodes embedded."""
    embedder = get_embedder()
    with session() as s:
        rows = [dict(r) for r in s.run(_FETCH_EMBEDDABLE)]
        if not rows:
            logger.info("No :Embeddable nodes to embed")
            return 0

        total = 0
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            texts = [compose_node_text(r["name"], r["desc"], r["muscles"], r["patterns"]) for r in batch]
            vectors = embedder.embed_documents(texts)
            payload = [{"eid": r["eid"], "embedding": vec} for r, vec in zip(batch, vectors)]
            s.run(_WRITE_EMBEDDING, rows=payload).consume()
            total += len(payload)

    logger.info("Embedded %d nodes (model dim=%d)", total, embedder.dimension)
    return total


def vector_search(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Embed the query and return the top-k ranked nodes from the vector index."""
    vec = get_embedder().embed_query(query)
    with session() as s:
        return [dict(r) for r in s.run(_VECTOR_QUERY, k=k, vec=vec)]

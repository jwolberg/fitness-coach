"""One-shot graph seeding for the demo (PRD §15.1; ARCH §7).

Applies schema, ingests exercises + Maya + her signals, and embeds nodes so the demo
works on first boot. Idempotent — safe to re-run. Embeddings need OPENAI_API_KEY; if
it's missing we seed the graph and skip embeddings with a clear warning (retrieval
needs them, so set the key and re-run to enable the LLM flows).

Run: ``python -m app.seed`` (the Compose ``seed`` service runs this).
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.client import close_driver, verify_connectivity
from app.graph.schema import apply_schema
from app.ingestion.exercises import ingest_exercises
from app.ingestion.members import ingest_member
from app.ingestion.signals import structure_member_signals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.seed")


def main() -> None:
    verify_connectivity()
    apply_schema()
    n_ex = ingest_exercises()
    member_id = ingest_member()
    structure_member_signals()
    logger.info("Seeded graph: %d exercises, member '%s'", n_ex, member_id)

    if get_settings().openai_api_key:
        from app.retrieval.embeddings import embed_graph_nodes

        n = embed_graph_nodes()
        logger.info("Embedded %d nodes", n)
    else:
        logger.warning(
            "OPENAI_API_KEY not set — skipped embeddings. Retrieval/generation need them; "
            "set the key and re-run `python -m app.seed`."
        )
    close_driver()
    logger.info("Seeding complete.")


if __name__ == "__main__":
    main()

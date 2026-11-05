"""Embed the knowledge base into pgvector.

python -m app.ingest
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.factory import build_knowledge_base
from app.knowledge_base import load_markdown_chunks


def ingest() -> int:
    s = get_settings()
    chunks = load_markdown_chunks(s.kb_path)
    count = build_knowledge_base(s).ingest(chunks)
    logging.getLogger(__name__).info("ingested %s chunks from %s", count, s.kb_path)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(f"ingested {ingest()} chunks")

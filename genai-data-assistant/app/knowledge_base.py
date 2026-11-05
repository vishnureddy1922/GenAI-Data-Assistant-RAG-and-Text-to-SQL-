"""Documentation RAG: markdown docs -> chunks -> embeddings in pgvector -> cited answers."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.prompts import RAG_SYSTEM

log = logging.getLogger(__name__)


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[Document]: ...


def load_markdown_chunks(folder: str | Path, chunk_size: int = 900, overlap: int = 120) -> list[Document]:
    """Split by markdown headers first (keeps sections intact), then by size."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")], strip_headers=False
    )
    size_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)

    chunks: list[Document] = []
    for path in sorted(Path(folder).glob("**/*.md")):
        for section in header_splitter.split_text(path.read_text(encoding="utf-8")):
            heading = " > ".join(section.metadata[h] for h in ("h1", "h2", "h3") if h in section.metadata)
            for piece in size_splitter.split_documents([section]):
                piece.metadata = {"source": path.name, "section": heading}
                chunks.append(piece)
    return chunks


def chunk_id(doc: Document) -> str:
    """Stable id, so re-ingesting the same text upserts instead of duplicating."""
    key = f"{doc.metadata.get('source')}|{doc.metadata.get('section')}|{doc.page_content}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


class PgVectorKnowledgeBase:
    def __init__(self, connection: str, collection: str, embeddings):
        from langchain_postgres import PGVector

        self.store = PGVector(
            embeddings=embeddings,
            collection_name=collection,
            connection=connection,
            use_jsonb=True,
        )

    def ingest(self, docs: list[Document]) -> int:
        if docs:
            self.store.add_documents(docs, ids=[chunk_id(d) for d in docs])
        return len(docs)

    def search(self, query: str, k: int) -> list[Document]:
        return self.store.similarity_search(query, k=k)


@dataclass
class RAGResult:
    answer: str
    sources: list[dict]
    contexts: list[str]


class DocsQA:
    def __init__(self, llm: BaseChatModel, retriever: Retriever, k: int = 4):
        self.llm = llm
        self.retriever = retriever
        self.k = k

    def run(self, question: str) -> RAGResult:
        docs = self.retriever.search(question, self.k)
        if not docs:
            return RAGResult("I couldn't find anything about that in the data documentation.", [], [])

        context = "\n\n".join(
            f"[{i}] ({d.metadata.get('source')} / {d.metadata.get('section')})\n{d.page_content}"
            for i, d in enumerate(docs, start=1)
        )
        reply = self.llm.invoke([SystemMessage(RAG_SYSTEM.format(context=context)), HumanMessage(question)])
        sources = [
            {"ref": i, "source": d.metadata.get("source"), "section": d.metadata.get("section")}
            for i, d in enumerate(docs, start=1)
        ]
        return RAGResult(str(reply.content).strip(), sources, [d.page_content for d in docs])

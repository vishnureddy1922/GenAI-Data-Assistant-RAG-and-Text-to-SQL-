"""Wire real components from settings (used by the API, CLI and eval)."""

from __future__ import annotations

from sqlalchemy import create_engine

from app.assistant import Assistant
from app.config import Settings, get_settings
from app.knowledge_base import DocsQA, PgVectorKnowledgeBase
from app.llm import get_chat_model, get_embeddings
from app.schema_context import SchemaContext
from app.text_to_sql import TextToSQL


def build_knowledge_base(s: Settings) -> PgVectorKnowledgeBase:
    return PgVectorKnowledgeBase(s.database_url, s.kb_collection, get_embeddings(s))


def build_assistant(settings: Settings | None = None) -> Assistant:
    s = settings or get_settings()
    llm = get_chat_model(s)
    ro_engine = create_engine(s.readonly_database_url, pool_pre_ping=True, pool_size=5)
    schema = SchemaContext.from_database(ro_engine, s.warehouse_schema)

    sql = TextToSQL(llm, ro_engine, schema, max_rows=s.sql_max_rows, timeout_ms=s.sql_timeout_ms)
    docs = DocsQA(llm, build_knowledge_base(s), k=s.retrieval_k)
    return Assistant(llm, sql, docs)

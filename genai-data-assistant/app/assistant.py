"""Orchestrates routing, text-to-SQL and docs RAG behind one ask() call."""

from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.knowledge_base import DocsQA
from app.router import Route, route_question
from app.text_to_sql import TextToSQL

log = logging.getLogger(__name__)


class AssistantResponse(BaseModel):
    question: str
    route: Route
    answer: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    sources: list[dict] = []
    contexts: list[str] = []
    error: str | None = None
    latency_ms: int = 0


class Assistant:
    def __init__(self, llm: BaseChatModel, sql: TextToSQL, docs: DocsQA):
        self.llm = llm
        self.sql = sql
        self.docs = docs

    def ask(self, question: str, force_route: Route | None = None) -> AssistantResponse:
        started = time.perf_counter()
        route = force_route or route_question(question, self.llm)

        if route == "sql":
            r = self.sql.run(question)
            resp = AssistantResponse(
                question=question,
                route="sql",
                answer=r.answer,
                sql=r.sql,
                columns=r.columns,
                rows=r.rows,
                error=r.error,
            )
        else:
            d = self.docs.run(question)
            resp = AssistantResponse(
                question=question, route="docs", answer=d.answer, sources=d.sources, contexts=d.contexts
            )

        resp.latency_ms = int((time.perf_counter() - started) * 1000)
        log.info("answered route=%s latency_ms=%s error=%s", route, resp.latency_ms, resp.error)
        return resp

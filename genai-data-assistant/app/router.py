"""Decide whether a question needs the warehouse (text-to-SQL) or the docs (RAG).

Cheap keyword scoring handles the obvious cases with no model call; ambiguous
questions go to the LLM.
"""

from __future__ import annotations

import re
from typing import Literal

from langchain_core.language_models import BaseChatModel

from app.prompts import ROUTER

Route = Literal["sql", "docs"]

SQL_HINTS = [
    r"\bhow many\b",
    r"\bhow much\b",
    r"\btotal\b",
    r"\btop \d+\b",
    r"\btop\b",
    r"\baverage\b",
    r"\bavg\b",
    r"\bcount\b",
    r"\bsum\b",
    r"\btrend\b",
    r"\bby (month|week|day|year|country|category|channel)\b",
    r"\blist\b",
    r"\bwhich (customers|products|countries)\b",
    r"\bper (month|customer|order)\b",
    r"\blast (month|quarter|year)\b",
    r"\bin 20\d\d\b",
    r"\bhighest\b",
    r"\blowest\b",
    r"\bcompare\b",
]
# Definitional phrasing outweighs metric words ("how is average order value calculated?")
DOCS_STRONG_HINTS = [
    r"\bdefin",
    r"\bhow (is|are|do we|should) .* (calculated|computed|measured)\b",
    r"\bmean(s|ing)?\b",
]
DOCS_HINTS = [
    r"\bpolicy\b",
    r"\bwho owns\b",
    r"\bowner\b",
    r"\brefresh",
    r"\bschedule\b",
    r"\bdata quality\b",
    r"\bwhat does\b",
    r"\bsla\b",
    r"\bpii\b",
    r"\bretention\b",
]


def heuristic_scores(question: str) -> tuple[int, int]:
    q = question.lower()
    sql = sum(bool(re.search(p, q)) for p in SQL_HINTS)
    docs = sum(bool(re.search(p, q)) for p in DOCS_HINTS) + 2 * sum(bool(re.search(p, q)) for p in DOCS_STRONG_HINTS)
    return sql, docs


def route_question(question: str, llm: BaseChatModel | None = None) -> Route:
    sql, docs = heuristic_scores(question)
    if sql >= docs + 2 or (sql and not docs):
        return "sql"
    if docs >= sql + 2 or (docs and not sql):
        return "docs"
    if llm is None:
        return "sql" if sql >= docs else "docs"

    reply = llm.invoke(ROUTER.format(question=question)).content
    word = str(reply).strip().lower()
    return "docs" if word.startswith("doc") else "sql"

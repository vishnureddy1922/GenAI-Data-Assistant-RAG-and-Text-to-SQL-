"""Question -> guarded SQL -> read-only execution -> plain English answer."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.prompts import ANSWER_FROM_ROWS, SQL_REPAIR, TEXT_TO_SQL_SYSTEM
from app.schema_context import SchemaContext
from app.sql_guard import UnsafeSQLError, extract_sql, guard_sql

log = logging.getLogger(__name__)


@dataclass
class SQLResult:
    sql: str
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    attempts: int = 1
    error: str | None = None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def run_readonly(engine: Engine, sql: str, timeout_ms: int) -> tuple[list[str], list[dict[str, Any]]]:
    with engine.connect() as conn:
        with conn.begin():
            if engine.dialect.name == "postgresql":
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [{c: _jsonable(v) for c, v in zip(columns, r, strict=True)} for r in result.fetchall()]
    return columns, rows


def rows_to_markdown(columns: list[str], rows: list[dict[str, Any]], limit: int = 20) -> str:
    if not rows:
        return "(no rows)"
    head = "| " + " | ".join(columns) + " |\n|" + "---|" * len(columns)
    body = "\n".join("| " + " | ".join(str(r[c]) for c in columns) + " |" for r in rows[:limit])
    return f"{head}\n{body}"


class TextToSQL:
    def __init__(
        self,
        llm: BaseChatModel,
        engine: Engine,
        schema: SchemaContext,
        max_rows: int = 200,
        timeout_ms: int = 5000,
        max_repairs: int = 1,
    ):
        self.llm = llm
        self.engine = engine
        self.schema = schema
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms
        self.max_repairs = max_repairs

    def generate_sql(self, question: str) -> str:
        messages = [
            SystemMessage(TEXT_TO_SQL_SYSTEM.format(schema=self.schema.to_prompt())),
            HumanMessage(question),
        ]
        return extract_sql(str(self.llm.invoke(messages).content))

    def _guard(self, sql: str) -> str:
        return guard_sql(sql, self.schema.allowed_tables, self.max_rows, self.schema.schema)

    def run(self, question: str) -> SQLResult:
        raw_sql = self.generate_sql(question)
        attempts = 1

        while True:
            try:
                safe_sql = self._guard(raw_sql)
                columns, rows = run_readonly(self.engine, safe_sql, self.timeout_ms)
                break
            except UnsafeSQLError as exc:
                # Never retry around a guardrail: report it.
                log.warning("blocked SQL: %s", exc)
                return SQLResult(
                    sql=raw_sql,
                    error=f"Query blocked by guardrails: {exc}",
                    attempts=attempts,
                    answer="I couldn't run a safe query for that question.",
                )
            except SQLAlchemyError as exc:
                if attempts > self.max_repairs:
                    return SQLResult(
                        sql=raw_sql,
                        error=str(exc.__cause__ or exc),
                        attempts=attempts,
                        answer="The query failed to run. Try rephrasing the question.",
                    )
                attempts += 1
                log.info("repairing SQL after error: %s", exc)
                repair = SQL_REPAIR.format(question=question, sql=raw_sql, error=str(exc.__cause__ or exc)[:500])
                raw_sql = extract_sql(
                    str(
                        self.llm.invoke(
                            [
                                SystemMessage(TEXT_TO_SQL_SYSTEM.format(schema=self.schema.to_prompt())),
                                HumanMessage(repair),
                            ]
                        ).content
                    )
                )

        answer = str(
            self.llm.invoke(
                ANSWER_FROM_ROWS.format(
                    question=question,
                    sql=safe_sql,
                    row_count=len(rows),
                    table=rows_to_markdown(columns, rows),
                )
            ).content
        ).strip()
        return SQLResult(sql=safe_sql, columns=columns, rows=rows, answer=answer, attempts=attempts)

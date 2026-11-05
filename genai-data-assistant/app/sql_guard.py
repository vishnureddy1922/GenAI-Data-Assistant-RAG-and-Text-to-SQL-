"""Guardrails for LLM generated SQL.

LLM output is untrusted input. Before anything reaches the database it must:
  * parse as exactly one PostgreSQL statement
  * be a read query (SELECT / WITH / UNION), with no DML, DDL or SELECT INTO
  * only reference allow-listed warehouse tables (CTEs are fine)
  * avoid dangerous functions (pg_sleep, file access, dblink, config changes)
  * carry a LIMIT no larger than max_rows (added or capped automatically)

The database role is read only as well; this is defense in depth, not the only layer.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp


class UnsafeSQLError(ValueError):
    """Raised when generated SQL fails a guardrail."""


_FORBIDDEN_NODE_NAMES = (
    "Insert",
    "Update",
    "Delete",
    "Merge",
    "Drop",
    "Create",
    "Alter",
    "AlterTable",
    "TruncateTable",
    "Command",
    "Grant",
    "Into",
    "Copy",
    "Set",
    "Transaction",
    "Commit",
    "Rollback",
)
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NODE_NAMES if hasattr(exp, n))

BLOCKED_FUNCTIONS = {
    "pg_sleep",
    "pg_sleep_for",
    "pg_sleep_until",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "lo_import",
    "lo_export",
    "dblink",
    "dblink_exec",
    "set_config",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "pg_reload_conf",
    "current_setting",
    "query_to_xml",
    "pg_stat_file",
}


def guard_sql(sql: str, allowed_tables: set[str], max_rows: int = 200, default_schema: str = "analytics") -> str:
    """Validate and normalize SQL. Returns safe SQL or raises UnsafeSQLError."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise UnsafeSQLError("empty SQL")

    try:
        statements = [s for s in sqlglot.parse(cleaned, read="postgres") if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise UnsafeSQLError(f"could not parse SQL: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeSQLError("exactly one statement is allowed")
    tree = statements[0]

    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError(f"only read queries are allowed, got {type(tree).__name__}")

    bad = tree.find(*FORBIDDEN_NODES)
    if bad is not None:
        raise UnsafeSQLError(f"statement type not allowed: {type(bad).__name__}")

    for func in tree.find_all(exp.Func):
        name = (func.name if isinstance(func, exp.Anonymous) else func.sql_name()).lower()
        if name in BLOCKED_FUNCTIONS:
            raise UnsafeSQLError(f"function not allowed: {name}")

    allowed = {t.lower() for t in allowed_tables}
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = (table.name or "").lower()
        if not name:
            raise UnsafeSQLError("table functions are not allowed")
        if not table.db and name in cte_names:
            continue
        qualified = f"{(table.db or default_schema).lower()}.{name}"
        if qualified not in allowed:
            raise UnsafeSQLError(f"table not allowed: {qualified}")

    tree = _enforce_limit(tree, max_rows)
    return tree.sql(dialect="postgres")


def _enforce_limit(tree: exp.Query, max_rows: int) -> exp.Query:
    limit = tree.args.get("limit")
    if limit is None:
        return tree.limit(max_rows)
    value = limit.expression
    if isinstance(value, exp.Literal) and value.is_int and int(value.name) <= max_rows:
        return tree
    return tree.limit(max_rows)


def extract_sql(text: str) -> str:
    """Pull SQL out of a model reply (```sql fences or bare text)."""
    import re

    fenced = re.search(r"```(?:sql|postgresql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return (fenced.group(1) if fenced else text).strip()

import pytest

from app.sql_guard import UnsafeSQLError, extract_sql, guard_sql

ALLOWED = {"analytics.customers", "analytics.orders", "analytics.order_items", "analytics.products"}


def guard(sql, max_rows=200):
    return guard_sql(sql, ALLOWED, max_rows=max_rows)


def test_simple_select_gets_limit():
    out = guard("SELECT country, count(*) FROM analytics.customers GROUP BY country")
    assert out.endswith("LIMIT 200")


def test_existing_small_limit_is_kept():
    assert guard("SELECT * FROM analytics.orders LIMIT 5").endswith("LIMIT 5")


def test_large_limit_is_capped():
    assert guard("SELECT * FROM analytics.orders LIMIT 100000", max_rows=50).endswith("LIMIT 50")


def test_trailing_semicolon_ok():
    guard("SELECT 1 FROM analytics.orders;")


def test_unqualified_table_uses_default_schema():
    guard("SELECT * FROM customers")


def test_cte_and_join_allowed():
    guard(
        """
        WITH completed AS (SELECT * FROM analytics.orders WHERE status = 'completed')
        SELECT c.country, count(*) FROM completed o JOIN analytics.customers c ON c.customer_id = o.customer_id
        GROUP BY c.country
        """
    )


def test_union_allowed():
    guard("SELECT customer_id FROM analytics.customers UNION SELECT customer_id FROM analytics.orders")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM analytics.orders",
        "UPDATE analytics.customers SET tier = 'platinum'",
        "INSERT INTO analytics.orders VALUES (1, 1, 'completed')",
        "DROP TABLE analytics.orders",
        "CREATE TABLE analytics.x AS SELECT * FROM analytics.orders",
        "ALTER TABLE analytics.orders ADD COLUMN x int",
        "TRUNCATE analytics.orders",
        "GRANT SELECT ON analytics.orders TO public",
        "SELECT * INTO analytics.copy FROM analytics.orders",
        "SET statement_timeout = 0",
    ],
)
def test_writes_and_ddl_blocked(sql):
    with pytest.raises(UnsafeSQLError):
        guard(sql)


def test_stacked_statements_blocked():
    with pytest.raises(UnsafeSQLError, match="one statement"):
        guard("SELECT * FROM analytics.orders; DROP TABLE analytics.orders")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM public.api_users",
        "SELECT * FROM langchain_pg_embedding",
    ],
)
def test_tables_outside_allowlist_blocked(sql):
    with pytest.raises(UnsafeSQLError, match="table not allowed"):
        guard(sql)


def test_subquery_tables_checked_too():
    with pytest.raises(UnsafeSQLError):
        guard("SELECT * FROM analytics.orders WHERE customer_id IN (SELECT 1 FROM public.secrets)")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(30) FROM analytics.orders",
        "SELECT pg_read_file('/etc/passwd') FROM analytics.orders",
        "SELECT set_config('statement_timeout', '0', false) FROM analytics.orders",
    ],
)
def test_dangerous_functions_blocked(sql):
    with pytest.raises(UnsafeSQLError, match="function not allowed"):
        guard(sql)


def test_garbage_is_rejected():
    with pytest.raises(UnsafeSQLError):
        guard("this is not sql at all )))")


def test_extract_sql_from_fenced_reply():
    reply = "Here you go:\n```sql\nSELECT 1\n```\nHope that helps"
    assert extract_sql(reply) == "SELECT 1"


def test_extract_sql_from_bare_reply():
    assert extract_sql("  SELECT 2  ") == "SELECT 2"

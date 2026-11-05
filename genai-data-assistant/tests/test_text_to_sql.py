from app.text_to_sql import TextToSQL, rows_to_markdown
from tests.conftest import fake_llm


def test_happy_path_runs_guarded_sql_and_summarizes(warehouse, schema):
    llm = fake_llm(
        "```sql\nSELECT country, count(*) AS customers FROM analytics.customers "
        "WHERE tier = 'platinum' GROUP BY country ORDER BY country\n```",
        "US and IN each have one platinum customer.",
    )
    result = TextToSQL(llm, warehouse, schema).run("How many platinum customers per country?")

    assert result.error is None
    assert result.columns == ["country", "customers"]
    assert result.rows == [{"country": "IN", "customers": 1}, {"country": "US", "customers": 1}]
    assert "LIMIT 200" in result.sql
    assert result.answer.startswith("US and IN")


def test_failed_query_is_repaired_once(warehouse, schema):
    llm = fake_llm(
        "SELECT revenue FROM analytics.orders",  # column does not exist
        "SELECT count(*) AS n FROM analytics.orders",  # repaired
        "There are 2 orders.",
    )
    result = TextToSQL(llm, warehouse, schema).run("How many orders?")
    assert result.attempts == 2
    assert result.rows == [{"n": 2}]
    assert result.error is None


def test_gives_up_after_max_repairs(warehouse, schema):
    llm = fake_llm("SELECT nope FROM analytics.orders", "SELECT still_nope FROM analytics.orders")
    result = TextToSQL(llm, warehouse, schema, max_repairs=1).run("How many orders?")
    assert result.error is not None
    assert result.rows == []


def test_guardrail_violation_never_executes(warehouse, schema):
    llm = fake_llm("DELETE FROM analytics.orders")
    result = TextToSQL(llm, warehouse, schema).run("Remove all orders")
    assert "blocked by guardrails" in result.error

    with warehouse.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM analytics.orders").scalar() == 2


def test_schema_prompt_lists_tables_and_comments(schema):
    prompt = schema.to_prompt()
    assert "TABLE analytics.customers  -- One row per customer" in prompt
    assert "country text  -- ISO code" in prompt
    assert schema.allowed_tables == {"analytics.customers", "analytics.orders"}


def test_rows_to_markdown():
    md = rows_to_markdown(["a", "b"], [{"a": 1, "b": "x"}])
    assert md.splitlines()[0] == "| a | b |"
    assert rows_to_markdown(["a"], []) == "(no rows)"

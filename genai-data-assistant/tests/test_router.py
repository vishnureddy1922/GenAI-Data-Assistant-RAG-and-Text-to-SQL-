import pytest

from app.router import route_question
from tests.conftest import fake_llm


@pytest.mark.parametrize(
    "question",
    [
        "How many customers signed up in 2025?",
        "Top 5 products by revenue",
        "What was total revenue by month?",
        "Which countries have the highest average order value?",
    ],
)
def test_obvious_sql_questions(question):
    assert route_question(question) == "sql"


@pytest.mark.parametrize(
    "question",
    [
        "How is average order value calculated?",
        "What does the store channel mean?",
        "Who owns the analytics schema?",
        "When is the warehouse refresh scheduled?",
        "What is our PII policy?",
    ],
)
def test_obvious_docs_questions(question):
    assert route_question(question) == "docs"


def test_ambiguous_question_uses_llm():
    assert route_question("Tell me about refunds", fake_llm("docs")) == "docs"
    assert route_question("Tell me about refunds", fake_llm("sql")) == "sql"


def test_unexpected_llm_reply_defaults_to_sql():
    assert route_question("Tell me about refunds", fake_llm("not sure")) == "sql"

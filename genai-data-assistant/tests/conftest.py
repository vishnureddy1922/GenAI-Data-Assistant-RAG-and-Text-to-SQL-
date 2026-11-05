import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

from app.schema_context import SchemaContext, TableInfo


@pytest.fixture()
def warehouse():
    """SQLite stand-in for the warehouse, with an attached 'analytics' schema."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def attach(dbapi_conn, _):
        dbapi_conn.execute("ATTACH DATABASE ':memory:' AS analytics")

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE analytics.customers (customer_id INTEGER, country TEXT, tier TEXT)"))
        conn.execute(text("CREATE TABLE analytics.orders (order_id INTEGER, customer_id INTEGER, status TEXT)"))
        conn.execute(
            text(
                "INSERT INTO analytics.customers VALUES (1,'US','gold'),(2,'US','platinum'),(3,'IN','platinum'),"
                "(4,'CA','bronze')"
            )
        )
        conn.execute(text("INSERT INTO analytics.orders VALUES (10,1,'completed'),(11,2,'cancelled')"))
    return engine


@pytest.fixture()
def schema():
    return SchemaContext(
        schema="analytics",
        tables={
            "customers": TableInfo(
                "customers",
                "One row per customer",
                [("customer_id", "integer", None), ("country", "text", "ISO code"), ("tier", "text", None)],
            ),
            "orders": TableInfo(
                "orders",
                None,
                [("order_id", "integer", None), ("customer_id", "integer", None), ("status", "text", None)],
            ),
        },
    )


def fake_llm(*responses: str) -> FakeListChatModel:
    return FakeListChatModel(responses=list(responses))


class FakeRetriever:
    def __init__(self, docs=None):
        self.docs = (
            docs
            if docs is not None
            else [
                Document(
                    page_content="Revenue is quantity times unit_price for completed orders.",
                    metadata={"source": "metric_definitions.md", "section": "Metric definitions > Revenue"},
                ),
                Document(
                    page_content="Cancelled and refunded orders are excluded.",
                    metadata={"source": "metric_definitions.md", "section": "Metric definitions > Orders"},
                ),
            ]
        )
        self.queries = []

    def search(self, query, k):
        self.queries.append((query, k))
        return self.docs[:k]

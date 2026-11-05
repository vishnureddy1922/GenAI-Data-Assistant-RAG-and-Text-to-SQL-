import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import api
from app.assistant import Assistant
from app.config import Settings
from app.knowledge_base import DocsQA
from app.text_to_sql import TextToSQL
from tests.conftest import FakeRetriever, fake_llm


@pytest.fixture()
def client(warehouse, schema):
    llm = fake_llm(
        "SELECT count(*) AS customers FROM analytics.customers",
        "There are 4 customers.",
    )
    docs_llm = fake_llm("Revenue counts completed orders only [1].")
    api.app.state.assistant = Assistant(llm, TextToSQL(llm, warehouse, schema), DocsQA(docs_llm, FakeRetriever()))
    with TestClient(api.app) as c:
        yield c
    del api.app.state.assistant


def test_ask_sql_route(client):
    body = client.post("/ask", json={"question": "How many customers are there?"}).json()
    assert body["route"] == "sql"
    assert body["rows"] == [{"customers": 4}]
    assert body["answer"] == "There are 4 customers."
    assert body["sql"].startswith("SELECT")


def test_ask_docs_route(client):
    body = client.post("/ask", json={"question": "How is revenue defined?"}).json()
    assert body["route"] == "docs"
    assert body["sources"][0]["source"] == "metric_definitions.md"


def test_forced_route(client):
    body = client.post("/ask", json={"question": "Revenue please", "route": "docs"}).json()
    assert body["route"] == "docs"


def test_validation(client):
    assert client.post("/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/ask", json={"question": "valid question", "route": "web"}).status_code == 422


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_ingest_requires_api_key(client, monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: Settings(api_key=SecretStr("s3cret")))
    assert client.post("/ingest").status_code == 401
    assert client.post("/ingest", headers={"X-API-Key": "wrong"}).status_code == 401

"""HTTP API for the assistant.

uvicorn app.api:app --reload
"""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.assistant import Assistant, AssistantResponse
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "assistant"):
        from app.factory import build_assistant

        app.state.assistant = build_assistant()
    yield


app = FastAPI(
    title="GenAI Data Assistant",
    version="1.0.0",
    description="Ask questions about company data in plain English. Numbers come from SQL, definitions from the docs.",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    route: Literal["sql", "docs"] | None = Field(None, description="Force a route instead of auto routing")


def get_assistant(request: Request) -> Assistant:
    return request.app.state.assistant


def require_api_key(x_api_key: str | None = Header(None)) -> None:
    expected = get_settings().api_key
    if expected is None:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected.get_secret_value()):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post("/ask", response_model=AssistantResponse)
def ask(body: AskRequest, assistant: Assistant = Depends(get_assistant)) -> AssistantResponse:
    return assistant.ask(body.question, force_route=body.route)


@app.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest_docs() -> dict:
    from app.ingest import ingest

    return {"chunks": ingest()}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

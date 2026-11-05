from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider: "openai" or "bedrock"
    llm_provider: str = "openai"
    llm_temperature: float = 0.0

    openai_api_key: SecretStr | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    aws_region: str = "us-east-1"
    bedrock_chat_model: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"

    # Vector store + app tables (read/write) and the warehouse (read only role)
    database_url: str = "postgresql+psycopg://assistant:assistant@localhost:5432/assistant"
    readonly_database_url: str = "postgresql+psycopg://assistant_ro:assistant_ro@localhost:5432/assistant"
    warehouse_schema: str = "analytics"

    kb_collection: str = "data_docs"
    kb_path: str = "knowledge_base"
    retrieval_k: int = 4

    sql_max_rows: int = 200
    sql_timeout_ms: int = 5000

    api_key: SecretStr | None = None  # protects /ingest


@lru_cache
def get_settings() -> Settings:
    return Settings()

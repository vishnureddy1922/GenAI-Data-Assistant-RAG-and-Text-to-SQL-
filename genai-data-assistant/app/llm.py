"""Model factories. Provider SDKs are imported lazily so tests need neither."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    s = settings or get_settings()
    if s.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=s.openai_chat_model,
            temperature=s.llm_temperature,
            api_key=s.openai_api_key.get_secret_value() if s.openai_api_key else None,
            timeout=60,
            max_retries=2,
        )
    if s.llm_provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(model=s.bedrock_chat_model, region_name=s.aws_region, temperature=s.llm_temperature)
    raise ValueError(f"Unknown LLM_PROVIDER: {s.llm_provider}")


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    s = settings or get_settings()
    if s.llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=s.openai_embedding_model,
            api_key=s.openai_api_key.get_secret_value() if s.openai_api_key else None,
        )
    if s.llm_provider == "bedrock":
        from langchain_aws import BedrockEmbeddings

        return BedrockEmbeddings(model_id=s.bedrock_embedding_model, region_name=s.aws_region)
    raise ValueError(f"Unknown LLM_PROVIDER: {s.llm_provider}")

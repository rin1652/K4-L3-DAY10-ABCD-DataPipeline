from __future__ import annotations

import warnings

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from core.config import Settings, normalized_provider, require_llm_credentials

_OPENAI_REASONING_PREFIXES = ("o1", "o3", "o4", "gpt-5", "gpt-6")
# langchain-openai's Responses API parsing triggers noisy (harmless) pydantic serializer warnings.
warnings.filterwarnings("ignore", message="Pydantic serializer warnings", category=UserWarning)


def _is_openai_reasoning_model(model_name: str) -> bool:
    return model_name.strip().lower().startswith(_OPENAI_REASONING_PREFIXES)


def build_llm(settings: Settings, temperature: float = 0.0):
    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    if provider == "openai":
        # Reasoning models (o-series, gpt-5+) reject `temperature` and only allow
        # function tools / structured output through the Responses API.
        sampling = {} if _is_openai_reasoning_model(settings.model_name) else {"temperature": temperature}
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            use_responses_api=True,
            **sampling,
        )
    if provider == "anthropic":
        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )
    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
        )
    if provider == "ollama":
        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    if provider == "custom":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
        )
    if provider == "mock":
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(responses=["This is a mock response from the scholarly corpus."])
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

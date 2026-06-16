"""Factory for optional LLM providers."""

from __future__ import annotations

import os
from collections.abc import Mapping

from projectpilot.llm.base import BaseLLMClient, LLMConfigurationError
from projectpilot.llm.deepseek_client import DeepSeekLLMClient
from projectpilot.llm.mock_client import MockLLMClient


def get_llm_provider(env: Mapping[str, str] | None = None) -> str:
    values = env or os.environ
    return values.get("LLM_PROVIDER", "mock").strip().lower() or "mock"


def get_llm_client(
    provider: str | None = None,
    env: Mapping[str, str] | None = None,
) -> BaseLLMClient:
    values = env or os.environ
    selected_provider = (provider or get_llm_provider(values)).strip().lower()
    if selected_provider == "mock":
        return MockLLMClient()
    if selected_provider == "deepseek":
        api_key = values.get("DEEPSEEK_API_KEY", "")
        base_url = values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = values.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
        return DeepSeekLLMClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    raise LLMConfigurationError(f"不支持的 LLM_PROVIDER：{selected_provider}")

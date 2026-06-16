from __future__ import annotations

import pytest

from projectpilot.llm.base import LLMConfigurationError
from projectpilot.llm.client_factory import get_llm_client, get_llm_provider
from projectpilot.llm.deepseek_client import DeepSeekLLMClient
from projectpilot.llm.mock_client import MockLLMClient


def test_default_provider_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert get_llm_provider() == "mock"
    assert isinstance(get_llm_client(), MockLLMClient)


def test_mock_provider_does_not_require_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    client = get_llm_client()

    assert isinstance(client, MockLLMClient)
    assert "mock LLM provider" in client.generate("review this")


def test_deepseek_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(LLMConfigurationError, match="DEEPSEEK_API_KEY"):
        get_llm_client()


def test_deepseek_client_uses_mocked_openai_compatible_client() -> None:
    class FakeMessage:
        content = "DeepSeek mocked review"

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "deepseek-v4-flash"
            assert kwargs["messages"][1]["content"] == "prompt"
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAIClient:
        chat = FakeChat()

    client = DeepSeekLLMClient(
        api_key="test-key",
        model="deepseek-v4-flash",
        openai_client=FakeOpenAIClient(),
    )

    assert client.generate("prompt") == "DeepSeek mocked review"

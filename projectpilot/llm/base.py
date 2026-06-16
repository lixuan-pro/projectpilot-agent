"""Base LLM client interface for optional review advisors."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMConfigurationError(RuntimeError):
    """Raised when an LLM provider is selected but not configured."""


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider call fails."""


class BaseLLMClient(ABC):
    provider_name: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text for a bounded review prompt."""


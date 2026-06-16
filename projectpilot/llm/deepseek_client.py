"""DeepSeek OpenAI-compatible client for optional LLM review."""

from __future__ import annotations

from typing import Any

from projectpilot.llm.base import BaseLLMClient, LLMConfigurationError, LLMProviderError


class DeepSeekLLMClient(BaseLLMClient):
    provider_name = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        openai_client: Any | None = None,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError("LLM_PROVIDER=deepseek 需要配置 DEEPSEEK_API_KEY。")
        self._api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = openai_client

    def generate(self, prompt: str) -> str:
        if not prompt.strip():
            return ""
        client = self._client or self._build_client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 ProjectPilot Agent 的可选 LLM Review Advisor。"
                            "只能基于已有分析报告做语义审阅，不要要求自动修改代码或提交。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:  # pragma: no cover - exact SDK exceptions vary.
            raise LLMProviderError("DeepSeek LLM 调用失败。") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMProviderError("DeepSeek LLM 返回格式不可解析。") from exc
        return content or ""

    def _build_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on local env.
            raise LLMConfigurationError("使用 DeepSeek provider 需要安装 openai SDK。") from exc
        return OpenAI(api_key=self._api_key, base_url=self.base_url)


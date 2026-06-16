"""Mock LLM client used by default and in tests."""

from __future__ import annotations

from projectpilot.llm.base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    provider_name = "mock"

    def generate(self, prompt: str) -> str:
        if not prompt.strip():
            return ""
        return "\n".join(
            [
                "使用 mock LLM provider 生成审阅报告。",
                "",
                "- 当前报告链路已覆盖 README、docs、tests、eval、git log 和 Tool Call Log。",
                "- 建议继续保持 rule-based analyzer 作为确定性 baseline，LLM 只作为语义审阅补充。",
                "- 输出建议应继续进入 Human Confirmation，不应自动修改代码或执行 commit。",
            ]
        )


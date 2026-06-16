from __future__ import annotations

from projectpilot.analyzers.llm_review_advisor import LLMReviewAdvisor
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_llm_review_advisor_generates_mock_review(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    report = tmp_path / "project_status_report.md"
    report.write_text("# 项目状态报告\n\n- 交付就绪评分：80/100\n", encoding="utf-8")
    output_path = tmp_path / "llm_review.md"

    result = LLMReviewAdvisor().review(
        report_paths={"project_status_report": report},
        output_path=output_path,
    )

    assert result.provider == "mock"
    assert result.status == ToolCallStatus.SUCCESS
    assert output_path.exists()
    markdown = output_path.read_text(encoding="utf-8")
    assert "# LLM 语义审阅报告" in markdown
    assert "本报告由可选 LLM Review Advisor 基于已有分析结果生成" in markdown
    assert "## 7. 人工确认状态" in markdown
    assert "状态：pending" in markdown
    assert "mock LLM provider" in markdown


def test_llm_review_advisor_handles_deepseek_without_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    report = tmp_path / "risk_report.md"
    report.write_text("# 风险提醒\n", encoding="utf-8")
    output_path = tmp_path / "llm_review.md"

    result = LLMReviewAdvisor().review(
        report_paths={"risk_report": report},
        output_path=output_path,
    )

    assert result.provider == "deepseek"
    assert result.status == ToolCallStatus.PERMISSION_DENIED
    markdown = output_path.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY" in markdown
    assert "Tool Call 状态：permission_denied" in markdown

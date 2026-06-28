from __future__ import annotations

from projectpilot.analyzers.llm_raghub_risk_reviewer import (
    LLMRAGHubRiskReviewer,
    build_raghub_risk_review_prompt,
)
from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    RetrievalModeMetrics,
)
from projectpilot.analyzers.raghub_delivery_analyzer import analyze_raghub_delivery
from projectpilot.schemas.tool_schema import ToolCallStatus


def test_llm_raghub_risk_reviewer_generates_mock_review(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "llm_risk_review.md"

    result = LLMRAGHubRiskReviewer().review(
        metrics=metrics,
        delivery_report=report,
        output_path=output_path,
    )

    assert result.provider == "mock"
    assert result.status == ToolCallStatus.SUCCESS
    markdown = output_path.read_text(encoding="utf-8")
    assert "## 1. 风险总览" in markdown
    assert "## 2. no-answer 风险为什么可以标记为 resolved" in markdown
    assert "## 3. source competition 为什么仍然 open" in markdown
    assert "## 4. hybrid 为什么不建议默认启用" in markdown
    assert "## 5. Eval-100 为什么不是生产 benchmark" in markdown
    assert "状态：pending" in markdown
    assert "不声称 no-answer 已经解决所有幻觉或安全问题" in markdown


def test_llm_raghub_risk_reviewer_deepseek_without_key_is_controlled(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    metrics = _metrics()
    report = analyze_raghub_delivery(metrics)
    output_path = tmp_path / "llm_risk_review.md"

    result = LLMRAGHubRiskReviewer().review(
        metrics=metrics,
        delivery_report=report,
        output_path=output_path,
    )

    assert result.provider == "deepseek"
    assert result.status == ToolCallStatus.PERMISSION_DENIED
    markdown = output_path.read_text(encoding="utf-8")
    assert "Tool Call 状态：permission_denied" in markdown
    assert "DEEPSEEK_API_KEY" in markdown


def test_raghub_risk_review_prompt_contains_boundaries() -> None:
    prompt = build_raghub_risk_review_prompt(
        metrics=_metrics(),
        delivery_report=analyze_raghub_delivery(_metrics()),
    )

    assert "你只能基于给定的 RAGHub Eval-100 指标" in prompt
    assert "不要编造不存在的指标" in prompt
    assert "不要声称项目是生产级系统" in prompt
    assert "不要声称 no-answer 已经解决所有幻觉或安全问题" in prompt
    assert "不要建议自动修改或自动提交代码" in prompt


def _metrics() -> RAGHubEvalMetrics:
    return RAGHubEvalMetrics(
        total_queries=100,
        in_corpus_count=88,
        out_of_corpus_count=12,
        answerability_accuracy=0.99,
        expected_answerable_accept_rate=0.9886,
        expected_unanswerable_reject_rate=1.0,
        out_of_corpus_rejected="12/12",
        exact_source_hit_rate=0.5909,
        acceptable_source_hit_rate=0.7955,
        source_group_hit_rate=0.9091,
        keyword_hit_rate=0.6414,
        retrieval_modes={
            "vector": RetrievalModeMetrics(
                mode="vector",
                total_queries=100,
                top_k=3,
                exact_source_hit_rate=0.5909,
                acceptable_source_hit_rate=0.7955,
                source_group_hit_rate=0.9091,
                keyword_hit_rate=0.6391,
            )
        },
        vector_average_score=8.83,
        hybrid_average_score=8.9,
        vector_wins=12,
        hybrid_wins=12,
        ties=76,
        source_files={},
    )

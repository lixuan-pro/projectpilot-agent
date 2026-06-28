from __future__ import annotations

import json

from projectpilot.analyzers.consistency_checker import ConsistencyChecker


def test_consistency_checker_flags_high_risk_overclaims(tmp_path) -> None:
    risky_path = tmp_path / "risky.md"
    risky_path.write_text(
        "\n".join(
            [
                "RAGHub 是生产级平台。",
                "hybrid 全面优于 vector。",
                "ProjectPilot 自动提交 RAGHub。",
                "source_hit_rate = 0.95。",
                "完全解决幻觉。",
            ]
        ),
        encoding="utf-8",
    )
    output_md = tmp_path / "consistency_check.md"
    output_json = tmp_path / "consistency_check.json"

    report = ConsistencyChecker().check(
        files={"risky": risky_path},
        output_markdown_path=output_md,
        output_json_path=output_json,
    )

    assert report.status == "failed"
    check_types = {finding.check_type for finding in report.findings}
    assert "overclaimed_production_ready" in check_types
    assert "overclaimed_hybrid_gain" in check_types
    assert "overclaimed_agent_autonomy" in check_types
    assert "unsupported_metric" in check_types
    assert "overclaimed_no_answer_security" in check_types
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert output_md.exists()


def test_consistency_checker_accepts_negated_boundaries(tmp_path) -> None:
    safe_path = tmp_path / "safe.md"
    safe_path.write_text(
        "\n".join(
            [
                "ProjectPilot 不是生产级治理平台。",
                "不能说 hybrid 全面优于 vector。",
                "不能说完全解决幻觉。",
                "不自动提交 RAGHub。",
                "不涉及任何自动代码修改或自动提交。",
                "移除或淡化 README 中的生产就绪表述。",
                "human_confirmation_status=pending。",
            ]
        ),
        encoding="utf-8",
    )

    report = ConsistencyChecker().check(
        files={"safe": safe_path},
        output_markdown_path=tmp_path / "consistency_check.md",
        output_json_path=tmp_path / "consistency_check.json",
    )

    assert report.status == "passed"
    assert report.findings == []

"""Deterministic consistency checks for RAGHub interview and resume assets."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


HIGH = "high"
WARNING = "warning"


@dataclass(frozen=True)
class ConsistencyFinding:
    check_type: str
    severity: str
    file: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class ConsistencyCheckReport:
    status: str
    findings: list[ConsistencyFinding]
    checked_files: list[str]
    human_confirmation_status: str = "pending"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "findings": [asdict(finding) for finding in self.findings],
            "checked_files": self.checked_files,
            "human_confirmation_status": self.human_confirmation_status,
        }


class ConsistencyChecker:
    """Rule-based guard against unsupported public-facing claims."""

    def check(
        self,
        files: dict[str, str | Path],
        output_markdown_path: str | Path = "outputs/raghub_eval100/consistency_check.md",
        output_json_path: str | Path = "outputs/raghub_eval100/consistency_check.json",
    ) -> ConsistencyCheckReport:
        loaded = _load_files(files)
        findings: list[ConsistencyFinding] = []
        for label, text in loaded.items():
            findings.extend(_check_text(label, text))
        status = _status(findings)
        report = ConsistencyCheckReport(
            status=status,
            findings=findings,
            checked_files=list(loaded),
        )

        markdown_path = Path(output_markdown_path)
        json_path = Path(output_json_path)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(build_consistency_markdown(report), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return report


def build_consistency_markdown(report: ConsistencyCheckReport) -> str:
    lines = [
        "# RAGHub Asset Consistency Check",
        "",
        f"- status: {report.status}",
        f"- human_confirmation_status: {report.human_confirmation_status}",
        f"- checked_files: {len(report.checked_files)}",
        "",
        "## Checked Files",
        "",
        *[f"- {path}" for path in report.checked_files],
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("- No high-risk overclaim or unsupported metric was detected.")
    else:
        lines.extend(
            [
                "| check_type | severity | file | evidence | recommendation |",
                "| ---------- | -------- | ---- | -------- | -------------- |",
                *[
                    "| "
                    f"{finding.check_type} | "
                    f"{finding.severity} | "
                    f"{finding.file} | "
                    f"{_table_cell(finding.evidence)} | "
                    f"{_table_cell(finding.recommendation)} |"
                    for finding in report.findings
                ],
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- 本检查是规则化文本守卫，不是生产级审计。",
            "- status=passed 只表示当前检查规则未发现指定高风险表述。",
            "- 所有输出仍需人工确认，不自动修改 RAGHub，不自动提交代码。",
            "",
        ]
    )
    return "\n".join(lines)


def _load_files(files: dict[str, str | Path]) -> dict[str, str]:
    loaded: dict[str, str] = {}
    for label, raw_path in files.items():
        path = Path(raw_path)
        if path.exists() and path.is_file():
            loaded[f"{label}: {path}"] = path.read_text(encoding="utf-8")
    return loaded


def _check_text(label: str, text: str) -> list[ConsistencyFinding]:
    findings: list[ConsistencyFinding] = []
    findings.extend(_check_overclaimed_production_ready(label, text))
    findings.extend(_check_overclaimed_no_answer_security(label, text))
    findings.extend(_check_overclaimed_hybrid_gain(label, text))
    findings.extend(_check_overclaimed_agent_autonomy(label, text))
    findings.extend(_check_unsupported_metrics(label, text))
    if not _has_boundary_statement(text):
        findings.append(
            ConsistencyFinding(
                check_type="missing_boundary_statement",
                severity=WARNING,
                file=label,
                evidence="No pending/manual-confirmation/project-level boundary marker found.",
                recommendation="Add a boundary statement that keeps output pending and non-production.",
            )
        )
    return findings


def _check_overclaimed_production_ready(
    label: str,
    text: str,
) -> list[ConsistencyFinding]:
    findings: list[ConsistencyFinding] = []
    for phrase in ["生产级", "企业级", "生产可用", "生产就绪"]:
        for evidence in _iter_phrase_evidence(text, phrase):
            if _is_negated_boundary(evidence):
                continue
            findings.append(
                ConsistencyFinding(
                    check_type="overclaimed_production_ready",
                    severity=HIGH,
                    file=label,
                    evidence=evidence,
                    recommendation="Keep RAGHub/ProjectPilot wording at project-level evidence, not production or enterprise readiness.",
                )
            )
    return findings


def _check_overclaimed_no_answer_security(
    label: str,
    text: str,
) -> list[ConsistencyFinding]:
    patterns = [
        "完全解决幻觉",
        "彻底解决幻觉",
        "解决所有幻觉",
        "完全解决安全",
        "彻底解决 no-answer 安全问题",
    ]
    return [
        ConsistencyFinding(
            check_type="overclaimed_no_answer_security",
            severity=HIGH,
            file=label,
            evidence=evidence,
            recommendation="Limit no-answer claims to Eval-100 out-of-corpus evidence and keep broader safety claims out.",
        )
        for pattern in patterns
        for evidence in _iter_phrase_evidence(text, pattern)
        if not _is_negated_boundary(evidence)
    ]


def _check_overclaimed_hybrid_gain(
    label: str,
    text: str,
) -> list[ConsistencyFinding]:
    patterns = [
        "hybrid 全面优于 vector",
        "hybrid 已经全面胜过 vector",
        "混合检索全面优于",
        "默认替换 vector",
    ]
    return [
        ConsistencyFinding(
            check_type="overclaimed_hybrid_gain",
            severity=HIGH,
            file=label,
            evidence=evidence,
            recommendation="State that hybrid remains experimental and is not the default.",
        )
        for pattern in patterns
        for evidence in _iter_phrase_evidence(text, pattern)
        if not _is_negated_boundary(evidence)
    ]


def _check_overclaimed_agent_autonomy(
    label: str,
    text: str,
) -> list[ConsistencyFinding]:
    patterns = [
        "自动修复 RAGHub",
        "自动修改 RAGHub",
        "自动提交",
        "自动创建 PR",
        "自动执行工具",
    ]
    return [
        ConsistencyFinding(
            check_type="overclaimed_agent_autonomy",
            severity=HIGH,
            file=label,
            evidence=evidence,
            recommendation="Describe ProjectPilot as an advisor/workflow logger, not an autonomous code-changing agent.",
        )
        for pattern in patterns
        for evidence in _iter_phrase_evidence(text, pattern)
        if not _is_negated_boundary(evidence)
    ]


def _check_unsupported_metrics(label: str, text: str) -> list[ConsistencyFinding]:
    findings: list[ConsistencyFinding] = []
    metric_patterns = [
        (
            re.compile(r"(?:source_hit_rate|source hit rate)\s*[:=]?\s*(0\.9[5-9]|1\.0|95%)", re.I),
            "unsupported source_hit_rate above documented Eval-100 metrics",
        ),
        (
            re.compile(r"准确率\s*(?:达到|=|:)?\s*99%"),
            "unsupported generic accuracy claim",
        ),
        (
            re.compile(r"(?:hybrid|混合检索)\s*(?:显著领先|大幅领先)", re.I),
            "unsupported hybrid lead claim",
        ),
        (
            re.compile(r"out[_-]?of[_-]?corpus\s*(?:>|超过)\s*12/12", re.I),
            "unsupported out-of-corpus ratio beyond Eval-100 total",
        ),
    ]
    for pattern, recommendation_detail in metric_patterns:
        for match in pattern.finditer(text):
            evidence = _window(text, match.start(), match.end())
            if _is_negated_boundary(evidence):
                continue
            findings.append(
                ConsistencyFinding(
                    check_type="unsupported_metric",
                    severity=HIGH,
                    file=label,
                    evidence=evidence,
                    recommendation=f"Remove or qualify this metric: {recommendation_detail}.",
                )
            )
    return findings


def _iter_phrase_evidence(text: str, phrase: str) -> list[str]:
    return [
        _window(text, match.start(), match.end())
        for match in re.finditer(re.escape(phrase), text, flags=re.I)
    ]


def _window(text: str, start: int, end: int, radius: int = 42) -> str:
    line_left = text.rfind("\n", 0, start) + 1
    line_right = text.find("\n", end)
    if line_right == -1:
        line_right = len(text)
    context_left = line_left
    current_line = text[line_left:line_right].lstrip()
    if current_line.startswith(("-", "*")):
        scan_pos = max(0, line_left - 1)
        for _ in range(8):
            previous_left = text.rfind("\n", 0, scan_pos)
            if previous_left == -1:
                context_left = 0
                break
            context_left = previous_left + 1
            scan_pos = previous_left
    if line_right - line_left <= radius * 4:
        return " ".join(text[context_left:line_right].split())

    left = max(line_left, start - radius)
    right = min(line_right, end + radius)
    return " ".join(text[left:right].split())


def _is_negated_boundary(evidence: str) -> bool:
    normalized = evidence.lower().replace(" ", "")
    safe_markers = [
        "不是",
        "不代表",
        "不等同",
        "不声称",
        "不宣称",
        "不写",
        "不能",
        "不要",
        "不包含",
        "不输出",
        "不建议",
        "不把",
        "不默认",
        "不自动",
        "不涉及",
        "不会",
        "不应",
        "不宜",
        "移除",
        "删除",
        "淡化",
        "检查并删除",
        "避免",
        "限制",
        "而非",
        "非生产",
        "严格区分",
        "未注明",
        "生产就绪准备",
        "过度表述清单",
        "overclaimsnot",
        "notputinresume",
        "≠",
        "未自动",
        "未输出",
        "notproduction",
        "notaproduction",
        "notenterprise",
        "notdefault",
        "notclaim",
    ]
    return any(marker in normalized for marker in safe_markers)


def _has_boundary_statement(text: str) -> bool:
    markers = [
        "human_confirmation_status",
        "pending",
        "人工确认",
        "不能夸大",
        "当前边界",
        "不是生产级",
        "不自动",
        "不提交",
        "project-level benchmark",
        "项目级",
    ]
    return any(marker in text for marker in markers)


def _status(findings: list[ConsistencyFinding]) -> str:
    if any(finding.severity == HIGH for finding in findings):
        return "failed"
    if findings:
        return "passed_with_warnings"
    return "passed"


def _table_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")

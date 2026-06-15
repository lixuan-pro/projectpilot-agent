"""Markdown report writers for ProjectPilot analysis outputs."""

from __future__ import annotations

from pathlib import Path

from projectpilot.analyzers.project_status_analyzer import ProjectStatusReport


def write_project_status_report(
    report: ProjectStatusReport,
    output_path: str | Path = "outputs/project_status_report.md",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_project_status_report(report), encoding="utf-8")
    return path


def write_next_tasks(
    report: ProjectStatusReport,
    output_path: str | Path = "outputs/next_tasks.md",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_next_tasks(report), encoding="utf-8")
    return path


def build_project_status_report(report: ProjectStatusReport) -> str:
    lines = [
        "# Project Status Report",
        "",
        "## 1. Target Project",
        "",
        f"- Name: {report.project_name}",
        f"- Path: {report.project_path}",
        f"- Identity: {report.project_identity}",
        "",
        "## 2. Current Evidence",
        "",
        *_bullet_lines(report.evidence_files),
        "",
        "## 3. Implemented Capabilities",
        "",
        *_bullet_lines(report.implemented_capabilities),
        "",
        "## 4. Delivery Strengths",
        "",
        *_bullet_lines(report.delivery_strengths),
        "",
        "## 5. Delivery Gaps",
        "",
        *_bullet_lines(report.delivery_gaps),
        "",
        "## 6. Risks",
        "",
        *_bullet_lines(report.risks),
        "",
        "## 7. Delivery Readiness Score",
        "",
        f"- 交付就绪评分：{report.delivery_readiness_score}/100",
        "- 评分类型：规则化证据完整度检查（v0.1 rule-based checklist）。",
        "- 解释：该分数表示目标项目在当前展示范围内的 README、docs、tests、eval、bad case 等证据完整度，不代表生产级可用或企业级 readiness。",
        "",
        *_score_lines(report),
        "",
        "## 8. Current Boundary",
        "",
        "This report is generated from bounded read-only evidence. It does not call an LLM, modify the target project, create commits, deploy code, or represent a production readiness audit.",
        "",
        "## 9. Suggested Next Step",
        "",
        *_bullet_lines(report.next_tasks[:3]),
        "",
    ]
    return "\n".join(lines)


def build_next_tasks(report: ProjectStatusReport) -> str:
    p0 = [item for item in report.next_tasks if item.startswith("P0:")]
    p1 = [item for item in report.next_tasks if item.startswith("P1:")]
    p2 = [item for item in report.next_tasks if item.startswith("P2:")]

    lines = [
        "# Next Tasks",
        "",
        "## P0",
        "",
        *_bullet_lines(_strip_priority(p0) or ["No P0 task detected by the current rules."]),
        "",
        "## P1",
        "",
        *_bullet_lines(_strip_priority(p1) or ["No P1 task detected by the current rules."]),
        "",
        "## P2",
        "",
        *_bullet_lines(_strip_priority(p2) or ["No P2 task detected by the current rules."]),
        "",
        "## Interview Preparation",
        "",
        *_bullet_lines(report.interview_preparation),
        "",
    ]
    return "\n".join(lines)


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- No evidence found."]
    return [f"- {item}" for item in items]


def _score_lines(report: ProjectStatusReport) -> list[str]:
    return [
        f"- {name}: +{points}"
        for name, points in report.score_breakdown.items()
    ]


def _strip_priority(items: list[str]) -> list[str]:
    return [item.split(":", 1)[1].strip() for item in items]

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
        "# 项目状态报告",
        "",
        "## 1. 目标项目",
        "",
        f"- 项目名称：{report.project_name}",
        f"- 项目路径：{report.project_path}",
        f"- 项目识别：{report.project_identity}",
        "",
        "## 2. 当前证据",
        "",
        *_bullet_lines(report.evidence_files),
        "",
        "## 3. 已实现能力",
        "",
        *_bullet_lines(report.implemented_capabilities),
        "",
        "## 4. 交付优势",
        "",
        *_bullet_lines(report.delivery_strengths),
        "",
        "## 5. 交付缺口",
        "",
        *_bullet_lines(report.delivery_gaps),
        "",
        "## 6. 风险提醒",
        "",
        *_bullet_lines(report.risks),
        "",
        "## 7. 交付就绪评分",
        "",
        f"- 交付就绪评分：{report.delivery_readiness_score}/100",
        "- 评分类型：规则化证据完整度检查（v0.1 rule-based checklist）。",
        "- 解释：该分数表示目标项目在当前展示范围内的 README、docs、tests、eval、bad case 等证据完整度，不代表生产级可用或企业级 readiness。",
        "",
        *_score_lines(report),
        "",
        "## 8. 当前边界",
        "",
        "本报告基于有限、只读的项目证据生成。它不调用 LLM，不修改目标项目，不创建 commit，不执行部署，也不代表生产级 readiness 审计。",
        "",
        "## 9. 建议下一步",
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
        "# 下一步任务",
        "",
        "## P0：当前必须处理",
        "",
        *_bullet_lines(_strip_priority(p0) or ["当前规则未检测到 P0 任务。"]),
        "",
        "## P1：近期增强",
        "",
        *_bullet_lines(_strip_priority(p1) or ["当前规则未检测到 P1 任务。"]),
        "",
        "## P2：后续规划",
        "",
        *_bullet_lines(_strip_priority(p2) or ["当前规则未检测到 P2 任务。"]),
        "",
        "## 面试准备",
        "",
        *_bullet_lines(report.interview_preparation),
        "",
    ]
    return "\n".join(lines)


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- 未检测到相关证据。"]
    return [f"- {item}" for item in items]


def _score_lines(report: ProjectStatusReport) -> list[str]:
    score_labels = {
        "README present": "README 存在",
        "docs present": "docs 存在",
        "tests present": "tests 存在",
        "eval present": "eval 存在",
        "bad_cases present": "bad_cases 存在",
        "problems_and_solutions present": "problems_and_solutions 存在",
        "recent commits present": "recent commits 存在",
        "clear boundaries / roadmap signals": "边界 / Roadmap 信号清晰",
    }
    return [
        f"- {score_labels.get(name, name)}：+{points}"
        for name, points in report.score_breakdown.items()
    ]


def _strip_priority(items: list[str]) -> list[str]:
    return [item.split(":", 1)[1].strip() for item in items]

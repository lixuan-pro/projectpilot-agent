"""Rule-based project status analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field

from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitLogResult


@dataclass(frozen=True)
class ProjectStatusReport:
    project_name: str
    project_path: str
    project_identity: str
    implemented_capabilities: list[str]
    evidence_files: list[str]
    delivery_strengths: list[str]
    delivery_gaps: list[str]
    risks: list[str]
    next_tasks: list[str]
    interview_preparation: list[str]
    delivery_readiness_score: int
    score_breakdown: dict[str, int] = field(default_factory=dict)


class ProjectStatusAnalyzer:
    """Generate a deterministic status report from bounded read-only evidence."""

    def analyze(
        self,
        project_name: str,
        context_result: ContextReadResult,
        git_result: GitLogResult,
    ) -> ProjectStatusReport:
        files = context_result.files
        evidence = _Evidence(files=files, git_result=git_result)
        breakdown = _score(evidence)

        return ProjectStatusReport(
            project_name=project_name,
            project_path=str(context_result.project_path),
            project_identity=_project_identity(project_name, evidence),
            implemented_capabilities=_implemented_capabilities(evidence),
            evidence_files=[item.path for item in files],
            delivery_strengths=_delivery_strengths(evidence),
            delivery_gaps=_delivery_gaps(evidence),
            risks=_risks(evidence, context_result, git_result),
            next_tasks=_next_tasks(evidence),
            interview_preparation=_interview_preparation(evidence),
            delivery_readiness_score=sum(breakdown.values()),
            score_breakdown=breakdown,
        )


@dataclass(frozen=True)
class _Evidence:
    files: list[ContextFile]
    git_result: GitLogResult

    @property
    def has_readme(self) -> bool:
        return any(item.category == "readme" for item in self.files)

    @property
    def has_docs(self) -> bool:
        return any(item.category == "docs" for item in self.files)

    @property
    def has_tests(self) -> bool:
        return any(item.category == "tests" for item in self.files)

    @property
    def has_eval(self) -> bool:
        return any(item.category == "eval" for item in self.files)

    @property
    def has_bad_cases(self) -> bool:
        return any("bad_cases" in item.path.lower() for item in self.files)

    @property
    def has_problems_and_solutions(self) -> bool:
        return any("problems_and_solutions" in item.path.lower() for item in self.files)

    @property
    def has_recent_commits(self) -> bool:
        return bool(self.git_result.commits)

    @property
    def has_boundaries_or_roadmap(self) -> bool:
        needles = ("boundary", "boundaries", "roadmap", "scope", "current boundary")
        return any(
            any(needle in item.content.lower() for needle in needles)
            for item in self.files
        )


def _score(evidence: _Evidence) -> dict[str, int]:
    return {
        "README present": 15 if evidence.has_readme else 0,
        "docs present": 15 if evidence.has_docs else 0,
        "tests present": 15 if evidence.has_tests else 0,
        "eval present": 15 if evidence.has_eval else 0,
        "bad_cases present": 10 if evidence.has_bad_cases else 0,
        "problems_and_solutions present": 10
        if evidence.has_problems_and_solutions
        else 0,
        "recent commits present": 10 if evidence.has_recent_commits else 0,
        "clear boundaries / roadmap signals": 10
        if evidence.has_boundaries_or_roadmap
        else 0,
    }


def _project_identity(project_name: str, evidence: _Evidence) -> str:
    if evidence.has_readme:
        return f"{project_name} 已检测到根目录 README，并具备可用于 rule-based review 的有限项目上下文。"
    return f"{project_name} 在当前有限读取范围内未检测到根目录 README。"


def _implemented_capabilities(evidence: _Evidence) -> list[str]:
    capabilities: list[str] = []
    content = "\n".join(item.content.lower() for item in evidence.files)
    keyword_map = {
        "README 项目定位证据": evidence.has_readme,
        "docs 文档证据": evidence.has_docs,
        "tests 测试证据": evidence.has_tests,
        "eval 评测证据": evidence.has_eval,
        "bad cases 记录": evidence.has_bad_cases,
        "problems_and_solutions 问题复盘": evidence.has_problems_and_solutions,
        "recent git commits 迭代记录": evidence.has_recent_commits,
        "/retrieve API 证据": "/retrieve" in content or "retrieve" in content,
        "/chat API 证据": "/chat" in content or "chat" in content,
        "citation / source 证据": "citation" in content or "source" in content,
        "no-answer 行为证据": "no-answer" in content or "no answer" in content,
    }
    for label, present in keyword_map.items():
        if present:
            capabilities.append(label)
    return capabilities or ["当前有限读取范围内未检测到已实现能力证据。"]


def _delivery_strengths(evidence: _Evidence) -> list[str]:
    strengths: list[str] = []
    if evidence.has_readme:
        strengths.append("已检测到 README，可用于说明项目定位、运行方式和当前边界。")
    if evidence.has_docs:
        strengths.append("docs 文档提供了实现思路、范围说明或交付背景。")
    if evidence.has_tests:
        strengths.append("tests 文件为当前实现能力提供了基础可信度。")
    if evidence.has_eval:
        strengths.append("eval 材料为检索或问答质量复盘提供了依据。")
    if evidence.has_bad_cases:
        strengths.append("bad cases 记录说明项目已开始显式沉淀已知问题。")
    if evidence.has_problems_and_solutions:
        strengths.append("problems_and_solutions 文档有助于项目复盘和面试表达。")
    if evidence.has_recent_commits:
        strengths.append("recent git commits 展示了近期迭代记录。")
    return strengths or ["当前规则未检测到明确的交付优势。"]


def _delivery_gaps(evidence: _Evidence) -> list[str]:
    gaps: list[str] = []
    if not evidence.has_readme:
        gaps.append("补充根目录 README，用于说明项目定位、运行方式和边界。")
    if not evidence.has_docs:
        gaps.append("补充 docs，说明架构、范围或 workflow 决策。")
    if not evidence.has_tests:
        gaps.append("补充 tests，覆盖核心项目行为。")
    if not evidence.has_eval:
        gaps.append("补充 eval 材料，让质量检查可以复现。")
    if not evidence.has_bad_cases:
        gaps.append("补充 bad cases，让当前限制和失败样例更明确。")
    if not evidence.has_problems_and_solutions:
        gaps.append("补充 problems_and_solutions，支持交付复盘和面试表达。")
    if not evidence.has_recent_commits:
        gaps.append("补充 recent git commits 或提交记录证据。")
    if not evidence.has_boundaries_or_roadmap:
        gaps.append("在 README/docs 中补充当前边界或 Roadmap 信号。")
    return gaps or ["当前规则未检测到影响主链路闭环的 P0 缺口。"]


def _risks(
    evidence: _Evidence,
    context_result: ContextReadResult,
    git_result: GitLogResult,
) -> list[str]:
    risks: list[str] = []
    if context_result.truncated_files:
        risks.append(
            "部分文件因读取上限被截断，报告中的细节可能不完整。"
        )
    if context_result.skipped_large_files:
        risks.append("部分非 README 大文件因读取上限被跳过。")
    if not git_result.is_git_repo:
        risks.append("目标路径未提供可读取的 git commit 证据。")
    if not evidence.has_eval:
        risks.append("缺少 eval 证据时，质量相关说法较难验证。")
    if not evidence.has_tests:
        risks.append("缺少 tests 时，实现能力说明的工程支撑较弱。")
    return risks or ["当前有限读取范围内未检测到明显规则化风险。"]


def _next_tasks(evidence: _Evidence) -> list[str]:
    tasks: list[str] = []
    if not evidence.has_readme:
        tasks.append("P0: 补充根目录 README，说明项目范围、运行方式和当前边界。")
    if not evidence.has_tests:
        tasks.append("P0: 为核心 workflow 补充 tests。")
    if not evidence.has_eval:
        tasks.append("P0: 补充最小 eval cases 和结果记录。")
    if not evidence.has_bad_cases:
        tasks.append("P1: 补充 bad case 记录，沉淀已知失败模式。")
    if not evidence.has_problems_and_solutions:
        tasks.append("P1: 补充 problems_and_solutions 文档，用于项目复盘。")
    if not evidence.has_boundaries_or_roadmap:
        tasks.append("P1: 在 README 或 docs 中补充当前边界和 Roadmap。")
    if not tasks:
        tasks.append("P1: 继续增强 eval 质量和项目展示材料。")
    tasks.append("P2: 在当前交付叙事清晰后，再扩展 Roadmap。")
    return tasks


def _interview_preparation(evidence: _Evidence) -> list[str]:
    items = [
        "准备项目目标、当前范围和明确不做事项的 1 分钟说明。",
        "准备 README、docs、tests、eval 和 recent commits 的简短 walkthrough。",
    ]
    if evidence.has_bad_cases:
        items.append("准备一个 bad case，说明它如何影响后续迭代。")
    if evidence.has_problems_and_solutions:
        items.append("将 problems_and_solutions 内容整理成 STAR 风格面试案例。")
    return items

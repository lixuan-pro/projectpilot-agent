"""Risk advisor for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import dataclass

from projectpilot.analyzers.project_status_analyzer import ProjectStatusReport
from projectpilot.tools.context_reader import ContextReadResult
from projectpilot.tools.git_reader import GitLogResult


@dataclass(frozen=True)
class RiskAdvice:
    p0: list[str]
    p1: list[str]
    p2: list[str]
    interview_risks: list[str]


class RiskAdvisor:
    """Classify risks into P0/P1/P2 and interview risks."""

    def advise(
        self,
        status_report: ProjectStatusReport,
        context_result: ContextReadResult,
        git_result: GitLogResult,
    ) -> RiskAdvice:
        p0: list[str] = []
        p1: list[str] = []
        p2: list[str] = [
            "后续可以再考虑更工业级的质量评估、权限控制和部署链路，但当前不应作为 Day 4 范围。"
        ]
        interview: list[str] = [
            "需要能解释交付证据完整度评分是规则化证据类型覆盖检查，不是项目质量满分或生产级 readiness。",
            "需要能说明 ProjectPilot 不自动修改代码、不自动提交、不调用目标项目 API。",
        ]

        gaps_text = "\n".join(status_report.delivery_gaps)
        if "README" in gaps_text:
            p0.append("README 证据不足会影响项目定位和面试可信度，建议优先处理。")
        if "tests" in gaps_text:
            p0.append("tests 证据不足会影响主链路工程可信度，建议优先处理。")
        if "eval" in gaps_text:
            p0.append("eval 证据不足会影响质量闭环说明，建议优先处理。")

        if context_result.truncated_files:
            p1.append("部分文件被截断，报告细节可能不完整；如需更细分析，可提高读取上限或补充摘要文档。")
        if context_result.skipped_large_files:
            p1.append("部分大文件被跳过，可能遗漏细节；当前不阻塞展示，但需要在复盘时说明。")
        if not git_result.is_git_repo:
            p1.append("未读取到 git commit 证据，项目迭代记录展示会变弱。")
        if not p1:
            p1.append("当前规则未检测到阻塞展示的 P1 风险，可继续增强材料质量。")
        if not p0:
            p0.append("当前规则未检测到必须立即处理的 P0 风险。")

        return RiskAdvice(p0=p0, p1=p1, p2=p2, interview_risks=interview)

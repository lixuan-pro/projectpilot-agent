"""Commit suggestion advisor for ProjectPilot Agent."""

from __future__ import annotations

from dataclasses import dataclass

from projectpilot.analyzers.project_status_analyzer import ProjectStatusReport
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.tools.git_reader import GitLogResult


@dataclass(frozen=True)
class CommitAdvice:
    recent_commit_summary: list[str]
    suggested_commit_type: str
    recommended_message: str
    not_recommended: list[str]
    confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING


class CommitAdvisor:
    """Generate commit message drafts without running git commands."""

    def advise(
        self,
        project_name: str,
        status_report: ProjectStatusReport,
        git_result: GitLogResult,
    ) -> CommitAdvice:
        recent = [
            f"{commit.hash} {commit.subject}" for commit in git_result.commits[:5]
        ]
        if not recent:
            recent = ["未读取到最近提交记录。"]

        if status_report.delivery_gaps and "P0" not in status_report.delivery_gaps[0]:
            commit_type = "docs"
        else:
            commit_type = "chore"

        return CommitAdvice(
            recent_commit_summary=recent,
            suggested_commit_type=commit_type,
            recommended_message=(
                f"{commit_type}: update {project_name} delivery analysis materials"
            ),
            not_recommended=[
                "不要提交 outputs/、run_logs/、缓存目录或临时文件。",
                "不要在未人工确认前执行 git add 或 git commit。",
                "不要把建议草案当作已经执行的目标项目变更。",
            ],
        )

"""Command line interface for ProjectPilot Agent."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from projectpilot.analyzers.commit_advisor import CommitAdvisor
from projectpilot.analyzers.llm_review_advisor import LLMReviewAdvisor
from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.analyzers.readme_advisor import ReadmeAdvisor
from projectpilot.analyzers.risk_advisor import RiskAdvisor
from projectpilot.config import load_config
from projectpilot.feedback.human_feedback import default_human_feedback
from projectpilot.logging.run_log import write_run_log
from projectpilot.logging.tool_call_log import (
    build_tool_call_record,
    tool_call_to_dict,
    utc_now,
    write_tool_call_log,
)
from projectpilot.schemas.tool_schema import ToolCallRecord, ToolCallStatus
from projectpilot.tools.context_reader import read_project_context
from projectpilot.tools.git_reader import read_recent_git_commits
from projectpilot.workflow.context_summary import write_context_summary
from projectpilot.workflow.report_writer import (
    write_commit_suggestions,
    write_next_tasks,
    write_project_status_report,
    write_readme_suggestions,
    write_risk_report,
)
from projectpilot.workflow.workflow_run import (
    build_workflow_step,
    workflow_step_to_dict,
)


T = TypeVar("T")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectpilot",
        description="ProjectPilot Agent CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Read bounded project context and write analysis outputs.",
    )
    analyze_parser.add_argument(
        "--config",
        required=True,
        help="Path to a projectpilot.yaml config file.",
    )

    return parser


def run_analyze(config_path: str) -> int:
    path = Path(config_path)
    config = load_config(path)
    run_id = f"analysis-{uuid4()}"
    workflow_started_at = utc_now()
    tool_calls: list[ToolCallRecord] = []
    workflow_steps = []

    project_config = config.get("project", {})
    context_config = config.get("context", {})
    git_config = config.get("git", {})
    outputs_config = config.get("outputs", {})
    llm_config = config.get("llm", {})

    project_name = str(project_config.get("name", "Unknown Project"))
    project_path = Path(
        str(
            project_config.get(
                "path",
                project_config.get("repository_path", "."),
            )
        )
    )

    max_files = int(context_config.get("max_files", 30))
    max_file_size_kb = int(context_config.get("max_file_size_kb", 20))
    include = context_config.get("include")
    exclude_dirs = context_config.get("exclude_dirs")
    max_commits = int(git_config.get("max_commits", 10))
    llm_provider = str(llm_config.get("provider", "")).strip() or None

    output_dir = Path(str(outputs_config.get("directory", "outputs")))
    run_logs_dir = Path(str(outputs_config.get("run_logs_directory", "run_logs")))
    summary_path = output_dir / "context_summary.md"
    status_report_path = output_dir / "project_status_report.md"
    next_tasks_path = output_dir / "next_tasks.md"
    readme_suggestions_path = output_dir / "readme_suggestions.md"
    risk_report_path = output_dir / "risk_report.md"
    commit_suggestions_path = output_dir / "commit_suggestions.md"
    llm_review_path = output_dir / "llm_review.md"
    tool_call_log_path = output_dir / "tool_call_log.md"

    context_result = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="reading_context",
        tool_name="context_reader",
        input_summary={
            "project_path": str(project_path),
            "max_files": max_files,
            "max_file_size_kb": max_file_size_kb,
        },
        action=lambda: read_project_context(
            project_path=project_path,
            include=include if isinstance(include, list) else None,
            exclude_dirs=exclude_dirs if isinstance(exclude_dirs, list) else None,
            max_files=max_files,
            max_file_size_kb=max_file_size_kb,
        ),
        output_summary=lambda result: {
            "target_exists": result.target_exists,
            "files_read": len(result.files),
            "truncated_files": len(result.truncated_files),
        },
        message=lambda result: "已读取目标项目上下文。"
        if result.files
        else "目标项目上下文为空或路径不可用。",
        empty_result=lambda result: not result.target_exists or not result.files,
    )
    git_result = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="reading_git_log",
        tool_name="git_reader",
        input_summary={"project_path": str(project_path), "max_commits": max_commits},
        action=lambda: read_recent_git_commits(project_path, max_commits=max_commits),
        output_summary=lambda result: {
            "is_git_repo": result.is_git_repo,
            "commits_read": len(result.commits),
        },
        message=lambda result: "已读取最近 git commit。"
        if result.commits
        else "未读取到 git commit 记录。",
        empty_result=lambda result: not result.commits,
    )
    written_summary_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_context_summary",
        tool_name="context_summary_writer",
        input_summary={"output_path": str(summary_path)},
        action=lambda: write_context_summary(
            project_name=project_name,
            context_result=context_result,
            git_result=git_result,
            output_path=summary_path,
        ),
        output_summary=lambda result: {"context_summary": str(result)},
        message=lambda result: "已生成上下文摘要。",
    )
    status_report = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="analyzing_project_status",
        tool_name="project_status_analyzer",
        input_summary={"files_read": len(context_result.files)},
        action=lambda: ProjectStatusAnalyzer().analyze(
            project_name=project_name,
            context_result=context_result,
            git_result=git_result,
        ),
        output_summary=lambda result: {
            "delivery_readiness_score": result.delivery_readiness_score,
            "gaps": len(result.delivery_gaps),
            "risks": len(result.risks),
        },
        message=lambda result: "已完成规则化项目状态分析。",
    )
    written_status_report_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_project_status_report",
        tool_name="project_status_report_writer",
        input_summary={"output_path": str(status_report_path)},
        action=lambda: write_project_status_report(
            report=status_report,
            output_path=status_report_path,
        ),
        output_summary=lambda result: {"project_status_report": str(result)},
        message=lambda result: "已生成项目状态报告。",
    )
    written_next_tasks_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_next_tasks",
        tool_name="next_tasks_writer",
        input_summary={"output_path": str(next_tasks_path)},
        action=lambda: write_next_tasks(
            report=status_report,
            output_path=next_tasks_path,
        ),
        output_summary=lambda result: {"next_tasks": str(result)},
        message=lambda result: "已生成下一步任务。",
    )

    readme_advice = ReadmeAdvisor().advise(context_result)
    risk_advice = RiskAdvisor().advise(
        status_report=status_report,
        context_result=context_result,
        git_result=git_result,
    )
    commit_advice = CommitAdvisor().advise(
        project_name=project_name,
        status_report=status_report,
        git_result=git_result,
    )
    human_feedback = default_human_feedback()

    written_readme_suggestions_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_readme_suggestions",
        tool_name="readme_advisor",
        input_summary={"output_path": str(readme_suggestions_path)},
        action=lambda: write_readme_suggestions(
            advice=readme_advice,
            output_path=readme_suggestions_path,
        ),
        output_summary=lambda result: {"readme_suggestions": str(result)},
        message=lambda result: "已生成 README 建议。",
    )
    written_risk_report_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_risk_report",
        tool_name="risk_advisor",
        input_summary={"output_path": str(risk_report_path)},
        action=lambda: write_risk_report(
            advice=risk_advice,
            output_path=risk_report_path,
        ),
        output_summary=lambda result: {"risk_report": str(result)},
        message=lambda result: "已生成风险提醒。",
    )
    written_commit_suggestions_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_commit_suggestions",
        tool_name="commit_advisor",
        input_summary={"output_path": str(commit_suggestions_path)},
        action=lambda: write_commit_suggestions(
            advice=commit_advice,
            output_path=commit_suggestions_path,
        ),
        output_summary=lambda result: {"commit_suggestions": str(result)},
        message=lambda result: "已生成 commit 建议草案。",
    )
    # Provide the LLM review step a bounded snapshot of tool calls before final log rewrite.
    write_tool_call_log(
        records=tool_calls,
        output_path=tool_call_log_path,
        human_confirmation_status=human_feedback.status,
    )
    llm_review_result = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="llm_reviewing",
        tool_name="llm_review_advisor",
        input_summary={
            "provider": llm_provider or "env/default",
            "reports": "context_summary, project_status_report, next_tasks, risk_report, commit_suggestions, tool_call_log",
        },
        action=lambda: LLMReviewAdvisor().review(
            report_paths={
                "context_summary": written_summary_path,
                "project_status_report": written_status_report_path,
                "next_tasks": written_next_tasks_path,
                "risk_report": written_risk_report_path,
                "commit_suggestions": written_commit_suggestions_path,
                "tool_call_log": tool_call_log_path,
            },
            output_path=llm_review_path,
            provider=llm_provider,
        ),
        output_summary=lambda result: {
            "llm_provider": result.provider,
            "llm_review": str(result.output_path),
        },
        message=lambda result: result.message,
        status_selector=lambda result: result.status,
        error_type_selector=lambda result: result.status.value
        if result.status
        in {ToolCallStatus.PERMISSION_DENIED, ToolCallStatus.INTERNAL_ERROR}
        else None,
    )
    workflow_steps.append(
        build_workflow_step(
            step_name="pending_human_confirmation",
            status=ToolCallStatus.SUCCESS,
            started_at=utc_now(),
            finished_at=utc_now(),
            message="已记录人工确认状态为 pending。",
        )
    )
    written_tool_call_log_path = _execute_logged_step(
        tool_calls=tool_calls,
        workflow_steps=workflow_steps,
        step_name="generating_tool_call_log",
        tool_name="tool_call_log_writer",
        input_summary={"output_path": str(tool_call_log_path)},
        action=lambda: write_tool_call_log(
            records=tool_calls,
            output_path=tool_call_log_path,
            human_confirmation_status=human_feedback.status,
        ),
        output_summary=lambda result: {"tool_call_log": str(result)},
        message=lambda result: "已生成 Tool Call Log。",
    )

    workflow_finished_at = utc_now()
    run_log_path = write_run_log(
        run_id=run_id,
        status="success" if context_result.target_exists else "empty_result",
        message=f"已为 {project_name} 生成项目分析结果，并记录 workflow steps 和 tool calls。",
        output_dir=run_logs_dir,
        started_at=workflow_started_at.isoformat(),
        finished_at=workflow_finished_at.isoformat(),
        extra_fields={
            "target_project": project_name,
            "workflow_status": "completed",
            "files_read": len(context_result.files),
            "git_commits_read": len(git_result.commits),
            "delivery_readiness_score": status_report.delivery_readiness_score,
            "human_confirmation_status": human_feedback.status.value,
            "llm_provider": llm_review_result.provider,
            "llm_review_output": str(llm_review_result.output_path),
            "steps": [workflow_step_to_dict(step) for step in workflow_steps],
            "tool_calls": [tool_call_to_dict(call) for call in tool_calls],
            "outputs": {
                "context_summary": str(written_summary_path),
                "project_status_report": str(written_status_report_path),
                "next_tasks": str(written_next_tasks_path),
                "readme_suggestions": str(written_readme_suggestions_path),
                "risk_report": str(written_risk_report_path),
                "commit_suggestions": str(written_commit_suggestions_path),
                "llm_review": str(llm_review_result.output_path),
                "tool_call_log": str(written_tool_call_log_path),
            },
        },
    )

    print("ProjectPilot 分析完成。")
    print(f"目标项目：{project_name}")
    print(f"读取文件数：{len(context_result.files)}")
    print(f"最近提交数：{len(git_result.commits)}")
    print(f"交付就绪评分：{status_report.delivery_readiness_score}/100")
    print("评分类型：规则化证据完整度检查")
    print("解释：该分数表示目标项目在当前展示范围内证据较完整，不代表生产级可用。")
    print(f"上下文摘要：{written_summary_path}")
    print(f"项目状态报告：{written_status_report_path}")
    print(f"下一步任务：{written_next_tasks_path}")
    print(f"README 建议：{written_readme_suggestions_path}")
    print(f"风险提醒：{written_risk_report_path}")
    print(f"Commit 建议：{written_commit_suggestions_path}")
    print(f"LLM Review：{llm_review_result.output_path}")
    print(f"LLM Provider：{llm_review_result.provider}")
    print(f"Tool Call Log：{written_tool_call_log_path}")
    print("Workflow 状态：completed")
    print(f"人工确认状态：{human_feedback.status.value}")
    print(f"运行日志：{run_log_path}")
    return 0


def _execute_logged_step(
    tool_calls: list[ToolCallRecord],
    workflow_steps: list[Any],
    step_name: str,
    tool_name: str,
    input_summary: dict[str, Any],
    action: Callable[[], T],
    output_summary: Callable[[T], dict[str, Any]],
    message: Callable[[T], str],
    empty_result: Callable[[T], bool] | None = None,
    status_selector: Callable[[T], ToolCallStatus] | None = None,
    error_type_selector: Callable[[T], str | None] | None = None,
) -> T:
    started_at = utc_now()
    try:
        result = action()
    except Exception:
        finished_at = utc_now()
        tool_calls.append(
            build_tool_call_record(
                tool_name=tool_name,
                status=ToolCallStatus.INTERNAL_ERROR,
                started_at=started_at,
                finished_at=finished_at,
                input_summary=input_summary,
                output_summary={},
                error_type="internal_error",
                message="步骤执行失败。",
            )
        )
        workflow_steps.append(
            build_workflow_step(
                step_name=step_name,
                status=ToolCallStatus.INTERNAL_ERROR,
                started_at=started_at,
                finished_at=finished_at,
                message="步骤执行失败。",
            )
        )
        raise

    finished_at = utc_now()
    if status_selector is not None:
        status = status_selector(result)
    else:
        status = (
            ToolCallStatus.EMPTY_RESULT
            if empty_result is not None and empty_result(result)
            else ToolCallStatus.SUCCESS
        )
    error_type = error_type_selector(result) if error_type_selector is not None else None
    step_message = message(result)
    tool_calls.append(
        build_tool_call_record(
            tool_name=tool_name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            input_summary=input_summary,
            output_summary=output_summary(result),
            error_type=error_type,
            message=step_message,
        )
    )
    workflow_steps.append(
        build_workflow_step(
            step_name=step_name,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            message=step_message,
        )
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args.config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line interface for ProjectPilot Agent."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from projectpilot.agent.agent_run import run_agent_workflow
from projectpilot.analyzers.commit_advisor import CommitAdvisor
from projectpilot.analyzers.consistency_checker import (
    ConsistencyCheckReport,
    ConsistencyChecker,
)
from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    read_raghub_eval_metrics,
)
from projectpilot.analyzers.llm_interview_asset_writer import (
    LLMInterviewAssetResult,
    LLMInterviewAssetWriter,
)
from projectpilot.analyzers.llm_raghub_risk_reviewer import (
    LLMRAGHubRiskReviewResult,
    LLMRAGHubRiskReviewer,
)
from projectpilot.analyzers.llm_raghub_task_planner import (
    LLMRAGHubTaskPlanResult,
    LLMRAGHubTaskPlanner,
)
from projectpilot.analyzers.llm_resume_asset_writer import (
    LLMResumeAssetResult,
    LLMResumeAssetWriter,
)
from projectpilot.analyzers.llm_review_advisor import LLMReviewAdvisor
from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.analyzers.raghub_delivery_analyzer import (
    RAGHubDeliveryReport,
    analyze_raghub_delivery,
)
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
from projectpilot.workflow.raghub_case_report_writer import write_raghub_case_reports
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
    agent_run_parser = subparsers.add_parser(
        "agent-run",
        help="Run the planner-driven read-only agent workflow.",
    )
    agent_run_parser.add_argument(
        "--config",
        required=True,
        help="Path to a projectpilot.yaml config file.",
    )
    agent_run_parser.add_argument(
        "--goal",
        required=True,
        help="Goal for the read-only agent planner.",
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
    raghub_eval100_config = config.get("raghub_eval100")

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
    llm_risk_review_path = output_dir / "llm_risk_review.md"
    llm_task_plan_path = output_dir / "llm_task_plan.md"
    interview_assets_path = output_dir / "interview_case_cards.md"
    resume_assets_path = output_dir / "resume_assets.md"
    consistency_check_path = output_dir / "consistency_check.md"
    consistency_check_json_path = output_dir / "consistency_check.json"
    raghub_metrics: RAGHubEvalMetrics | None = None
    raghub_delivery_report: RAGHubDeliveryReport | None = None
    raghub_output_paths: dict[str, Path] = {}
    raghub_llm_advisors_enabled = (
        isinstance(raghub_eval100_config, dict)
        and bool(raghub_eval100_config.get("enable_llm_advisors", False))
    )
    raghub_asset_writers_enabled = (
        isinstance(raghub_eval100_config, dict)
        and bool(raghub_eval100_config.get("enable_asset_writers", False))
    )
    raghub_consistency_check_enabled = (
        isinstance(raghub_eval100_config, dict)
        and bool(raghub_eval100_config.get("enable_consistency_check", False))
    )
    raghub_llm_risk_review: LLMRAGHubRiskReviewResult | None = None
    raghub_llm_task_plan: LLMRAGHubTaskPlanResult | None = None
    raghub_interview_assets: LLMInterviewAssetResult | None = None
    raghub_resume_assets: LLMResumeAssetResult | None = None
    raghub_consistency_report: ConsistencyCheckReport | None = None

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
    if isinstance(raghub_eval100_config, dict):
        raghub_metrics = _execute_logged_step(
            tool_calls=tool_calls,
            workflow_steps=workflow_steps,
            step_name="reading_raghub_eval_metrics",
            tool_name="raghub_eval_metrics_reader",
            input_summary={
                "project_path": str(project_path),
                "results_path": str(
                    raghub_eval100_config.get("results_path", "eval/results_100.json")
                ),
                "retrieval_comparison_path": str(
                    raghub_eval100_config.get(
                        "retrieval_comparison_path",
                        "eval/retrieval_comparison_100.json",
                    )
                ),
                "llm_ab_review_path": str(
                    raghub_eval100_config.get(
                        "llm_ab_review_path",
                        "eval/llm_ab_review_100_results.json",
                    )
                ),
            },
            action=lambda: read_raghub_eval_metrics(
                project_path=project_path,
                config=raghub_eval100_config,
            ),
            output_summary=lambda result: {
                "total_queries": result.total_queries,
                "out_of_corpus_rejected": result.out_of_corpus_rejected,
                "answerability_accuracy": result.answerability_accuracy,
                "retrieval_modes": ",".join(result.retrieval_modes),
            },
            message=lambda result: "已确定性读取 RAGHub Eval-100 指标。",
        )
        raghub_delivery_report = _execute_logged_step(
            tool_calls=tool_calls,
            workflow_steps=workflow_steps,
            step_name="analyzing_raghub_delivery",
            tool_name="raghub_delivery_analyzer",
            input_summary={
                "total_queries": raghub_metrics.total_queries,
                "out_of_corpus_rejected": raghub_metrics.out_of_corpus_rejected,
            },
            action=lambda: analyze_raghub_delivery(raghub_metrics),
            output_summary=lambda result: {
                issue.issue_name: issue.status for issue in result.issues
            },
            message=lambda result: "已完成 RAGHub 交付风险识别。",
        )
        raghub_output_paths = _execute_logged_step(
            tool_calls=tool_calls,
            workflow_steps=workflow_steps,
            step_name="generating_raghub_case_reports",
            tool_name="raghub_case_report_writer",
            input_summary={"output_dir": str(output_dir)},
            action=lambda: write_raghub_case_reports(
                metrics=raghub_metrics,
                report=raghub_delivery_report,
                output_dir=output_dir,
            ),
            output_summary=lambda result: {
                key: str(value) for key, value in result.items()
            },
            message=lambda result: "已生成 RAGHub Eval-100 case 输出。",
        )
        if raghub_llm_advisors_enabled:
            raghub_llm_risk_review = _execute_logged_step(
                tool_calls=tool_calls,
                workflow_steps=workflow_steps,
                step_name="llm_reviewing_raghub_risks",
                tool_name="llm_raghub_risk_reviewer",
                input_summary={
                    "provider": llm_provider or "env/default",
                    "total_queries": raghub_metrics.total_queries,
                    "risk_issues": len(raghub_delivery_report.issues),
                },
                action=lambda: LLMRAGHubRiskReviewer().review(
                    metrics=raghub_metrics,
                    delivery_report=raghub_delivery_report,
                    output_path=llm_risk_review_path,
                    provider=llm_provider,
                ),
                output_summary=lambda result: {
                    "llm_provider": result.provider,
                    "llm_risk_review": str(result.output_path),
                },
                message=lambda result: result.message,
                status_selector=lambda result: result.status,
                error_type_selector=lambda result: result.status.value
                if result.status
                in {ToolCallStatus.PERMISSION_DENIED, ToolCallStatus.INTERNAL_ERROR}
                else None,
            )
            raghub_output_paths["llm_risk_review"] = raghub_llm_risk_review.output_path
            raghub_llm_task_plan = _execute_logged_step(
                tool_calls=tool_calls,
                workflow_steps=workflow_steps,
                step_name="llm_planning_raghub_tasks",
                tool_name="llm_raghub_task_planner",
                input_summary={
                    "provider": llm_provider or "env/default",
                    "risk_review": str(raghub_llm_risk_review.output_path),
                },
                action=lambda: LLMRAGHubTaskPlanner().plan(
                    metrics=raghub_metrics,
                    delivery_report=raghub_delivery_report,
                    risk_review_summary=raghub_llm_risk_review.review_text,
                    output_path=llm_task_plan_path,
                    provider=llm_provider,
                ),
                output_summary=lambda result: {
                    "llm_provider": result.provider,
                    "llm_task_plan": str(result.output_path),
                },
                message=lambda result: result.message,
                status_selector=lambda result: result.status,
                error_type_selector=lambda result: result.status.value
                if result.status
                in {ToolCallStatus.PERMISSION_DENIED, ToolCallStatus.INTERNAL_ERROR}
                else None,
            )
            raghub_output_paths["llm_task_plan"] = raghub_llm_task_plan.output_path
        if raghub_asset_writers_enabled:
            raghub_interview_assets = _execute_logged_step(
                tool_calls=tool_calls,
                workflow_steps=workflow_steps,
                step_name="llm_writing_raghub_interview_assets",
                tool_name="llm_interview_asset_writer",
                input_summary={
                    "provider": llm_provider or "env/default",
                    "total_queries": raghub_metrics.total_queries,
                    "llm_advisors_enabled": raghub_llm_advisors_enabled,
                },
                action=lambda: LLMInterviewAssetWriter().write(
                    metrics=raghub_metrics,
                    delivery_report=raghub_delivery_report,
                    risk_review_summary=raghub_llm_risk_review.review_text
                    if raghub_llm_risk_review is not None
                    else "",
                    task_plan_summary=raghub_llm_task_plan.plan_text
                    if raghub_llm_task_plan is not None
                    else "",
                    output_path=interview_assets_path,
                    provider=llm_provider,
                ),
                output_summary=lambda result: {
                    "llm_provider": result.provider,
                    "interview_assets": str(result.output_path),
                },
                message=lambda result: result.message,
                status_selector=lambda result: result.status,
                error_type_selector=lambda result: result.status.value
                if result.status
                in {ToolCallStatus.PERMISSION_DENIED, ToolCallStatus.INTERNAL_ERROR}
                else None,
            )
            raghub_output_paths["interview_case_cards"] = (
                raghub_interview_assets.output_path
            )
            raghub_resume_assets = _execute_logged_step(
                tool_calls=tool_calls,
                workflow_steps=workflow_steps,
                step_name="llm_writing_raghub_resume_assets",
                tool_name="llm_resume_asset_writer",
                input_summary={
                    "provider": llm_provider or "env/default",
                    "interview_assets": str(raghub_interview_assets.output_path),
                },
                action=lambda: LLMResumeAssetWriter().write(
                    metrics=raghub_metrics,
                    delivery_report=raghub_delivery_report,
                    interview_assets_summary=raghub_interview_assets.asset_text,
                    task_plan_summary=raghub_llm_task_plan.plan_text
                    if raghub_llm_task_plan is not None
                    else "",
                    output_path=resume_assets_path,
                    provider=llm_provider,
                ),
                output_summary=lambda result: {
                    "llm_provider": result.provider,
                    "resume_assets": str(result.output_path),
                },
                message=lambda result: result.message,
                status_selector=lambda result: result.status,
                error_type_selector=lambda result: result.status.value
                if result.status
                in {ToolCallStatus.PERMISSION_DENIED, ToolCallStatus.INTERNAL_ERROR}
                else None,
            )
            raghub_output_paths["resume_assets"] = raghub_resume_assets.output_path
        if raghub_consistency_check_enabled:
            consistency_input_paths = {
                key: value
                for key, value in {
                    "raghub_risk_review": raghub_output_paths.get(
                        "raghub_risk_review"
                    ),
                    "issue_to_task_map": raghub_output_paths.get("issue_to_task_map"),
                    "llm_risk_review": raghub_output_paths.get("llm_risk_review"),
                    "llm_task_plan": raghub_output_paths.get("llm_task_plan"),
                    "interview_case_cards": raghub_output_paths.get(
                        "interview_case_cards"
                    ),
                    "resume_assets": raghub_output_paths.get("resume_assets"),
                }.items()
                if value is not None
            }
            raghub_consistency_report = _execute_logged_step(
                tool_calls=tool_calls,
                workflow_steps=workflow_steps,
                step_name="checking_raghub_asset_consistency",
                tool_name="consistency_checker",
                input_summary={
                    "files": ",".join(consistency_input_paths),
                    "output_path": str(consistency_check_path),
                },
                action=lambda: ConsistencyChecker().check(
                    files=consistency_input_paths,
                    output_markdown_path=consistency_check_path,
                    output_json_path=consistency_check_json_path,
                ),
                output_summary=lambda result: {
                    "consistency_status": result.status,
                    "findings": len(result.findings),
                    "consistency_check": str(consistency_check_path),
                    "consistency_check_json": str(consistency_check_json_path),
                },
                message=lambda result: "已完成 RAGHub asset consistency check。",
            )
            raghub_output_paths["consistency_check"] = consistency_check_path
            raghub_output_paths["consistency_check_json"] = (
                consistency_check_json_path
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
    run_log_outputs = {
        "context_summary": str(written_summary_path),
        "project_status_report": str(written_status_report_path),
        "next_tasks": str(written_next_tasks_path),
        "readme_suggestions": str(written_readme_suggestions_path),
        "risk_report": str(written_risk_report_path),
        "commit_suggestions": str(written_commit_suggestions_path),
        "llm_review": str(llm_review_result.output_path),
        "tool_call_log": str(written_tool_call_log_path),
    }
    if raghub_output_paths:
        run_log_outputs.update(
            {key: str(value) for key, value in raghub_output_paths.items()}
        )
    run_log_extra_fields: dict[str, Any] = {
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
        "outputs": run_log_outputs,
    }
    if raghub_metrics is not None and raghub_delivery_report is not None:
        run_log_extra_fields["raghub_eval100"] = {
            "total_queries": raghub_metrics.total_queries,
            "out_of_corpus_rejected": raghub_metrics.out_of_corpus_rejected,
            "answerability_accuracy": raghub_metrics.answerability_accuracy,
            "exact_source_hit_rate": raghub_metrics.exact_source_hit_rate,
            "hybrid_average_score": raghub_metrics.hybrid_average_score,
            "vector_average_score": raghub_metrics.vector_average_score,
            "hybrid_default_recommended": (
                raghub_delivery_report.hybrid_default_recommended
            ),
            "llm_advisors_enabled": raghub_llm_advisors_enabled,
            "asset_writers_enabled": raghub_asset_writers_enabled,
            "consistency_check_enabled": raghub_consistency_check_enabled,
            "llm_risk_review": _llm_generation_state(raghub_llm_risk_review),
            "llm_task_plan": _llm_generation_state(raghub_llm_task_plan),
            "interview_assets": _llm_generation_state(raghub_interview_assets),
            "resume_assets": _llm_generation_state(raghub_resume_assets),
            "consistency_status": raghub_consistency_report.status
            if raghub_consistency_report is not None
            else "disabled",
            "human_confirmation_status": human_feedback.status.value,
        }
    run_log_path = write_run_log(
        run_id=run_id,
        status="success" if context_result.target_exists else "empty_result",
        message=f"已为 {project_name} 生成项目分析结果，并记录 workflow steps 和 tool calls。",
        output_dir=run_logs_dir,
        started_at=workflow_started_at.isoformat(),
        finished_at=workflow_finished_at.isoformat(),
        extra_fields=run_log_extra_fields,
    )

    print("ProjectPilot 分析完成。")
    print(f"目标项目：{project_name}")
    print(f"读取文件数：{len(context_result.files)}")
    print(f"最近提交数：{len(git_result.commits)}")
    print(f"交付证据完整度评分（Evidence Coverage Score）：{status_report.delivery_readiness_score}/100")
    print("评分类型：规则化证据类型覆盖检查")
    print("解释：该分数只表示 README、docs、tests、eval、bad case、git commit 等证据类型覆盖程度，不代表项目质量满分、生产级可用或企业级审计结果。")
    print(f"上下文摘要：{written_summary_path}")
    print(f"项目状态报告：{written_status_report_path}")
    print(f"下一步任务：{written_next_tasks_path}")
    print(f"README 建议：{written_readme_suggestions_path}")
    print(f"风险提醒：{written_risk_report_path}")
    print(f"Commit 建议：{written_commit_suggestions_path}")
    print(f"LLM Review：{llm_review_result.output_path}")
    print(f"LLM Provider：{llm_review_result.provider}")
    if raghub_output_paths:
        print(f"RAGHub Eval-100 指标摘要：{raghub_output_paths['eval_metrics_summary']}")
        print(f"RAGHub Eval-100 风险登记：{raghub_output_paths['risk_register']}")
        if "llm_risk_review" in raghub_output_paths:
            print(f"RAGHub LLM 风险复盘：{raghub_output_paths['llm_risk_review']}")
        if "llm_task_plan" in raghub_output_paths:
            print(f"RAGHub LLM 任务计划：{raghub_output_paths['llm_task_plan']}")
        if "interview_case_cards" in raghub_output_paths:
            print(
                "RAGHub interview assets："
                f"{raghub_output_paths['interview_case_cards']}"
            )
        if "resume_assets" in raghub_output_paths:
            print(f"RAGHub resume assets：{raghub_output_paths['resume_assets']}")
        if "consistency_check" in raghub_output_paths:
            print(
                "RAGHub consistency check："
                f"{raghub_output_paths['consistency_check']}"
            )
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


def _llm_generation_state(
    result: (
        LLMRAGHubRiskReviewResult
        | LLMRAGHubTaskPlanResult
        | LLMInterviewAssetResult
        | LLMResumeAssetResult
        | None
    ),
) -> str:
    if result is None:
        return "disabled"
    if result.status == ToolCallStatus.SUCCESS:
        return "generated"
    return result.status.value


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args.config)
    if args.command == "agent-run":
        return run_agent_run(args.config, args.goal)

    parser.print_help()
    return 0


def run_agent_run(config_path: str, goal: str) -> int:
    result = run_agent_workflow(config_path=config_path, goal=goal)
    print("ProjectPilot agent-run 完成。")
    print(f"目标：{result.goal}")
    print(f"Planner Provider：{result.planner_provider}")
    print(f"Planned Steps：{len(result.plan.planned_steps)}")
    print(f"Executed Steps：{result.executed_steps_count}")
    print(f"Skipped Steps：{result.skipped_steps_count}")
    print(f"Agent Plan：{result.output_paths['agent_plan']}")
    print(f"Agent Run Summary：{result.output_paths['agent_run_summary']}")
    print(f"Skipped Steps Log：{result.output_paths['skipped_steps']}")
    print(f"Tool Call Log：{result.tool_call_log_path}")
    print(f"Run Log：{result.run_log_path}")
    print(f"人工确认状态：{result.human_confirmation_status.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

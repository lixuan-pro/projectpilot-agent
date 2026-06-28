"""Planner-driven read-only agent workflow runner."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from projectpilot.agent.planner import AgentPlan, MockAgentPlanner, PlannedStep
from projectpilot.agent.tool_router import (
    AgentToolRouter,
    RoutedToolResult,
    build_read_only_tool_catalog,
)
from projectpilot.analyzers.consistency_checker import (
    ConsistencyCheckReport,
    ConsistencyChecker,
)
from projectpilot.analyzers.eval_metrics_reader import (
    RAGHubEvalMetrics,
    read_raghub_eval_metrics,
)
from projectpilot.analyzers.raghub_delivery_analyzer import (
    RAGHubDeliveryReport,
    analyze_raghub_delivery,
)
from projectpilot.config import load_config
from projectpilot.feedback.human_feedback import HumanFeedbackStatus
from projectpilot.logging.run_log import write_run_log
from projectpilot.logging.tool_call_log import (
    build_tool_call_record,
    tool_call_to_dict,
    utc_now,
    write_tool_call_log,
)
from projectpilot.schemas.tool_schema import ToolCallRecord, ToolCallStatus
from projectpilot.tools.context_reader import ContextReadResult, read_project_context
from projectpilot.tools.git_reader import GitLogResult, read_recent_git_commits
from projectpilot.workflow.workflow_run import build_workflow_step, workflow_step_to_dict


@dataclass
class AgentExecutionContext:
    config: dict[str, Any]
    project_name: str
    project_path: Path
    output_dir: Path
    run_logs_dir: Path
    plan: AgentPlan
    agent_plan_path: Path
    agent_run_summary_path: Path
    skipped_steps_path: Path
    tool_call_log_path: Path
    next_tasks_path: Path
    consistency_check_path: Path
    consistency_check_json_path: Path
    context_result: ContextReadResult | None = None
    git_result: GitLogResult | None = None
    metrics: RAGHubEvalMetrics | None = None
    delivery_report: RAGHubDeliveryReport | None = None
    consistency_report: ConsistencyCheckReport | None = None
    routed_results: list[RoutedToolResult] = field(default_factory=list)


@dataclass(frozen=True)
class AgentRunResult:
    goal: str
    planner_provider: str
    plan: AgentPlan
    routed_results: list[RoutedToolResult]
    output_paths: dict[str, Path]
    tool_call_log_path: Path
    run_log_path: Path
    human_confirmation_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING

    @property
    def executed_steps_count(self) -> int:
        return sum(1 for result in self.routed_results if result.status == "executed")

    @property
    def skipped_steps_count(self) -> int:
        return sum(1 for result in self.routed_results if result.status == "skipped")


def run_agent_workflow(
    config_path: str | Path,
    goal: str,
    planner: Any | None = None,
    output_dir: str | Path = "outputs/raghub_agent",
) -> AgentRunResult:
    config = load_config(config_path)
    run_id = f"agent-run-{uuid4()}"
    workflow_started_at = utc_now()
    tool_calls: list[ToolCallRecord] = []
    workflow_steps = []

    project_config = config.get("project", {})
    outputs_config = config.get("outputs", {})
    project_name = str(project_config.get("name", "Unknown Project"))
    project_path = Path(
        str(
            project_config.get(
                "path",
                project_config.get("repository_path", "."),
            )
        )
    )
    agent_output_dir = Path(output_dir)
    run_logs_dir = Path(str(outputs_config.get("run_logs_directory", "run_logs")))
    agent_output_dir.mkdir(parents=True, exist_ok=True)

    selected_planner = planner or MockAgentPlanner()
    tool_catalog = build_read_only_tool_catalog()
    plan = selected_planner.plan(goal, tool_catalog)

    context = AgentExecutionContext(
        config=config,
        project_name=project_name,
        project_path=project_path,
        output_dir=agent_output_dir,
        run_logs_dir=run_logs_dir,
        plan=plan,
        agent_plan_path=agent_output_dir / "agent_plan.md",
        agent_run_summary_path=agent_output_dir / "agent_run_summary.md",
        skipped_steps_path=agent_output_dir / "skipped_steps.md",
        tool_call_log_path=agent_output_dir / "tool_call_log.md",
        next_tasks_path=agent_output_dir / "agent_next_tasks.md",
        consistency_check_path=agent_output_dir / "consistency_check.md",
        consistency_check_json_path=agent_output_dir / "consistency_check.json",
    )
    context.agent_plan_path.write_text(build_agent_plan_markdown(plan), encoding="utf-8")

    router = AgentToolRouter(handlers=_build_handlers(context))
    for step in plan.planned_steps:
        started_at = utc_now()
        routed_result = router.execute(step)
        finished_at = utc_now()
        context.routed_results.append(routed_result)

        tool_status = _tool_status_for_routed_result(routed_result)
        tool_calls.append(
            build_tool_call_record(
                tool_name=step.tool_name,
                status=tool_status,
                started_at=started_at,
                finished_at=finished_at,
                input_summary={
                    "step_id": step.step_id,
                    "read_only": step.read_only,
                    "depends_on": ",".join(step.depends_on) if step.depends_on else "-",
                },
                output_summary=routed_result.output_summary,
                error_type=routed_result.reason
                if routed_result.status in {"skipped", "failed"}
                else None,
                message=routed_result.reason,
            )
        )
        workflow_steps.append(
            build_workflow_step(
                step_name=step.step_id,
                status=tool_status,
                started_at=started_at,
                finished_at=finished_at,
                message=routed_result.reason,
            )
        )

    _write_skipped_steps(context.skipped_steps_path, context.routed_results)
    context.agent_run_summary_path.write_text(
        build_agent_run_summary_markdown(
            plan=plan,
            routed_results=context.routed_results,
            human_confirmation_status=HumanFeedbackStatus.PENDING,
        ),
        encoding="utf-8",
    )
    written_tool_call_log = write_tool_call_log(
        records=tool_calls,
        output_path=context.tool_call_log_path,
        human_confirmation_status=HumanFeedbackStatus.PENDING,
    )

    workflow_finished_at = utc_now()
    output_paths = {
        "agent_plan": context.agent_plan_path,
        "agent_run_summary": context.agent_run_summary_path,
        "skipped_steps": context.skipped_steps_path,
        "tool_call_log": written_tool_call_log,
    }
    if context.next_tasks_path.exists():
        output_paths["agent_next_tasks"] = context.next_tasks_path
    if context.consistency_check_path.exists():
        output_paths["consistency_check"] = context.consistency_check_path
    if context.consistency_check_json_path.exists():
        output_paths["consistency_check_json"] = context.consistency_check_json_path

    run_log_path = write_run_log(
        run_id=run_id,
        status="success",
        message=f"Completed planner-driven read-only agent run for {project_name}.",
        output_dir=run_logs_dir,
        filename="raghub_agent_latest_run.json",
        started_at=workflow_started_at.isoformat(),
        finished_at=workflow_finished_at.isoformat(),
        extra_fields={
            "target_project": project_name,
            "workflow_status": "completed",
            "human_confirmation_status": HumanFeedbackStatus.PENDING.value,
            "steps": [workflow_step_to_dict(step) for step in workflow_steps],
            "tool_calls": [tool_call_to_dict(call) for call in tool_calls],
            "outputs": {key: str(path) for key, path in output_paths.items()},
            "agent_run": {
                "goal": goal,
                "planner_provider": plan.planner_provider,
                "planned_steps_count": len(plan.planned_steps),
                "executed_steps_count": sum(
                    1 for result in context.routed_results if result.status == "executed"
                ),
                "skipped_steps_count": sum(
                    1 for result in context.routed_results if result.status == "skipped"
                ),
                "human_confirmation_status": HumanFeedbackStatus.PENDING.value,
            },
        },
    )

    return AgentRunResult(
        goal=goal,
        planner_provider=plan.planner_provider,
        plan=plan,
        routed_results=list(context.routed_results),
        output_paths=output_paths,
        tool_call_log_path=written_tool_call_log,
        run_log_path=run_log_path,
    )


def build_agent_plan_markdown(plan: AgentPlan) -> str:
    lines = [
        "# Agent Plan",
        "",
        f"- goal: {plan.goal}",
        f"- planner_provider: {plan.planner_provider}",
        f"- planned_steps_count: {len(plan.planned_steps)}",
        "",
        "| step_id | tool | read_only | requires_human_confirmation | depends_on | reason |",
        "| ------- | ---- | --------- | --------------------------- | ---------- | ------ |",
    ]
    for step in plan.planned_steps:
        lines.append(
            "| "
            f"{step.step_id} | "
            f"{step.tool_name} | "
            f"{step.read_only} | "
            f"{step.requires_human_confirmation} | "
            f"{', '.join(step.depends_on) if step.depends_on else '-'} | "
            f"{_table_cell(step.reason)} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- The planner only proposes step metadata.",
            "- Tool execution is controlled by the static Tool Router allowlist.",
            "- This workflow does not modify the target project, commit, push, deploy, or run arbitrary shell commands.",
            "- human_confirmation_status = pending",
            "",
        ]
    )
    return "\n".join(lines)


def build_agent_run_summary_markdown(
    plan: AgentPlan,
    routed_results: list[RoutedToolResult],
    human_confirmation_status: HumanFeedbackStatus,
) -> str:
    executed = [result for result in routed_results if result.status == "executed"]
    skipped = [result for result in routed_results if result.status == "skipped"]
    lines = [
        "# Agent Run Summary",
        "",
        "## Overview",
        "",
        f"- goal: {plan.goal}",
        f"- planner_provider: {plan.planner_provider}",
        f"- planned_steps_count: {len(plan.planned_steps)}",
        f"- executed_steps_count: {len(executed)}",
        f"- skipped_steps_count: {len(skipped)}",
        f"- human_confirmation_status: {human_confirmation_status.value}",
        "",
        "## Executed Steps",
        "",
        "| step | tool | status | reason |",
        "| ---- | ---- | ------ | ------ |",
        *_result_table_lines(executed),
        "",
        "## Skipped Steps",
        "",
        "| step | tool | status | reason |",
        "| ---- | ---- | ------ | ------ |",
        *_result_table_lines(skipped),
        "",
        "## Boundary",
        "",
        "- ProjectPilot did not modify the target project.",
        "- ProjectPilot did not run git add, git commit, git push, deploy, or arbitrary shell commands.",
        "- Dangerous or unknown planned tools are recorded as skipped.",
        "- DeepSeek planner is not required for this default mock run.",
        "- This remains a read-only Agent prototype, not an enterprise governance platform.",
        "",
    ]
    return "\n".join(lines)


def _build_handlers(context: AgentExecutionContext) -> dict[str, Any]:
    return {
        "context_reader": lambda step: _handle_context_reader(context, step),
        "git_reader": lambda step: _handle_git_reader(context, step),
        "raghub_eval_metrics_reader": lambda step: _handle_eval_metrics_reader(
            context,
            step,
        ),
        "raghub_delivery_analyzer": lambda step: _handle_delivery_analyzer(
            context,
            step,
        ),
        "next_tasks_writer": lambda step: _handle_next_tasks_writer(context, step),
        "consistency_checker": lambda step: _handle_consistency_checker(context, step),
        "agent_summary_writer": lambda step: _handle_agent_summary_writer(
            context,
            step,
        ),
    }


def _handle_context_reader(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    context_config = context.config.get("context", {})
    include = context_config.get("include")
    exclude_dirs = context_config.get("exclude_dirs")
    max_files = int(context_config.get("max_files", 30))
    max_file_size_kb = int(context_config.get("max_file_size_kb", 20))
    result = read_project_context(
        project_path=context.project_path,
        include=include if isinstance(include, list) else None,
        exclude_dirs=exclude_dirs if isinstance(exclude_dirs, list) else None,
        max_files=max_files,
        max_file_size_kb=max_file_size_kb,
    )
    context.context_result = result
    return {
        "target_exists": result.target_exists,
        "files_read": len(result.files),
        "truncated_files": len(result.truncated_files),
    }


def _handle_git_reader(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    git_config = context.config.get("git", {})
    max_commits = int(git_config.get("max_commits", 10))
    result = read_recent_git_commits(context.project_path, max_commits=max_commits)
    context.git_result = result
    return {
        "is_git_repo": result.is_git_repo,
        "commits_read": len(result.commits),
    }


def _handle_eval_metrics_reader(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    raghub_config = context.config.get("raghub_eval100")
    if not isinstance(raghub_config, dict):
        raise ValueError("raghub_eval100 config is required for Eval-100 metrics.")
    metrics = read_raghub_eval_metrics(
        project_path=context.project_path,
        config=raghub_config,
    )
    context.metrics = metrics
    return {
        "total_queries": metrics.total_queries,
        "out_of_corpus_rejected": metrics.out_of_corpus_rejected,
        "answerability_accuracy": metrics.answerability_accuracy,
        "retrieval_modes": ",".join(metrics.retrieval_modes),
    }


def _handle_delivery_analyzer(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    if context.metrics is None:
        raise ValueError("read_eval_metrics must complete before delivery analysis.")
    report = analyze_raghub_delivery(context.metrics)
    context.delivery_report = report
    return {
        "issues": len(report.issues),
        "hybrid_default_recommended": report.hybrid_default_recommended,
        "human_confirmation_status": report.human_confirmation_status,
    }


def _handle_next_tasks_writer(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    if context.delivery_report is None:
        raise ValueError("analyze_delivery_risks must complete before next tasks.")
    context.next_tasks_path.write_text(
        _build_agent_next_tasks(context.delivery_report),
        encoding="utf-8",
    )
    return {
        "next_tasks": str(context.next_tasks_path),
        "tasks": len(context.delivery_report.issues),
        "human_confirmation_status": HumanFeedbackStatus.PENDING.value,
    }


def _handle_consistency_checker(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    files: dict[str, Path] = {"agent_plan": context.agent_plan_path}
    if context.next_tasks_path.exists():
        files["agent_next_tasks"] = context.next_tasks_path
    report = ConsistencyChecker().check(
        files=files,
        output_markdown_path=context.consistency_check_path,
        output_json_path=context.consistency_check_json_path,
    )
    context.consistency_report = report
    return {
        "consistency_status": report.status,
        "findings": len(report.findings),
        "consistency_check": str(context.consistency_check_path),
        "consistency_check_json": str(context.consistency_check_json_path),
    }


def _handle_agent_summary_writer(
    context: AgentExecutionContext,
    step: PlannedStep,
) -> dict[str, Any]:
    del step
    return {
        "agent_run_summary": str(context.agent_run_summary_path),
        "human_confirmation_status": HumanFeedbackStatus.PENDING.value,
    }


def _build_agent_next_tasks(report: RAGHubDeliveryReport) -> str:
    lines = [
        "# Agent Next Tasks",
        "",
        "- source: RAGHub Eval-100 delivery analysis",
        "- human_confirmation_status: pending",
        "",
        "| issue | status | recommended_action |",
        "| ----- | ------ | ------------------ |",
    ]
    for issue in report.issues:
        lines.append(
            "| "
            f"{issue.issue_name} | "
            f"{issue.status} | "
            f"{_table_cell(issue.recommended_action)} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- These tasks are suggestions for human review.",
            "- ProjectPilot does not modify RAGHub or create commits.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_skipped_steps(path: Path, routed_results: list[RoutedToolResult]) -> None:
    skipped = [result for result in routed_results if result.status == "skipped"]
    lines = [
        "# Skipped Steps",
        "",
        f"- skipped_steps_count: {len(skipped)}",
        "",
        "| step | tool | reason |",
        "| ---- | ---- | ------ |",
    ]
    if skipped:
        lines.extend(
            [
                f"| {result.step_id} | {result.tool_name} | {result.reason} |"
                for result in skipped
            ]
        )
    else:
        lines.append("| - | - | no_skipped_steps |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Dangerous, non-read-only, or unknown tools are skipped by the static Tool Router.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _tool_status_for_routed_result(result: RoutedToolResult) -> ToolCallStatus:
    if result.status == "executed":
        return ToolCallStatus.SUCCESS
    if result.status == "skipped":
        return ToolCallStatus.SKIPPED
    return ToolCallStatus.INTERNAL_ERROR


def _result_table_lines(results: list[RoutedToolResult]) -> list[str]:
    if not results:
        return ["| - | - | - | - |"]
    return [
        "| "
        f"{result.step_id} | "
        f"{result.tool_name} | "
        f"{result.status} | "
        f"{result.reason} |"
        for result in results
    ]


def _table_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")


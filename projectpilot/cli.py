"""Command line interface for ProjectPilot Agent."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4

from projectpilot.analyzers.project_status_analyzer import ProjectStatusAnalyzer
from projectpilot.config import load_config
from projectpilot.logging.run_log import write_run_log
from projectpilot.tools.context_reader import read_project_context
from projectpilot.tools.git_reader import read_recent_git_commits
from projectpilot.workflow.context_summary import write_context_summary
from projectpilot.workflow.report_writer import (
    write_next_tasks,
    write_project_status_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectpilot",
        description="ProjectPilot Agent CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Read bounded project context and write a context summary.",
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

    project_config = config.get("project", {})
    context_config = config.get("context", {})
    git_config = config.get("git", {})
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

    max_files = int(context_config.get("max_files", 30))
    max_file_size_kb = int(context_config.get("max_file_size_kb", 20))
    include = context_config.get("include")
    exclude_dirs = context_config.get("exclude_dirs")
    max_commits = int(git_config.get("max_commits", 10))

    output_dir = Path(str(outputs_config.get("directory", "outputs")))
    run_logs_dir = Path(str(outputs_config.get("run_logs_directory", "run_logs")))
    summary_path = output_dir / "context_summary.md"
    status_report_path = output_dir / "project_status_report.md"
    next_tasks_path = output_dir / "next_tasks.md"

    context_result = read_project_context(
        project_path=project_path,
        include=include if isinstance(include, list) else None,
        exclude_dirs=exclude_dirs if isinstance(exclude_dirs, list) else None,
        max_files=max_files,
        max_file_size_kb=max_file_size_kb,
    )
    git_result = read_recent_git_commits(project_path, max_commits=max_commits)
    written_summary_path = write_context_summary(
        project_name=project_name,
        context_result=context_result,
        git_result=git_result,
        output_path=summary_path,
    )
    analyzer = ProjectStatusAnalyzer()
    status_report = analyzer.analyze(
        project_name=project_name,
        context_result=context_result,
        git_result=git_result,
    )
    written_status_report_path = write_project_status_report(
        report=status_report,
        output_path=status_report_path,
    )
    written_next_tasks_path = write_next_tasks(
        report=status_report,
        output_path=next_tasks_path,
    )
    run_log_path = write_run_log(
        run_id=f"analysis-{uuid4()}",
        status="success" if context_result.target_exists else "empty_result",
        message=f"Generated project status report and next tasks for {project_name}.",
        output_dir=run_logs_dir,
        extra_fields={
            "target_project": project_name,
            "files_read": len(context_result.files),
            "git_commits_read": len(git_result.commits),
            "delivery_readiness_score": status_report.delivery_readiness_score,
            "outputs": {
                "context_summary": str(written_summary_path),
                "project_status_report": str(written_status_report_path),
                "next_tasks": str(written_next_tasks_path),
            },
        },
    )

    print("ProjectPilot analysis completed.")
    print(f"Target project: {project_name}")
    print(f"Files read: {len(context_result.files)}")
    print(f"Git commits read: {len(git_result.commits)}")
    print(f"交付就绪评分：{status_report.delivery_readiness_score}/100")
    print("评分类型：规则化证据完整度检查")
    print("解释：该分数表示目标项目在当前展示范围内证据较完整，不代表生产级可用。")
    print(f"Context summary: {written_summary_path}")
    print(f"Status report: {written_status_report_path}")
    print(f"Next tasks: {written_next_tasks_path}")
    print(f"Run log: {run_log_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args.config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

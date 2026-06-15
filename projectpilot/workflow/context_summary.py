"""Generate a Day 2 project context summary."""

from __future__ import annotations

from pathlib import Path

from projectpilot.tools.context_reader import ContextReadResult
from projectpilot.tools.git_reader import GitLogResult


def write_context_summary(
    project_name: str,
    context_result: ContextReadResult,
    git_result: GitLogResult,
    output_path: str | Path = "outputs/context_summary.md",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_context_summary(project_name, context_result, git_result),
        encoding="utf-8",
    )
    return path


def build_context_summary(
    project_name: str,
    context_result: ContextReadResult,
    git_result: GitLogResult,
) -> str:
    grouped = {
        "readme": [item for item in context_result.files if item.category == "readme"],
        "docs": [item for item in context_result.files if item.category == "docs"],
        "tests": [item for item in context_result.files if item.category == "tests"],
        "eval": [item for item in context_result.files if item.category == "eval"],
    }

    lines = [
        "# Project Context Summary",
        "",
        "## 1. Target Project",
        "",
        f"- Name: {project_name}",
        f"- Path: {context_result.project_path}",
        f"- Exists: {context_result.target_exists}",
        "",
        "## 2. Files Read",
        "",
    ]
    lines.extend(_file_lines(context_result))
    lines.extend(
        [
            "",
            "## 3. Key README Signals",
            "",
            *_signal_lines(grouped["readme"]),
            "",
            "## 4. Docs Signals",
            "",
            *_signal_lines(grouped["docs"]),
            "",
            "## 5. Tests Signals",
            "",
            *_signal_lines(grouped["tests"]),
            "",
            "## 6. Eval Signals",
            "",
            *_signal_lines(grouped["eval"]),
            "",
            "## 7. Recent Git Commits",
            "",
            *_commit_lines(git_result),
            "",
            "## 8. Reader Limits",
            "",
            f"- Max files: {context_result.max_files}",
            f"- Max file size: {context_result.max_file_size_bytes // 1024} KB",
            f"- Skipped large files: {len(context_result.skipped_large_files)}",
            f"- Skipped binary files: {len(context_result.skipped_binary_files)}",
            f"- Skipped disallowed files: {len(context_result.skipped_disallowed_files)}",
            f"- Truncated files: {len(context_result.truncated_files)}",
            "",
            "## 9. Current Boundary",
            "",
            "Day 2 only reads bounded project context and recent git commits. It does not run semantic analysis, call an LLM, modify target files, create commits, or call external project APIs.",
            "",
        ]
    )
    return "\n".join(lines)


def _file_lines(context_result: ContextReadResult) -> list[str]:
    if not context_result.files:
        if context_result.target_exists:
            return ["No matching context files were read."]
        return ["Target project path does not exist or is not a directory."]

    return [
        f"- `{item.path}` ({item.category}, {item.size_bytes} bytes)"
        for item in context_result.files
    ]


def _signal_lines(files: list[object]) -> list[str]:
    if not files:
        return ["No files read in this category."]

    lines: list[str] = []
    for item in files:
        path = getattr(item, "path")
        content = getattr(item, "content")
        first_lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("```")
        ][:3]
        preview = " / ".join(first_lines) if first_lines else "No textual preview."
        lines.append(f"- `{path}`: {preview[:300]}")
    return lines


def _commit_lines(git_result: GitLogResult) -> list[str]:
    if not git_result.is_git_repo:
        detail = f" Reason: {git_result.error}" if git_result.error else ""
        return [f"No git commits read.{detail}"]
    if not git_result.commits:
        return ["Git repository detected, but no commits were returned."]
    return [f"- `{commit.hash}` {commit.subject}" for commit in git_result.commits]

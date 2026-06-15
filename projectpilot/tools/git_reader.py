"""Read recent git commit metadata without modifying the repository."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitCommit:
    hash: str
    subject: str


@dataclass(frozen=True)
class GitLogResult:
    project_path: Path
    commits: list[GitCommit]
    is_git_repo: bool
    error: str | None = None


def read_recent_git_commits(
    project_path: str | Path,
    max_commits: int = 10,
) -> GitLogResult:
    root = Path(project_path)
    if not root.exists() or not root.is_dir():
        return GitLogResult(root, [], is_git_repo=False, error="project_path_not_found")
    if not (root / ".git").exists():
        return GitLogResult(root, [], is_git_repo=False, error="git_metadata_not_found")

    command = [
        "git",
        "-C",
        str(root),
        "log",
        f"--max-count={max_commits}",
        "--pretty=format:%h%x09%s",
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "git_log_failed"
        return GitLogResult(root, [], is_git_repo=False, error=error)

    commits: list[GitCommit] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        short_hash, _, subject = line.partition("\t")
        commits.append(GitCommit(hash=short_hash, subject=subject))

    return GitLogResult(root, commits, is_git_repo=True)

"""Read bounded project context from a target repository."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_INCLUDE_PATTERNS = [
    "README.md",
    "docs/**/*.md",
    "tests/**/*.py",
    "eval/**/*.jsonl",
    "eval/**/*.json",
    "eval/**/*.md",
]
DEFAULT_EXCLUDE_DIRS = [
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "data/raw",
    "data/processed",
    "models",
    "cache",
]
ALLOWED_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yaml", ".yml"}


@dataclass(frozen=True)
class ContextFile:
    path: str
    category: str
    size_bytes: int
    content: str


@dataclass(frozen=True)
class ContextReadResult:
    project_path: Path
    files: list[ContextFile]
    skipped_large_files: list[str] = field(default_factory=list)
    skipped_binary_files: list[str] = field(default_factory=list)
    skipped_disallowed_files: list[str] = field(default_factory=list)
    truncated_files: list[str] = field(default_factory=list)
    target_exists: bool = True
    max_files: int = 30
    max_file_size_bytes: int = 20 * 1024


def read_project_context(
    project_path: str | Path,
    include: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    max_files: int = 30,
    max_file_size_kb: int = 20,
) -> ContextReadResult:
    root = Path(project_path)
    max_file_size_bytes = max_file_size_kb * 1024

    if not root.exists() or not root.is_dir():
        return ContextReadResult(
            project_path=root,
            files=[],
            target_exists=False,
            max_files=max_files,
            max_file_size_bytes=max_file_size_bytes,
        )

    include_patterns = include or DEFAULT_INCLUDE_PATTERNS
    exclude_patterns = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    candidates = _collect_candidates(root, include_patterns, exclude_patterns)

    files: list[ContextFile] = []
    skipped_large: list[str] = []
    skipped_binary: list[str] = []
    skipped_disallowed: list[str] = []
    truncated: list[str] = []

    for path in candidates:
        relative_path = _relative_posix(root, path)
        if len(files) >= max_files:
            break
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            skipped_disallowed.append(relative_path)
            continue

        size_bytes = path.stat().st_size
        if size_bytes > max_file_size_bytes:
            if _is_root_readme(relative_path):
                raw = path.read_bytes()[:max_file_size_bytes]
                truncated.append(relative_path)
            else:
                skipped_large.append(relative_path)
                continue
        else:
            raw = path.read_bytes()

        if _looks_binary(raw):
            skipped_binary.append(relative_path)
            continue

        files.append(
            ContextFile(
                path=relative_path,
                category=_categorize_path(relative_path),
                size_bytes=size_bytes,
                content=_decode_text(raw),
            )
        )

    return ContextReadResult(
        project_path=root,
        files=files,
        skipped_large_files=skipped_large,
        skipped_binary_files=skipped_binary,
        skipped_disallowed_files=skipped_disallowed,
        truncated_files=truncated,
        max_files=max_files,
        max_file_size_bytes=max_file_size_bytes,
    )


def _collect_candidates(
    root: Path, include_patterns: list[str], exclude_dirs: list[str]
) -> list[Path]:
    seen: set[Path] = set()
    candidates: list[Path] = []

    for pattern in include_patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if _is_excluded(root, path, exclude_dirs):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)

    return sorted(candidates, key=lambda item: _candidate_sort_key(root, item))


def _is_excluded(root: Path, path: Path, exclude_dirs: list[str]) -> bool:
    relative_parts = path.relative_to(root).parts[:-1]
    relative_dir = "/".join(relative_parts)
    normalized_patterns = [item.replace("\\", "/").strip("/") for item in exclude_dirs]

    for pattern in normalized_patterns:
        if not pattern:
            continue
        if pattern in relative_parts:
            return True
        if relative_dir == pattern or relative_dir.startswith(f"{pattern}/"):
            return True
    return False


def _relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _candidate_sort_key(root: Path, path: Path) -> tuple[int, str]:
    relative_path = _relative_posix(root, path).lower()
    if _is_root_readme(relative_path):
        return (0, relative_path)
    if relative_path.startswith("docs/"):
        return (1, relative_path)
    if relative_path.startswith("tests/"):
        return (2, relative_path)
    if relative_path.startswith("eval/"):
        return (3, relative_path)
    return (4, relative_path)


def _looks_binary(raw: bytes) -> bool:
    return b"\x00" in raw


def _is_root_readme(relative_path: str) -> bool:
    return relative_path.replace("\\", "/").lower() == "readme.md"


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "cp936"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _categorize_path(relative_path: str) -> str:
    lower_path = relative_path.lower()
    if fnmatch.fnmatch(lower_path, "readme.md"):
        return "readme"
    if lower_path.startswith("docs/"):
        return "docs"
    if lower_path.startswith("tests/"):
        return "tests"
    if lower_path.startswith("eval/"):
        return "eval"
    return "other"

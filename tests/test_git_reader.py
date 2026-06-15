from __future__ import annotations

from projectpilot.tools.git_reader import read_recent_git_commits


def test_git_reader_does_not_crash_in_non_git_directory(tmp_path) -> None:
    result = read_recent_git_commits(tmp_path)

    assert result.is_git_repo is False
    assert result.commits == []
    assert result.error is not None

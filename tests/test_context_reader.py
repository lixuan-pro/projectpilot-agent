from __future__ import annotations

from projectpilot.tools.context_reader import read_project_context


def test_context_reader_reads_expected_project_context(tmp_path) -> None:
    project = tmp_path / "fake_project"
    (project / "docs").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "eval").mkdir()

    (project / "README.md").write_text("# Fake Project\n", encoding="utf-8")
    (project / "docs" / "guide.md").write_text("## Guide\n", encoding="utf-8")
    (project / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    (project / "eval" / "cases.jsonl").write_text('{"input": "x"}\n', encoding="utf-8")
    (project / "eval" / "summary.json").write_text('{"score": 1}\n', encoding="utf-8")
    (project / "eval" / "notes.md").write_text("# Eval Notes\n", encoding="utf-8")

    result = read_project_context(project)

    assert result.target_exists is True
    assert {item.path for item in result.files} == {
        "README.md",
        "docs/guide.md",
        "tests/test_app.py",
        "eval/cases.jsonl",
        "eval/summary.json",
        "eval/notes.md",
    }
    assert result.files[0].path == "README.md"


def test_context_reader_reads_root_readme_before_other_files(tmp_path) -> None:
    project = tmp_path / "fake_project"
    (project / "docs").mkdir(parents=True)
    (project / "README.md").write_text("# Root README\n", encoding="utf-8")
    (project / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    result = read_project_context(project, max_files=1)

    assert [item.path for item in result.files] == ["README.md"]


def test_context_reader_truncates_large_root_readme(tmp_path) -> None:
    project = tmp_path / "fake_project"
    project.mkdir()
    (project / "README.md").write_text("# Root README\n" + ("x" * 2048), encoding="utf-8")

    result = read_project_context(project, max_file_size_kb=1)

    assert [item.path for item in result.files] == ["README.md"]
    assert result.truncated_files == ["README.md"]
    assert len(result.files[0].content.encode("utf-8")) <= 1024


def test_context_reader_skips_large_files(tmp_path) -> None:
    project = tmp_path / "fake_project"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "large.md").write_text("x" * 2048, encoding="utf-8")

    result = read_project_context(project, max_file_size_kb=1)

    assert result.files == []
    assert result.skipped_large_files == ["docs/large.md"]


def test_context_reader_skips_excluded_dirs(tmp_path) -> None:
    project = tmp_path / "fake_project"
    (project / "cache").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "cache" / "skip.md").write_text("# Skip\n", encoding="utf-8")
    (project / "docs" / "keep.md").write_text("# Keep\n", encoding="utf-8")

    result = read_project_context(project, include=["**/*.md"])

    assert {item.path for item in result.files} == {"docs/keep.md"}

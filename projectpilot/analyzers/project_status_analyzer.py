"""Rule-based project status analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field

from projectpilot.tools.context_reader import ContextFile, ContextReadResult
from projectpilot.tools.git_reader import GitLogResult


@dataclass(frozen=True)
class ProjectStatusReport:
    project_name: str
    project_path: str
    project_identity: str
    implemented_capabilities: list[str]
    evidence_files: list[str]
    delivery_strengths: list[str]
    delivery_gaps: list[str]
    risks: list[str]
    next_tasks: list[str]
    interview_preparation: list[str]
    delivery_readiness_score: int
    score_breakdown: dict[str, int] = field(default_factory=dict)


class ProjectStatusAnalyzer:
    """Generate a deterministic status report from bounded read-only evidence."""

    def analyze(
        self,
        project_name: str,
        context_result: ContextReadResult,
        git_result: GitLogResult,
    ) -> ProjectStatusReport:
        files = context_result.files
        evidence = _Evidence(files=files, git_result=git_result)
        breakdown = _score(evidence)

        return ProjectStatusReport(
            project_name=project_name,
            project_path=str(context_result.project_path),
            project_identity=_project_identity(project_name, evidence),
            implemented_capabilities=_implemented_capabilities(evidence),
            evidence_files=[item.path for item in files],
            delivery_strengths=_delivery_strengths(evidence),
            delivery_gaps=_delivery_gaps(evidence),
            risks=_risks(evidence, context_result, git_result),
            next_tasks=_next_tasks(evidence),
            interview_preparation=_interview_preparation(evidence),
            delivery_readiness_score=sum(breakdown.values()),
            score_breakdown=breakdown,
        )


@dataclass(frozen=True)
class _Evidence:
    files: list[ContextFile]
    git_result: GitLogResult

    @property
    def has_readme(self) -> bool:
        return any(item.category == "readme" for item in self.files)

    @property
    def has_docs(self) -> bool:
        return any(item.category == "docs" for item in self.files)

    @property
    def has_tests(self) -> bool:
        return any(item.category == "tests" for item in self.files)

    @property
    def has_eval(self) -> bool:
        return any(item.category == "eval" for item in self.files)

    @property
    def has_bad_cases(self) -> bool:
        return any("bad_cases" in item.path.lower() for item in self.files)

    @property
    def has_problems_and_solutions(self) -> bool:
        return any("problems_and_solutions" in item.path.lower() for item in self.files)

    @property
    def has_recent_commits(self) -> bool:
        return bool(self.git_result.commits)

    @property
    def has_boundaries_or_roadmap(self) -> bool:
        needles = ("boundary", "boundaries", "roadmap", "scope", "current boundary")
        return any(
            any(needle in item.content.lower() for needle in needles)
            for item in self.files
        )


def _score(evidence: _Evidence) -> dict[str, int]:
    return {
        "README present": 15 if evidence.has_readme else 0,
        "docs present": 15 if evidence.has_docs else 0,
        "tests present": 15 if evidence.has_tests else 0,
        "eval present": 15 if evidence.has_eval else 0,
        "bad_cases present": 10 if evidence.has_bad_cases else 0,
        "problems_and_solutions present": 10
        if evidence.has_problems_and_solutions
        else 0,
        "recent commits present": 10 if evidence.has_recent_commits else 0,
        "clear boundaries / roadmap signals": 10
        if evidence.has_boundaries_or_roadmap
        else 0,
    }


def _project_identity(project_name: str, evidence: _Evidence) -> str:
    if evidence.has_readme:
        return f"{project_name} has a root README and bounded project context available for rule-based review."
    return f"{project_name} is missing root README evidence in the current bounded read."


def _implemented_capabilities(evidence: _Evidence) -> list[str]:
    capabilities: list[str] = []
    content = "\n".join(item.content.lower() for item in evidence.files)
    keyword_map = {
        "README-based project framing": evidence.has_readme,
        "Documentation coverage": evidence.has_docs,
        "Automated test coverage signals": evidence.has_tests,
        "Evaluation artifacts": evidence.has_eval,
        "Bad case tracking": evidence.has_bad_cases,
        "Problem and solution notes": evidence.has_problems_and_solutions,
        "Recent git activity": evidence.has_recent_commits,
        "Retrieve API evidence": "/retrieve" in content or "retrieve" in content,
        "Chat API evidence": "/chat" in content or "chat" in content,
        "Citation or source evidence": "citation" in content or "source" in content,
        "No-answer behavior evidence": "no-answer" in content or "no answer" in content,
    }
    for label, present in keyword_map.items():
        if present:
            capabilities.append(label)
    return capabilities or ["No implemented capability evidence found in the bounded read."]


def _delivery_strengths(evidence: _Evidence) -> list[str]:
    strengths: list[str] = []
    if evidence.has_readme:
        strengths.append("Root README gives the project a visible entry point.")
    if evidence.has_docs:
        strengths.append("Documentation files provide implementation and delivery context.")
    if evidence.has_tests:
        strengths.append("Test files give credibility to the current implementation claims.")
    if evidence.has_eval:
        strengths.append("Eval artifacts create a basis for retrieval or answer quality review.")
    if evidence.has_bad_cases:
        strengths.append("Bad case tracking shows known limitations are being recorded.")
    if evidence.has_problems_and_solutions:
        strengths.append("Problem and solution notes support interview and project retrospective use.")
    if evidence.has_recent_commits:
        strengths.append("Recent git commits show active iteration history.")
    return strengths or ["No clear delivery strengths were detected by the current rules."]


def _delivery_gaps(evidence: _Evidence) -> list[str]:
    gaps: list[str] = []
    if not evidence.has_readme:
        gaps.append("Add or expose a root README for project framing.")
    if not evidence.has_docs:
        gaps.append("Add docs that explain architecture, scope, or workflow decisions.")
    if not evidence.has_tests:
        gaps.append("Add tests that cover the core project behavior.")
    if not evidence.has_eval:
        gaps.append("Add eval artifacts to make quality checks repeatable.")
    if not evidence.has_bad_cases:
        gaps.append("Track bad cases so limitations are explicit.")
    if not evidence.has_problems_and_solutions:
        gaps.append("Record problems and solutions for delivery review and interviews.")
    if not evidence.has_recent_commits:
        gaps.append("Provide git history or commit evidence for recent work.")
    if not evidence.has_boundaries_or_roadmap:
        gaps.append("Clarify current boundaries or roadmap signals in README/docs.")
    return gaps or ["No P0 evidence gap detected by the current rules."]


def _risks(
    evidence: _Evidence,
    context_result: ContextReadResult,
    git_result: GitLogResult,
) -> list[str]:
    risks: list[str] = []
    if context_result.truncated_files:
        risks.append(
            "Some files were truncated by the reader limit; details may be incomplete."
        )
    if context_result.skipped_large_files:
        risks.append("Some large non-README files were skipped by the reader limit.")
    if not git_result.is_git_repo:
        risks.append("Git commit evidence was unavailable for the target path.")
    if not evidence.has_eval:
        risks.append("Without eval evidence, quality claims are harder to verify.")
    if not evidence.has_tests:
        risks.append("Without tests, implementation claims have weaker engineering support.")
    return risks or ["No immediate rule-based risk detected from the bounded read."]


def _next_tasks(evidence: _Evidence) -> list[str]:
    tasks: list[str] = []
    if not evidence.has_readme:
        tasks.append("P0: Add a root README that states scope, run commands, and boundaries.")
    if not evidence.has_tests:
        tasks.append("P0: Add tests for the core project workflow.")
    if not evidence.has_eval:
        tasks.append("P0: Add minimal eval cases and result tracking.")
    if not evidence.has_bad_cases:
        tasks.append("P1: Add bad case notes for known failure modes.")
    if not evidence.has_problems_and_solutions:
        tasks.append("P1: Add problems-and-solutions notes for project review.")
    if not evidence.has_boundaries_or_roadmap:
        tasks.append("P1: Clarify current boundaries and roadmap in README or docs.")
    if not tasks:
        tasks.append("P1: Keep improving eval quality and presentation materials.")
    tasks.append("P2: Revisit roadmap only after the current delivery story is coherent.")
    return tasks


def _interview_preparation(evidence: _Evidence) -> list[str]:
    items = [
        "Explain the project goal, current scope, and what is deliberately out of scope.",
        "Prepare a concise walkthrough of README, docs, tests, eval, and recent commits.",
    ]
    if evidence.has_bad_cases:
        items.append("Prepare one bad case and explain how it shaped the next iteration.")
    if evidence.has_problems_and_solutions:
        items.append("Turn problems-and-solutions notes into STAR-style interview examples.")
    return items

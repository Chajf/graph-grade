from __future__ import annotations

from collections.abc import Iterable

from app.graphs.state import SectionGraphState
from app.models import (
    CheckResult,
    EvidenceIndex,
    GradeStatus,
    RequirementGrade,
    RequirementSpec,
    SectionEvidence,
)
from app.services.grading_checks import run_result_checks


def grade_result_requirements(state: SectionGraphState) -> dict[str, list[RequirementGrade]]:
    part_spec = state["part_spec"]
    section = state["section"]
    evidence_index = state["evidence_index"]
    grades = [
        _grade_result_requirement(section, requirement, evidence_index)
        for requirement in part_spec.result_requirements
    ]
    return {"result_grades": grades}


def _grade_result_requirement(
    section: SectionEvidence,
    requirement: RequirementSpec,
    evidence_index: EvidenceIndex,
) -> RequirementGrade:
    checks = run_result_checks(section, requirement, evidence_index)
    failed_checks = [check for check in checks if not check.passed]
    critical_failures = [
        check for check in failed_checks if check.severity == "critical"
    ]
    points_awarded = 0 if failed_checks else requirement.points

    if not checks:
        status: GradeStatus = "minimal"
        comment = "No deterministic result checks are configured."
    elif critical_failures:
        status = "failed"
        comment = _check_summary(checks)
    elif failed_checks:
        status = "partial"
        comment = _check_summary(checks)
    else:
        status = "full"
        comment = _check_summary(checks)

    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="results",
        points_awarded=points_awarded,
        points_possible=requirement.points,
        status=status,
        evidence_cells=_unique_cells(
            cell_index for check in checks for cell_index in check.evidence_cells
        ),
        comment=comment,
        confidence="high",
    )


def _check_summary(checks: list[CheckResult]) -> str:
    if not checks:
        return "No deterministic result checks are configured."
    return " ".join(check.comment for check in checks if check.comment)


def _unique_cells(values: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    unique_values: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values

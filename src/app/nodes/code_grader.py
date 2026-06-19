from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.models import GradeStatus, RequirementGrade, RequirementSpec, SectionEvidence
from app.services.code_features import match_code_markers

if TYPE_CHECKING:
    from app.graphs.state import SectionGraphState


def grade_code_requirements(state: SectionGraphState) -> dict[str, list[RequirementGrade]]:
    part_spec = state["part_spec"]
    section = state["section"]
    grades = [
        _grade_code_requirement(section, requirement)
        for requirement in part_spec.code_requirements
    ]
    return {"code_grades": grades, "deterministic_code_grades": grades}


def _grade_code_requirement(
    section: SectionEvidence,
    requirement: RequirementSpec,
) -> RequirementGrade:
    markers = requirement.evidence.cell_markers
    if not markers:
        has_code = bool(section.code_cells)
        return RequirementGrade(
            requirement_id=requirement.id,
            bucket="code",
            points_awarded=requirement.points if has_code else 0,
            points_possible=requirement.points,
            status="minimal" if has_code else "missing",
            evidence_cells=[cell.index for cell in section.code_cells],
            comment=(
                "Code cells are present, but no deterministic markers are configured."
                if has_code
                else "No code cells found for this requirement."
            ),
            confidence="low",
        )

    findings = match_code_markers(section.code_cells, markers)
    matched_findings = [finding for finding in findings if finding.matched]
    matched_count = len(matched_findings)
    points_awarded = requirement.points * matched_count / len(markers)

    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="code",
        points_awarded=points_awarded,
        points_possible=requirement.points,
        status=_marker_status(matched_count, len(markers)),
        evidence_cells=_unique_cells(
            cell_index
            for finding in matched_findings
            for cell_index in finding.evidence_cells
        ),
        comment=_marker_summary(matched_count, len(markers), findings),
        confidence="high",
    )


def _marker_status(matched_count: int, marker_count: int) -> GradeStatus:
    if matched_count == marker_count:
        return "full"
    if matched_count > 0:
        return "partial"
    return "missing"


def _marker_summary(matched_count: int, marker_count: int, findings) -> str:
    missing_markers = [finding.marker for finding in findings if not finding.matched]
    if not missing_markers:
        return f"Matched all {marker_count} required code marker(s)."
    return (
        f"Matched {matched_count} of {marker_count} required code marker(s). "
        f"Missing: {', '.join(missing_markers)}."
    )


def _unique_cells(values: Iterable[int]) -> list[int]:
    seen: set[int] = set()
    unique_values: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values

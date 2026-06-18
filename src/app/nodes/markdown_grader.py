from __future__ import annotations

from app.graphs.state import SectionGraphState
from app.models import RequirementGrade, RequirementSpec, SectionEvidence
from app.services.grading_checks import check_markdown_requirement


def grade_markdown_requirements(state: SectionGraphState) -> dict[str, list[RequirementGrade]]:
    part_spec = state["part_spec"]
    section = state["section"]
    grades = [
        _grade_markdown_requirement(section, requirement)
        for requirement in part_spec.markdown_requirements
    ]
    return {"markdown_grades": grades}


def _grade_markdown_requirement(
    section: SectionEvidence,
    requirement: RequirementSpec,
) -> RequirementGrade:
    check = check_markdown_requirement(section, requirement)
    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="markdown",
        points_awarded=requirement.points if check.passed else 0,
        points_possible=requirement.points,
        status="full" if check.passed else "missing",
        evidence_cells=check.evidence_cells,
        comment=check.comment,
        confidence="medium",
    )

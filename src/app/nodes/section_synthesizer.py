from __future__ import annotations

from app.graphs.state import SectionGraphState
from app.models import SectionGrade


def synthesize_section_grade(state: SectionGraphState) -> dict[str, SectionGrade]:
    part_spec = state["part_spec"]
    requirement_grades = [
        *state.get("code_grades", []),
        *state.get("markdown_grades", []),
        *state.get("result_grades", []),
    ]
    points_awarded = sum(grade.points_awarded for grade in requirement_grades)
    points_possible = sum(grade.points_possible for grade in requirement_grades)

    section_grade = SectionGrade(
        part_id=part_spec.part_id,
        title=part_spec.title,
        points_awarded=points_awarded,
        points_possible=points_possible,
        requirement_grades=requirement_grades,
        summary=f"Preliminary deterministic score: {points_awarded:g} / {points_possible:g}.",
    )
    return {"section_grade": section_grade}

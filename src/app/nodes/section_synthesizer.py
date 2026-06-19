from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import SectionGrade

if TYPE_CHECKING:
    from app.graphs.state import SectionGraphState


def synthesize_section_grade(state: SectionGraphState) -> dict[str, object]:
    part_spec = state["part_spec"]
    requirement_grades = [
        *state.get("code_grades", []),
        *state.get("markdown_grades", []),
        *state.get("result_grades", []),
    ]
    points_awarded = sum(grade.points_awarded for grade in requirement_grades)
    points_possible = sum(grade.points_possible for grade in requirement_grades)
    deterministic_grades = [
        *state.get("deterministic_code_grades", state.get("code_grades", [])),
        *state.get("deterministic_markdown_grades", state.get("markdown_grades", [])),
        *state.get("deterministic_result_grades", state.get("result_grades", [])),
    ]
    deterministic_points_awarded = sum(
        grade.points_awarded for grade in deterministic_grades
    )
    deterministic_points_possible = sum(
        grade.points_possible for grade in deterministic_grades
    )

    section_grade = SectionGrade(
        part_id=part_spec.part_id,
        title=part_spec.title,
        points_awarded=points_awarded,
        points_possible=points_possible,
        requirement_grades=requirement_grades,
        summary=(
            "Preliminary deterministic score: "
            f"{deterministic_points_awarded:g} / {deterministic_points_possible:g}."
        ),
    )
    return {
        "section_grade": section_grade,
        "section_grades": [section_grade],
    }

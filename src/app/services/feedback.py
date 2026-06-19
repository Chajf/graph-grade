from __future__ import annotations

from collections.abc import Sequence

from app.models import FinalGrade, RequirementGrade, SectionGrade


def render_lab_feedback(final_grade: FinalGrade) -> str:
    lines = [
        f"# Feedback for {final_grade.lab_id}",
        "",
        f"Student: {final_grade.student_folder}",
        f"Group: {final_grade.group_id}",
        f"Notebook: {final_grade.notebook_path}",
        f"Score: {_format_points(final_grade.points_awarded)} / {_format_points(final_grade.points_possible)}",
        f"Status: {final_grade.status}",
    ]

    if final_grade.summary:
        lines.extend(["", final_grade.summary])

    if final_grade.flags:
        lines.extend(["", "## Flags"])
        lines.extend(f"- {flag}" for flag in final_grade.flags)

    lines.extend(["", "## Sections"])
    if not final_grade.section_grades:
        lines.append("- No section grades were produced.")
    else:
        for section_grade in final_grade.section_grades:
            lines.extend(_render_section(section_grade))

    return "\n".join(lines).rstrip() + "\n"


def render_student_summary(final_grades: Sequence[FinalGrade]) -> str:
    sorted_grades = sorted(final_grades, key=lambda grade: grade.lab_id)
    if not sorted_grades:
        return "# Student Summary\n\nNo graded labs found.\n"

    first_grade = sorted_grades[0]
    lines = [
        "# Student Summary",
        "",
        f"Student: {first_grade.student_folder}",
        f"Group: {first_grade.group_id}",
        "",
        "| Lab | Score | Status | Flags |",
        "| --- | ---: | --- | --- |",
    ]

    total_awarded = 0.0
    total_possible = 0.0
    for grade in sorted_grades:
        total_awarded += grade.points_awarded
        total_possible += grade.points_possible
        flags = ", ".join(grade.flags) if grade.flags else "-"
        lines.append(
            "| "
            f"{grade.lab_id} | "
            f"{_format_points(grade.points_awarded)} / {_format_points(grade.points_possible)} | "
            f"{grade.status} | "
            f"{flags} |"
        )

    lines.extend(
        [
            "",
            f"Total: {_format_points(total_awarded)} / {_format_points(total_possible)}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_section(section_grade: SectionGrade) -> list[str]:
    lines = [
        "",
        f"### {section_grade.part_id}: {section_grade.title}",
        "",
        f"Score: {_format_points(section_grade.points_awarded)} / {_format_points(section_grade.points_possible)}",
    ]
    if section_grade.summary:
        lines.extend(["", section_grade.summary])

    if not section_grade.requirement_grades:
        lines.extend(["", "- No requirement grades were produced."])
        return lines

    lines.extend(["", "| Requirement | Bucket | Score | Status | Evidence | Comment |"])
    lines.append("| --- | --- | ---: | --- | --- | --- |")
    for requirement_grade in section_grade.requirement_grades:
        lines.append(_render_requirement_row(requirement_grade))

    return lines


def _render_requirement_row(requirement_grade: RequirementGrade) -> str:
    evidence = _format_evidence_cells(requirement_grade.evidence_cells)
    comment = requirement_grade.comment or "-"
    return (
        "| "
        f"{requirement_grade.requirement_id} | "
        f"{requirement_grade.bucket} | "
        f"{_format_points(requirement_grade.points_awarded)} / "
        f"{_format_points(requirement_grade.points_possible)} | "
        f"{requirement_grade.status} | "
        f"{evidence} | "
        f"{comment} |"
    )


def _format_evidence_cells(evidence_cells: list[int]) -> str:
    if not evidence_cells:
        return "-"
    if len(evidence_cells) == 1:
        return f"cell {evidence_cells[0]}"
    return "cells " + ", ".join(str(cell_index) for cell_index in evidence_cells)


def _format_points(value: float) -> str:
    return f"{value:g}"

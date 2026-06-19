from __future__ import annotations

from app.graphs.state import GradingGraphState
from app.models import FinalGrade


def final_synthesizer(state: GradingGraphState) -> dict[str, object]:
    submission = state["submission"]
    section_grades = sorted(state.get("section_grades", []), key=lambda grade: grade.part_id)
    points_awarded = sum(grade.points_awarded for grade in section_grades)
    points_possible = sum(grade.points_possible for grade in section_grades)
    flags = list(state.get("flags", []))

    for section in state.get("sections", []):
        if section.mapping_confidence == "low":
            flags.append(f"section_mapping_low_confidence:{section.part_id}")

    evidence_index = state.get("evidence_index")
    if evidence_index is not None:
        if evidence_index.errors:
            flags.append("error_outputs_present")
        if evidence_index.possible_secrets:
            flags.append("possible_plaintext_secret")

    final_grade = FinalGrade(
        lab_id=state["lab_spec"].lab_id,
        group_id=submission.group_id,
        student_folder=submission.student_folder,
        notebook_path=str(submission.notebook_path) if submission.notebook_path is not None else "",
        points_awarded=points_awarded,
        points_possible=points_possible,
        section_grades=section_grades,
        flags=_deduplicate(flags),
        summary=f"Final score: {points_awarded:g} / {points_possible:g}.",
    )
    return {"final_grade": final_grade, "flags": final_grade.flags}


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduplicated.append(value)
    return deduplicated

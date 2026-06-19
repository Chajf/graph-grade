from __future__ import annotations

import json
from pathlib import Path

from app.graphs.state import GradingGraphState
from app.models import FinalGrade
from app.services.feedback import render_lab_feedback, render_student_summary


def result_persister(state: GradingGraphState) -> dict[str, object]:
    final_grade = state.get("final_grade")
    if final_grade is None:
        raise ValueError("Final grade is required before persistence.")

    lab_grade_path = state["lab_grade_path"]
    lab_feedback_path = state["lab_feedback_path"]
    student_summary_path = state["student_summary_path"]

    lab_grade_path.parent.mkdir(parents=True, exist_ok=True)
    student_summary_path.parent.mkdir(parents=True, exist_ok=True)

    lab_grade_path.write_text(
        json.dumps(final_grade.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    lab_feedback_path.write_text(render_lab_feedback(final_grade), encoding="utf-8")

    summary_grades = _load_student_grades(
        output_root=Path(state["output_root"]),
        group_id=final_grade.group_id,
        student_folder=final_grade.student_folder,
    )
    summary_grades[final_grade.lab_id] = final_grade
    student_summary_path.write_text(
        render_student_summary(list(summary_grades.values())),
        encoding="utf-8",
    )

    return {
        "lab_grade_path": lab_grade_path,
        "lab_feedback_path": lab_feedback_path,
        "student_summary_path": student_summary_path,
    }


def _load_student_grades(
    output_root: Path,
    group_id: str,
    student_folder: str,
) -> dict[str, FinalGrade]:
    grades: dict[str, FinalGrade] = {}
    for grade_path in sorted(output_root.glob(f"*/{group_id}/{student_folder}/grade.json")):
        final_grade = _load_final_grade(grade_path)
        if final_grade is not None:
            grades[final_grade.lab_id] = final_grade
    return grades


def _load_final_grade(grade_path: Path) -> FinalGrade | None:
    try:
        return FinalGrade.model_validate_json(grade_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

from __future__ import annotations

from pathlib import Path

from app.graphs.state import GradingGraphState


def submission_loader(state: GradingGraphState) -> dict[str, object]:
    lab_spec = state["lab_spec"]
    submission = state["submission"]
    output_root = Path(state["output_root"])

    lab_output_dir = output_root / lab_spec.lab_id / submission.group_id / submission.student_folder
    student_summary_path = output_root / submission.group_id / submission.student_folder / "summary.md"
    flags = list(state.get("flags", []))

    if not submission.resolved:
        flags.append(f"submission_{submission.status}")
        if submission.issue is not None:
            flags.append(submission.issue.code)

    for missing_file in submission.missing_required_files:
        flags.append(f"missing_required_file:{missing_file}")

    return {
        "flags": _deduplicate(flags),
        "section_grades": state.get("section_grades", []),
        "lab_output_dir": lab_output_dir,
        "lab_grade_path": lab_output_dir / "grade.json",
        "lab_feedback_path": lab_output_dir / "feedback.md",
        "student_summary_path": student_summary_path,
    }


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduplicated.append(value)
    return deduplicated

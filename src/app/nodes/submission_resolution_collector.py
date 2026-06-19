from __future__ import annotations

from app.graphs.state import LaboratoryGraphState
from app.models import FinalGrade, LabSpec, SharePointStudentSubmission


def submission_resolution_collector(state: LaboratoryGraphState) -> dict[str, object]:
    lab_spec = state.get("lab_spec")
    if lab_spec is None:
        raise ValueError("Lab spec is required before collecting submission resolution results.")

    final_grades: list[FinalGrade] = []
    for submission in state.get("submissions", []):
        if submission.resolved:
            continue
        final_grades.append(_skipped_grade(lab_spec, submission))

    return {"final_grades": final_grades}


def _skipped_grade(lab_spec: LabSpec, submission: SharePointStudentSubmission) -> FinalGrade:
    flags = [f"submission_{submission.status}"]
    if submission.issue is not None:
        flags.append(f"issue:{submission.issue.code}")
    flags.extend(f"missing_required_file:{file_name}" for file_name in submission.missing_required_files)

    return FinalGrade(
        lab_id=lab_spec.lab_id,
        group_id=submission.group_id,
        student_folder=submission.student_folder,
        notebook_path=str(submission.notebook_path) if submission.notebook_path is not None else "",
        points_awarded=0,
        points_possible=lab_spec.total_points,
        flags=_deduplicate(flags),
        status="skipped",
        summary="Submission was skipped because it could not be resolved automatically.",
    )


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduplicated.append(value)
    return deduplicated

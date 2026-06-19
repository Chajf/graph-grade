from __future__ import annotations

from app.graphs.state import LaboratoryGraphState
from app.models import SharePointStudentSubmission
from app.repositories import SharePointRepository


def submission_lister(state: LaboratoryGraphState) -> dict[str, object]:
    lab_spec = state.get("lab_spec")
    if lab_spec is None:
        raise ValueError("Lab spec is required before listing submissions.")

    submissions = SharePointRepository(state["prace_root"]).list_submissions(
        state["group_id"],
        lab_spec,
    )
    return {
        "submissions": submissions,
        "laboratory_errors": _submission_errors(submissions),
    }


def _submission_errors(submissions: list[SharePointStudentSubmission]) -> list[str]:
    errors: list[str] = []
    for submission in submissions:
        if submission.resolved or submission.issue is None:
            continue
        errors.append(
            f"{submission.group_id}/{submission.student_folder}: "
            f"{submission.issue.code}: {submission.issue.message}"
        )
    return errors

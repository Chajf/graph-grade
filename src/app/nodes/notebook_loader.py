from __future__ import annotations

from app.graphs.state import GradingGraphState


def notebook_loader(state: GradingGraphState) -> dict[str, object]:
    submission = state["submission"]

    if not submission.resolved or submission.notebook_path is None:
        raise ValueError(
            f"Submission is not resolved for {submission.group_id}/{submission.student_folder}/{submission.lab_id}."
        )

    if not submission.notebook_path.is_file():
        raise FileNotFoundError(f"Notebook file not found: {submission.notebook_path}")

    return {}

from __future__ import annotations

import csv
from pathlib import Path

from app.models import FinalGrade, SharePointStudentSubmission


GROUP_SUMMARY_HEADERS = [
    "group_id",
    "student_folder",
    "lab_id",
    "status",
    "notebook_found",
    "points_awarded",
    "points_possible",
    "flags",
    "human_review_needed",
    "issue",
    "notebook_path",
]


def write_group_summary(
    output_root: Path | str,
    lab_id: str,
    group_id: str,
    submissions: list[SharePointStudentSubmission],
    final_grades: list[FinalGrade],
    laboratory_errors: list[str] | None = None,
) -> tuple[Path, Path]:
    summary_dir = Path(output_root) / lab_id / group_id
    summary_dir.mkdir(parents=True, exist_ok=True)

    rows = _summary_rows(
        lab_id=lab_id,
        group_id=group_id,
        submissions=submissions,
        final_grades=final_grades,
    )
    csv_path = summary_dir / "group_summary.csv"
    md_path = summary_dir / "group_summary.md"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=GROUP_SUMMARY_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    md_path.write_text(
        _render_group_summary_markdown(
            lab_id=lab_id,
            group_id=group_id,
            rows=rows,
            laboratory_errors=laboratory_errors or [],
        ),
        encoding="utf-8",
    )

    return csv_path, md_path


def _summary_rows(
    lab_id: str,
    group_id: str,
    submissions: list[SharePointStudentSubmission],
    final_grades: list[FinalGrade],
) -> list[dict[str, str]]:
    grades_by_student = {grade.student_folder: grade for grade in final_grades}
    rows: list[dict[str, str]] = []

    for submission in submissions:
        grade = grades_by_student.get(submission.student_folder)
        issue = submission.issue.code if submission.issue is not None else ""
        notebook_path = _notebook_path(submission, grade)
        flags = grade.flags if grade is not None else []
        status = grade.status if grade is not None else "missing"

        rows.append(
            {
                "group_id": group_id,
                "student_folder": submission.student_folder,
                "lab_id": lab_id,
                "status": status,
                "notebook_found": "yes" if submission.notebook_path is not None else "no",
                "points_awarded": _format_points(grade.points_awarded) if grade is not None else "",
                "points_possible": _format_points(grade.points_possible) if grade is not None else "",
                "flags": ", ".join(flags),
                "human_review_needed": _human_review_needed(status, flags, submission),
                "issue": issue,
                "notebook_path": notebook_path,
            }
        )

    return rows


def _render_group_summary_markdown(
    lab_id: str,
    group_id: str,
    rows: list[dict[str, str]],
    laboratory_errors: list[str],
) -> str:
    lines = [
        f"# Group Summary for {lab_id}",
        "",
        f"Group: {group_id}",
        "",
        "| Student | Notebook | Score | Status | Flags | Human Review | Issue |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]

    for row in rows:
        score = _format_score(row)
        flags = row["flags"] or "-"
        issue = row["issue"] or "-"
        lines.append(
            "| "
            f"{row['student_folder']} | "
            f"{row['notebook_found']} | "
            f"{score} | "
            f"{row['status']} | "
            f"{flags} | "
            f"{row['human_review_needed']} | "
            f"{issue} |"
        )

    if laboratory_errors:
        lines.extend(["", "## Laboratory Errors"])
        lines.extend(f"- {error}" for error in laboratory_errors)

    return "\n".join(lines).rstrip() + "\n"


def _notebook_path(
    submission: SharePointStudentSubmission,
    grade: FinalGrade | None,
) -> str:
    if submission.notebook_path is not None:
        return str(submission.notebook_path)
    if grade is not None:
        return grade.notebook_path
    return ""


def _human_review_needed(
    status: str,
    flags: list[str],
    submission: SharePointStudentSubmission,
) -> str:
    if status != "graded" or flags or not submission.resolved:
        return "yes"
    return "no"


def _format_score(row: dict[str, str]) -> str:
    if not row["points_awarded"] or not row["points_possible"]:
        return "-"
    return f"{row['points_awarded']} / {row['points_possible']}"


def _format_points(value: float) -> str:
    return f"{value:g}"

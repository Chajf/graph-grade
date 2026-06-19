import csv
from pathlib import Path

from app.models import FinalGrade, NotebookResolutionIssue, SharePointStudentSubmission
from app.repositories.results import GROUP_SUMMARY_HEADERS, write_group_summary


def test_write_group_summary_outputs_csv_and_markdown(tmp_path: Path) -> None:
    resolved = resolved_submission(tmp_path, "Anna_Nowak")
    unresolved = unresolved_submission(tmp_path, "Jan_Kowalski")
    failed = resolved_submission(tmp_path, "Zofia_Testowa")
    final_grades = [
        FinalGrade(
            lab_id="lab7",
            group_id="lab1",
            student_folder="Anna_Nowak",
            notebook_path=str(resolved.notebook_path),
            points_awarded=10,
            points_possible=12,
            status="graded",
        ),
        FinalGrade(
            lab_id="lab7",
            group_id="lab1",
            student_folder="Jan_Kowalski",
            notebook_path="",
            points_awarded=0,
            points_possible=12,
            status="skipped",
            flags=["submission_unresolved", "issue:missing_notebook"],
        ),
        FinalGrade(
            lab_id="lab7",
            group_id="lab1",
            student_folder="Zofia_Testowa",
            notebook_path=str(failed.notebook_path),
            points_awarded=0,
            points_possible=12,
            status="failed",
            flags=["grading_failed"],
        ),
    ]

    csv_path, md_path = write_group_summary(
        output_root=tmp_path / "grading_results",
        lab_id="lab7",
        group_id="lab1",
        submissions=[resolved, unresolved, failed],
        final_grades=final_grades,
        laboratory_errors=["lab1/Zofia_Testowa: grading_failed: invalid notebook"],
    )

    assert csv_path == tmp_path / "grading_results" / "lab7" / "lab1" / "group_summary.csv"
    assert md_path == tmp_path / "grading_results" / "lab7" / "lab1" / "group_summary.md"

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0].keys() == set(GROUP_SUMMARY_HEADERS)
    assert rows[0] == {
        "group_id": "lab1",
        "student_folder": "Anna_Nowak",
        "lab_id": "lab7",
        "status": "graded",
        "notebook_found": "yes",
        "points_awarded": "10",
        "points_possible": "12",
        "flags": "",
        "human_review_needed": "no",
        "issue": "",
        "notebook_path": str(resolved.notebook_path),
    }
    assert rows[1]["student_folder"] == "Jan_Kowalski"
    assert rows[1]["status"] == "skipped"
    assert rows[1]["notebook_found"] == "no"
    assert rows[1]["flags"] == "submission_unresolved, issue:missing_notebook"
    assert rows[1]["human_review_needed"] == "yes"
    assert rows[1]["issue"] == "missing_notebook"
    assert rows[2]["status"] == "failed"
    assert rows[2]["human_review_needed"] == "yes"

    markdown = md_path.read_text(encoding="utf-8")
    assert "# Group Summary for lab7" in markdown
    assert "| Anna_Nowak | yes | 10 / 12 | graded | - | no | - |" in markdown
    assert "| Jan_Kowalski | no | 0 / 12 | skipped | submission_unresolved, issue:missing_notebook | yes | missing_notebook |" in markdown
    assert "## Laboratory Errors" in markdown
    assert "- lab1/Zofia_Testowa: grading_failed: invalid notebook" in markdown


def resolved_submission(tmp_path: Path, student_folder: str) -> SharePointStudentSubmission:
    notebook_path = tmp_path / "prace" / "lab1" / student_folder / "lab7" / "Wersja 1" / "lab7.ipynb"
    return SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder=student_folder,
        lab_id="lab7",
        lab_folder=notebook_path.parents[1],
        version_folder=notebook_path.parent,
        notebook_path=notebook_path,
        status="resolved",
    )


def unresolved_submission(tmp_path: Path, student_folder: str) -> SharePointStudentSubmission:
    return SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder=student_folder,
        lab_id="lab7",
        status="unresolved",
        issue=NotebookResolutionIssue(
            code="missing_notebook",
            message="No .ipynb files found.",
        ),
    )

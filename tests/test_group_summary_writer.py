import csv
from pathlib import Path

from app.models import FinalGrade, SharePointStudentSubmission
from app.nodes.group_summary_writer import group_summary_writer


def test_group_summary_writer_writes_summary_paths_from_laboratory_state(tmp_path: Path) -> None:
    submission = resolved_submission(tmp_path, "Anna_Nowak")

    result = group_summary_writer(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "submissions": [submission],
            "final_grades": [
                FinalGrade(
                    lab_id="lab7",
                    group_id="lab1",
                    student_folder="Anna_Nowak",
                    notebook_path=str(submission.notebook_path),
                    points_awarded=4,
                    points_possible=4,
                    status="graded",
                )
            ],
            "laboratory_errors": [],
        }
    )

    csv_path = tmp_path / "grading_results" / "lab7" / "lab1" / "group_summary.csv"
    md_path = tmp_path / "grading_results" / "lab7" / "lab1" / "group_summary.md"
    assert result == {
        "summary_csv_path": csv_path,
        "summary_md_path": md_path,
    }
    assert csv_path.is_file()
    assert md_path.is_file()

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["student_folder"] == "Anna_Nowak"
    assert rows[0]["human_review_needed"] == "no"
    assert "| Anna_Nowak | yes | 4 / 4 | graded | - | no | - |" in md_path.read_text(
        encoding="utf-8"
    )


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

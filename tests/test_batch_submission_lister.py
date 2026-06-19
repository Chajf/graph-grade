from pathlib import Path

import pytest

from app.models import LabSpec
from app.nodes.submission_lister import submission_lister


def test_submission_lister_returns_resolved_submissions_without_errors(tmp_path: Path) -> None:
    prace_root = tmp_path / "prace"
    version_folder = create_submission(prace_root, "Jan_Kowalski", ["lab7_Kowalski.ipynb"])

    result = submission_lister(
        {
            "prace_root": prace_root,
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": build_lab_spec(),
        }
    )

    assert result["batch_errors"] == []
    submissions = result["submissions"]
    assert len(submissions) == 1
    assert submissions[0].student_folder == "Jan_Kowalski"
    assert submissions[0].status == "resolved"
    assert submissions[0].notebook_path == version_folder / "lab7_Kowalski.ipynb"


def test_submission_lister_preserves_missing_notebook_and_records_error(tmp_path: Path) -> None:
    prace_root = tmp_path / "prace"
    (prace_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1").mkdir(parents=True)

    result = submission_lister(
        {
            "prace_root": prace_root,
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": build_lab_spec(),
        }
    )

    submissions = result["submissions"]
    assert len(submissions) == 1
    assert submissions[0].student_folder == "Jan_Kowalski"
    assert submissions[0].status == "unresolved"
    assert submissions[0].issue is not None
    assert submissions[0].issue.code == "missing_notebook"
    assert result["batch_errors"] == [
        (
            "lab1/Jan_Kowalski: missing_notebook: "
            f"No .ipynb files found in: {prace_root / 'lab1' / 'Jan_Kowalski' / 'lab7' / 'Wersja 1'}"
        )
    ]


def test_submission_lister_preserves_ambiguous_submission_and_records_error(tmp_path: Path) -> None:
    prace_root = tmp_path / "prace"
    create_submission(prace_root, "Jan_Kowalski", ["lab7_a.ipynb", "lab7_b.ipynb"])

    result = submission_lister(
        {
            "prace_root": prace_root,
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": build_lab_spec(),
        }
    )

    submissions = result["submissions"]
    assert len(submissions) == 1
    assert submissions[0].status == "ambiguous"
    assert submissions[0].issue is not None
    assert submissions[0].issue.code == "ambiguous_notebook"
    assert [candidate.name for candidate in submissions[0].issue.candidates] == [
        "lab7_a.ipynb",
        "lab7_b.ipynb",
    ]
    assert result["batch_errors"] == [
        "lab1/Jan_Kowalski: ambiguous_notebook: Multiple notebook candidates found."
    ]


def test_submission_lister_requires_loaded_lab_spec(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Lab spec is required"):
        submission_lister(
            {
                "prace_root": tmp_path / "prace",
                "specs_root": tmp_path / "grading_specs",
                "output_root": tmp_path / "grading_results",
                "lab_id": "lab7",
                "group_id": "lab1",
            }
        )


def create_submission(
    prace_root: Path,
    student_folder: str,
    filenames: list[str],
    version_folder: str = "Wersja 1",
) -> Path:
    folder = prace_root / "lab1" / student_folder / "lab7" / version_folder
    folder.mkdir(parents=True)
    for filename in filenames:
        (folder / filename).write_text("{}", encoding="utf-8")
    return folder


def build_lab_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        required_files=[],
        parts=[],
    )

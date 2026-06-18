from pathlib import Path

import pytest

from app.models import LabSpec
from app.repositories import SharePointRepository


@pytest.fixture
def lab_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        required_files=[],
        parts=[],
    )


def create_submission(
    submissions_root: Path,
    student_folder: str,
    filenames: list[str],
    version_folder: str = "Wersja 1",
    group_id: str = "lab1",
    lab_id: str = "lab7",
) -> Path:
    folder = submissions_root / group_id / student_folder / lab_id / version_folder
    folder.mkdir(parents=True)
    for filename in filenames:
        (folder / filename).write_text("{}", encoding="utf-8")
    return folder


def test_lists_groups_and_students_sorted(tmp_path: Path, lab_spec: LabSpec) -> None:
    create_submission(tmp_path, "Zofia_Testowa", ["lab7_Zofia.ipynb"])
    create_submission(tmp_path, "Anna_Testowa", ["lab7_Anna.ipynb"])
    create_submission(tmp_path, "Adam_Inny", ["lab7_Adam.ipynb"], group_id="lab2")

    repository = SharePointRepository(tmp_path)

    assert repository.list_groups() == ["lab1", "lab2"]
    assert repository.list_students("lab1") == ["Anna_Testowa", "Zofia_Testowa"]
    assert [
        submission.student_folder
        for submission in repository.list_submissions("lab1", lab_spec)
    ] == ["Anna_Testowa", "Zofia_Testowa"]


def test_resolves_expected_sharepoint_notebook_path(tmp_path: Path, lab_spec: LabSpec) -> None:
    version_folder = create_submission(tmp_path, "Jan_Kowalski", ["lab7_Kowalski.ipynb"])

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is True
    assert submission.submissions_root == tmp_path
    assert submission.version_folder == version_folder
    assert submission.notebook_path == version_folder / "lab7_Kowalski.ipynb"
    assert submission.issue is None


def test_prefers_highest_numbered_version_folder(tmp_path: Path, lab_spec: LabSpec) -> None:
    create_submission(tmp_path, "Jan_Kowalski", ["lab7_old.ipynb"], version_folder="Wersja 1")
    selected_folder = create_submission(
        tmp_path,
        "Jan_Kowalski",
        ["lab7_new.ipynb"],
        version_folder="Wersja 12",
    )
    create_submission(tmp_path, "Jan_Kowalski", ["lab7_mid.ipynb"], version_folder="Wersja 2")

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is True
    assert submission.version_folder == selected_folder
    assert submission.notebook_path == selected_folder / "lab7_new.ipynb"


def test_prefers_spec_pattern_over_lab_prefix(tmp_path: Path, lab_spec: LabSpec) -> None:
    version_folder = create_submission(
        tmp_path,
        "Jan_Kowalski",
        ["lab7_Kowalski.ipynb", "lab7draft.ipynb"],
    )

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is True
    assert submission.notebook_path == version_folder / "lab7_Kowalski.ipynb"


def test_falls_back_to_lab_prefix_pattern(tmp_path: Path, lab_spec: LabSpec) -> None:
    version_folder = create_submission(
        tmp_path,
        "Jan_Kowalski",
        ["notes.ipynb", "lab7draft.ipynb"],
    )

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is True
    assert submission.notebook_path == version_folder / "lab7draft.ipynb"


def test_falls_back_to_only_notebook(tmp_path: Path, lab_spec: LabSpec) -> None:
    version_folder = create_submission(tmp_path, "Jan_Kowalski", ["final_submission.ipynb"])

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is True
    assert submission.notebook_path == version_folder / "final_submission.ipynb"


def test_flags_ambiguous_multiple_notebooks(tmp_path: Path, lab_spec: LabSpec) -> None:
    create_submission(tmp_path, "Jan_Kowalski", ["lab7_a.ipynb", "lab7_b.ipynb"])

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is False
    assert submission.status == "ambiguous"
    assert submission.issue is not None
    assert submission.issue.code == "ambiguous_notebook"
    assert [candidate.name for candidate in submission.issue.candidates] == [
        "lab7_a.ipynb",
        "lab7_b.ipynb",
    ]


def test_flags_missing_lab_folder(tmp_path: Path, lab_spec: LabSpec) -> None:
    (tmp_path / "lab1" / "Jan_Kowalski").mkdir(parents=True)

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is False
    assert submission.status == "unresolved"
    assert submission.issue is not None
    assert submission.issue.code == "missing_lab_folder"


def test_flags_missing_version_folder(tmp_path: Path, lab_spec: LabSpec) -> None:
    (tmp_path / "lab1" / "Jan_Kowalski" / "lab7").mkdir(parents=True)

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.resolved is False
    assert submission.issue is not None
    assert submission.issue.code == "missing_version_folder"


def test_resolves_required_files_near_notebook_then_lab_folder(tmp_path: Path) -> None:
    lab_spec = LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        required_files=["near_version.csv", "near_lab.csv", "missing.csv"],
        parts=[],
    )
    version_folder = create_submission(tmp_path, "Jan_Kowalski", ["lab7_Kowalski.ipynb"])
    lab_folder = version_folder.parent
    (version_folder / "near_version.csv").write_text("value\n1\n", encoding="utf-8")
    (lab_folder / "near_lab.csv").write_text("value\n2\n", encoding="utf-8")

    submission = SharePointRepository(tmp_path).resolve_student_submission(
        "lab1",
        "Jan_Kowalski",
        lab_spec,
    )

    assert submission.required_files == [
        version_folder / "near_version.csv",
        lab_folder / "near_lab.csv",
    ]
    assert submission.missing_required_files == ["missing.csv"]

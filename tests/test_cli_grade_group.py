import json
from pathlib import Path

from app.main import main


def write_minimal_spec(specs_root: Path) -> None:
    lab_dir = specs_root / "labs" / "lab7"
    parts_dir = lab_dir / "parts"
    parts_dir.mkdir(parents=True)
    (lab_dir / "notebook.yaml").write_text(
        """
lab_id: "lab7"
title: "Lab 7"
language: "pl"
expected_submission:
  notebook_pattern: "lab7_*.ipynb"
  required_files:
    - "data.csv"
grading:
  total_points: 100
  parts_dir: "parts"
  part_files:
    - "01_first.yaml"
    - "02_second.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_first.yaml").write_text(
        """
part_id: "01"
title: "First"
source_heading: "## First"
cell_range:
  start_heading: "## First"
  end_heading: "## Second"
requirements:
  code: []
  markdown: []
  results: []
  code_applicability: "required"
  markdown_applicability: "required"
  results_applicability: "required"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_second.yaml").write_text(
        """
part_id: "02"
title: "Second"
source_heading: "## Second"
cell_range:
  start_heading: "## Second"
  end_heading: null
requirements:
  code: []
  markdown: []
  results: []
  code_applicability: "not_applicable"
  markdown_applicability: "required"
  results_applicability: "not_applicable"
""".lstrip(),
        encoding="utf-8",
    )


def create_submission(
    submissions_root: Path,
    student_folder: str,
    filenames: list[str],
    version_folder: str = "Wersja 1",
) -> Path:
    folder = submissions_root / "lab1" / student_folder / "lab7" / version_folder
    folder.mkdir(parents=True)
    for filename in filenames:
        (folder / filename).write_text("{}", encoding="utf-8")
    return folder


def test_grade_group_dry_run_outputs_resolved_submissions(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    write_minimal_spec(specs_root)
    version_folder = create_submission(
        submissions_root,
        "Jan_Kowalski",
        ["lab7_Kowalski.ipynb"],
        version_folder="Wersja 2",
    )
    (version_folder / "data.csv").write_text("value\n1\n", encoding="utf-8")

    exit_code = main(
        [
            "grade-group",
            "--dry-run",
            "--prace-root",
            str(submissions_root),
            "--group",
            "lab1",
            "--lab",
            "lab7",
            "--specs-dir",
            str(specs_root),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["dry_run"] is True
    assert output["group_id"] == "lab1"
    assert output["lab_id"] == "lab7"
    assert output["spec"] == {
        "expected_notebook_pattern": "lab7_*.ipynb",
        "language": "pl",
        "part_ids": ["01", "02"],
        "required_files": ["data.csv"],
        "title": "Lab 7",
        "total_points": 100.0,
    }
    assert len(output["submissions"]) == 1
    submission = output["submissions"][0]
    assert submission["student_folder"] == "Jan_Kowalski"
    assert submission["status"] == "resolved"
    assert submission["issue"] is None
    assert submission["version_folder"] == str(version_folder)
    assert submission["notebook_path"] == str(version_folder / "lab7_Kowalski.ipynb")
    assert submission["required_files"] == [str(version_folder / "data.csv")]
    assert submission["missing_required_files"] == []


def test_grade_group_dry_run_outputs_ambiguous_submission(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    write_minimal_spec(specs_root)
    create_submission(
        submissions_root,
        "Jan_Kowalski",
        ["lab7_a.ipynb", "lab7_b.ipynb"],
    )

    exit_code = main(
        [
            "grade-group",
            "--dry-run",
            "--prace-root",
            str(submissions_root),
            "--group",
            "lab1",
            "--lab",
            "lab7",
            "--specs-dir",
            str(specs_root),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    submission = output["submissions"][0]
    assert submission["status"] == "ambiguous"
    assert submission["notebook_path"] is None
    assert submission["issue"]["code"] == "ambiguous_notebook"
    assert [Path(candidate).name for candidate in submission["issue"]["candidates"]] == [
        "lab7_a.ipynb",
        "lab7_b.ipynb",
    ]

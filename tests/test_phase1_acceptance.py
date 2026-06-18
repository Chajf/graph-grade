import json
from pathlib import Path

from app.main import main


def write_lab7_spec(specs_root: Path) -> None:
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
  required_files: []
grading:
  total_points: 100
  parts_dir: "parts"
  part_files:
    - "01_first_agent.yaml"
    - "02_tools.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_first_agent.yaml").write_text(
        """
part_id: "01"
title: "First agent"
source_heading: "## First agent"
cell_range:
  start_heading: "## First agent"
  end_heading: "## Tools"
requirements:
  code:
    - id: "lab7_part01_code"
      description: "Code requirement"
      points: 4
      evidence:
        cell_markers:
          - "create_agent"
  markdown: []
  results: []
  code_applicability: "required"
  markdown_applicability: "not_applicable"
  results_applicability: "not_applicable"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_tools.yaml").write_text(
        """
part_id: "02"
title: "Tools"
source_heading: "## Tools"
cell_range:
  start_heading: "## Tools"
  end_heading: null
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


def create_notebooks(
    submissions_root: Path,
    student_folder: str,
    filenames: list[str],
    version_folder: str = "Wersja 1",
    lab_folder: str = "lab7",
) -> Path:
    folder = submissions_root / "lab1" / student_folder / lab_folder / version_folder
    folder.mkdir(parents=True)
    for filename in filenames:
        (folder / filename).write_text("{}", encoding="utf-8")
    return folder


def test_phase1_acceptance_flow_is_ci_safe(tmp_path: Path, capsys) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    write_lab7_spec(specs_root)
    create_notebooks(
        submissions_root,
        "Alicja_Resolved",
        ["notes.ipynb", "lab7_Alicja.ipynb"],
        lab_folder="Lab7",
    )
    create_notebooks(
        submissions_root,
        "Bartek_Highest_Version",
        ["lab7_old.ipynb"],
        version_folder="Wersja 1",
    )
    highest_version = create_notebooks(
        submissions_root,
        "Bartek_Highest_Version",
        ["lab7_new.ipynb"],
        version_folder="Wersja 3",
    )
    create_notebooks(
        submissions_root,
        "Celina_Ambiguous",
        ["lab7_a.ipynb", "lab7_b.ipynb"],
    )
    (submissions_root / "lab1" / "Damian_Missing_Lab").mkdir(parents=True)

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
    submissions = {
        submission["student_folder"]: submission
        for submission in output["submissions"]
    }

    assert output["group_id"] == "lab1"
    assert output["lab_id"] == "lab7"
    assert output["spec"]["expected_notebook_pattern"] == "lab7_*.ipynb"
    assert output["spec"]["part_ids"] == ["01", "02"]
    assert list(submissions) == [
        "Alicja_Resolved",
        "Bartek_Highest_Version",
        "Celina_Ambiguous",
        "Damian_Missing_Lab",
    ]

    assert submissions["Alicja_Resolved"]["status"] == "resolved"
    assert Path(submissions["Alicja_Resolved"]["lab_folder"]).name == "Lab7"
    assert Path(submissions["Alicja_Resolved"]["notebook_path"]).name == "lab7_Alicja.ipynb"

    assert submissions["Bartek_Highest_Version"]["status"] == "resolved"
    assert submissions["Bartek_Highest_Version"]["version_folder"] == str(highest_version)
    assert Path(submissions["Bartek_Highest_Version"]["notebook_path"]).name == "lab7_new.ipynb"

    assert submissions["Celina_Ambiguous"]["status"] == "ambiguous"
    assert submissions["Celina_Ambiguous"]["issue"]["code"] == "ambiguous_notebook"
    assert [Path(candidate).name for candidate in submissions["Celina_Ambiguous"]["issue"]["candidates"]] == [
        "lab7_a.ipynb",
        "lab7_b.ipynb",
    ]

    assert submissions["Damian_Missing_Lab"]["status"] == "unresolved"
    assert submissions["Damian_Missing_Lab"]["issue"]["code"] == "missing_lab_folder"

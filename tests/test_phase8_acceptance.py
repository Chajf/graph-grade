import json
from pathlib import Path

from app.main import main


def test_phase8_grade_group_grades_found_students_and_writes_group_summary(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    prace_root = tmp_path / "prace"
    output_root = tmp_path / "grading_results"
    write_spec(specs_root)
    write_notebook(prace_root / "lab1" / "Anna_Nowak" / "lab7" / "Wersja 1" / "lab7_Anna.ipynb")
    (prace_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1").mkdir(parents=True)

    exit_code = main(
        [
            "grade-group",
            "--prace-root",
            str(prace_root),
            "--specs-root",
            str(specs_root),
            "--output-root",
            str(output_root),
            "--group",
            "lab1",
            "--lab",
            "lab7",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    summary_csv_path = output_root / "lab7" / "lab1" / "group_summary.csv"
    assert output["graded_count"] == 1
    assert output["skipped_count"] == 1
    assert output["failed_count"] == 0
    assert Path(output["summary_csv_path"]) == summary_csv_path
    assert summary_csv_path.is_file()

    summary_csv = summary_csv_path.read_text(encoding="utf-8")
    assert "Anna_Nowak" in summary_csv
    assert "Jan_Kowalski" in summary_csv
    assert "missing_notebook" in summary_csv
    assert (output_root / "lab7" / "lab1" / "Anna_Nowak" / "grade.json").is_file()


def write_spec(specs_root: Path) -> None:
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
  total_points: 4
  parts_dir: "parts"
  part_files:
    - "01_schema.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_schema.yaml").write_text(
        """
part_id: "01"
title: "Schema"
source_heading: "## Part 1"
cell_range:
  start_heading: "## Part 1"
  end_heading: null
requirements:
  code:
    - id: "code_schema"
      description: "Defines supplier schema."
      points: 4
      evidence:
        cell_markers:
          - "class SupplierOffer"
  markdown: []
  results: []
""".lstrip(),
        encoding="utf-8",
    )


def write_notebook(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": ["# Lab 7\n", "## Part 1\n"],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": ["class SupplierOffer:\n", "    pass\n"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

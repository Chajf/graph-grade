import json
from pathlib import Path

from langgraph.graph import END

from app.graphs.laboratory_graph import create_laboratory_graph, fan_out_students
from app.models import LabSpec, NotebookResolutionIssue, SharePointStudentSubmission
from app.nodes.submission_resolution_collector import submission_resolution_collector


def test_fan_out_students_creates_send_for_each_submission(tmp_path: Path) -> None:
    submissions = [
        submission(tmp_path, "Anna_Nowak"),
        submission(tmp_path, "Jan_Kowalski"),
    ]

    sends = fan_out_students(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": lab_spec(),
            "submissions": submissions,
        }
    )

    assert not isinstance(sends, str)
    assert [send.node for send in sends] == ["student_grading", "student_grading"]
    assert [send.arg["submission"].student_folder for send in sends] == [
        "Anna_Nowak",
        "Jan_Kowalski",
    ]
    assert [send.arg["lab_spec"].lab_id for send in sends] == ["lab7", "lab7"]


def test_fan_out_students_routes_empty_submissions_to_end(tmp_path: Path) -> None:
    result = fan_out_students(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": lab_spec(),
            "submissions": [],
        }
    )

    assert result == END


def test_fan_out_students_only_sends_resolved_submissions(tmp_path: Path) -> None:
    sends = fan_out_students(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": lab_spec(),
            "submissions": [
                submission(tmp_path, "Anna_Nowak"),
                unresolved_submission(tmp_path, "Jan_Kowalski"),
            ],
        }
    )

    assert not isinstance(sends, str)
    assert [send.arg["submission"].student_folder for send in sends] == ["Anna_Nowak"]


def test_submission_resolution_collector_adds_skipped_grades_for_unresolved_submissions(
    tmp_path: Path,
) -> None:
    result = submission_resolution_collector(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": tmp_path / "grading_specs",
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
            "lab_spec": lab_spec(),
            "submissions": [
                submission(tmp_path, "Anna_Nowak"),
                unresolved_submission(tmp_path, "Jan_Kowalski"),
            ],
        }
    )

    final_grades = result["final_grades"]
    assert len(final_grades) == 1
    assert final_grades[0].student_folder == "Jan_Kowalski"
    assert final_grades[0].status == "skipped"
    assert final_grades[0].flags == ["submission_unresolved", "issue:missing_notebook"]


def test_create_laboratory_graph_compiles() -> None:
    graph = create_laboratory_graph()

    assert graph is not None


def test_laboratory_graph_collects_embedded_grading_graph_results(tmp_path: Path) -> None:
    specs_root = tmp_path / "grading_specs"
    prace_root = tmp_path / "prace"
    write_spec(specs_root)
    write_notebook(
        prace_root / "lab1" / "Anna_Nowak" / "lab7" / "Wersja 1" / "lab7_Anna.ipynb"
    )
    (prace_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1").mkdir(parents=True)

    final_state = create_laboratory_graph().invoke(
        {
            "prace_root": prace_root,
            "specs_root": specs_root,
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
        }
    )

    final_grades = sorted(final_state["final_grades"], key=lambda grade: grade.student_folder)
    assert [grade.student_folder for grade in final_grades] == ["Anna_Nowak", "Jan_Kowalski"]
    assert [grade.status for grade in final_grades] == ["graded", "skipped"]
    assert final_grades[0].points_awarded == 4
    assert final_grades[1].flags == ["submission_unresolved", "issue:missing_notebook"]


def submission(tmp_path: Path, student_folder: str) -> SharePointStudentSubmission:
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


def lab_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=12,
        expected_notebook_pattern="lab7*.ipynb",
        required_files=[],
        parts=[],
    )


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

import json
from pathlib import Path

from app.main import main


def test_phase7_grade_student_creates_artifacts_and_sums_section_scores(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    prace_root = tmp_path / "prace"
    output_root = tmp_path / "grading_results"
    write_phase7_spec(specs_root)
    notebook_path = prace_root / "lab1" / "Anna_Nowak" / "lab7" / "Wersja 2" / "lab7_Nowak.ipynb"
    write_phase7_notebook(notebook_path)

    exit_code = main(
        [
            "grade-student",
            "--prace-root",
            str(prace_root),
            "--specs-root",
            str(specs_root),
            "--output-root",
            str(output_root),
            "--group",
            "lab1",
            "--student",
            "Anna_Nowak",
            "--lab",
            "lab7",
        ]
    )

    assert exit_code == 0
    cli_output = json.loads(capsys.readouterr().out)
    grade_path = output_root / "lab7" / "lab1" / "Anna_Nowak" / "grade.json"
    feedback_path = output_root / "lab7" / "lab1" / "Anna_Nowak" / "feedback.md"
    summary_path = output_root / "lab1" / "Anna_Nowak" / "summary.md"

    assert Path(cli_output["grade_path"]) == grade_path
    assert Path(cli_output["feedback_path"]) == feedback_path
    assert Path(cli_output["student_summary_path"]) == summary_path
    assert grade_path.is_file()
    assert feedback_path.is_file()
    assert summary_path.is_file()

    grade = json.loads(grade_path.read_text(encoding="utf-8"))
    section_scores = [section["points_awarded"] for section in grade["section_grades"]]
    section_possible = [section["points_possible"] for section in grade["section_grades"]]

    assert grade["points_awarded"] == sum(section_scores)
    assert grade["points_possible"] == sum(section_possible)
    assert grade["points_awarded"] == 16
    assert grade["points_possible"] == 16
    assert [section["part_id"] for section in grade["section_grades"]] == ["01", "02"]

    requirement_grades = [
        requirement
        for section in grade["section_grades"]
        for requirement in section["requirement_grades"]
    ]
    assert [requirement["requirement_id"] for requirement in requirement_grades] == [
        "agent_factory",
        "tool_reflection",
        "executed_cleanly",
    ]
    assert {requirement["bucket"] for requirement in requirement_grades} == {
        "code",
        "markdown",
        "results",
    }
    assert requirement_grades[0]["points_awarded"] == 4
    assert requirement_grades[1]["points_awarded"] == 8
    assert requirement_grades[2]["points_awarded"] == 4

    feedback = feedback_path.read_text(encoding="utf-8")
    assert "# Feedback for lab7" in feedback
    assert "### 01: Agent setup" in feedback
    assert "### 02: Tool reflection" in feedback
    assert "agent_factory" in feedback
    assert "tool_reflection" in feedback
    assert "executed_cleanly" in feedback
    assert "Score: 16 / 16" in feedback

    summary = summary_path.read_text(encoding="utf-8")
    assert "| lab7 | 16 / 16 | graded | - |" in summary
    assert "Total: 16 / 16" in summary


def write_phase7_spec(specs_root: Path) -> None:
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
  total_points: 16
  parts_dir: "parts"
  part_files:
    - "01_agent.yaml"
    - "02_tools.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_agent.yaml").write_text(
        """
part_id: "01"
title: "Agent setup"
source_heading: "## Part 1"
cell_range:
  start_heading: "## Part 1"
  end_heading: "## Part 2"
requirements:
  code:
    - id: "agent_factory"
      description: "Defines the agent factory."
      points: 4
      evidence:
        cell_markers:
          - "def build_agent"
          - "create_react_agent"
  markdown: []
  results: []
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_tools.yaml").write_text(
        """
part_id: "02"
title: "Tool reflection"
source_heading: "## Part 2"
cell_range:
  start_heading: "## Part 2"
  end_heading: null
requirements:
  code: []
  markdown:
    - id: "tool_reflection"
      description: "Explains why tool failures matter."
      points: 8
      evidence:
        heading_or_text: "Required reflection"
  results:
    - id: "executed_cleanly"
      description: "Code cells execute without visible errors."
      points: 4
      checks:
        - "required_code_cells_have_execution_count_or_equivalent_visible_outputs"
        - "no_error_outputs_in_required_cells"
""".lstrip(),
        encoding="utf-8",
    )


def write_phase7_notebook(path: Path) -> None:
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
                        "source": [
                            "def build_agent(model, tools):\n",
                            "    return create_react_agent(model, tools)\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": ["agent ready\n"],
                            }
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": [
                            "## Part 2\n",
                            "Required reflection: tool failures can produce bad business decisions.\n",
                        ],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 2,
                        "source": ["print('tool call ok')\n"],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": ["tool call ok\n"],
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

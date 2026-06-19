import json
from pathlib import Path

import app.main as main_module
from app.main import main
from app.models import ApiResponseJudgeResult, CodeJudgeResult, MarkdownJudgeResult


def test_grade_student_creates_grade_feedback_and_student_summary(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    output_root = tmp_path / "grading_results"
    write_spec(specs_root)
    notebook_path = (
        submissions_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1" / "lab7_Kowalski.ipynb"
    )
    write_notebook(notebook_path)

    exit_code = main(
        [
            "grade-student",
            "--prace-root",
            str(submissions_root),
            "--specs-root",
            str(specs_root),
            "--output-root",
            str(output_root),
            "--group",
            "lab1",
            "--student",
            "Jan_Kowalski",
            "--lab",
            "lab7",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    grade_path = Path(output["grade_path"])
    feedback_path = Path(output["feedback_path"])
    summary_path = Path(output["student_summary_path"])

    assert output["group_id"] == "lab1"
    assert output["lab_id"] == "lab7"
    assert output["student_folder"] == "Jan_Kowalski"
    assert output["points_awarded"] == 12
    assert output["points_possible"] == 12
    assert grade_path == output_root / "lab7" / "lab1" / "Jan_Kowalski" / "grade.json"
    assert feedback_path == output_root / "lab7" / "lab1" / "Jan_Kowalski" / "feedback.md"
    assert summary_path == output_root / "lab1" / "Jan_Kowalski" / "summary.md"

    grade_json = json.loads(grade_path.read_text(encoding="utf-8"))
    assert grade_json["points_awarded"] == 12
    assert [section["part_id"] for section in grade_json["section_grades"]] == ["01", "02"]
    assert "code_schema" in feedback_path.read_text(encoding="utf-8")
    assert "| lab7 | 12 / 12 | graded | - |" in summary_path.read_text(encoding="utf-8")


def test_grade_student_reports_unresolved_submission(
    tmp_path: Path,
    capsys,
) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    (submissions_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1").mkdir(parents=True)
    write_spec(specs_root)

    exit_code = main(
        [
            "grade-student",
            "--prace-root",
            str(submissions_root),
            "--specs-dir",
            str(specs_root),
            "--output-root",
            str(tmp_path / "grading_results"),
            "--group",
            "lab1",
            "--student",
            "Jan_Kowalski",
            "--lab",
            "lab7",
        ]
    )

    assert exit_code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "unresolved"
    assert output["issue"]["code"] == "missing_notebook"


def test_grade_student_can_enable_llm_judges(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    specs_root = tmp_path / "grading_specs"
    submissions_root = tmp_path / "prace"
    output_root = tmp_path / "grading_results"
    captured_settings = []
    write_spec(specs_root)
    write_notebook(
        submissions_root / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1" / "lab7_Kowalski.ipynb"
    )

    def create_code_judge(settings):
        captured_settings.append(("code", settings))
        return StubCodeJudge()

    def create_markdown_judge(settings):
        captured_settings.append(("markdown", settings))
        return StubMarkdownJudge()

    def create_api_response_judge(settings):
        captured_settings.append(("api_response", settings))
        return StubApiResponseJudge()

    monkeypatch.setattr(main_module, "create_api_response_judge", create_api_response_judge)
    monkeypatch.setattr(main_module, "create_code_judge", create_code_judge)
    monkeypatch.setattr(main_module, "create_markdown_judge", create_markdown_judge)

    exit_code = main(
        [
            "grade-student",
            "--prace-root",
            str(submissions_root),
            "--specs-root",
            str(specs_root),
            "--output-root",
            str(output_root),
            "--group",
            "lab1",
            "--student",
            "Jan_Kowalski",
            "--lab",
            "lab7",
            "--llm-judges",
            "--judge-model",
            "test/model",
            "--judge-provider",
            "test-provider",
            "--judge-temperature",
            "0.2",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["points_awarded"] == 10
    assert [(kind, settings.model, settings.model_provider, settings.temperature) for kind, settings in captured_settings] == [
        ("api_response", "test/model", "test-provider", 0.2),
        ("code", "test/model", "test-provider", 0.2),
        ("markdown", "test/model", "test-provider", 0.2),
    ]

    grade_json = json.loads(Path(output["grade_path"]).read_text(encoding="utf-8"))
    requirement_grades = [
        requirement
        for section in grade_json["section_grades"]
        for requirement in section["requirement_grades"]
    ]
    assert requirement_grades[0]["comment"] == "LLM code judge adjusted score."
    assert requirement_grades[1]["comment"] == "LLM markdown judge adjusted score."


class StubCodeJudge:
    def judge_code(self, context):
        return CodeJudgeResult(
            points_awarded=2,
            status="partial",
            evidence_cells=context.deterministic_grade.evidence_cells,
            reasoning="Stub code judge.",
            comment="LLM code judge adjusted score.",
            confidence="medium",
        )


class StubMarkdownJudge:
    def judge_markdown(self, context):
        return MarkdownJudgeResult(
            points_awarded=8,
            status="full",
            evidence_cells=context.deterministic_grade.evidence_cells,
            reasoning="Stub markdown judge.",
            comment="LLM markdown judge adjusted score.",
            confidence="high",
        )


class StubApiResponseJudge:
    def judge_api_response(self, context):
        return ApiResponseJudgeResult(
            points_awarded=context.deterministic_grade.points_awarded,
            status=context.deterministic_grade.status,
            evidence_cells=context.deterministic_grade.evidence_cells,
            reasoning="Stub API response judge.",
            comment="LLM API response judge kept score.",
            confidence=context.deterministic_grade.confidence,
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
  total_points: 12
  parts_dir: "parts"
  part_files:
    - "01_schema.yaml"
    - "02_reflection.yaml"
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
  end_heading: "## Part 2"
requirements:
  code:
    - id: "code_schema"
      description: "Defines supplier schema and parser."
      points: 4
      evidence:
        cell_markers:
          - "class SupplierOffer"
          - "def parse_supplier_offer"
  markdown: []
  results: []
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_reflection.yaml").write_text(
        """
part_id: "02"
title: "Reflection"
source_heading: "## Part 2"
cell_range:
  start_heading: "## Part 2"
  end_heading: null
requirements:
  code: []
  markdown:
    - id: "reflection"
      description: "Explains parsing risk."
      points: 8
      evidence:
        heading_or_text: "Required reflection"
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
                        "source": [
                            "class SupplierOffer:\n",
                            "    pass\n",
                            "\n",
                            "def parse_supplier_offer(text):\n",
                            "    return SupplierOffer()\n",
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": [
                            "## Part 2\n",
                            "Required reflection: parsing failures can affect allocations.\n",
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

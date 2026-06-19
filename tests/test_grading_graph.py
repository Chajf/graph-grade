import json
from pathlib import Path

from app.graphs.grading_graph import create_grading_graph, fan_out_sections
from app.models import (
    CellRangeSpec,
    LabSpec,
    PartSpec,
    RequirementEvidence,
    RequirementSpec,
    SharePointStudentSubmission,
)
from app.nodes.evidence_builder import evidence_builder
from app.nodes.notebook_parser import notebook_parser
from app.nodes.section_splitter import section_splitter


def test_grading_graph_grades_student_lab_with_section_fan_out(tmp_path: Path) -> None:
    notebook_path = tmp_path / "prace" / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1" / "lab7.ipynb"
    write_two_part_notebook(notebook_path)
    lab_spec = build_two_part_lab_spec()
    submission = resolved_submission(tmp_path, notebook_path)

    final_state = create_grading_graph().invoke(
        {
            "lab_spec": lab_spec,
            "submission": submission,
            "output_root": tmp_path / "grading_results",
        }
    )

    final_grade = final_state["final_grade"]
    assert final_grade.points_awarded == 12
    assert final_grade.points_possible == 12
    assert [section.part_id for section in final_grade.section_grades] == ["01", "02"]

    grade_json = json.loads(final_state["lab_grade_path"].read_text(encoding="utf-8"))
    feedback = final_state["lab_feedback_path"].read_text(encoding="utf-8")
    summary = final_state["student_summary_path"].read_text(encoding="utf-8")

    assert grade_json["points_awarded"] == 12
    assert [section["part_id"] for section in grade_json["section_grades"]] == ["01", "02"]
    assert "### 01: Schema" in feedback
    assert "### 02: Reflection" in feedback
    assert "| lab7 | 12 / 12 | graded | - |" in summary


def test_fan_out_sections_creates_send_for_each_section(tmp_path: Path) -> None:
    notebook_path = tmp_path / "prace" / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1" / "lab7.ipynb"
    write_two_part_notebook(notebook_path)
    lab_spec = build_two_part_lab_spec()
    state = {
        "lab_spec": lab_spec,
        "submission": resolved_submission(tmp_path, notebook_path),
        "output_root": tmp_path / "grading_results",
    }
    state.update(notebook_parser(state))
    state.update(section_splitter(state))
    state.update(evidence_builder(state))

    sends = fan_out_sections(state)

    assert not isinstance(sends, str)
    assert [send.node for send in sends] == ["section_grading", "section_grading"]
    assert [send.arg["part_spec"].part_id for send in sends] == ["01", "02"]
    assert [send.arg["section"].part_id for send in sends] == ["01", "02"]


def test_fan_out_sections_routes_empty_sections_to_final_synthesis(tmp_path: Path) -> None:
    result = fan_out_sections(
        {
            "lab_spec": build_two_part_lab_spec(),
            "submission": SharePointStudentSubmission(
                submissions_root=tmp_path / "prace",
                group_id="lab1",
                student_folder="Jan_Kowalski",
                lab_id="lab7",
                status="resolved",
                notebook_path=tmp_path / "lab7.ipynb",
            ),
            "output_root": tmp_path / "grading_results",
            "sections": [],
        }
    )

    assert result == "final_synthesizer"


def resolved_submission(tmp_path: Path, notebook_path: Path) -> SharePointStudentSubmission:
    return SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        lab_id="lab7",
        lab_folder=notebook_path.parents[1],
        version_folder=notebook_path.parent,
        notebook_path=notebook_path,
        status="resolved",
    )


def write_two_part_notebook(path: Path) -> None:
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


def build_two_part_lab_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=12,
        expected_notebook_pattern="lab7*.ipynb",
        required_files=[],
        parts=[
            PartSpec(
                part_id="01",
                title="Schema",
                source_heading="## Part 1",
                cell_range=CellRangeSpec(
                    start_heading="## Part 1",
                    end_heading="## Part 2",
                ),
                code_requirements=[
                    RequirementSpec(
                        id="code_schema",
                        description="Defines supplier schema and parser.",
                        points=4,
                        evidence=RequirementEvidence(
                            cell_markers=["class SupplierOffer", "def parse_supplier_offer"]
                        ),
                    )
                ],
                markdown_requirements=[],
                result_requirements=[],
            ),
            PartSpec(
                part_id="02",
                title="Reflection",
                source_heading="## Part 2",
                cell_range=CellRangeSpec(start_heading="## Part 2"),
                code_requirements=[],
                markdown_requirements=[
                    RequirementSpec(
                        id="reflection",
                        description="Explains parsing risk.",
                        points=8,
                        evidence=RequirementEvidence(heading_or_text="Required reflection"),
                    )
                ],
                result_requirements=[],
            ),
        ],
    )

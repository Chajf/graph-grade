import json
from pathlib import Path

import pytest

from app.graphs.section_graph import create_section_graph
from app.models import (
    CellRangeSpec,
    LabSpec,
    PartSpec,
    RequirementEvidence,
    RequirementSpec,
    SharePointStudentSubmission,
)
from app.nodes.evidence_builder import evidence_builder
from app.nodes.final_synthesizer import final_synthesizer
from app.nodes.notebook_loader import notebook_loader
from app.nodes.notebook_parser import notebook_parser
from app.nodes.result_persister import result_persister
from app.nodes.section_loader import initialize_section_state
from app.nodes.section_splitter import section_splitter
from app.nodes.submission_loader import submission_loader


def test_student_grading_nodes_produce_final_grade_and_artifacts(tmp_path: Path) -> None:
    notebook_path = tmp_path / "prace" / "lab1" / "Jan_Kowalski" / "lab7" / "Wersja 1" / "lab7.ipynb"
    write_notebook(notebook_path)
    lab_spec = build_lab_spec()
    submission = SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        lab_id="lab7",
        lab_folder=notebook_path.parents[1],
        version_folder=notebook_path.parent,
        notebook_path=notebook_path,
        status="resolved",
    )
    state = {
        "lab_spec": lab_spec,
        "submission": submission,
        "output_root": tmp_path / "grading_results",
    }

    state.update(submission_loader(state))
    state.update(notebook_loader(state))
    state.update(notebook_parser(state))
    state.update(section_splitter(state))
    state.update(evidence_builder(state))

    section_result = create_section_graph().invoke(
        initialize_section_state(
            lab_spec.parts[0],
            state["sections"][0],
            state["evidence_index"],
            lab_id=lab_spec.lab_id,
        )
    )
    state.update(section_result)
    state.update(final_synthesizer(state))
    state.update(result_persister(state))

    final_grade = state["final_grade"]
    assert final_grade.points_awarded == 12
    assert final_grade.points_possible == 12
    assert [section.part_id for section in final_grade.section_grades] == ["01"]

    grade_json = json.loads(state["lab_grade_path"].read_text(encoding="utf-8"))
    feedback = state["lab_feedback_path"].read_text(encoding="utf-8")
    summary = state["student_summary_path"].read_text(encoding="utf-8")

    assert grade_json["lab_id"] == "lab7"
    assert grade_json["points_awarded"] == 12
    assert grade_json["section_grades"][0]["requirement_grades"][0]["requirement_id"] == "code_schema"
    assert "# Feedback for lab7" in feedback
    assert "code_schema" in feedback
    assert "| lab7 | 12 / 12 | graded | - |" in summary


def test_submission_loader_records_missing_files_and_output_paths(tmp_path: Path) -> None:
    lab_spec = build_lab_spec()
    submission = SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        lab_id="lab7",
        missing_required_files=["data.csv"],
        status="unresolved",
    )

    result = submission_loader(
        {
            "lab_spec": lab_spec,
            "submission": submission,
            "output_root": tmp_path / "grading_results",
        }
    )

    assert result["flags"] == ["submission_unresolved", "missing_required_file:data.csv"]
    assert result["lab_grade_path"] == (
        tmp_path / "grading_results" / "lab7" / "lab1" / "Jan_Kowalski" / "grade.json"
    )
    assert result["student_summary_path"] == (
        tmp_path / "grading_results" / "lab1" / "Jan_Kowalski" / "summary.md"
    )


def test_notebook_loader_rejects_unresolved_submission(tmp_path: Path) -> None:
    submission = SharePointStudentSubmission(
        submissions_root=tmp_path / "prace",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        lab_id="lab7",
        status="unresolved",
    )

    with pytest.raises(ValueError, match="Submission is not resolved"):
        notebook_loader(
            {
                "lab_spec": build_lab_spec(),
                "submission": submission,
                "output_root": tmp_path / "grading_results",
            }
        )


def write_notebook(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": [
                            "# Lab 7\n",
                            "## Part 1\n",
                            "Required reflection: parsing failures can affect allocations.\n",
                        ],
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
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": ["ok\n"],
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def build_lab_spec() -> LabSpec:
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
                title="Part 1",
                source_heading="## Part 1",
                cell_range=CellRangeSpec(start_heading="## Part 1"),
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
                markdown_requirements=[
                    RequirementSpec(
                        id="reflection",
                        description="Explains parsing risk.",
                        points=8,
                        evidence=RequirementEvidence(heading_or_text="Required reflection"),
                    )
                ],
                result_requirements=[],
            )
        ],
    )

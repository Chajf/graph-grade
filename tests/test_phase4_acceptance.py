import json
from pathlib import Path

from app.models import CellRangeSpec, LabSpec, PartSpec, RequirementSpec
from app.services.code_features import match_code_markers
from app.services.evidence import build_evidence_index
from app.services.grading_checks import run_result_checks
from app.services.notebook_parser import parse_notebook
from app.services.notebook_splitter import split_notebook_by_lab_spec


def test_phase4_detects_deterministic_code_result_and_secret_evidence(
    tmp_path: Path,
) -> None:
    notebook_path = tmp_path / "lab7_phase4.ipynb"
    write_phase4_lab7_notebook(notebook_path)

    parsed = parse_notebook(notebook_path)
    sections = split_notebook_by_lab_spec(parsed, build_phase4_lab7_spec())
    supplier_section = sections[0]
    error_section = sections[1]
    evidence_index = build_evidence_index(parsed)

    marker_findings = match_code_markers(
        supplier_section.code_cells,
        ["class SupplierOffer", "def parse_supplier_offer"],
    )
    result_checks = run_result_checks(
        supplier_section,
        supplier_section_spec().result_requirements[0],
        evidence_index,
    )

    assert [finding.matched for finding in marker_findings] == [True, True]
    assert [finding.evidence_cells for finding in marker_findings] == [[1], [1]]
    assert evidence_index.classes["SupplierOffer"] == [1]
    assert evidence_index.functions["parse_supplier_offer"] == [1]

    assert len(evidence_index.api_scores) == 1
    assert evidence_index.api_scores[0].cell_index == 2
    assert evidence_index.api_scores[0].score == 9
    assert evidence_index.api_scores[0].max_score == 10

    assert error_section.errors[0].ename == "ValueError"
    assert evidence_index.errors[0].ename == "ValueError"

    assert {finding.kind for finding in evidence_index.possible_secrets} >= {
        "api_key",
        "openai_api_key",
    }
    assert all("..." in finding.snippet for finding in evidence_index.possible_secrets)

    assert [check.check_name for check in result_checks] == [
        "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
        "api_response_visible",
        "no_error_outputs_in_required_cells",
        "no_plaintext_api_keys",
    ]
    assert [check.passed for check in result_checks] == [True, True, True, False]


def write_phase4_lab7_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": [
                            "# Lab 7\n",
                            "## Supplier ranking agent\n",
                            "This section builds and validates supplier offer parsing.\n",
                        ],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": [
                            "import json\n",
                            "\n",
                            "API_KEY = 'sk-abc1234567890abc1234567890abc1234567890'\n",
                            "\n",
                            "class SupplierOffer:\n",
                            "    pass\n",
                            "\n",
                            "def parse_supplier_offer(raw_offer):\n",
                            "    return json.loads(raw_offer)\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": "parser ready\n",
                            }
                        ],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 2,
                        "source": "api_response\n",
                        "outputs": [
                            {
                                "output_type": "execute_result",
                                "data": {
                                    "application/json": {
                                        "score": 9,
                                        "max_score": 10,
                                        "details": {"parsed_offers": 3},
                                    }
                                },
                                "metadata": {},
                                "execution_count": 2,
                            }
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": "## Optimization\nExplain allocation constraints.\n",
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 3,
                        "source": [
                            "def optimize_allocation_lp(offers):\n",
                            "    raise ValueError('no feasible allocation')\n",
                            "\n",
                            "optimize_allocation_lp([])\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "error",
                                "ename": "ValueError",
                                "evalue": "no feasible allocation",
                                "traceback": ["ValueError: no feasible allocation"],
                            }
                        ],
                    },
                ],
                "metadata": {"kernelspec": {"name": "python3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def build_phase4_lab7_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        parts=[
            supplier_section_spec(),
            PartSpec(
                part_id="02",
                title="Optimization",
                source_heading="## Optimization",
                cell_range=CellRangeSpec(start_heading="## Optimization"),
            ),
        ],
    )


def supplier_section_spec() -> PartSpec:
    return PartSpec(
        part_id="01",
        title="Supplier ranking agent",
        source_heading="## Supplier ranking agent",
        cell_range=CellRangeSpec(
            start_heading="## Supplier ranking agent",
            end_heading="## Optimization",
        ),
        result_requirements=[
            RequirementSpec(
                id="supplier_api_result",
                description="Shows visible API scoring response without execution errors or plaintext keys.",
                points=4,
                checks=[
                    "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
                    "api_response_visible",
                    "no_error_outputs_in_required_cells",
                    "no_plaintext_api_keys",
                ],
            )
        ],
    )

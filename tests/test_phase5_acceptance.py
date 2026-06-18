import json
from pathlib import Path

from app.graphs.section_graph import create_section_graph
from app.nodes.section_loader import initialize_section_state
from app.repositories import GradingSpecRepository
from app.services.evidence import build_evidence_index
from app.services.notebook_parser import parse_notebook
from app.services.notebook_splitter import split_notebook_by_lab_spec


def test_phase5_grades_lab7_part02_with_requirement_level_results(tmp_path: Path) -> None:
    notebook_path = tmp_path / "lab7_phase5.ipynb"
    write_lab7_part02_notebook(notebook_path)

    lab_spec = GradingSpecRepository(Path("work/grading_specs")).load_lab_spec("lab7")
    part_spec = next(part for part in lab_spec.parts if part.part_id == "02")
    parsed = parse_notebook(notebook_path)
    section = next(
        section
        for section in split_notebook_by_lab_spec(parsed, lab_spec)
        if section.part_id == "02"
    )
    evidence_index = build_evidence_index(parsed)

    final_state = create_section_graph().invoke(
        initialize_section_state(part_spec, section, evidence_index, lab_id=lab_spec.lab_id)
    )
    section_grade = final_state["section_grade"]

    assert section_grade.part_id == "02"
    assert section_grade.title == "Tools: parsing, TOPSIS, and LP allocation"
    assert section_grade.points_awarded > 0
    assert section_grade.points_possible == 25

    requirement_grades = section_grade.requirement_grades
    assert [grade.requirement_id for grade in requirement_grades] == [
        "lab7_part02_supplier_offer_schema",
        "lab7_part02_parse_supplier_offer_tool",
        "lab7_part02_rank_suppliers_topsis_tool",
        "lab7_part02_optimize_allocation_lp_tool",
        "lab7_part02_tools_reflection",
        "lab7_part02_executed_cells",
    ]
    assert {grade.bucket for grade in requirement_grades} == {
        "code",
        "markdown",
        "results",
    }

    code_grades = [grade for grade in requirement_grades if grade.bucket == "code"]
    assert all(grade.status == "full" for grade in code_grades)
    assert all(grade.evidence_cells for grade in code_grades)

    markdown_grade = next(grade for grade in requirement_grades if grade.bucket == "markdown")
    assert markdown_grade.status == "full"
    assert markdown_grade.points_awarded == 8

    result_grade = next(grade for grade in requirement_grades if grade.bucket == "results")
    assert result_grade.status == "full"
    assert result_grade.points_possible == 0
    assert result_grade.evidence_cells


def write_lab7_part02_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": [
                            "# Lab 7\n",
                            "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP\n",
                        ],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": [
                            "import json\n",
                            "from pydantic import BaseModel, Field\n",
                            "from langchain.tools import tool\n",
                            "from langchain.agents.structured_output import ProviderStrategy\n",
                            "from pulp import LpProblem, LpVariable\n",
                            "\n",
                            "class SupplierOffer(BaseModel):\n",
                            "    supplier_name: str = Field(description='Supplier name')\n",
                            "    price_per_unit: float = Field(description='Unit price')\n",
                            "    delivery_days: int = Field(description='Delivery time')\n",
                            "    quality_score: float = Field(description='Quality score')\n",
                            "    capacity: int = Field(description='Maximum capacity')\n",
                            "    payment_days: int = Field(description='Payment terms')\n",
                            "\n",
                            "@tool\n",
                            "def parse_supplier_offer(raw_offer: str) -> str:\n",
                            "    strategy = ProviderStrategy(SupplierOffer)\n",
                            "    offer = SupplierOffer(\n",
                            "        supplier_name='Alpha',\n",
                            "        price_per_unit=10.0,\n",
                            "        delivery_days=3,\n",
                            "        quality_score=0.95,\n",
                            "        capacity=100,\n",
                            "        payment_days=14,\n",
                            "    )\n",
                            "    return offer.model_dump_json() + str(strategy)\n",
                            "\n",
                            "def rank_suppliers_topsis(raw_offers: str) -> str:\n",
                            "    offers = json.loads(raw_offers)\n",
                            "    weights = [0.4, 0.2, 0.2, 0.2]\n",
                            "    types = [-1, -1, 1, 1]\n",
                            "    method = 'TOPSIS'\n",
                            "    return f'{method} ranking: {offers} {weights} {types}'\n",
                            "\n",
                            "def optimize_allocation_lp(offers: list[dict]) -> str:\n",
                            "    problem = LpProblem('allocation')\n",
                            "    quantity = LpVariable('quantity', lowBound=0, cat=\"Integer\")\n",
                            "    status = 'Infeasible' if not offers else 'Optimal'\n",
                            "    return f'{problem.name}: {quantity.name}: {status}'\n",
                            "\n",
                            "print(parse_supplier_offer('Alpha offer'))\n",
                            "print(rank_suppliers_topsis('[{\"supplier\": \"Alpha\"}]'))\n",
                            "print(optimize_allocation_lp([{\"supplier\": \"Alpha\"}]))\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": [
                                    "{\"supplier_name\":\"Alpha\",\"price_per_unit\":10.0}\n",
                                    "TOPSIS ranking: Alpha\n",
                                    "allocation: quantity: Optimal\n",
                                ],
                            }
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": [
                            "### Wymagany komentarz – Część 2\n",
                            "Narzędzia @tool rozdzielają parsowanie ofert, ranking TOPSIS i alokację LP. "
                            "Ekstrakcja LLM jest mniej krucha niż regex, ale błędne wartości ceny, "
                            "jakości lub pojemności mogą zmienić ranking i decyzję biznesową. "
                            "Osobne parsowanie ułatwia diagnostykę, a batched parsing może obniżyć koszt.\n",
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": "## Część 3 – Structured Output z `ProviderStrategy`\n",
                    },
                ],
                "metadata": {"kernelspec": {"name": "python3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

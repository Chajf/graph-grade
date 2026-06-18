import json
from pathlib import Path

from app.models import CellRangeSpec, LabSpec, PartSpec
from app.services.notebook_parser import parse_notebook
from app.services.notebook_splitter import split_notebook_by_lab_spec


def test_phase3_splits_lab7_style_notebook_into_spec_sections(tmp_path: Path) -> None:
    notebook_path = tmp_path / "lab7_acceptance.ipynb"
    write_lab7_style_notebook(notebook_path)

    parsed = parse_notebook(notebook_path)
    sections = split_notebook_by_lab_spec(parsed, build_lab7_split_spec())

    assert [section.part_id for section in sections] == ["01", "02", "99"]

    first_section = sections[0]
    assert [cell.index for cell in first_section.cells] == [0, 1]
    assert [cell.index for cell in first_section.markdown_cells] == [0]
    assert [cell.index for cell in first_section.code_cells] == [1]
    assert first_section.output_text == "parsed\n"
    assert first_section.errors == []
    assert first_section.mapping_confidence == "high"

    second_section = sections[1]
    assert [cell.index for cell in second_section.cells] == [2, 3, 4]
    assert [cell.index for cell in second_section.markdown_cells] == [2, 4]
    assert [cell.index for cell in second_section.code_cells] == [3]
    assert "ValueError: no feasible allocation" in second_section.output_text
    assert second_section.errors[0].ename == "ValueError"
    assert second_section.mapping_confidence == "high"

    missing_section = sections[2]
    assert missing_section.cells == []
    assert missing_section.code_cells == []
    assert missing_section.markdown_cells == []
    assert missing_section.output_text == ""
    assert missing_section.errors == []
    assert missing_section.mapping_confidence == "low"
    assert missing_section.missing_start_heading is True


def write_lab7_style_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": [
                            "# Lab 7\n",
                            "## Supplier ranking agent\n",
                            "This notebook documents the procurement workflow.\n",
                        ],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": [
                            "import json\n",
                            "\n",
                            "class SupplierOffer:\n",
                            "    pass\n",
                            "\n",
                            "def parse_supplier_offer(raw_offer):\n",
                            "    return json.loads(raw_offer)\n",
                            "\n",
                            "print('parsed')\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": "parsed\n",
                            }
                        ],
                    },
                    {
                        "cell_type": "markdown",
                        "source": "## Optimization\nExplain allocation constraints.\n",
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 2,
                        "source": [
                            "class ProcurementDecision:\n",
                            "    pass\n",
                            "\n",
                            "def optimize_allocation_lp(offers):\n",
                            "    raise ValueError('no feasible allocation')\n",
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
                    {
                        "cell_type": "markdown",
                        "source": "Final notes without a heading.\n",
                    },
                ],
                "metadata": {"kernelspec": {"name": "python3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def build_lab7_split_spec() -> LabSpec:
    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        parts=[
            part("01", "Supplier ranking agent", "## Supplier ranking agent", "## Optimization"),
            part("02", "Optimization", "## Optimization", None),
            part("99", "Missing reflection", "## Missing reflection", None),
        ],
    )


def part(
    part_id: str,
    title: str,
    start_heading: str,
    end_heading: str | None,
) -> PartSpec:
    return PartSpec(
        part_id=part_id,
        title=title,
        source_heading=start_heading,
        cell_range=CellRangeSpec(
            start_heading=start_heading,
            end_heading=end_heading,
        ),
        code_requirements=[],
        markdown_requirements=[],
        result_requirements=[],
    )

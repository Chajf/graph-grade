import json
from pathlib import Path

from app.main import main
from app.services.notebook_parser import parse_notebook


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
                ],
                "metadata": {"kernelspec": {"name": "python3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_phase2_parses_lab7_style_notebook_service_api(tmp_path: Path) -> None:
    notebook_path = tmp_path / "lab7_acceptance.ipynb"
    write_lab7_style_notebook(notebook_path)

    parsed = parse_notebook(notebook_path)

    code_cells = [cell for cell in parsed.cells if cell.cell_type == "code"]
    markdown_cells = [cell for cell in parsed.cells if cell.cell_type == "markdown"]

    assert parsed.path == notebook_path
    assert len(parsed.cells) == 4
    assert len(code_cells) == 2
    assert len(markdown_cells) == 2
    assert markdown_cells[0].headings == ["Lab 7", "Supplier ranking agent"]
    assert code_cells[0].output_text == "parsed\n"
    assert code_cells[1].errors[0].ename == "ValueError"
    assert "ValueError: no feasible allocation" in code_cells[1].output_text

    first_features = code_cells[0].code_features
    second_features = code_cells[1].code_features
    assert first_features is not None
    assert second_features is not None
    assert first_features.functions == ["parse_supplier_offer"]
    assert first_features.classes == ["SupplierOffer"]
    assert second_features.functions == ["optimize_allocation_lp"]
    assert second_features.classes == ["ProcurementDecision"]


def test_phase2_parse_notebook_cli_reports_lab7_style_summary(
    tmp_path: Path,
    capsys,
) -> None:
    notebook_path = tmp_path / "lab7_acceptance.ipynb"
    write_lab7_style_notebook(notebook_path)

    exit_code = main(
        [
            "parse-notebook",
            "--notebook-path",
            str(notebook_path),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "path": str(notebook_path),
        "total_cells": 4,
        "code_cell_count": 2,
        "markdown_cell_count": 2,
        "raw_cell_count": 0,
        "output_count": 2,
        "error_count": 1,
        "functions": ["parse_supplier_offer", "optimize_allocation_lp"],
        "classes": ["SupplierOffer", "ProcurementDecision"],
    }

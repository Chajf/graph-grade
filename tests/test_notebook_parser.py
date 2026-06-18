import json
from pathlib import Path

import pytest

from app.services.notebook_parser import parse_notebook


def write_notebook(path: Path, cells: list[dict], metadata: dict | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": cells,
                "metadata": metadata or {"kernelspec": {"name": "python3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_parse_notebook_extracts_cells_outputs_and_errors(tmp_path: Path) -> None:
    notebook_path = tmp_path / "lab7_example.ipynb"
    write_notebook(
        notebook_path,
        [
            {
                "cell_type": "markdown",
                "source": ["# Lab 7\n", "Intro\n", "## First agent\n"],
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "source": ["print('hello')\n"],
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": ["hello\n"],
                    },
                    {
                        "output_type": "execute_result",
                        "data": {
                            "text/plain": ["{'score': 1}\n"],
                            "application/json": {"score": 1},
                        },
                        "metadata": {},
                    },
                    {
                        "output_type": "error",
                        "ename": "ValueError",
                        "evalue": "bad value",
                        "traceback": ["Traceback line"],
                    },
                ],
            },
            {
                "cell_type": "raw",
                "source": "raw notes",
            },
        ],
    )

    parsed = parse_notebook(notebook_path)

    assert parsed.path == notebook_path
    assert parsed.metadata["kernelspec"]["name"] == "python3"
    assert [cell.index for cell in parsed.cells] == [0, 1, 2]
    assert [cell.cell_type for cell in parsed.cells] == ["markdown", "code", "raw"]
    assert parsed.cells[0].source == "# Lab 7\nIntro\n## First agent\n"
    assert parsed.cells[0].normalized_source == "# Lab 7\nIntro\n## First agent"
    assert parsed.cells[0].headings == ["Lab 7", "First agent"]

    code_cell = parsed.cells[1]
    assert code_cell.execution_count == 1
    assert code_cell.source == "print('hello')\n"
    assert len(code_cell.outputs) == 3
    assert code_cell.outputs[0].text == "hello\n"
    assert "{'score': 1}\n" in code_cell.output_text
    assert "ValueError: bad value" in code_cell.output_text
    assert len(code_cell.errors) == 1
    assert code_cell.errors[0].ename == "ValueError"
    assert code_cell.errors[0].traceback == ["Traceback line"]


def test_parse_notebook_extracts_display_data_and_unknown_outputs(tmp_path: Path) -> None:
    notebook_path = tmp_path / "display.ipynb"
    write_notebook(
        notebook_path,
        [
            {
                "cell_type": "code",
                "source": "display(data)",
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {
                            "text/html": ["<table>", "</table>"],
                        },
                        "metadata": {},
                    },
                    {
                        "output_type": "custom_output",
                        "text": ["custom text"],
                        "extra": {"kept": True},
                    },
                ],
            }
        ],
    )

    parsed = parse_notebook(notebook_path)

    code_cell = parsed.cells[0]
    assert code_cell.output_text == "<table></table>custom text"
    assert code_cell.outputs[0].data == {"text/html": ["<table>", "</table>"]}
    assert code_cell.outputs[1].raw["extra"] == {"kept": True}


def test_parse_notebook_defaults_missing_source_and_outputs(tmp_path: Path) -> None:
    notebook_path = tmp_path / "minimal.ipynb"
    write_notebook(
        notebook_path,
        [
            {
                "cell_type": "code",
                "execution_count": None,
            },
            {
                "cell_type": "unexpected",
                "source": None,
            },
        ],
    )

    parsed = parse_notebook(notebook_path)

    assert parsed.cells[0].source == ""
    assert parsed.cells[0].outputs == []
    assert parsed.cells[0].output_text == ""
    assert parsed.cells[1].cell_type == "raw"


def test_parse_notebook_rejects_invalid_json(tmp_path: Path) -> None:
    notebook_path = tmp_path / "invalid.ipynb"
    notebook_path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid notebook JSON"):
        parse_notebook(notebook_path)


def test_parse_notebook_rejects_missing_cells(tmp_path: Path) -> None:
    notebook_path = tmp_path / "missing_cells.ipynb"
    notebook_path.write_text(json.dumps({"metadata": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing top-level cells list"):
        parse_notebook(notebook_path)

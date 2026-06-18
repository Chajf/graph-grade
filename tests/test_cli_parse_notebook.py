import json
from pathlib import Path

from app.main import main


def write_notebook(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "source": "# Lab 7\n",
                    },
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "source": [
                            "class AgentFactory:\n",
                            "    pass\n",
                            "def build_agent():\n",
                            "    return AgentFactory()\n",
                        ],
                        "outputs": [
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": "created\n",
                            },
                            {
                                "output_type": "error",
                                "ename": "ValueError",
                                "evalue": "bad value",
                                "traceback": [],
                            },
                        ],
                    },
                    {
                        "cell_type": "raw",
                        "source": "notes",
                    },
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_parse_notebook_outputs_summary(tmp_path: Path, capsys) -> None:
    notebook_path = tmp_path / "lab7_example.ipynb"
    write_notebook(notebook_path)

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
        "total_cells": 3,
        "code_cell_count": 1,
        "markdown_cell_count": 1,
        "raw_cell_count": 1,
        "output_count": 2,
        "error_count": 1,
        "functions": ["build_agent"],
        "classes": ["AgentFactory"],
    }

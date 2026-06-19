from __future__ import annotations

from app.graphs.state import GradingGraphState
from app.services.notebook_parser import parse_notebook


def notebook_parser(state: GradingGraphState) -> dict[str, object]:
    notebook_path = state["submission"].notebook_path
    if notebook_path is None:
        raise ValueError("Notebook path is required before parsing.")

    return {"parsed_notebook": parse_notebook(notebook_path)}

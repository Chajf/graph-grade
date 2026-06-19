from __future__ import annotations

from app.graphs.state import GradingGraphState
from app.services.notebook_splitter import split_notebook_by_lab_spec


def section_splitter(state: GradingGraphState) -> dict[str, object]:
    parsed_notebook = state.get("parsed_notebook")
    if parsed_notebook is None:
        raise ValueError("Parsed notebook is required before section splitting.")

    return {"sections": split_notebook_by_lab_spec(parsed_notebook, state["lab_spec"])}

from __future__ import annotations

from app.graphs.state import GradingGraphState
from app.services.evidence import build_evidence_index


def evidence_builder(state: GradingGraphState) -> dict[str, object]:
    parsed_notebook = state.get("parsed_notebook")
    if parsed_notebook is None:
        raise ValueError("Parsed notebook is required before evidence building.")

    return {"evidence_index": build_evidence_index(parsed_notebook)}

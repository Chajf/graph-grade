from __future__ import annotations

from app.graphs.state import BatchGraphState
from app.repositories import GradingSpecRepository


def lab_spec_loader(state: BatchGraphState) -> dict[str, object]:
    lab_spec = GradingSpecRepository(state["specs_root"]).load_lab_spec(state["lab_id"])
    return {
        "lab_spec": lab_spec,
        "batch_errors": [],
    }

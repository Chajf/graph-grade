from __future__ import annotations

from app.graphs.state import LaboratoryGraphState
from app.repositories import write_group_summary


def group_summary_writer(state: LaboratoryGraphState) -> dict[str, object]:
    csv_path, md_path = write_group_summary(
        output_root=state["output_root"],
        lab_id=state["lab_id"],
        group_id=state["group_id"],
        submissions=state.get("submissions", []),
        final_grades=state.get("final_grades", []),
        laboratory_errors=state.get("laboratory_errors", []),
    )
    return {
        "summary_csv_path": csv_path,
        "summary_md_path": md_path,
    }

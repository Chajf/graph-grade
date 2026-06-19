from __future__ import annotations

from app.graphs.section_graph import create_section_graph
from app.graphs.state import SectionGradingPayload
from app.nodes.section_loader import initialize_section_state


def section_grading(payload: SectionGradingPayload) -> dict[str, object]:
    state = initialize_section_state(
        payload["part_spec"],
        payload["section"],
        payload["evidence_index"],
        lab_id=payload["lab_id"],
    )

    if "code_judge" in payload:
        state["code_judge"] = payload["code_judge"]
    if "markdown_judge" in payload:
        state["markdown_judge"] = payload["markdown_judge"]

    final_state = create_section_graph().invoke(state)
    return {"section_grades": [final_state["section_grade"]]}

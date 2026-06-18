from __future__ import annotations

from app.graphs.state import SectionGraphState
from app.models import EvidenceIndex, PartSpec, SectionEvidence


def initialize_section_state(
    part_spec: PartSpec,
    section: SectionEvidence,
    evidence_index: EvidenceIndex,
    lab_id: str | None = None,
) -> SectionGraphState:
    state: SectionGraphState = {
        "part_spec": part_spec,
        "section": section,
        "evidence_index": evidence_index,
    }
    if lab_id is not None:
        state["lab_id"] = lab_id
    return state


def section_loader(state: SectionGraphState) -> SectionGraphState:
    return {
        **state,
        "code_grades": state.get("code_grades", []),
        "markdown_grades": state.get("markdown_grades", []),
        "result_grades": state.get("result_grades", []),
    }

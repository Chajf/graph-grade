from __future__ import annotations

from typing import NotRequired, TypedDict

from app.models import EvidenceIndex, PartSpec, RequirementGrade, SectionEvidence, SectionGrade


class SectionGraphState(TypedDict):
    lab_id: NotRequired[str]
    part_spec: PartSpec
    section: SectionEvidence
    evidence_index: EvidenceIndex
    evidence: NotRequired[SectionEvidence]
    global_evidence: NotRequired[EvidenceIndex]
    code_grades: NotRequired[list[RequirementGrade]]
    markdown_grades: NotRequired[list[RequirementGrade]]
    result_grades: NotRequired[list[RequirementGrade]]
    section_grade: NotRequired[SectionGrade]

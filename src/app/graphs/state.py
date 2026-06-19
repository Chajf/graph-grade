from __future__ import annotations

import operator
from pathlib import Path
from typing import Annotated, NotRequired, TypedDict

from app.models import (
    EvidenceIndex,
    FinalGrade,
    LabSpec,
    ParsedNotebook,
    PartSpec,
    RequirementGrade,
    SectionEvidence,
    SectionGrade,
    SharePointStudentSubmission,
)
from app.services.llms import CodeJudgeProtocol, MarkdownJudgeProtocol


class SectionGraphState(TypedDict):
    lab_id: NotRequired[str]
    part_spec: PartSpec
    section: SectionEvidence
    evidence_index: EvidenceIndex
    evidence: NotRequired[SectionEvidence]
    global_evidence: NotRequired[EvidenceIndex]
    code_judge: NotRequired[CodeJudgeProtocol]
    markdown_judge: NotRequired[MarkdownJudgeProtocol]
    code_grades: NotRequired[list[RequirementGrade]]
    markdown_grades: NotRequired[list[RequirementGrade]]
    result_grades: NotRequired[list[RequirementGrade]]
    section_grade: NotRequired[SectionGrade]


class SectionGradingPayload(TypedDict):
    lab_id: str
    part_spec: PartSpec
    section: SectionEvidence
    evidence_index: EvidenceIndex
    code_judge: NotRequired[CodeJudgeProtocol]
    markdown_judge: NotRequired[MarkdownJudgeProtocol]
    section_grades: Annotated[list[SectionGrade], operator.add]


class GradingGraphState(TypedDict):
    lab_spec: LabSpec
    submission: SharePointStudentSubmission
    output_root: Path
    parsed_notebook: NotRequired[ParsedNotebook]
    sections: NotRequired[list[SectionEvidence]]
    evidence_index: NotRequired[EvidenceIndex]
    code_judge: NotRequired[CodeJudgeProtocol]
    markdown_judge: NotRequired[MarkdownJudgeProtocol]
    section_grades: Annotated[list[SectionGrade], operator.add]
    flags: NotRequired[list[str]]
    final_grade: NotRequired[FinalGrade]
    lab_output_dir: NotRequired[Path]
    lab_grade_path: NotRequired[Path]
    lab_feedback_path: NotRequired[Path]
    student_summary_path: NotRequired[Path]

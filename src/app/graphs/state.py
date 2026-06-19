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
    section_grades: NotRequired[Annotated[list[SectionGrade], operator.add]]


class SectionGraphOutput(TypedDict):
    section_grade: SectionGrade
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
    section_grades: NotRequired[Annotated[list[SectionGrade], operator.add]]
    flags: NotRequired[list[str]]
    final_grade: NotRequired[FinalGrade]
    final_grades: NotRequired[Annotated[list[FinalGrade], operator.add]]
    lab_output_dir: NotRequired[Path]
    lab_grade_path: NotRequired[Path]
    lab_feedback_path: NotRequired[Path]
    student_summary_path: NotRequired[Path]


class GradingGraphOutput(TypedDict):
    final_grade: FinalGrade
    final_grades: Annotated[list[FinalGrade], operator.add]
    lab_output_dir: Path
    lab_grade_path: Path
    lab_feedback_path: Path
    student_summary_path: Path


class LaboratoryGraphState(TypedDict):
    prace_root: Path
    specs_root: Path
    output_root: Path
    lab_id: str
    group_id: str
    lab_spec: NotRequired[LabSpec]
    submissions: NotRequired[list[SharePointStudentSubmission]]
    final_grades: NotRequired[Annotated[list[FinalGrade], operator.add]]
    laboratory_errors: NotRequired[Annotated[list[str], operator.add]]
    summary_csv_path: NotRequired[Path]
    summary_md_path: NotRequired[Path]

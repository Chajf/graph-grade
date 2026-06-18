from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.evidence import CheckResult, CodeMarkerFinding, EvidenceIndex
from app.models.grades import GradeConfidence, GradeStatus, RequirementGrade
from app.models.notebooks import NotebookCell
from app.models.specs import RequirementSpec


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points_awarded: float = Field(ge=0)
    status: GradeStatus
    evidence_cells: list[int] = Field(default_factory=list)
    reasoning: str
    comment: str
    confidence: GradeConfidence
    flags: list[str] = Field(default_factory=list)


class CodeJudgeResult(JudgeResult):
    pass


class MarkdownJudgeResult(JudgeResult):
    pass


class CodeJudgeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lab_id: str
    part_id: str
    part_title: str
    requirement: RequirementSpec
    deterministic_grade: RequirementGrade
    marker_findings: list[CodeMarkerFinding] = Field(default_factory=list)
    code_cells: list[NotebookCell] = Field(default_factory=list)
    evidence_index: EvidenceIndex


class MarkdownJudgeContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lab_id: str
    part_id: str
    part_title: str
    requirement: RequirementSpec
    deterministic_grade: RequirementGrade
    deterministic_check: CheckResult
    markdown_cells: list[NotebookCell] = Field(default_factory=list)

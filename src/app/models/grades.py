from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


GradeBucket = Literal["code", "markdown", "results"]
GradeConfidence = Literal["high", "medium", "low"]
GradeStatus = Literal["full", "partial", "minimal", "missing", "failed"]
FinalGradeStatus = Literal["graded", "failed", "skipped"]


class RequirementGrade(BaseModel):
    requirement_id: str
    bucket: GradeBucket
    points_awarded: float
    points_possible: float
    status: GradeStatus
    evidence_cells: list[int] = Field(default_factory=list)
    comment: str = ""
    confidence: GradeConfidence = "high"


class SectionGrade(BaseModel):
    part_id: str
    title: str
    points_awarded: float
    points_possible: float
    requirement_grades: list[RequirementGrade] = Field(default_factory=list)
    summary: str = ""


class FinalGrade(BaseModel):
    lab_id: str
    group_id: str
    student_folder: str
    notebook_path: str
    points_awarded: float
    points_possible: float
    section_grades: list[SectionGrade] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    status: FinalGradeStatus = "graded"
    summary: str = ""

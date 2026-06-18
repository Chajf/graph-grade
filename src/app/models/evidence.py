from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.notebooks import NotebookCell, NotebookError


MappingConfidence = Literal["high", "medium", "low"]
SecretConfidence = Literal["high", "medium", "low"]
CheckSeverity = Literal["info", "warning", "critical"]


class CodeMarkerFinding(BaseModel):
    marker: str
    matched: bool
    kind: str
    evidence_cells: list[int] = Field(default_factory=list)
    comment: str = ""


class ApiScoreEvidence(BaseModel):
    cell_index: int
    score: float | int | None = None
    max_score: float | int | None = None
    details: dict | list | str | int | float | bool | None = None
    raw_text: str = ""


class SecretFinding(BaseModel):
    cell_index: int
    kind: str
    snippet: str
    confidence: SecretConfidence


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    evidence_cells: list[int] = Field(default_factory=list)
    comment: str = ""
    severity: CheckSeverity = "info"


class EvidenceIndex(BaseModel):
    functions: dict[str, list[int]] = Field(default_factory=dict)
    classes: dict[str, list[int]] = Field(default_factory=dict)
    imports: dict[str, list[int]] = Field(default_factory=dict)
    calls: dict[str, list[int]] = Field(default_factory=dict)
    errors: list[NotebookError] = Field(default_factory=list)
    api_scores: list[ApiScoreEvidence] = Field(default_factory=list)
    possible_secrets: list[SecretFinding] = Field(default_factory=list)


class SectionEvidence(BaseModel):
    part_id: str
    title: str
    start_heading: str
    end_heading: str | None = None
    mapping_confidence: MappingConfidence
    cells: list[NotebookCell] = Field(default_factory=list)
    code_cells: list[NotebookCell] = Field(default_factory=list)
    markdown_cells: list[NotebookCell] = Field(default_factory=list)
    output_text: str = ""
    errors: list[NotebookError] = Field(default_factory=list)
    missing_start_heading: bool = False
    missing_end_heading: bool = False

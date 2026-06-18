from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


Applicability = Literal["required", "optional", "not_applicable"]


class RequirementEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    cell_markers: list[str] = Field(default_factory=list)
    heading_or_text: str | None = None


class RequirementSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    description: str
    points: float
    evidence: RequirementEvidence = Field(default_factory=RequirementEvidence)
    expected_outputs: list[str] = Field(default_factory=list)
    quality_criteria: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)


class CellRangeSpec(BaseModel):
    start_heading: str
    end_heading: str | None = None


class PartSpec(BaseModel):
    part_id: str
    title: str
    source_heading: str
    cell_range: CellRangeSpec
    code_requirements: list[RequirementSpec] = Field(default_factory=list)
    markdown_requirements: list[RequirementSpec] = Field(default_factory=list)
    result_requirements: list[RequirementSpec] = Field(default_factory=list)
    code_applicability: Applicability = "required"
    markdown_applicability: Applicability = "required"
    results_applicability: Applicability = "required"

    @computed_field
    @property
    def start_heading(self) -> str:
        return self.cell_range.start_heading

    @computed_field
    @property
    def end_heading(self) -> str | None:
        return self.cell_range.end_heading

    @computed_field
    @property
    def code_applicable(self) -> bool:
        return self.code_applicability != "not_applicable"

    @computed_field
    @property
    def markdown_applicable(self) -> bool:
        return self.markdown_applicability != "not_applicable"

    @computed_field
    @property
    def results_applicable(self) -> bool:
        return self.results_applicability != "not_applicable"


class LabSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    lab_id: str
    title: str
    language: str
    total_points: float
    expected_notebook_pattern: str
    required_files: list[str] = Field(default_factory=list)
    parts: list[PartSpec] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)

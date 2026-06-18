from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.models.notebooks import NotebookCell, NotebookError


MappingConfidence = Literal["high", "medium", "low"]


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

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


CellType = Literal["code", "markdown", "raw"]


class NotebookError(BaseModel):
    ename: str
    evalue: str
    traceback: list[str] = Field(default_factory=list)


class NotebookOutput(BaseModel):
    output_type: str
    name: str | None = None
    text: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: NotebookError | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class NotebookCell(BaseModel):
    index: int
    cell_type: CellType
    source: str
    normalized_source: str
    headings: list[str] = Field(default_factory=list)
    execution_count: int | None = None
    outputs: list[NotebookOutput] = Field(default_factory=list)
    output_text: str = ""
    errors: list[NotebookError] = Field(default_factory=list)
    code_features: Any | None = None


class ParsedNotebook(BaseModel):
    path: Path
    cells: list[NotebookCell] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

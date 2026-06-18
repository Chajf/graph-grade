from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


ResolutionStatus = Literal["resolved", "unresolved", "ambiguous"]


class NotebookResolutionIssue(BaseModel):
    code: str
    message: str
    candidates: list[Path] = Field(default_factory=list)


class SharePointStudentSubmission(BaseModel):
    submissions_root: Path
    group_id: str
    student_folder: str
    lab_id: str
    lab_folder: Path | None = None
    version_folder: Path | None = None
    notebook_path: Path | None = None
    required_files: list[Path] = Field(default_factory=list)
    missing_required_files: list[str] = Field(default_factory=list)
    status: ResolutionStatus = "unresolved"
    issue: NotebookResolutionIssue | None = None

    @property
    def resolved(self) -> bool:
        return self.status == "resolved" and self.notebook_path is not None

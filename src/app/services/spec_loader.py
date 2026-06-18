from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models import LabSpec, PartSpec


def build_lab_spec(notebook_data: Mapping[str, Any], part_data: list[Mapping[str, Any]]) -> LabSpec:
    expected_submission = notebook_data.get("expected_submission") or {}
    grading = notebook_data.get("grading") or {}

    return LabSpec(
        lab_id=str(notebook_data["lab_id"]),
        title=str(notebook_data["title"]),
        language=str(notebook_data["language"]),
        total_points=float(grading["total_points"]),
        expected_notebook_pattern=str(expected_submission["notebook_pattern"]),
        required_files=list(expected_submission.get("required_files") or []),
        parts=[build_part_spec(part) for part in part_data],
        source=dict(notebook_data),
    )


def build_part_spec(part_data: Mapping[str, Any]) -> PartSpec:
    requirements = part_data.get("requirements") or {}

    return PartSpec(
        part_id=str(part_data["part_id"]),
        title=str(part_data["title"]),
        source_heading=str(part_data["source_heading"]),
        cell_range=part_data["cell_range"],
        code_requirements=list(requirements.get("code") or []),
        markdown_requirements=list(requirements.get("markdown") or []),
        result_requirements=list(requirements.get("results") or []),
        code_applicability=str(requirements.get("code_applicability", "required")),
        markdown_applicability=str(requirements.get("markdown_applicability", "required")),
        results_applicability=str(requirements.get("results_applicability", "required")),
    )

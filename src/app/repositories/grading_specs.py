from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import LabSpec
from app.services.spec_loader import build_lab_spec


class GradingSpecRepository:
    def __init__(self, specs_root: Path | str) -> None:
        self.specs_root = Path(specs_root)

    def load_lab_spec(self, lab_id: str) -> LabSpec:
        lab_dir = self.specs_root / "labs" / lab_id
        notebook_path = lab_dir / "notebook.yaml"
        notebook_data = _read_yaml_mapping(notebook_path)

        grading = notebook_data.get("grading") or {}
        parts_dir = lab_dir / str(grading.get("parts_dir", "parts"))
        part_files = grading.get("part_files") or []

        part_data = [_read_yaml_mapping(parts_dir / str(part_file)) for part_file in part_files]
        return build_lab_spec(notebook_data, part_data)


def load_lab_spec(specs_root: Path | str, lab_id: str) -> LabSpec:
    return GradingSpecRepository(specs_root).load_lab_spec(lab_id)


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Grading spec file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in grading spec file: {path}")

    return data

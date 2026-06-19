import operator
from pathlib import Path
from typing import get_args, get_type_hints

import pytest

from app.graphs.state import BatchGraphState, BatchStudentGradingPayload
from app.models import CellRangeSpec, LabSpec, PartSpec, RequirementSpec
from app.nodes.lab_spec_loader import lab_spec_loader
from app.nodes.lab_spec_validator import lab_spec_validator, validate_lab_spec


def test_batch_state_has_reducer_fields() -> None:
    batch_hints = get_type_hints(BatchGraphState, include_extras=True)
    payload_hints = get_type_hints(BatchStudentGradingPayload, include_extras=True)

    assert _reducer_for(batch_hints["final_grades"]) is operator.add
    assert _reducer_for(batch_hints["batch_errors"]) is operator.add
    assert _reducer_for(payload_hints["final_grades"]) is operator.add
    assert _reducer_for(payload_hints["batch_errors"]) is operator.add


def test_lab_spec_loader_loads_spec_and_initializes_errors(tmp_path: Path) -> None:
    specs_root = tmp_path / "grading_specs"
    write_spec(specs_root)

    result = lab_spec_loader(
        {
            "prace_root": tmp_path / "prace",
            "specs_root": specs_root,
            "output_root": tmp_path / "grading_results",
            "lab_id": "lab7",
            "group_id": "lab1",
        }
    )

    lab_spec = result["lab_spec"]
    assert isinstance(lab_spec, LabSpec)
    assert lab_spec.lab_id == "lab7"
    assert [part.part_id for part in lab_spec.parts] == ["01", "02"]
    assert result["batch_errors"] == []


def test_lab_spec_validator_accepts_valid_spec() -> None:
    result = lab_spec_validator({"lab_spec": build_lab_spec()})

    assert result == {}
    assert validate_lab_spec(build_lab_spec()) == []


def test_lab_spec_validator_rejects_total_points_mismatch() -> None:
    lab_spec = build_lab_spec(total_points=99)

    with pytest.raises(ValueError, match="points total 12 does not match lab total 99"):
        lab_spec_validator({"lab_spec": lab_spec})


def test_lab_spec_validator_rejects_duplicate_requirement_ids() -> None:
    lab_spec = build_lab_spec(duplicate_requirement_id=True)

    with pytest.raises(ValueError, match="duplicate requirement id: code_schema"):
        lab_spec_validator({"lab_spec": lab_spec})


def test_lab_spec_validator_rejects_invalid_requirement_fields() -> None:
    lab_spec = build_lab_spec(invalid_requirement=True)

    with pytest.raises(ValueError) as exc_info:
        lab_spec_validator({"lab_spec": lab_spec})

    message = str(exc_info.value)
    assert "empty id" in message
    assert "empty description" in message
    assert "negative points" in message


def test_lab_spec_validator_rejects_duplicate_and_empty_part_ids() -> None:
    duplicate_part_spec = build_lab_spec(duplicate_part_id=True)
    empty_part_spec = build_lab_spec(empty_part_id=True)

    with pytest.raises(ValueError, match="duplicate part_id: 01"):
        lab_spec_validator({"lab_spec": duplicate_part_spec})
    with pytest.raises(ValueError, match="empty part_id"):
        lab_spec_validator({"lab_spec": empty_part_spec})


def test_lab_spec_validator_requires_loaded_spec() -> None:
    with pytest.raises(ValueError, match="Lab spec is required"):
        lab_spec_validator({})


def build_lab_spec(
    *,
    total_points: float = 12,
    duplicate_requirement_id: bool = False,
    invalid_requirement: bool = False,
    duplicate_part_id: bool = False,
    empty_part_id: bool = False,
) -> LabSpec:
    first_requirement = RequirementSpec(
        id="" if invalid_requirement else "code_schema",
        description="" if invalid_requirement else "Defines supplier schema.",
        points=-1 if invalid_requirement else 4,
    )
    second_requirement_id = "code_schema" if duplicate_requirement_id else "reflection"
    first_part_id = "" if empty_part_id else "01"
    second_part_id = "01" if duplicate_part_id else "02"

    return LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=total_points,
        expected_notebook_pattern="lab7_*.ipynb",
        parts=[
            PartSpec(
                part_id=first_part_id,
                title="Schema",
                source_heading="## Part 1",
                cell_range=CellRangeSpec(start_heading="## Part 1", end_heading="## Part 2"),
                code_requirements=[first_requirement],
            ),
            PartSpec(
                part_id=second_part_id,
                title="Reflection",
                source_heading="## Part 2",
                cell_range=CellRangeSpec(start_heading="## Part 2"),
                markdown_requirements=[
                    RequirementSpec(
                        id=second_requirement_id,
                        description="Explains parsing risk.",
                        points=8,
                    )
                ],
            ),
        ],
    )


def write_spec(specs_root: Path) -> None:
    lab_dir = specs_root / "labs" / "lab7"
    parts_dir = lab_dir / "parts"
    parts_dir.mkdir(parents=True)
    (lab_dir / "notebook.yaml").write_text(
        """
lab_id: "lab7"
title: "Lab 7"
language: "pl"
expected_submission:
  notebook_pattern: "lab7_*.ipynb"
  required_files: []
grading:
  total_points: 12
  parts_dir: "parts"
  part_files:
    - "01_schema.yaml"
    - "02_reflection.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_schema.yaml").write_text(
        """
part_id: "01"
title: "Schema"
source_heading: "## Part 1"
cell_range:
  start_heading: "## Part 1"
  end_heading: "## Part 2"
requirements:
  code:
    - id: "code_schema"
      description: "Defines supplier schema."
      points: 4
  markdown: []
  results: []
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_reflection.yaml").write_text(
        """
part_id: "02"
title: "Reflection"
source_heading: "## Part 2"
cell_range:
  start_heading: "## Part 2"
  end_heading: null
requirements:
  code: []
  markdown:
    - id: "reflection"
      description: "Explains parsing risk."
      points: 8
  results: []
""".lstrip(),
        encoding="utf-8",
    )


def _reducer_for(type_hint: object) -> object:
    annotated_hint = get_args(type_hint)[0]
    return get_args(annotated_hint)[1]

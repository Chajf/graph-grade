from __future__ import annotations

from collections.abc import Iterable
from math import isclose

from app.graphs.state import BatchGraphState
from app.models import LabSpec, PartSpec, RequirementSpec


def lab_spec_validator(state: BatchGraphState) -> dict[str, object]:
    lab_spec = state.get("lab_spec")
    if lab_spec is None:
        raise ValueError("Lab spec is required before validation.")

    errors = validate_lab_spec(lab_spec)
    if errors:
        raise ValueError("Invalid lab spec: " + "; ".join(errors))

    return {}


def validate_lab_spec(lab_spec: LabSpec) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_parts(lab_spec.parts))
    errors.extend(_validate_requirements(lab_spec.parts))

    total_points = sum(requirement.points for part in lab_spec.parts for requirement in _part_requirements(part))
    if not isclose(total_points, lab_spec.total_points):
        errors.append(
            f"requirement points total {total_points:g} does not match lab total {lab_spec.total_points:g}"
        )

    return errors


def _validate_parts(parts: list[PartSpec]) -> list[str]:
    errors: list[str] = []
    seen_part_ids: set[str] = set()

    for index, part in enumerate(parts, start=1):
        if not part.part_id.strip():
            errors.append(f"part at position {index} has an empty part_id")
            continue
        if part.part_id in seen_part_ids:
            errors.append(f"duplicate part_id: {part.part_id}")
        seen_part_ids.add(part.part_id)

    return errors


def _validate_requirements(parts: list[PartSpec]) -> list[str]:
    errors: list[str] = []
    seen_requirement_ids: set[str] = set()

    for part in parts:
        for requirement in _part_requirements(part):
            context = f"part {part.part_id or '<empty>'}"
            if not requirement.id.strip():
                errors.append(f"{context} has a requirement with an empty id")
            elif requirement.id in seen_requirement_ids:
                errors.append(f"duplicate requirement id: {requirement.id}")
            else:
                seen_requirement_ids.add(requirement.id)

            if not requirement.description.strip():
                errors.append(f"requirement {requirement.id or '<empty>'} has an empty description")
            if requirement.points < 0:
                errors.append(f"requirement {requirement.id or '<empty>'} has negative points")

    return errors


def _part_requirements(part: PartSpec) -> Iterable[RequirementSpec]:
    yield from part.code_requirements
    yield from part.markdown_requirements
    yield from part.result_requirements

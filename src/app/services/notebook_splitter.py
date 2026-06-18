from __future__ import annotations

import re

from app.models import LabSpec, NotebookCell, ParsedNotebook, PartSpec, SectionEvidence


HEADING_PREFIX_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
TRAILING_HEADING_RE = re.compile(r"\s+#+\s*$")
WHITESPACE_RE = re.compile(r"\s+")


def split_notebook_by_lab_spec(
    notebook: ParsedNotebook,
    lab_spec: LabSpec,
) -> list[SectionEvidence]:
    return split_notebook_by_parts(notebook, lab_spec.parts)


def split_notebook_by_parts(
    notebook: ParsedNotebook,
    parts: list[PartSpec],
) -> list[SectionEvidence]:
    return [_split_part(notebook, part) for part in parts]


def _split_part(notebook: ParsedNotebook, part: PartSpec) -> SectionEvidence:
    start_index = _find_heading_cell_index(
        cells=notebook.cells,
        heading=part.start_heading,
        start_at=0,
    )

    if start_index is None:
        return _build_section_evidence(
            part=part,
            cells=[],
            mapping_confidence="low",
            missing_start_heading=True,
        )

    end_index: int | None = None
    missing_end_heading = False

    if part.end_heading is not None:
        end_index = _find_heading_cell_index(
            cells=notebook.cells,
            heading=part.end_heading,
            start_at=start_index + 1,
        )
        missing_end_heading = end_index is None

    section_cells = notebook.cells[start_index:end_index]
    mapping_confidence = "medium" if missing_end_heading else "high"

    return _build_section_evidence(
        part=part,
        cells=section_cells,
        mapping_confidence=mapping_confidence,
        missing_end_heading=missing_end_heading,
    )


def _find_heading_cell_index(
    cells: list[NotebookCell],
    heading: str,
    start_at: int,
) -> int | None:
    expected_heading = _normalize_heading(heading)
    if not expected_heading:
        return None

    for index, cell in enumerate(cells[start_at:], start=start_at):
        if cell.cell_type != "markdown":
            continue
        normalized_headings = [_normalize_heading(cell_heading) for cell_heading in cell.headings]
        if expected_heading in normalized_headings:
            return index

    return None


def _build_section_evidence(
    part: PartSpec,
    cells: list[NotebookCell],
    mapping_confidence: str,
    missing_start_heading: bool = False,
    missing_end_heading: bool = False,
) -> SectionEvidence:
    code_cells = [cell for cell in cells if cell.cell_type == "code"]
    markdown_cells = [cell for cell in cells if cell.cell_type == "markdown"]

    return SectionEvidence(
        part_id=part.part_id,
        title=part.title,
        start_heading=part.start_heading,
        end_heading=part.end_heading,
        mapping_confidence=mapping_confidence,
        cells=cells,
        code_cells=code_cells,
        markdown_cells=markdown_cells,
        output_text="".join(cell.output_text for cell in code_cells),
        errors=[error for cell in code_cells for error in cell.errors],
        missing_start_heading=missing_start_heading,
        missing_end_heading=missing_end_heading,
    )


def _normalize_heading(heading: str) -> str:
    normalized = HEADING_PREFIX_RE.sub("", heading)
    normalized = TRAILING_HEADING_RE.sub("", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip().lower()

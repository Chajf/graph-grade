from pathlib import Path

from app.models import (
    CellRangeSpec,
    LabSpec,
    NotebookCell,
    NotebookError,
    PartSpec,
    ParsedNotebook,
)
from app.services.notebook_splitter import (
    split_notebook_by_lab_spec,
    split_notebook_by_parts,
)


def test_split_notebook_by_parts_maps_clean_section_boundaries() -> None:
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            markdown_cell(0, "## First agent", ["First agent"]),
            code_cell(1, "create_agent()", output_text="agent output\n"),
            markdown_cell(2, "## Tools", ["Tools"]),
            code_cell(3, "parse_supplier_offer()", output_text="tools output\n"),
        ],
    )

    sections = split_notebook_by_parts(
        notebook,
        [
            part("01", "First agent", "## First agent", "## Tools"),
            part("02", "Tools", "## Tools", None),
        ],
    )

    assert [section.part_id for section in sections] == ["01", "02"]
    assert [cell.index for cell in sections[0].cells] == [0, 1]
    assert [cell.index for cell in sections[1].cells] == [2, 3]
    assert sections[0].code_cells == [notebook.cells[1]]
    assert sections[0].markdown_cells == [notebook.cells[0]]
    assert sections[0].output_text == "agent output\n"
    assert sections[0].mapping_confidence == "high"
    assert sections[1].mapping_confidence == "high"


def test_split_notebook_by_lab_spec_maps_last_section_without_end_heading() -> None:
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            markdown_cell(0, "## Tools", ["Tools"]),
            code_cell(1, "parse_supplier_offer()", output_text="parsed\n"),
            markdown_cell(2, "notes", []),
        ],
    )
    lab_spec = LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        parts=[part("02", "Tools", "## Tools", None)],
    )

    sections = split_notebook_by_lab_spec(notebook, lab_spec)

    assert len(sections) == 1
    assert [cell.index for cell in sections[0].cells] == [0, 1, 2]
    assert sections[0].mapping_confidence == "high"
    assert sections[0].missing_end_heading is False


def test_split_notebook_by_parts_returns_low_confidence_empty_section_for_missing_start_heading() -> None:
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            markdown_cell(0, "## First agent", ["First agent"]),
            code_cell(1, "create_agent()", output_text="agent output\n"),
        ],
    )

    section = split_notebook_by_parts(
        notebook,
        [part("02", "Tools", "## Tools", None)],
    )[0]

    assert section.cells == []
    assert section.code_cells == []
    assert section.markdown_cells == []
    assert section.output_text == ""
    assert section.errors == []
    assert section.mapping_confidence == "low"
    assert section.missing_start_heading is True
    assert section.missing_end_heading is False


def test_split_notebook_by_parts_uses_medium_confidence_when_end_heading_is_missing() -> None:
    error = NotebookError(
        ename="ValueError",
        evalue="bad allocation",
        traceback=["ValueError: bad allocation"],
    )
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            markdown_cell(0, "## Tools", ["Tools"]),
            code_cell(
                1,
                "optimize_allocation_lp()",
                output_text="ValueError: bad allocation",
                errors=[error],
            ),
            markdown_cell(2, "final notes", []),
        ],
    )

    section = split_notebook_by_parts(
        notebook,
        [part("02", "Tools", "## Tools", "## Structured output")],
    )[0]

    assert [cell.index for cell in section.cells] == [0, 1, 2]
    assert section.output_text == "ValueError: bad allocation"
    assert section.errors == [error]
    assert section.mapping_confidence == "medium"
    assert section.missing_start_heading is False
    assert section.missing_end_heading is True


def test_split_notebook_by_parts_matches_spec_hash_headings_to_parsed_heading_text() -> None:
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            markdown_cell(
                0,
                "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP",
                ["Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP"],
            ),
            code_cell(1, "class SupplierOffer: ...", output_text="supplier output\n"),
            markdown_cell(
                2,
                "## Część 3 – Structured Output z `ProviderStrategy`",
                ["Część 3 – Structured Output z `ProviderStrategy`"],
            ),
        ],
    )

    section = split_notebook_by_parts(
        notebook,
        [
            part(
                "02",
                "Tools",
                "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP",
                "## Część 3 – Structured Output z `ProviderStrategy`",
            )
        ],
    )[0]

    assert [cell.index for cell in section.cells] == [0, 1]
    assert section.code_cells == [notebook.cells[1]]
    assert section.output_text == "supplier output\n"
    assert section.mapping_confidence == "high"


def markdown_cell(index: int, source: str, headings: list[str]) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="markdown",
        source=source,
        normalized_source=source,
        headings=headings,
    )


def code_cell(
    index: int,
    source: str,
    output_text: str = "",
    errors: list[NotebookError] | None = None,
) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="code",
        source=source,
        normalized_source=source,
        output_text=output_text,
        errors=errors or [],
    )


def part(
    part_id: str,
    title: str,
    start_heading: str,
    end_heading: str | None,
) -> PartSpec:
    return PartSpec(
        part_id=part_id,
        title=title,
        source_heading=start_heading,
        cell_range=CellRangeSpec(
            start_heading=start_heading,
            end_heading=end_heading,
        ),
        code_requirements=[],
        markdown_requirements=[],
        result_requirements=[],
    )

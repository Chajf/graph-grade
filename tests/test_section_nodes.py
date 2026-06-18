from pathlib import Path

from app.models import (
    CellRangeSpec,
    NotebookCell,
    NotebookOutput,
    PartSpec,
    ParsedNotebook,
    RequirementEvidence,
    RequirementSpec,
)
from app.nodes.code_grader import grade_code_requirements
from app.nodes.markdown_grader import grade_markdown_requirements
from app.nodes.results_grader import grade_result_requirements
from app.nodes.section_synthesizer import synthesize_section_grade
from app.services.code_features import extract_code_features
from app.services.evidence import build_evidence_index
from app.services.notebook_splitter import split_notebook_by_parts


def test_grade_code_requirements_awards_full_points_for_all_markers() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Tools"),
            code_cell(
                1,
                "class SupplierOffer:\n"
                "    pass\n\n"
                "def parse_supplier_offer(raw_offer):\n"
                "    return raw_offer\n",
            ),
        ]
    )
    part = part_with_requirements(
        code_requirements=[
            RequirementSpec(
                id="code_schema",
                description="Defines schema and parser.",
                points=4,
                evidence=RequirementEvidence(
                    cell_markers=["class SupplierOffer", "def parse_supplier_offer"]
                ),
            )
        ]
    )

    result = grade_code_requirements(state(part, section))

    assert result["code_grades"][0].points_awarded == 4
    assert result["code_grades"][0].status == "full"
    assert result["code_grades"][0].evidence_cells == [1]


def test_grade_code_requirements_awards_partial_points_for_some_markers() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Tools"),
            code_cell(1, "class SupplierOffer:\n    pass\n"),
        ]
    )
    part = part_with_requirements(
        code_requirements=[
            RequirementSpec(
                id="code_schema",
                description="Defines schema and parser.",
                points=4,
                evidence=RequirementEvidence(
                    cell_markers=["class SupplierOffer", "def parse_supplier_offer"]
                ),
            )
        ]
    )

    result = grade_code_requirements(state(part, section))

    assert result["code_grades"][0].points_awarded == 2
    assert result["code_grades"][0].status == "partial"
    assert "def parse_supplier_offer" in result["code_grades"][0].comment


def test_grade_code_requirements_marks_missing_without_markers() -> None:
    section = section_with_cells([markdown_cell(0, "## Tools"), code_cell(1, "x = 1")])
    part = part_with_requirements(
        code_requirements=[
            RequirementSpec(
                id="code_schema",
                description="Defines schema.",
                points=4,
                evidence=RequirementEvidence(cell_markers=["class SupplierOffer"]),
            )
        ]
    )

    result = grade_code_requirements(state(part, section))

    assert result["code_grades"][0].points_awarded == 0
    assert result["code_grades"][0].status == "missing"


def test_grade_markdown_requirements_awards_points_for_non_placeholder_text() -> None:
    section = section_with_cells(
        [
            markdown_cell(
                0,
                "## Tools\n"
                "Wymagany komentarz - Część 2\n"
                "The parser can fail when supplier data is incomplete, which changes allocation risk.",
            )
        ]
    )
    part = part_with_requirements(
        markdown_requirements=[
            RequirementSpec(
                id="tools_reflection",
                description="Explains tool risks.",
                points=8,
                evidence=RequirementEvidence(heading_or_text="Wymagany komentarz - Część 2"),
            )
        ]
    )

    result = grade_markdown_requirements(state(part, section))

    assert result["markdown_grades"][0].points_awarded == 8
    assert result["markdown_grades"][0].status == "full"
    assert result["markdown_grades"][0].evidence_cells == [0]


def test_grade_markdown_requirements_rejects_placeholder_text() -> None:
    section = section_with_cells(
        [markdown_cell(0, "## Tools\nWymagany komentarz - Część 2\nTODO")]
    )
    part = part_with_requirements(
        markdown_requirements=[
            RequirementSpec(
                id="tools_reflection",
                description="Explains tool risks.",
                points=8,
                evidence=RequirementEvidence(heading_or_text="Wymagany komentarz - Część 2"),
            )
        ]
    )

    result = grade_markdown_requirements(state(part, section))

    assert result["markdown_grades"][0].points_awarded == 0
    assert result["markdown_grades"][0].status == "missing"


def test_grade_result_requirements_uses_deterministic_checks() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Tools"),
            code_cell(1, "print('ok')", execution_count=1, output_text="ok\n"),
        ]
    )
    part = part_with_requirements(
        result_requirements=[
            RequirementSpec(
                id="executed_cells",
                description="Cells execute cleanly.",
                points=0,
                checks=[
                    "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
                    "no_error_outputs_in_required_cells",
                ],
            )
        ]
    )

    result = grade_result_requirements(state(part, section))

    assert result["result_grades"][0].points_awarded == 0
    assert result["result_grades"][0].points_possible == 0
    assert result["result_grades"][0].status == "full"
    assert result["result_grades"][0].evidence_cells == [1]


def test_synthesize_section_grade_preserves_bucket_order_and_totals() -> None:
    section = section_with_cells(
        [
            markdown_cell(
                0,
                "## Tools\n"
                "Wymagany komentarz - Część 2\n"
                "The reflection links parser errors to business decisions.",
            ),
            code_cell(1, "class SupplierOffer:\n    pass\n", execution_count=1),
        ]
    )
    part = part_with_requirements(
        code_requirements=[
            RequirementSpec(
                id="code_schema",
                description="Defines schema.",
                points=4,
                evidence=RequirementEvidence(cell_markers=["class SupplierOffer"]),
            )
        ],
        markdown_requirements=[
            RequirementSpec(
                id="tools_reflection",
                description="Explains risks.",
                points=8,
                evidence=RequirementEvidence(heading_or_text="Wymagany komentarz - Część 2"),
            )
        ],
    )
    base_state = state(part, section)
    base_state.update(grade_code_requirements(base_state))
    base_state.update(grade_markdown_requirements(base_state))
    base_state.update(grade_result_requirements(base_state))

    result = synthesize_section_grade(base_state)

    section_grade = result["section_grade"]
    assert section_grade.part_id == "02"
    assert section_grade.points_awarded == 12
    assert section_grade.points_possible == 12
    assert [grade.requirement_id for grade in section_grade.requirement_grades] == [
        "code_schema",
        "tools_reflection",
    ]


def state(part: PartSpec, section):
    return {
        "part_spec": part,
        "section": section,
        "evidence_index": build_evidence_index(section),
    }


def section_with_cells(cells: list[NotebookCell]):
    notebook = ParsedNotebook(path=Path("/submissions/lab.ipynb"), cells=cells)
    return split_notebook_by_parts(
        notebook,
        [part_with_requirements(start_heading=cells[0].source.splitlines()[0])],
    )[0]


def markdown_cell(index: int, source: str) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="markdown",
        source=source,
        normalized_source=source,
        headings=[source.lstrip("# ").splitlines()[0]],
    )


def code_cell(
    index: int,
    source: str,
    output_text: str = "",
    outputs: list[NotebookOutput] | None = None,
    execution_count: int | None = None,
) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="code",
        source=source,
        normalized_source=source,
        execution_count=execution_count,
        outputs=outputs or [],
        output_text=output_text,
        code_features=extract_code_features(source),
    )


def part_with_requirements(
    start_heading: str = "## Tools",
    code_requirements: list[RequirementSpec] | None = None,
    markdown_requirements: list[RequirementSpec] | None = None,
    result_requirements: list[RequirementSpec] | None = None,
) -> PartSpec:
    return PartSpec(
        part_id="02",
        title="Tools",
        source_heading=start_heading,
        cell_range=CellRangeSpec(start_heading=start_heading),
        code_requirements=code_requirements or [],
        markdown_requirements=markdown_requirements or [],
        result_requirements=result_requirements or [],
    )

from pathlib import Path

from app.graphs.section_graph import (
    create_section_graph,
    route_to_grading_nodes,
)
from app.models import (
    CellRangeSpec,
    NotebookCell,
    PartSpec,
    ParsedNotebook,
    RequirementEvidence,
    RequirementSpec,
)
from app.nodes.section_loader import initialize_section_state
from app.services.code_features import extract_code_features
from app.services.evidence import build_evidence_index
from app.services.notebook_splitter import split_notebook_by_parts


def test_section_graph_grades_code_markdown_and_results() -> None:
    section = section_with_cells(
        [
            markdown_cell(
                0,
                "## Tools\n"
                "Wymagany komentarz - Część 2\n"
                "Parser errors affect supplier ranking and allocation decisions.",
            ),
            code_cell(
                1,
                "class SupplierOffer:\n"
                "    pass\n\n"
                "def parse_supplier_offer(raw_offer):\n"
                "    return raw_offer\n",
                execution_count=1,
                output_text="ok\n",
            ),
        ]
    )
    part_spec = part_with_requirements(
        code_requirements=[
            RequirementSpec(
                id="code_schema",
                description="Defines schema and parser.",
                points=4,
                evidence=RequirementEvidence(
                    cell_markers=["class SupplierOffer", "def parse_supplier_offer"]
                ),
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
        ],
    )

    final_state = invoke_section_graph(part_spec, section)
    section_grade = final_state["section_grade"]

    assert section_grade.part_id == "02"
    assert section_grade.points_awarded == 12
    assert section_grade.points_possible == 12
    assert [grade.requirement_id for grade in section_grade.requirement_grades] == [
        "code_schema",
        "tools_reflection",
        "executed_cells",
    ]
    assert [grade.bucket for grade in section_grade.requirement_grades] == [
        "code",
        "markdown",
        "results",
    ]


def test_section_graph_skips_not_applicable_branches() -> None:
    section = section_with_cells([markdown_cell(0, "## Tools\nShort note.")])
    part_spec = part_with_requirements(
        markdown_requirements=[
            RequirementSpec(
                id="tools_reflection",
                description="Explains risks.",
                points=3,
                evidence=RequirementEvidence(),
            )
        ],
        code_applicability="not_applicable",
        results_applicability="not_applicable",
    )
    graph = create_section_graph()

    final_state = graph.invoke(
        initialize_section_state(part_spec, section, build_evidence_index(section))
    )

    assert final_state["code_grades"] == []
    assert final_state["result_grades"] == []
    assert len(final_state["markdown_grades"]) == 1
    assert final_state["section_grade"].points_awarded == 3


def test_section_graph_synthesizes_empty_section_grade_when_no_branches_apply() -> None:
    section = section_with_cells([markdown_cell(0, "## Tools")])
    part_spec = part_with_requirements(
        code_applicability="not_applicable",
        markdown_applicability="not_applicable",
        results_applicability="not_applicable",
    )

    final_state = invoke_section_graph(part_spec, section)
    section_grade = final_state["section_grade"]

    assert section_grade.requirement_grades == []
    assert section_grade.points_awarded == 0
    assert section_grade.points_possible == 0


def test_route_to_grading_nodes_fans_out_to_all_applicable_branches() -> None:
    section = section_with_cells([markdown_cell(0, "## Tools")])
    state = initialize_section_state(
        part_with_requirements(
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
                    id="reflection",
                    description="Explains risks.",
                    points=3,
                    evidence=RequirementEvidence(),
                )
            ],
        ),
        section,
        build_evidence_index(section),
    )

    assert route_to_grading_nodes(state) == ["code_grader", "markdown_grader"]


def section_with_cells(cells: list[NotebookCell]):
    notebook = ParsedNotebook(path=Path("/submissions/lab.ipynb"), cells=cells)
    return split_notebook_by_parts(
        notebook,
        [part_with_requirements(start_heading=cells[0].source.splitlines()[0])],
    )[0]


def invoke_section_graph(part_spec: PartSpec, section):
    return create_section_graph().invoke(
        initialize_section_state(part_spec, section, build_evidence_index(section))
    )


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
    execution_count: int | None = None,
) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="code",
        source=source,
        normalized_source=source,
        execution_count=execution_count,
        output_text=output_text,
        code_features=extract_code_features(source),
    )


def part_with_requirements(
    start_heading: str = "## Tools",
    code_requirements: list[RequirementSpec] | None = None,
    markdown_requirements: list[RequirementSpec] | None = None,
    result_requirements: list[RequirementSpec] | None = None,
    code_applicability: str = "required",
    markdown_applicability: str = "required",
    results_applicability: str = "required",
) -> PartSpec:
    return PartSpec(
        part_id="02",
        title="Tools",
        source_heading=start_heading,
        cell_range=CellRangeSpec(start_heading=start_heading),
        code_requirements=code_requirements or [],
        markdown_requirements=markdown_requirements or [],
        result_requirements=result_requirements or [],
        code_applicability=code_applicability,
        markdown_applicability=markdown_applicability,
        results_applicability=results_applicability,
    )

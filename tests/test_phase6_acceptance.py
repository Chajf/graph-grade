from pathlib import Path

from app.graphs.section_graph import create_section_graph
from app.models import (
    CellRangeSpec,
    CodeJudgeContext,
    CodeJudgeResult,
    MarkdownJudgeContext,
    MarkdownJudgeResult,
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


def test_phase6_section_graph_runs_optional_structured_judges() -> None:
    section = section_with_cells(
        [
            markdown_cell(
                0,
                "## Tools\n"
                "Wymagany komentarz - Część 2\n"
                "Parser failures create business risk for allocation decisions.",
            ),
            code_cell(
                1,
                "class SupplierOffer:\n"
                "    pass\n",
                execution_count=1,
                output_text="ok\n",
            ),
        ]
    )
    part_spec = part_with_requirements()
    evidence_index = build_evidence_index(section)
    code_judge = RecordingCodeJudge(
        CodeJudgeResult(
            points_awarded=3,
            status="partial",
            evidence_cells=[1],
            reasoning="Schema exists, but the parser function is missing.",
            comment="Schema is present; parser function is missing.",
            confidence="medium",
        )
    )
    markdown_judge = RecordingMarkdownJudge(
        MarkdownJudgeResult(
            points_awarded=6,
            status="partial",
            evidence_cells=[0],
            reasoning="Reflection identifies business risk but misses mitigation detail.",
            comment="Reflection is useful but incomplete.",
            confidence="medium",
        )
    )
    state = initialize_section_state(part_spec, section, evidence_index, lab_id="lab7")
    state["code_judge"] = code_judge
    state["markdown_judge"] = markdown_judge

    final_state = create_section_graph().invoke(state)
    section_grade = final_state["section_grade"]

    assert final_state["section_grades"] == [section_grade]
    assert len(code_judge.contexts) == 1
    assert code_judge.contexts[0].deterministic_grade.points_awarded == 2
    assert [finding.matched for finding in code_judge.contexts[0].marker_findings] == [
        True,
        False,
    ]
    assert [cell.index for cell in code_judge.contexts[0].code_cells] == [1]

    assert len(markdown_judge.contexts) == 1
    assert markdown_judge.contexts[0].deterministic_grade.points_awarded == 8
    assert markdown_judge.contexts[0].deterministic_check.passed is True
    assert [cell.index for cell in markdown_judge.contexts[0].markdown_cells] == [0]

    requirement_grades = section_grade.requirement_grades
    assert [grade.requirement_id for grade in requirement_grades] == [
        "code_schema",
        "tools_reflection",
        "executed_cells",
    ]
    assert [grade.bucket for grade in requirement_grades] == [
        "code",
        "markdown",
        "results",
    ]
    assert requirement_grades[0].points_awarded == 3
    assert requirement_grades[0].comment == "Schema is present; parser function is missing."
    assert requirement_grades[1].points_awarded == 6
    assert requirement_grades[1].comment == "Reflection is useful but incomplete."
    assert requirement_grades[2].points_awarded == 0
    assert requirement_grades[2].status == "full"
    assert section_grade.points_awarded == 9
    assert section_grade.points_possible == 12
    assert section_grade.summary == "Preliminary deterministic score: 10 / 12."


def test_phase6_section_graph_runs_without_judges() -> None:
    section = section_with_cells(
        [
            markdown_cell(
                0,
                "## Tools\n"
                "Wymagany komentarz - Część 2\n"
                "Parser failures create business risk for allocation decisions.",
            ),
            code_cell(
                1,
                "class SupplierOffer:\n"
                "    pass\n",
                execution_count=1,
                output_text="ok\n",
            ),
        ]
    )
    part_spec = part_with_requirements()

    final_state = create_section_graph().invoke(
        initialize_section_state(part_spec, section, build_evidence_index(section), lab_id="lab7")
    )
    section_grade = final_state["section_grade"]

    requirement_grades = section_grade.requirement_grades
    assert [grade.requirement_id for grade in requirement_grades] == [
        "code_schema",
        "tools_reflection",
        "executed_cells",
    ]
    assert requirement_grades[0].points_awarded == 2
    assert requirement_grades[1].points_awarded == 8
    assert requirement_grades[2].points_awarded == 0
    assert section_grade.points_awarded == 10


def section_with_cells(cells: list[NotebookCell]):
    notebook = ParsedNotebook(path=Path("/submissions/lab.ipynb"), cells=cells)
    return split_notebook_by_parts(
        notebook,
        [PartSpec(
            part_id="02",
            title="Tools",
            source_heading=cells[0].source.splitlines()[0],
            cell_range=CellRangeSpec(start_heading=cells[0].source.splitlines()[0]),
        )],
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


def part_with_requirements() -> PartSpec:
    return PartSpec(
        part_id="02",
        title="Tools",
        source_heading="## Tools",
        cell_range=CellRangeSpec(start_heading="## Tools"),
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
                description="Explains tool risks.",
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


class RecordingCodeJudge:
    def __init__(self, result: CodeJudgeResult) -> None:
        self.result = result
        self.contexts: list[CodeJudgeContext] = []

    def judge_code(self, context: CodeJudgeContext) -> CodeJudgeResult:
        self.contexts.append(context)
        return self.result


class RecordingMarkdownJudge:
    def __init__(self, result: MarkdownJudgeResult) -> None:
        self.result = result
        self.contexts: list[MarkdownJudgeContext] = []

    def judge_markdown(self, context: MarkdownJudgeContext) -> MarkdownJudgeResult:
        self.contexts.append(context)
        return self.result

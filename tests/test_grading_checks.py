from pathlib import Path

from app.models import (
    ApiScoreEvidence,
    CellRangeSpec,
    EvidenceIndex,
    NotebookCell,
    NotebookError,
    NotebookOutput,
    PartSpec,
    ParsedNotebook,
    RequirementSpec,
)
from app.services.evidence import build_evidence_index
from app.services.grading_checks import run_named_check, run_result_checks
from app.services.notebook_splitter import split_notebook_by_parts


def test_api_response_visible_passes_when_api_score_exists_in_section() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## API"),
            code_cell(
                1,
                "response",
                output_text='{"score": 8, "max_score": 10}',
                outputs=[
                    NotebookOutput(
                        output_type="execute_result",
                        text='{"score": 8, "max_score": 10}',
                    )
                ],
            ),
        ]
    )
    evidence_index = build_evidence_index(section)

    result = run_named_check("api_response_visible", section, evidence_index)

    assert result.passed is True
    assert result.evidence_cells == [1]
    assert result.severity == "info"


def test_api_response_visible_ignores_scores_from_other_sections() -> None:
    section = section_with_cells([markdown_cell(0, "## API"), code_cell(1, "print('no score')")])
    evidence_index = EvidenceIndex(
        api_scores=[ApiScoreEvidence(cell_index=99, score=8, max_score=10)]
    )

    result = run_named_check("api_response_visible", section, evidence_index)

    assert result.passed is False
    assert result.evidence_cells == []


def test_no_error_outputs_in_required_cells_fails_when_section_has_error() -> None:
    error = NotebookError(ename="ValueError", evalue="bad allocation")
    section = section_with_cells(
        [
            markdown_cell(0, "## Results"),
            code_cell(
                1,
                "raise ValueError('bad allocation')",
                output_text="ValueError: bad allocation",
                errors=[error],
            ),
        ]
    )

    result = run_named_check(
        "no_error_outputs_in_required_cells",
        section,
        build_evidence_index(section),
    )

    assert result.passed is False
    assert result.evidence_cells == [1]
    assert result.severity == "critical"


def test_no_plaintext_api_keys_fails_when_secret_is_detected() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## API"),
            code_cell(1, 'API_KEY = "sk-abc1234567890abc1234567890abc1234567890"'),
        ]
    )

    result = run_named_check(
        "no_plaintext_api_keys",
        section,
        build_evidence_index(section),
    )

    assert result.passed is False
    assert result.evidence_cells == [1]
    assert result.severity == "critical"


def test_required_code_cells_have_execution_count_or_visible_output() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Results"),
            code_cell(1, "print('ok')", execution_count=1),
            code_cell(2, "print('visible')", output_text="visible\n"),
        ]
    )

    result = run_named_check(
        "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
        section,
        build_evidence_index(section),
    )

    assert result.passed is True
    assert result.evidence_cells == [1, 2]


def test_required_code_cells_check_fails_for_unexecuted_cells_without_outputs() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Results"),
            code_cell(1, "print('missing execution')"),
        ]
    )

    result = run_named_check(
        "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
        section,
        build_evidence_index(section),
    )

    assert result.passed is False
    assert result.evidence_cells == []
    assert result.severity == "critical"


def test_registered_output_presence_check_uses_visible_outputs() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## Agent"),
            code_cell(1, "agent.invoke({})", output_text="scenario result\n"),
        ]
    )

    result = run_named_check(
        "output_present_for_agent_scenarios",
        section,
        build_evidence_index(section),
    )

    assert result.passed is True
    assert result.evidence_cells == [1]


def test_unknown_check_fails_explicitly() -> None:
    section = section_with_cells([markdown_cell(0, "## Results")])

    result = run_named_check("missing_registry_entry", section, EvidenceIndex())

    assert result.passed is False
    assert result.evidence_cells == []
    assert result.severity == "warning"
    assert "Unknown" in result.comment


def test_run_result_checks_returns_one_result_per_requirement_check() -> None:
    section = section_with_cells(
        [
            markdown_cell(0, "## API"),
            code_cell(1, "print('ok')", execution_count=1, output_text="ok\n"),
        ]
    )
    requirement = RequirementSpec(
        id="result_api",
        description="Shows API response",
        points=2,
        checks=[
            "required_code_cells_have_execution_count_or_equivalent_visible_outputs",
            "no_error_outputs_in_required_cells",
            "missing_registry_entry",
        ],
    )

    results = run_result_checks(section, requirement, build_evidence_index(section))

    assert [result.check_name for result in results] == requirement.checks
    assert [result.passed for result in results] == [True, True, False]


def section_with_cells(cells: list[NotebookCell]):
    notebook = ParsedNotebook(path=Path("/submissions/lab.ipynb"), cells=cells)
    start_heading = cells[0].source if cells else "## Results"
    return split_notebook_by_parts(
        notebook,
        [part("01", "Results", start_heading, None)],
    )[0]


def markdown_cell(index: int, source: str) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="markdown",
        source=source,
        normalized_source=source,
        headings=[source.lstrip("# ")],
    )


def code_cell(
    index: int,
    source: str,
    output_text: str = "",
    outputs: list[NotebookOutput] | None = None,
    errors: list[NotebookError] | None = None,
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
    )

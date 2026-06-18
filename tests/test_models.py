from pathlib import Path

from app.models import (
    CellRangeSpec,
    LabSpec,
    NotebookCell,
    NotebookError,
    NotebookOutput,
    NotebookResolutionIssue,
    PartSpec,
    ParsedNotebook,
    RequirementEvidence,
    RequirementSpec,
    SectionEvidence,
    SharePointStudentSubmission,
)


def test_lab_spec_model_preserves_ordered_parts() -> None:
    first_part = PartSpec(
        part_id="01",
        title="First agent",
        source_heading="## First agent",
        cell_range=CellRangeSpec(start_heading="## First agent"),
        code_requirements=[
            RequirementSpec(
                id="lab7_part01_agent",
                description="Creates an agent.",
                points=4,
                evidence=RequirementEvidence(cell_markers=["create_agent"]),
            )
        ],
        markdown_requirements=[],
        result_requirements=[],
        code_applicability="required",
        markdown_applicability="not_applicable",
        results_applicability="required",
    )
    second_part = PartSpec(
        part_id="02",
        title="Tools",
        source_heading="## Tools",
        cell_range=CellRangeSpec(
            start_heading="## Tools",
            end_heading="## Structured output",
        ),
        code_requirements=[],
        markdown_requirements=[],
        result_requirements=[],
        code_applicability="optional",
        markdown_applicability="required",
        results_applicability="not_applicable",
    )

    spec = LabSpec(
        lab_id="lab7",
        title="Lab 7",
        language="pl",
        total_points=100,
        expected_notebook_pattern="lab7_*.ipynb",
        required_files=[],
        parts=[first_part, second_part],
    )

    assert [part.part_id for part in spec.parts] == ["01", "02"]
    assert spec.parts[0].code_applicable is True
    assert spec.parts[0].markdown_applicable is False
    assert spec.parts[1].results_applicable is False
    assert spec.parts[1].start_heading == "## Tools"
    assert spec.parts[1].end_heading == "## Structured output"


def test_sharepoint_submission_model_supports_resolution_issues() -> None:
    issue = NotebookResolutionIssue(
        code="ambiguous_notebook",
        message="Multiple notebook candidates found.",
        candidates=[
            Path("/prace/lab1/Jan/lab7/Wersja 2/lab7_a.ipynb"),
            Path("/prace/lab1/Jan/lab7/Wersja 2/lab7_b.ipynb"),
        ],
    )

    submission = SharePointStudentSubmission(
        submissions_root=Path("/prace"),
        group_id="lab1",
        student_folder="Jan_Kowalski",
        lab_id="lab7",
        lab_folder=Path("/prace/lab1/Jan_Kowalski/lab7"),
        version_folder=Path("/prace/lab1/Jan_Kowalski/lab7/Wersja 2"),
        status="ambiguous",
        issue=issue,
    )

    assert submission.resolved is False
    assert submission.issue is not None
    assert submission.issue.code == "ambiguous_notebook"
    assert len(submission.issue.candidates) == 2


def test_sharepoint_submission_model_marks_resolved_with_notebook() -> None:
    submission = SharePointStudentSubmission(
        submissions_root=Path("/prace"),
        group_id="lab1",
        student_folder="Anna_Nowak",
        lab_id="lab7",
        lab_folder=Path("/prace/lab1/Anna_Nowak/lab7"),
        version_folder=Path("/prace/lab1/Anna_Nowak/lab7/Wersja 3"),
        notebook_path=Path("/prace/lab1/Anna_Nowak/lab7/Wersja 3/lab7_Nowak.ipynb"),
        status="resolved",
    )

    assert submission.resolved is True


def test_parsed_notebook_model_preserves_ordered_cells() -> None:
    error = NotebookError(
        ename="ValueError",
        evalue="bad value",
        traceback=["Traceback line"],
    )
    stdout = NotebookOutput(
        output_type="stream",
        name="stdout",
        text="hello\n",
    )
    error_output = NotebookOutput(
        output_type="error",
        text="ValueError: bad value",
        error=error,
    )

    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        metadata={"kernelspec": {"name": "python3"}},
        cells=[
            NotebookCell(
                index=0,
                cell_type="markdown",
                source="# Lab 7\nIntro",
                normalized_source="# Lab 7\nIntro",
                headings=["Lab 7"],
            ),
            NotebookCell(
                index=1,
                cell_type="code",
                source="print('hello')",
                normalized_source="print('hello')",
                execution_count=1,
                outputs=[stdout, error_output],
                output_text="hello\nValueError: bad value",
                errors=[error],
            ),
            NotebookCell(
                index=2,
                cell_type="raw",
                source="raw notes",
                normalized_source="raw notes",
            ),
        ],
    )

    assert notebook.path == Path("/submissions/lab7.ipynb")
    assert notebook.metadata["kernelspec"]["name"] == "python3"
    assert [cell.index for cell in notebook.cells] == [0, 1, 2]
    assert [cell.cell_type for cell in notebook.cells] == ["markdown", "code", "raw"]
    assert notebook.cells[0].headings == ["Lab 7"]
    assert notebook.cells[1].execution_count == 1
    assert notebook.cells[1].outputs[0].text == "hello\n"
    assert notebook.cells[1].errors[0].ename == "ValueError"


def test_parsed_notebook_model_serializes_paths_and_outputs() -> None:
    notebook = ParsedNotebook(
        path=Path("/submissions/lab7.ipynb"),
        cells=[
            NotebookCell(
                index=0,
                cell_type="code",
                source="x = 1",
                normalized_source="x = 1",
                outputs=[
                    NotebookOutput(
                        output_type="execute_result",
                        text="1",
                        data={"text/plain": "1"},
                    )
                ],
            )
        ],
    )

    dumped = notebook.model_dump(mode="json")

    assert dumped["path"] == "/submissions/lab7.ipynb"
    assert dumped["cells"][0]["cell_type"] == "code"
    assert dumped["cells"][0]["outputs"][0]["data"] == {"text/plain": "1"}


def test_section_evidence_model_groups_cells_outputs_and_errors() -> None:
    error = NotebookError(
        ename="ValueError",
        evalue="bad value",
        traceback=["Traceback line"],
    )
    markdown_cell = NotebookCell(
        index=0,
        cell_type="markdown",
        source="## Tools",
        normalized_source="## Tools",
        headings=["Tools"],
    )
    code_cell = NotebookCell(
        index=1,
        cell_type="code",
        source="print('parsed')",
        normalized_source="print('parsed')",
        output_text="parsed\nValueError: bad value",
        errors=[error],
    )

    evidence = SectionEvidence(
        part_id="02",
        title="Tools",
        start_heading="## Tools",
        end_heading="## Structured output",
        mapping_confidence="high",
        cells=[markdown_cell, code_cell],
        code_cells=[code_cell],
        markdown_cells=[markdown_cell],
        output_text="parsed\nValueError: bad value",
        errors=[error],
    )

    dumped = evidence.model_dump(mode="json")

    assert evidence.part_id == "02"
    assert evidence.mapping_confidence == "high"
    assert evidence.missing_start_heading is False
    assert evidence.missing_end_heading is False
    assert [cell.index for cell in evidence.cells] == [0, 1]
    assert evidence.code_cells == [code_cell]
    assert evidence.markdown_cells == [markdown_cell]
    assert evidence.errors[0].ename == "ValueError"
    assert dumped["cells"][0]["cell_type"] == "markdown"
    assert dumped["errors"][0]["traceback"] == ["Traceback line"]

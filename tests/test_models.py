from pathlib import Path

from app.models import (
    CellRangeSpec,
    FinalGrade,
    LabSpec,
    NotebookCell,
    NotebookError,
    NotebookOutput,
    NotebookResolutionIssue,
    PartSpec,
    ParsedNotebook,
    RequirementEvidence,
    RequirementGrade,
    RequirementSpec,
    SectionEvidence,
    SectionGrade,
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


def test_grade_models_preserve_requirement_order_and_serialize() -> None:
    code_grade = RequirementGrade(
        requirement_id="lab7_part02_supplier_offer_schema",
        bucket="code",
        points_awarded=4,
        points_possible=4,
        status="full",
        evidence_cells=[2],
        comment="Matched all required code markers.",
        confidence="high",
    )
    markdown_grade = RequirementGrade(
        requirement_id="lab7_part02_tools_reflection",
        bucket="markdown",
        points_awarded=0,
        points_possible=8,
        status="missing",
        evidence_cells=[],
        comment="Required reflection text was not found.",
        confidence="medium",
    )

    section_grade = SectionGrade(
        part_id="02",
        title="Tools: parsing, TOPSIS, and LP allocation",
        points_awarded=code_grade.points_awarded + markdown_grade.points_awarded,
        points_possible=code_grade.points_possible + markdown_grade.points_possible,
        requirement_grades=[code_grade, markdown_grade],
        summary="Preliminary deterministic score: 4.0 / 12.0.",
    )

    dumped = section_grade.model_dump(mode="json")

    assert [grade.requirement_id for grade in section_grade.requirement_grades] == [
        "lab7_part02_supplier_offer_schema",
        "lab7_part02_tools_reflection",
    ]
    assert section_grade.points_awarded == 4
    assert section_grade.points_possible == 12
    assert dumped["requirement_grades"][0]["bucket"] == "code"
    assert dumped["requirement_grades"][0]["evidence_cells"] == [2]
    assert dumped["requirement_grades"][1]["status"] == "missing"


def test_final_grade_model_sums_sections_and_serializes() -> None:
    first_section = SectionGrade(
        part_id="01",
        title="Agent basics",
        points_awarded=7,
        points_possible=10,
    )
    second_section = SectionGrade(
        part_id="02",
        title="Tools",
        points_awarded=18,
        points_possible=25,
    )

    final_grade = FinalGrade(
        lab_id="lab7",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        notebook_path="/prace/lab1/Jan_Kowalski/lab7/Wersja 2/lab7.ipynb",
        points_awarded=sum(section.points_awarded for section in [first_section, second_section]),
        points_possible=sum(section.points_possible for section in [first_section, second_section]),
        section_grades=[first_section, second_section],
        flags=["missing_required_file:data.csv"],
        summary="Final score: 25 / 35.",
    )

    dumped = final_grade.model_dump(mode="json")

    assert final_grade.status == "graded"
    assert final_grade.points_awarded == 25
    assert final_grade.points_possible == 35
    assert [section.part_id for section in final_grade.section_grades] == ["01", "02"]
    assert dumped["notebook_path"].endswith("/lab7.ipynb")
    assert dumped["section_grades"][1]["title"] == "Tools"
    assert dumped["flags"] == ["missing_required_file:data.csv"]

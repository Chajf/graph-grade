from pathlib import Path

from app.models import (
    CellRangeSpec,
    LabSpec,
    NotebookResolutionIssue,
    PartSpec,
    RequirementEvidence,
    RequirementSpec,
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

from app.models import FinalGrade, RequirementGrade, SectionGrade
from app.services.feedback import render_lab_feedback, render_student_summary


def test_render_lab_feedback_includes_totals_sections_requirements_and_evidence() -> None:
    final_grade = FinalGrade(
        lab_id="lab7",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        notebook_path="/prace/lab1/Jan_Kowalski/lab7/Wersja 2/lab7.ipynb",
        points_awarded=9,
        points_possible=12,
        section_grades=[
            SectionGrade(
                part_id="02",
                title="Tools",
                points_awarded=9,
                points_possible=12,
                requirement_grades=[
                    RequirementGrade(
                        requirement_id="code_schema",
                        bucket="code",
                        points_awarded=3,
                        points_possible=4,
                        status="partial",
                        evidence_cells=[1, 3],
                        comment="Schema exists, but parser is missing.",
                    ),
                    RequirementGrade(
                        requirement_id="tools_reflection",
                        bucket="markdown",
                        points_awarded=6,
                        points_possible=8,
                        status="partial",
                        evidence_cells=[0],
                        comment="Reflection misses mitigation detail.",
                    ),
                ],
                summary="Preliminary score: 9 / 12.",
            )
        ],
        flags=["missing_required_file:data.csv"],
        summary="Final score: 9 / 12.",
    )

    feedback = render_lab_feedback(final_grade)

    assert "# Feedback for lab7" in feedback
    assert "Student: Jan_Kowalski" in feedback
    assert "Score: 9 / 12" in feedback
    assert "missing_required_file:data.csv" in feedback
    assert "### 02: Tools" in feedback
    assert "code_schema" in feedback
    assert "3 / 4" in feedback
    assert "cells 1, 3" in feedback
    assert "Schema exists, but parser is missing." in feedback
    assert "tools_reflection" in feedback
    assert "cell 0" in feedback


def test_render_student_summary_orders_labs_and_sums_totals() -> None:
    lab7_grade = FinalGrade(
        lab_id="lab7",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        notebook_path="/prace/lab1/Jan_Kowalski/lab7/Wersja 2/lab7.ipynb",
        points_awarded=9,
        points_possible=12,
        flags=["section_mapping_low_confidence"],
    )
    lab3_grade = FinalGrade(
        lab_id="lab3",
        group_id="lab1",
        student_folder="Jan_Kowalski",
        notebook_path="/prace/lab1/Jan_Kowalski/lab3/Wersja 1/lab3.ipynb",
        points_awarded=18,
        points_possible=20,
    )

    summary = render_student_summary([lab7_grade, lab3_grade])

    assert summary.index("| lab3 |") < summary.index("| lab7 |")
    assert "| lab3 | 18 / 20 | graded | - |" in summary
    assert "| lab7 | 9 / 12 | graded | section_mapping_low_confidence |" in summary
    assert "Total: 27 / 32" in summary


def test_render_student_summary_handles_no_grades() -> None:
    summary = render_student_summary([])

    assert summary == "# Student Summary\n\nNo graded labs found.\n"

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import (
    MarkdownJudgeContext,
    MarkdownJudgeResult,
    RequirementGrade,
    RequirementSpec,
)
from app.nodes.markdown_grader import _grade_markdown_requirement
from app.services.grading_checks import check_markdown_requirement

if TYPE_CHECKING:
    from app.graphs.state import SectionGraphState


def judge_markdown_requirements(state: SectionGraphState) -> dict[str, list[RequirementGrade]]:
    markdown_judge = state.get("markdown_judge")
    if markdown_judge is None:
        return {"markdown_grades": state.get("markdown_grades", [])}

    part_spec = state["part_spec"]
    section = state["section"]
    deterministic_grades = {
        grade.requirement_id: grade
        for grade in state.get("markdown_grades", [])
    }

    judged_grades: list[RequirementGrade] = []
    for requirement in part_spec.markdown_requirements:
        deterministic_grade = deterministic_grades.get(requirement.id)
        if deterministic_grade is None:
            deterministic_grade = _grade_markdown_requirement(section, requirement)

        deterministic_check = check_markdown_requirement(section, requirement)
        context = MarkdownJudgeContext(
            lab_id=state.get("lab_id", ""),
            part_id=part_spec.part_id,
            part_title=part_spec.title,
            requirement=requirement,
            deterministic_grade=deterministic_grade,
            deterministic_check=deterministic_check,
            markdown_cells=section.markdown_cells,
        )
        try:
            judge_result = markdown_judge.judge_markdown(context)
        except Exception as exc:
            judged_grades.append(_fallback_grade_after_judge_error(deterministic_grade, exc))
            continue

        judged_grades.append(_grade_from_judge_result(requirement, judge_result))

    return {"markdown_grades": judged_grades}


def _grade_from_judge_result(
    requirement: RequirementSpec,
    judge_result: MarkdownJudgeResult,
) -> RequirementGrade:
    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="markdown",
        points_awarded=_clamp_points(judge_result.points_awarded, requirement.points),
        points_possible=requirement.points,
        status=judge_result.status,
        evidence_cells=judge_result.evidence_cells,
        comment=judge_result.comment,
        confidence=judge_result.confidence,
    )


def _fallback_grade_after_judge_error(
    deterministic_grade: RequirementGrade,
    exc: Exception,
) -> RequirementGrade:
    return deterministic_grade.model_copy(
        update={
            "comment": (
                f"{deterministic_grade.comment} "
                f"Markdown judge failed; kept deterministic grade. Reason: {exc}."
            ),
            "confidence": "low",
        }
    )


def _clamp_points(points_awarded: float, points_possible: float) -> float:
    return min(max(points_awarded, 0), points_possible)

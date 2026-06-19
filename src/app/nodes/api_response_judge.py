from __future__ import annotations

from typing import TYPE_CHECKING

from app.models import (
    ApiResponseJudgeContext,
    ApiResponseJudgeResult,
    RequirementGrade,
    RequirementSpec,
)
from app.nodes.results_grader import _grade_result_requirement
from app.services.grading_checks import run_result_checks

if TYPE_CHECKING:
    from app.graphs.state import SectionGraphState


def judge_api_response_requirements(
    state: SectionGraphState,
) -> dict[str, list[RequirementGrade]]:
    api_response_judge = state.get("api_response_judge")
    if api_response_judge is None:
        return {"result_grades": state.get("result_grades", [])}

    part_spec = state["part_spec"]
    section = state["section"]
    evidence_index = state["evidence_index"]
    deterministic_grades = {
        grade.requirement_id: grade
        for grade in state.get("result_grades", [])
    }

    judged_grades: list[RequirementGrade] = []
    for requirement in part_spec.result_requirements:
        deterministic_grade = deterministic_grades.get(requirement.id)
        if deterministic_grade is None:
            deterministic_grade = _grade_result_requirement(
                section,
                requirement,
                evidence_index,
            )

        context = ApiResponseJudgeContext(
            lab_id=state.get("lab_id", ""),
            part_id=part_spec.part_id,
            part_title=part_spec.title,
            requirement=requirement,
            deterministic_grade=deterministic_grade,
            deterministic_checks=run_result_checks(section, requirement, evidence_index),
            code_cells=section.code_cells,
            markdown_cells=section.markdown_cells,
            evidence_index=evidence_index,
        )
        try:
            judge_result = api_response_judge.judge_api_response(context)
        except Exception as exc:
            judged_grades.append(_fallback_grade_after_judge_error(deterministic_grade, exc))
            continue

        judged_grades.append(_grade_from_judge_result(requirement, judge_result))

    return {"result_grades": judged_grades}


def _grade_from_judge_result(
    requirement: RequirementSpec,
    judge_result: ApiResponseJudgeResult,
) -> RequirementGrade:
    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="results",
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
                f"API response judge failed; kept deterministic grade. Reason: {exc}."
            ),
            "confidence": "low",
        }
    )


def _clamp_points(points_awarded: float, points_possible: float) -> float:
    return min(max(points_awarded, 0), points_possible)

from __future__ import annotations

from app.graphs.state import SectionGraphState
from app.models import CodeJudgeContext, CodeJudgeResult, RequirementGrade, RequirementSpec
from app.nodes.code_grader import _grade_code_requirement
from app.services.code_features import match_code_markers


def judge_code_requirements(state: SectionGraphState) -> dict[str, list[RequirementGrade]]:
    code_judge = state.get("code_judge")
    if code_judge is None:
        return {"code_grades": state.get("code_grades", [])}

    part_spec = state["part_spec"]
    section = state["section"]
    evidence_index = state["evidence_index"]
    deterministic_grades = {
        grade.requirement_id: grade
        for grade in state.get("code_grades", [])
    }

    judged_grades: list[RequirementGrade] = []
    for requirement in part_spec.code_requirements:
        deterministic_grade = deterministic_grades.get(requirement.id)
        if deterministic_grade is None:
            deterministic_grade = _grade_code_requirement(section, requirement)

        marker_findings = match_code_markers(
            section.code_cells,
            requirement.evidence.cell_markers,
        )
        context = CodeJudgeContext(
            lab_id=state.get("lab_id", ""),
            part_id=part_spec.part_id,
            part_title=part_spec.title,
            requirement=requirement,
            deterministic_grade=deterministic_grade,
            marker_findings=marker_findings,
            code_cells=section.code_cells,
            evidence_index=evidence_index,
        )
        try:
            judge_result = code_judge.judge_code(context)
        except Exception as exc:
            judged_grades.append(_fallback_grade_after_judge_error(deterministic_grade, exc))
            continue

        judged_grades.append(_grade_from_judge_result(requirement, judge_result))

    return {"code_grades": judged_grades}


def _grade_from_judge_result(
    requirement: RequirementSpec,
    judge_result: CodeJudgeResult,
) -> RequirementGrade:
    return RequirementGrade(
        requirement_id=requirement.id,
        bucket="code",
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
                f"Code judge failed; kept deterministic grade. Reason: {exc}."
            ),
            "confidence": "low",
        }
    )


def _clamp_points(points_awarded: float, points_possible: float) -> float:
    return min(max(points_awarded, 0), points_possible)

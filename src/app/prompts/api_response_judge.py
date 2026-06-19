from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.judges import ApiResponseJudgeContext


MAX_SOURCE_CHARS = 6000
MAX_OUTPUT_CHARS = 4000
MAX_MARKDOWN_CHARS = 3000


def build_api_response_judge_messages(
    context: ApiResponseJudgeContext,
) -> list[SystemMessage | HumanMessage]:
    return [
        build_api_response_judge_system_message(),
        build_api_response_judge_human_message(context),
    ]


def build_api_response_judge_system_message() -> SystemMessage:
    return SystemMessage(
        content=(
            "You are a strict API response grading judge for static Jupyter notebook "
            "review. Grade only the supplied result requirement using the supplied "
            "notebook cells, visible outputs, deterministic checks, and extracted API "
            "score evidence. Do not execute code, do not call external APIs, do not "
            "infer hidden runtime state, and do not assume outputs or files that are "
            "not present in the context. A visible API score alone is not sufficient: "
            "judge whether the displayed API response, score payload, surrounding "
            "code, and requirement criteria show that the expected API interaction "
            "was performed correctly. Return only a structured ApiResponseJudgeResult "
            "with points_awarded, status, evidence_cells, reasoning, comment, "
            "confidence, and flags. Use reasoning for a concise grading rationale "
            "intended for internal logging; keep comment suitable for student-facing "
            "feedback."
        )
    )


def build_api_response_judge_human_message(
    context: ApiResponseJudgeContext,
) -> HumanMessage:
    return HumanMessage(
        content=json.dumps(
            {
                "lab_id": context.lab_id,
                "part_id": context.part_id,
                "part_title": context.part_title,
                "requirement": context.requirement.model_dump(mode="json"),
                "deterministic_grade": context.deterministic_grade.model_dump(mode="json"),
                "deterministic_checks": [
                    check.model_dump(mode="json")
                    for check in context.deterministic_checks
                ],
                "api_scores": [
                    score.model_dump(mode="json")
                    for score in context.evidence_index.api_scores
                    if score.cell_index in _section_cell_indexes(context)
                ],
                "code_cells": [_code_cell_payload(cell) for cell in context.code_cells],
                "markdown_cells": [
                    {
                        "index": cell.index,
                        "source": _truncate(cell.source, MAX_MARKDOWN_CHARS),
                    }
                    for cell in context.markdown_cells
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _code_cell_payload(cell) -> dict:
    return {
        "index": cell.index,
        "source": _truncate(cell.source, MAX_SOURCE_CHARS),
        "execution_count": cell.execution_count,
        "output_text": _truncate(cell.output_text, MAX_OUTPUT_CHARS),
        "errors": [error.model_dump(mode="json") for error in cell.errors],
        "outputs": [
            {
                "output_type": output.output_type,
                "text": _truncate(output.text, MAX_OUTPUT_CHARS),
                "data": output.data,
            }
            for output in cell.outputs
        ],
    }


def _section_cell_indexes(context: ApiResponseJudgeContext) -> set[int]:
    return {
        cell.index
        for cell in [*context.code_cells, *context.markdown_cells]
    }


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}...[truncated]"

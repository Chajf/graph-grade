from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.judges import CodeJudgeContext


MAX_SOURCE_CHARS = 6000
MAX_OUTPUT_CHARS = 2000


def build_code_judge_messages(context: CodeJudgeContext) -> list[SystemMessage | HumanMessage]:
    return [
        build_code_judge_system_message(),
        build_code_judge_human_message(context),
    ]


def build_code_judge_system_message() -> SystemMessage:
    return SystemMessage(
        content=(
            "You are a strict code grading judge for static Jupyter notebook review. "
            "Grade only the supplied requirement using the supplied evidence. "
            "Do not execute code, do not infer hidden runtime state, and do not assume "
            "files or outputs that are not present in the context. Use deterministic "
            "findings as evidence, but correct them when the provided code clearly "
            "supports a different semantic grade. Return only a structured "
            "CodeJudgeResult with points_awarded, status, evidence_cells, reasoning, "
            "comment, confidence, and flags. Use reasoning for a concise grading "
            "rationale intended for internal logging; keep comment suitable for "
            "student-facing feedback."
        )
    )


def build_code_judge_human_message(context: CodeJudgeContext) -> HumanMessage:
    return HumanMessage(
        content=json.dumps(
            {
                "lab_id": context.lab_id,
                "part_id": context.part_id,
                "part_title": context.part_title,
                "requirement": context.requirement.model_dump(mode="json"),
                "deterministic_grade": context.deterministic_grade.model_dump(mode="json"),
                "marker_findings": [
                    finding.model_dump(mode="json")
                    for finding in context.marker_findings
                ],
                "code_cells": [_code_cell_payload(cell) for cell in context.code_cells],
                "evidence_index": context.evidence_index.model_dump(mode="json"),
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
        "code_features": (
            cell.code_features.model_dump(mode="json")
            if cell.code_features is not None
            else None
        ),
    }


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}...[truncated]"

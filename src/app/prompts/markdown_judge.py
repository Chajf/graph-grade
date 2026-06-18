from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.judges import MarkdownJudgeContext


MAX_MARKDOWN_CHARS = 6000


def build_markdown_judge_messages(
    context: MarkdownJudgeContext,
) -> list[SystemMessage | HumanMessage]:
    return [
        build_markdown_judge_system_message(),
        build_markdown_judge_human_message(context),
    ]


def build_markdown_judge_system_message() -> SystemMessage:
    return SystemMessage(
        content=(
            "You are a strict markdown grading judge for static Jupyter notebook "
            "review. Grade only the supplied requirement using the supplied markdown "
            "evidence. Do not execute code, do not infer hidden notebook content, and "
            "do not assume outputs or files that are not present in the context. Use "
            "deterministic placeholder and heading findings as evidence, but correct "
            "them when the supplied markdown clearly supports a different semantic "
            "grade. Return only a structured MarkdownJudgeResult with points_awarded, "
            "status, evidence_cells, reasoning, comment, confidence, and flags. Use "
            "reasoning for a concise grading rationale intended for internal logging; "
            "keep comment suitable for student-facing feedback."
        )
    )


def build_markdown_judge_human_message(context: MarkdownJudgeContext) -> HumanMessage:
    return HumanMessage(
        content=json.dumps(
            {
                "lab_id": context.lab_id,
                "part_id": context.part_id,
                "part_title": context.part_title,
                "requirement": context.requirement.model_dump(mode="json"),
                "deterministic_grade": context.deterministic_grade.model_dump(mode="json"),
                "deterministic_check": context.deterministic_check.model_dump(mode="json"),
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


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}...[truncated]"

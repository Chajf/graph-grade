import json

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.models import (
    CheckResult,
    CodeJudgeContext,
    CodeJudgeResult,
    CodeMarkerFinding,
    EvidenceIndex,
    MarkdownJudgeContext,
    MarkdownJudgeResult,
    NotebookCell,
    RequirementEvidence,
    RequirementGrade,
    RequirementSpec,
)
from app.prompts.code_judge import build_code_judge_messages
from app.prompts.markdown_judge import build_markdown_judge_messages


def test_code_judge_result_validates_status_confidence_and_points() -> None:
    valid = CodeJudgeResult(
        points_awarded=3.5,
        status="partial",
        evidence_cells=[2],
        reasoning="The schema is present, but one required field marker is missing.",
        comment="Implementation is mostly correct.",
        confidence="medium",
    )

    assert valid.points_awarded == 3.5

    with pytest.raises(ValidationError):
        CodeJudgeResult(
            points_awarded="many",
            status="partial",
            evidence_cells=[2],
            reasoning="Invalid point type.",
            comment="Invalid point type.",
            confidence="medium",
        )

    with pytest.raises(ValidationError):
        CodeJudgeResult(
            points_awarded=1,
            status="almost",
            evidence_cells=[2],
            reasoning="Invalid status.",
            comment="Invalid status.",
            confidence="medium",
        )

    with pytest.raises(ValidationError):
        CodeJudgeResult(
            points_awarded=1,
            status="partial",
            evidence_cells=[2],
            reasoning="Invalid confidence.",
            comment="Invalid confidence.",
            confidence="certain",
        )


def test_markdown_judge_result_validates_status_confidence_and_points() -> None:
    valid = MarkdownJudgeResult(
        points_awarded=6,
        status="partial",
        evidence_cells=[3],
        reasoning="The answer names risks but misses concrete tradeoffs.",
        comment="Reflection covers key risks but misses tradeoffs.",
        confidence="high",
    )

    assert valid.points_awarded == 6

    with pytest.raises(ValidationError):
        MarkdownJudgeResult(
            points_awarded=-1,
            status="partial",
            evidence_cells=[3],
            reasoning="Negative points are invalid.",
            comment="Negative points are invalid.",
            confidence="high",
        )

    with pytest.raises(ValidationError):
        MarkdownJudgeResult(
            points_awarded=1,
            status="complete",
            evidence_cells=[3],
            reasoning="Invalid status.",
            comment="Invalid status.",
            confidence="high",
        )

    with pytest.raises(ValidationError):
        MarkdownJudgeResult(
            points_awarded=1,
            status="partial",
            evidence_cells=[3],
            reasoning="Invalid confidence.",
            comment="Invalid confidence.",
            confidence="sure",
        )


def test_code_judge_prompt_separates_system_instructions_from_human_context() -> None:
    context = code_context()

    messages = build_code_judge_messages(context)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert "Do not execute code" in str(messages[0].content)
    assert "reasoning" in str(messages[0].content)
    assert "internal logging" in str(messages[0].content)
    assert "lab7_part02_supplier_offer_schema" not in str(messages[0].content)

    human_payload = json.loads(str(messages[1].content))
    assert human_payload["lab_id"] == "lab7"
    assert human_payload["requirement"]["id"] == "lab7_part02_supplier_offer_schema"
    assert human_payload["requirement"]["points"] == 4
    assert human_payload["deterministic_grade"]["evidence_cells"] == [2]
    assert human_payload["marker_findings"][0]["marker"] == "class SupplierOffer"
    assert human_payload["marker_findings"][1]["matched"] is False
    assert human_payload["code_cells"][0]["index"] == 2
    assert "class SupplierOffer" in human_payload["code_cells"][0]["source"]
    assert "unrelated section" not in str(messages[1].content)


def test_markdown_judge_prompt_separates_system_instructions_from_human_context() -> None:
    context = markdown_context()

    messages = build_markdown_judge_messages(context)

    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert "Do not execute code" in str(messages[0].content)
    assert "reasoning" in str(messages[0].content)
    assert "internal logging" in str(messages[0].content)
    assert "tools_reflection" not in str(messages[0].content)

    human_payload = json.loads(str(messages[1].content))
    assert human_payload["lab_id"] == "lab7"
    assert human_payload["requirement"]["id"] == "tools_reflection"
    assert human_payload["requirement"]["points"] == 8
    assert human_payload["deterministic_grade"]["evidence_cells"] == [3]
    assert human_payload["deterministic_check"]["check_name"] == "markdown_not_placeholder"
    assert human_payload["markdown_cells"][0]["index"] == 3
    assert "business risk" in human_payload["markdown_cells"][0]["source"]
    assert "unrelated section" not in str(messages[1].content)


def code_context() -> CodeJudgeContext:
    requirement = RequirementSpec(
        id="lab7_part02_supplier_offer_schema",
        description="Defines SupplierOffer as a Pydantic schema.",
        points=4,
        evidence=RequirementEvidence(
            cell_markers=["class SupplierOffer", "Field"]
        ),
        quality_criteria=["Uses typed fields.", "Documents fields."],
    )
    deterministic_grade = RequirementGrade(
        requirement_id=requirement.id,
        bucket="code",
        points_awarded=2,
        points_possible=4,
        status="partial",
        evidence_cells=[2],
        comment="Matched 1 of 2 required code marker(s). Missing: Field.",
        confidence="high",
    )
    return CodeJudgeContext(
        lab_id="lab7",
        part_id="02",
        part_title="Tools",
        requirement=requirement,
        deterministic_grade=deterministic_grade,
        marker_findings=[
            CodeMarkerFinding(
                marker="class SupplierOffer",
                matched=True,
                kind="class",
                evidence_cells=[2],
                comment="Matched class marker.",
            ),
            CodeMarkerFinding(
                marker="Field",
                matched=False,
                kind="identifier",
                evidence_cells=[],
                comment="Missing identifier marker.",
            ),
        ],
        code_cells=[
            NotebookCell(
                index=2,
                cell_type="code",
                source="class SupplierOffer:\n    pass\n",
                normalized_source="class SupplierOffer:\n    pass\n",
                execution_count=1,
                output_text="schema ok",
            )
        ],
        evidence_index=EvidenceIndex(classes={"SupplierOffer": [2]}),
    )


def markdown_context() -> MarkdownJudgeContext:
    requirement = RequirementSpec(
        id="tools_reflection",
        description="Explains tool risks.",
        points=8,
        evidence=RequirementEvidence(heading_or_text="Wymagany komentarz"),
        quality_criteria=["Explains business risk.", "Explains parser failure modes."],
    )
    deterministic_grade = RequirementGrade(
        requirement_id=requirement.id,
        bucket="markdown",
        points_awarded=8,
        points_possible=8,
        status="full",
        evidence_cells=[3],
        comment="Markdown evidence is present and does not look placeholder-only.",
        confidence="medium",
    )
    return MarkdownJudgeContext(
        lab_id="lab7",
        part_id="02",
        part_title="Tools",
        requirement=requirement,
        deterministic_grade=deterministic_grade,
        deterministic_check=CheckResult(
            check_name="markdown_not_placeholder",
            passed=True,
            evidence_cells=[3],
            comment="Markdown evidence is present and does not look placeholder-only.",
        ),
        markdown_cells=[
            NotebookCell(
                index=3,
                cell_type="markdown",
                source=(
                    "Wymagany komentarz\n"
                    "Parser failures create business risk for allocation decisions."
                ),
                normalized_source=(
                    "Wymagany komentarz\n"
                    "Parser failures create business risk for allocation decisions."
                ),
            )
        ],
    )

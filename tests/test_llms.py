from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.models import (
    CheckResult,
    CodeJudgeContext,
    CodeJudgeResult,
    EvidenceIndex,
    MarkdownJudgeContext,
    MarkdownJudgeResult,
    NotebookCell,
    RequirementGrade,
    RequirementSpec,
)
from app.services import llms
from app.services.llms import (
    JudgeModelSettings,
    LangChainCodeJudge,
    LangChainMarkdownJudge,
    create_chat_model,
)


def test_create_chat_model_uses_configured_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, Any] = {}

    def stub_init_chat_model(**kwargs):
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.setattr(llms, "init_chat_model", stub_init_chat_model)

    model = create_chat_model(
        JudgeModelSettings(
            model="test/model",
            model_provider="test-provider",
            temperature=0.2,
        )
    )

    assert model is not None
    assert captured_kwargs == {
        "model": "test/model",
        "model_provider": "test-provider",
        "temperature": 0.2,
    }


def test_code_judge_invokes_structured_model_with_code_schema() -> None:
    expected_result = CodeJudgeResult(
        points_awarded=4,
        status="full",
        evidence_cells=[1],
        reasoning="The implementation satisfies the requirement.",
        comment="Complete implementation.",
        confidence="high",
    )
    chat_model = StubChatModel(expected_result)
    judge = LangChainCodeJudge(chat_model=chat_model)

    result = judge.judge_code(code_context())

    assert result == expected_result
    assert chat_model.schema is CodeJudgeResult
    assert len(chat_model.messages) == 2
    assert "code_schema" in str(chat_model.messages[1].content)


def test_markdown_judge_validates_dict_response() -> None:
    chat_model = StubChatModel(
        {
            "points_awarded": 6,
            "status": "partial",
            "evidence_cells": [2],
            "reasoning": "The reflection identifies risk but misses mitigation detail.",
            "comment": "Reflection is partially complete.",
            "confidence": "medium",
            "flags": ["missing_mitigation_detail"],
        }
    )
    judge = LangChainMarkdownJudge(chat_model=chat_model)

    result = judge.judge_markdown(markdown_context())

    assert result == MarkdownJudgeResult(
        points_awarded=6,
        status="partial",
        evidence_cells=[2],
        reasoning="The reflection identifies risk but misses mitigation detail.",
        comment="Reflection is partially complete.",
        confidence="medium",
        flags=["missing_mitigation_detail"],
    )
    assert chat_model.schema is MarkdownJudgeResult
    assert len(chat_model.messages) == 2
    assert "markdown_reflection" in str(chat_model.messages[1].content)


def test_malformed_structured_response_fails_validation() -> None:
    chat_model = StubChatModel(
        {
            "points_awarded": 1,
            "status": "full",
            "evidence_cells": [1],
            "comment": "Missing required reasoning field.",
            "confidence": "high",
        }
    )
    judge = LangChainCodeJudge(chat_model=chat_model)

    with pytest.raises(ValidationError):
        judge.judge_code(code_context())


class StubChatModel:
    def __init__(self, response) -> None:
        self.response = response
        self.schema = None
        self.messages = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.messages = messages
        return self.response


def code_context() -> CodeJudgeContext:
    requirement = RequirementSpec(
        id="code_schema",
        description="Defines a schema.",
        points=4,
    )
    return CodeJudgeContext(
        lab_id="lab7",
        part_id="02",
        part_title="Tools",
        requirement=requirement,
        deterministic_grade=RequirementGrade(
            requirement_id=requirement.id,
            bucket="code",
            points_awarded=4,
            points_possible=4,
            status="full",
            evidence_cells=[1],
            comment="Matched all markers.",
            confidence="high",
        ),
        code_cells=[
            NotebookCell(
                index=1,
                cell_type="code",
                source="class SupplierOffer:\n    pass\n",
                normalized_source="class SupplierOffer:\n    pass\n",
            )
        ],
        evidence_index=EvidenceIndex(classes={"SupplierOffer": [1]}),
    )


def markdown_context() -> MarkdownJudgeContext:
    requirement = RequirementSpec(
        id="markdown_reflection",
        description="Explains the risk.",
        points=8,
    )
    return MarkdownJudgeContext(
        lab_id="lab7",
        part_id="02",
        part_title="Tools",
        requirement=requirement,
        deterministic_grade=RequirementGrade(
            requirement_id=requirement.id,
            bucket="markdown",
            points_awarded=8,
            points_possible=8,
            status="full",
            evidence_cells=[2],
            comment="Markdown is present.",
            confidence="medium",
        ),
        deterministic_check=CheckResult(
            check_name="markdown_not_placeholder",
            passed=True,
            evidence_cells=[2],
            comment="Markdown evidence is present.",
        ),
        markdown_cells=[
            NotebookCell(
                index=2,
                cell_type="markdown",
                source="Parser failures create business risk.",
                normalized_source="Parser failures create business risk.",
            )
        ],
    )

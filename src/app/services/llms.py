from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from langchain.chat_models import init_chat_model

from app.models.judges import (
    CodeJudgeContext,
    CodeJudgeResult,
    MarkdownJudgeContext,
    MarkdownJudgeResult,
)
from app.prompts.code_judge import build_code_judge_messages
from app.prompts.markdown_judge import build_markdown_judge_messages


DEFAULT_JUDGE_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_JUDGE_PROVIDER = "openrouter"
DEFAULT_JUDGE_TEMPERATURE = 0.0


class CodeJudgeProtocol(Protocol):
    def judge_code(self, context: CodeJudgeContext) -> CodeJudgeResult:
        ...


class MarkdownJudgeProtocol(Protocol):
    def judge_markdown(self, context: MarkdownJudgeContext) -> MarkdownJudgeResult:
        ...


@dataclass(frozen=True)
class JudgeModelSettings:
    model: str = DEFAULT_JUDGE_MODEL
    model_provider: str = DEFAULT_JUDGE_PROVIDER
    temperature: float = DEFAULT_JUDGE_TEMPERATURE


def create_chat_model(settings: JudgeModelSettings | None = None) -> Any:
    selected_settings = settings or JudgeModelSettings()
    return init_chat_model(
        model=selected_settings.model,
        model_provider=selected_settings.model_provider,
        temperature=selected_settings.temperature,
    )


def create_code_judge(settings: JudgeModelSettings | None = None) -> LangChainCodeJudge:
    return LangChainCodeJudge(chat_model=create_chat_model(settings))


def create_markdown_judge(
    settings: JudgeModelSettings | None = None,
) -> LangChainMarkdownJudge:
    return LangChainMarkdownJudge(chat_model=create_chat_model(settings))


class LangChainCodeJudge:
    def __init__(self, chat_model: Any) -> None:
        self._structured_model = chat_model.with_structured_output(CodeJudgeResult)

    def judge_code(self, context: CodeJudgeContext) -> CodeJudgeResult:
        raw_result = self._structured_model.invoke(build_code_judge_messages(context))
        return _validate_judge_result(raw_result, CodeJudgeResult)


class LangChainMarkdownJudge:
    def __init__(self, chat_model: Any) -> None:
        self._structured_model = chat_model.with_structured_output(MarkdownJudgeResult)

    def judge_markdown(self, context: MarkdownJudgeContext) -> MarkdownJudgeResult:
        raw_result = self._structured_model.invoke(build_markdown_judge_messages(context))
        return _validate_judge_result(raw_result, MarkdownJudgeResult)


def _validate_judge_result(raw_result: Any, result_type):
    if isinstance(raw_result, result_type):
        return raw_result
    return result_type.model_validate(raw_result)

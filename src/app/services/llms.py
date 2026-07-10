from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from langchain.chat_models import init_chat_model
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langsmith import Client

from app.models.judges import (
    CodeJudgeContext,
    CodeJudgeResult,
    MarkdownJudgeContext,
    MarkdownJudgeResult,
)
from app.prompts.code_judge import build_code_judge_prompt, serialize_code_judge_context
from app.prompts.markdown_judge import (
    build_markdown_judge_prompt,
    serialize_markdown_judge_context,
)


DEFAULT_JUDGE_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_JUDGE_PROVIDER = "openrouter"
DEFAULT_JUDGE_TEMPERATURE = 0.0
DEFAULT_CODE_JUDGE_PROMPT = "code-judge:production"
DEFAULT_MARKDOWN_JUDGE_PROMPT = "markdown-judge:production"


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


@dataclass(frozen=True)
class JudgePromptSettings:
    code_judge_prompt: str = DEFAULT_CODE_JUDGE_PROMPT
    markdown_judge_prompt: str = DEFAULT_MARKDOWN_JUDGE_PROMPT

    @classmethod
    def from_environment(cls) -> JudgePromptSettings:
        return cls(
            code_judge_prompt=os.getenv("CODE_JUDGE_PROMPT", DEFAULT_CODE_JUDGE_PROMPT),
            markdown_judge_prompt=os.getenv(
                "MARKDOWN_JUDGE_PROMPT", DEFAULT_MARKDOWN_JUDGE_PROMPT
            ),
        )


def create_chat_model(settings: JudgeModelSettings | None = None) -> Any:
    selected_settings = settings or JudgeModelSettings()
    return init_chat_model(
        model=selected_settings.model,
        model_provider=selected_settings.model_provider,
        temperature=selected_settings.temperature,
    )


def create_code_judge(
    settings: JudgeModelSettings | None = None,
    prompt: ChatPromptTemplate | None = None,
) -> LangChainCodeJudge:
    return LangChainCodeJudge(
        chat_model=create_chat_model(settings),
        prompt=prompt or build_code_judge_prompt(),
    )


def create_markdown_judge(
    settings: JudgeModelSettings | None = None,
    prompt: ChatPromptTemplate | None = None,
) -> LangChainMarkdownJudge:
    return LangChainMarkdownJudge(
        chat_model=create_chat_model(settings),
        prompt=prompt or build_markdown_judge_prompt(),
    )


def create_langsmith_client() -> Client:
    return Client()


def pull_judge_prompt(client: Client, prompt_handle: str) -> ChatPromptTemplate:
    prompt = client.pull_prompt(prompt_handle)
    if not _is_judge_prompt_template(prompt):
        raise ValueError(
            f"LangSmith prompt {prompt_handle!r} must be a ChatPromptTemplate with "
            "one system message, one human message, and only the {context} variable."
        )
    return prompt


def _is_judge_prompt_template(prompt: object) -> bool:
    return (
        isinstance(prompt, ChatPromptTemplate)
        and prompt.input_variables == ["context"]
        and len(prompt.messages) == 2
        and isinstance(prompt.messages[0], SystemMessagePromptTemplate)
        and isinstance(prompt.messages[1], HumanMessagePromptTemplate)
    )


class LangChainCodeJudge:
    def __init__(self, chat_model: Any, prompt: ChatPromptTemplate | None = None) -> None:
        self._structured_model = chat_model.with_structured_output(CodeJudgeResult)
        self._chain = (prompt or build_code_judge_prompt()) | self._structured_model

    def judge_code(self, context: CodeJudgeContext) -> CodeJudgeResult:
        raw_result = self._chain.invoke({"context": serialize_code_judge_context(context)})
        return _validate_judge_result(raw_result, CodeJudgeResult)


class LangChainMarkdownJudge:
    def __init__(self, chat_model: Any, prompt: ChatPromptTemplate | None = None) -> None:
        self._structured_model = chat_model.with_structured_output(MarkdownJudgeResult)
        self._chain = (prompt or build_markdown_judge_prompt()) | self._structured_model

    def judge_markdown(self, context: MarkdownJudgeContext) -> MarkdownJudgeResult:
        raw_result = self._chain.invoke(
            {"context": serialize_markdown_judge_context(context)}
        )
        return _validate_judge_result(raw_result, MarkdownJudgeResult)


def _validate_judge_result(raw_result: Any, result_type):
    if isinstance(raw_result, result_type):
        return raw_result
    return result_type.model_validate(raw_result)

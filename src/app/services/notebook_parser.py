from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.models import NotebookCell, NotebookError, NotebookOutput, ParsedNotebook


HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
VISIBLE_MIME_TYPES = (
    "text/plain",
    "text/html",
    "application/json",
)


def parse_notebook(path: Path | str) -> ParsedNotebook:
    notebook_path = Path(path)

    try:
        raw_notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid notebook JSON: {notebook_path}") from exc

    cells = raw_notebook.get("cells") if isinstance(raw_notebook, dict) else None
    if not isinstance(cells, list):
        raise ValueError(f"Notebook is missing top-level cells list: {notebook_path}")

    return ParsedNotebook(
        path=notebook_path,
        metadata=_as_dict(raw_notebook.get("metadata", {})),
        cells=[
            _parse_cell(index=index, raw_cell=raw_cell)
            for index, raw_cell in enumerate(cells)
            if isinstance(raw_cell, dict)
        ],
    )


def _parse_cell(index: int, raw_cell: dict[str, Any]) -> NotebookCell:
    cell_type = _normalize_cell_type(raw_cell.get("cell_type"))
    source = _normalize_text(raw_cell.get("source"))
    outputs, output_text, errors = _parse_outputs(raw_cell.get("outputs"))

    return NotebookCell(
        index=index,
        cell_type=cell_type,
        source=source,
        normalized_source=_normalize_source(source),
        headings=_extract_headings(source) if cell_type == "markdown" else [],
        execution_count=raw_cell.get("execution_count") if cell_type == "code" else None,
        outputs=outputs,
        output_text=output_text,
        errors=errors,
    )


def _parse_outputs(raw_outputs: Any) -> tuple[list[NotebookOutput], str, list[NotebookError]]:
    if not isinstance(raw_outputs, list):
        return [], "", []

    outputs: list[NotebookOutput] = []
    output_text_parts: list[str] = []
    errors: list[NotebookError] = []

    for raw_output in raw_outputs:
        if not isinstance(raw_output, dict):
            continue

        output_type = str(raw_output.get("output_type", "unknown"))
        output = _parse_output(output_type, raw_output)
        outputs.append(output)

        if output.text:
            output_text_parts.append(output.text)
        if output.error is not None:
            errors.append(output.error)

    return outputs, "".join(output_text_parts), errors


def _parse_output(output_type: str, raw_output: dict[str, Any]) -> NotebookOutput:
    if output_type == "stream":
        return NotebookOutput(
            output_type=output_type,
            name=raw_output.get("name"),
            text=_normalize_text(raw_output.get("text")),
            raw=raw_output,
        )

    if output_type in {"execute_result", "display_data"}:
        data = _as_dict(raw_output.get("data", {}))
        return NotebookOutput(
            output_type=output_type,
            text=_extract_visible_data_text(data),
            data=data,
            raw=raw_output,
        )

    if output_type == "error":
        error = NotebookError(
            ename=str(raw_output.get("ename", "")),
            evalue=str(raw_output.get("evalue", "")),
            traceback=[
                str(traceback_line)
                for traceback_line in raw_output.get("traceback", [])
            ]
            if isinstance(raw_output.get("traceback"), list)
            else [],
        )
        return NotebookOutput(
            output_type=output_type,
            text=_format_error_text(error),
            error=error,
            raw=raw_output,
        )

    return NotebookOutput(
        output_type=output_type,
        text=_normalize_text(raw_output.get("text")),
        data=_as_dict(raw_output.get("data", {})),
        raw=raw_output,
    )


def _extract_visible_data_text(data: dict[str, Any]) -> str:
    text_parts: list[str] = []

    for mime_type in VISIBLE_MIME_TYPES:
        if mime_type in data:
            text_parts.append(_normalize_mime_value(data[mime_type]))

    if text_parts:
        return "".join(text_parts)

    json_like_parts = [
        _normalize_mime_value(value)
        for mime_type, value in data.items()
        if "json" in mime_type
    ]
    return "".join(json_like_parts)


def _normalize_mime_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _normalize_source(source: str) -> str:
    return source.replace("\r\n", "\n").replace("\r", "\n").strip()


def _extract_headings(source: str) -> list[str]:
    headings: list[str] = []

    for line in source.splitlines():
        match = HEADING_RE.match(line)
        if match is not None:
            headings.append(match.group(2).strip())

    return headings


def _format_error_text(error: NotebookError) -> str:
    summary = f"{error.ename}: {error.evalue}".strip(": ")
    if error.traceback:
        return "\n".join([summary, *error.traceback])
    return summary


def _normalize_cell_type(value: Any) -> str:
    if value in {"code", "markdown", "raw"}:
        return str(value)
    return "raw"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}

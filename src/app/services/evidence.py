from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable
from typing import Any

from app.models import NotebookCell, ParsedNotebook, SectionEvidence
from app.models.evidence import ApiScoreEvidence, EvidenceIndex, SecretFinding


SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|bearer)\b\s*=\s*['\"]([^'\"]{12,})['\"]"
)
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
BEARER_TOKEN_RE = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{20,})")
LONG_SECRET_RE = re.compile(r"['\"]([A-Za-z0-9_/\-+=]{32,})['\"]")
API_SCORE_KEYS = {"score", "max_score", "details", "id", "session_id", "leaderboard"}


def build_evidence_index(
    cells_or_container: Iterable[NotebookCell] | ParsedNotebook | SectionEvidence,
) -> EvidenceIndex:
    cells = _resolve_cells(cells_or_container)
    index = EvidenceIndex()

    for cell in cells:
        _index_code_features(index, cell)
        index.errors.extend(cell.errors)
        index.api_scores.extend(_extract_api_scores(cell))
        index.possible_secrets.extend(_detect_possible_secrets(cell))

    return index


def _resolve_cells(
    cells_or_container: Iterable[NotebookCell] | ParsedNotebook | SectionEvidence,
) -> list[NotebookCell]:
    if isinstance(cells_or_container, ParsedNotebook | SectionEvidence):
        return list(cells_or_container.cells)
    return list(cells_or_container)


def _index_code_features(index: EvidenceIndex, cell: NotebookCell) -> None:
    features = cell.code_features
    if features is None:
        return

    for function_name in features.functions:
        _append_cell(index.functions, function_name, cell.index)
    for class_name in features.classes:
        _append_cell(index.classes, class_name, cell.index)
    for import_name in [*features.imports, *features.from_imports]:
        _append_cell(index.imports, import_name, cell.index)
    for call_name in features.calls:
        _append_cell(index.calls, call_name, cell.index)


def _append_cell(mapping: dict[str, list[int]], key: str, cell_index: int) -> None:
    cell_indexes = mapping.setdefault(key, [])
    if cell_index not in cell_indexes:
        cell_indexes.append(cell_index)


def _extract_api_scores(cell: NotebookCell) -> list[ApiScoreEvidence]:
    api_scores: list[ApiScoreEvidence] = []
    seen: set[tuple[int, float | int | None, float | int | None, str]] = set()

    for candidate, raw_text in _iter_output_payloads(cell):
        api_score = _api_score_from_payload(cell.index, candidate, raw_text)
        if api_score is not None:
            key = (
                api_score.cell_index,
                api_score.score,
                api_score.max_score,
                json.dumps(api_score.details, ensure_ascii=False, sort_keys=True),
            )
            if key in seen:
                continue
            seen.add(key)
            api_scores.append(api_score)

    return api_scores


def _iter_output_payloads(cell: NotebookCell) -> Iterable[tuple[Any, str]]:
    for output in cell.outputs:
        if output.data:
            yield output.data, json.dumps(output.data, ensure_ascii=False, sort_keys=True)
            for value in output.data.values():
                yield value, _payload_to_text(value)
        if output.text:
            yield output.text, output.text

    if cell.output_text:
        yield cell.output_text, cell.output_text


def _api_score_from_payload(
    cell_index: int,
    payload: Any,
    raw_text: str,
) -> ApiScoreEvidence | None:
    parsed_payload = _parse_payload(payload)
    if not isinstance(parsed_payload, dict):
        return None
    if not API_SCORE_KEYS.intersection(parsed_payload):
        return None
    if "score" not in parsed_payload and "max_score" not in parsed_payload:
        return None

    return ApiScoreEvidence(
        cell_index=cell_index,
        score=_number_or_none(parsed_payload.get("score")),
        max_score=_number_or_none(parsed_payload.get("max_score")),
        details=parsed_payload.get("details"),
        raw_text=raw_text.strip(),
    )


def _parse_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        if "application/json" in payload:
            return _parse_payload(payload["application/json"])
        if "text/plain" in payload:
            parsed_text = _parse_payload(payload["text/plain"])
            if isinstance(parsed_text, dict):
                return parsed_text
        return payload

    if isinstance(payload, list):
        return _parse_payload("".join(str(item) for item in payload))

    if not isinstance(payload, str):
        return payload

    text = payload.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None


def _payload_to_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        return "".join(str(item) for item in payload)
    if isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return str(payload)


def _number_or_none(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def _detect_possible_secrets(cell: NotebookCell) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for text in _secret_scan_texts(cell):
        findings.extend(_detect_secrets_in_text(cell.index, text))
    return _deduplicate_secret_findings(findings)


def _secret_scan_texts(cell: NotebookCell) -> Iterable[str]:
    if cell.source:
        yield cell.source
    for output in cell.outputs:
        if output.text:
            yield output.text
        if output.data:
            yield _payload_to_text(output.data)
    if cell.output_text:
        yield cell.output_text


def _detect_secrets_in_text(cell_index: int, text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []

    for match in SECRET_ASSIGNMENT_RE.finditer(text):
        findings.append(
            SecretFinding(
                cell_index=cell_index,
                kind=match.group(1).lower().replace("-", "_"),
                snippet=_redact_secret(match.group(2)),
                confidence="high",
            )
        )

    for match in OPENAI_KEY_RE.finditer(text):
        findings.append(
            SecretFinding(
                cell_index=cell_index,
                kind="openai_api_key",
                snippet=_redact_secret(match.group(0)),
                confidence="high",
            )
        )

    for match in BEARER_TOKEN_RE.finditer(text):
        findings.append(
            SecretFinding(
                cell_index=cell_index,
                kind="bearer_token",
                snippet=_redact_secret(match.group(1)),
                confidence="medium",
            )
        )

    for match in LONG_SECRET_RE.finditer(text):
        value = match.group(1)
        if _looks_high_entropy(value):
            findings.append(
                SecretFinding(
                    cell_index=cell_index,
                    kind="long_secret_literal",
                    snippet=_redact_secret(value),
                    confidence="medium",
                )
            )

    return findings


def _looks_high_entropy(value: str) -> bool:
    if len(value) < 32:
        return False
    character_classes = sum(
        bool(pattern.search(value))
        for pattern in (
            re.compile(r"[a-z]"),
            re.compile(r"[A-Z]"),
            re.compile(r"\d"),
            re.compile(r"[_/\-+=]"),
        )
    )
    return character_classes >= 3


def _redact_secret(value: str) -> str:
    if len(value) <= 12:
        return value
    return f"{value[:4]}...{value[-4:]}"


def _deduplicate_secret_findings(findings: list[SecretFinding]) -> list[SecretFinding]:
    seen: set[tuple[int, str, str]] = set()
    unique_findings: list[SecretFinding] = []
    for finding in findings:
        key = (finding.cell_index, finding.kind, finding.snippet)
        if key in seen:
            continue
        seen.add(key)
        unique_findings.append(finding)
    return unique_findings

from __future__ import annotations

import ast
import re
from collections.abc import Iterable

from app.models import CodeFeatures, CodeMarkerFinding, NotebookCell


FALLBACK_FUNCTION_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE)
FALLBACK_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b", re.MULTILINE)
CLASS_MARKER_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b")
FUNCTION_MARKER_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_]\w*)\b")
BARE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")


def extract_code_features(source: str) -> CodeFeatures:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return CodeFeatures(
            functions=_unique(FALLBACK_FUNCTION_RE.findall(source)),
            classes=_unique(FALLBACK_CLASS_RE.findall(source)),
            syntax_error=_format_syntax_error(exc),
        )

    visitor = _CodeFeatureVisitor()
    visitor.visit(tree)
    return CodeFeatures(
        functions=_unique(visitor.functions),
        classes=_unique(visitor.classes),
        imports=_unique(visitor.imports),
        from_imports=_unique(visitor.from_imports),
        calls=_unique(visitor.calls),
    )


def match_code_markers(
    cells: Iterable[NotebookCell],
    markers: Iterable[str],
) -> list[CodeMarkerFinding]:
    code_cells = [cell for cell in cells if cell.cell_type == "code"]
    return [_match_code_marker(code_cells, marker) for marker in markers]


class _CodeFeatureVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[str] = []
        self.classes: list[str] = []
        self.imports: list[str] = []
        self.from_imports: list[str] = []
        self.calls: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            imported_name = f"{module}.{alias.name}" if module else alias.name
            self.from_imports.append(imported_name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        if call_name is not None:
            self.calls.append(call_name)
        self.generic_visit(node)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent_name = _call_name(node.value)
        if parent_name is None:
            return node.attr
        return f"{parent_name}.{node.attr}"
    return None


def _match_code_marker(
    code_cells: list[NotebookCell],
    marker: str,
) -> CodeMarkerFinding:
    normalized_marker = marker.strip()
    kind, feature_name = _marker_kind_and_name(normalized_marker)

    matched_cells: list[int] = []
    for cell in code_cells:
        if _cell_matches_marker(cell, normalized_marker, kind, feature_name):
            matched_cells.append(cell.index)

    matched = bool(matched_cells)
    return CodeMarkerFinding(
        marker=marker,
        matched=matched,
        kind=kind,
        evidence_cells=matched_cells,
        comment=_marker_comment(normalized_marker, kind, matched_cells),
    )


def _marker_kind_and_name(marker: str) -> tuple[str, str]:
    class_match = CLASS_MARKER_RE.match(marker)
    if class_match is not None:
        return "class", class_match.group(1)

    function_match = FUNCTION_MARKER_RE.match(marker)
    if function_match is not None:
        return "function", function_match.group(1)

    if BARE_IDENTIFIER_RE.match(marker) is not None:
        return "identifier", marker

    return "source", marker


def _cell_matches_marker(
    cell: NotebookCell,
    marker: str,
    kind: str,
    feature_name: str,
) -> bool:
    features = cell.code_features
    if kind == "class":
        return features is not None and feature_name in features.classes
    if kind == "function":
        return features is not None and feature_name in features.functions
    if kind == "identifier":
        return _identifier_matches_features(feature_name, features) or _source_contains(
            cell.source,
            marker,
        )
    return _source_contains(cell.source, marker)


def _identifier_matches_features(name: str, features: CodeFeatures | None) -> bool:
    if features is None:
        return False
    return (
        name in features.classes
        or name in features.functions
        or name in features.calls
        or name in features.imports
        or name in features.from_imports
    )


def _source_contains(source: str, marker: str) -> bool:
    return _normalize_marker_text(marker) in _normalize_marker_text(source)


def _normalize_marker_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def _marker_comment(marker: str, kind: str, matched_cells: list[int]) -> str:
    if matched_cells:
        cells = ", ".join(str(cell_index) for cell_index in matched_cells)
        return f"Matched {kind} marker `{marker}` in cell(s): {cells}."
    return f"Missing {kind} marker `{marker}`."


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)

    return unique_values


def _format_syntax_error(exc: SyntaxError) -> str:
    location = f"line {exc.lineno}" if exc.lineno is not None else "unknown line"
    return f"{exc.msg} ({location})"

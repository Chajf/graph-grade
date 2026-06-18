from __future__ import annotations

import ast
import re

from app.models import CodeFeatures


FALLBACK_FUNCTION_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE)
FALLBACK_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b", re.MULTILINE)


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

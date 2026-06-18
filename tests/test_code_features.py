from app.models import NotebookCell
from app.services.code_features import extract_code_features, match_code_markers


def test_extract_code_features_from_valid_python() -> None:
    features = extract_code_features(
        """
import json
import pandas as pd
from langchain.agents import create_agent
from .helpers import tool

class LabAgent:
    def run(self):
        return self.client.invoke()

async def build_agent():
    agent = create_agent()
    print(agent)
"""
    )

    assert features.functions == ["run", "build_agent"]
    assert features.classes == ["LabAgent"]
    assert features.imports == ["json", "pandas"]
    assert features.from_imports == ["langchain.agents.create_agent", ".helpers.tool"]
    assert features.calls == ["self.client.invoke", "create_agent", "print"]
    assert features.syntax_error is None


def test_extract_code_features_uses_fallback_for_invalid_python() -> None:
    features = extract_code_features(
        """
class BrokenAgent
def build_agent(
async def async_agent(
"""
    )

    assert features.functions == ["build_agent", "async_agent"]
    assert features.classes == ["BrokenAgent"]
    assert features.imports == []
    assert features.from_imports == []
    assert features.calls == []
    assert features.syntax_error is not None


def test_extract_code_features_deduplicates_in_discovery_order() -> None:
    features = extract_code_features(
        """
def repeated():
    pass

def repeated():
    pass

repeated()
repeated()
"""
    )

    assert features.functions == ["repeated"]
    assert features.calls == ["repeated"]


def test_match_code_markers_detects_class_and_function_markers() -> None:
    cells = [
        code_cell(
            3,
            """
class SupplierOffer:
    pass

def parse_supplier_offer(raw_offer):
    return raw_offer
""",
        )
    ]

    findings = match_code_markers(
        cells,
        ["class SupplierOffer", "def parse_supplier_offer"],
    )

    assert [finding.matched for finding in findings] == [True, True]
    assert [finding.kind for finding in findings] == ["class", "function"]
    assert [finding.evidence_cells for finding in findings] == [[3], [3]]


def test_match_code_markers_detects_async_function_marker() -> None:
    findings = match_code_markers(
        [
            code_cell(
                1,
                """
async def fetch_supplier_offer():
    return {}
""",
            )
        ],
        ["async def fetch_supplier_offer"],
    )

    assert findings[0].matched is True
    assert findings[0].kind == "function"
    assert findings[0].evidence_cells == [1]


def test_match_code_markers_matches_bare_identifier_against_features() -> None:
    findings = match_code_markers(
        [
            code_cell(
                4,
                """
import json

def parse_supplier_offer(raw_offer):
    return json.loads(raw_offer)
""",
            )
        ],
        ["json.loads", "json", "parse_supplier_offer"],
    )

    assert [finding.matched for finding in findings] == [True, True, True]
    assert [finding.evidence_cells for finding in findings] == [[4], [4], [4]]


def test_match_code_markers_uses_source_substring_for_non_identifier_marker() -> None:
    findings = match_code_markers(
        [
            code_cell(
                2,
                """
result = {
    "recommendation": "choose supplier A",
}
""",
            )
        ],
        ['"recommendation": "choose supplier A"'],
    )

    assert findings[0].matched is True
    assert findings[0].kind == "source"
    assert findings[0].evidence_cells == [2]


def test_match_code_markers_reports_missing_marker() -> None:
    findings = match_code_markers(
        [code_cell(5, "class SupplierOffer:\n    pass\n")],
        ["def parse_supplier_offer"],
    )

    assert findings[0].matched is False
    assert findings[0].kind == "function"
    assert findings[0].evidence_cells == []
    assert "Missing" in findings[0].comment


def test_match_code_markers_uses_fallback_features_for_invalid_python() -> None:
    findings = match_code_markers(
        [
            code_cell(
                6,
                """
class SupplierOffer
def parse_supplier_offer(
""",
            )
        ],
        ["class SupplierOffer", "def parse_supplier_offer"],
    )

    assert [finding.matched for finding in findings] == [True, True]
    assert [finding.evidence_cells for finding in findings] == [[6], [6]]


def code_cell(index: int, source: str) -> NotebookCell:
    return NotebookCell(
        index=index,
        cell_type="code",
        source=source,
        normalized_source=source.strip(),
        code_features=extract_code_features(source),
    )

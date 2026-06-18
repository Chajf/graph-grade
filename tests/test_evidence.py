from app.models import NotebookCell, NotebookError, NotebookOutput, ParsedNotebook
from app.services.code_features import extract_code_features
from app.services.evidence import build_evidence_index


def test_build_evidence_index_maps_code_features_to_cells() -> None:
    index = build_evidence_index(
        [
            code_cell(
                2,
                """
import json

class SupplierOffer:
    pass

def parse_supplier_offer(raw_offer):
    return json.loads(raw_offer)
""",
            )
        ]
    )

    assert index.classes["SupplierOffer"] == [2]
    assert index.functions["parse_supplier_offer"] == [2]
    assert index.imports["json"] == [2]
    assert index.calls["json.loads"] == [2]


def test_build_evidence_index_collects_error_outputs() -> None:
    error = NotebookError(ename="ValueError", evalue="bad value")
    index = build_evidence_index(
        [
            NotebookCell(
                index=1,
                cell_type="code",
                source="raise ValueError('bad value')",
                normalized_source="raise ValueError('bad value')",
                errors=[error],
            )
        ]
    )

    assert index.errors == [error]


def test_build_evidence_index_extracts_api_score_from_json_output() -> None:
    index = build_evidence_index(
        [
            NotebookCell(
                index=3,
                cell_type="code",
                source="result",
                normalized_source="result",
                outputs=[
                    NotebookOutput(
                        output_type="execute_result",
                        text='{"score": 7, "max_score": 10, "details": {"ok": true}}',
                        data={
                            "application/json": {
                                "score": 7,
                                "max_score": 10,
                                "details": {"ok": True},
                            }
                        },
                    )
                ],
                output_text='{"score": 7, "max_score": 10, "details": {"ok": true}}',
            )
        ]
    )

    assert len(index.api_scores) == 1
    assert index.api_scores[0].cell_index == 3
    assert index.api_scores[0].score == 7
    assert index.api_scores[0].max_score == 10
    assert index.api_scores[0].details == {"ok": True}


def test_build_evidence_index_detects_likely_hardcoded_secrets() -> None:
    index = build_evidence_index(
        [
            code_cell(
                4,
                """
API_KEY = "sk-abc1234567890abc1234567890abc1234567890"
token = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
""",
            )
        ]
    )

    assert {finding.kind for finding in index.possible_secrets} >= {
        "api_key",
        "openai_api_key",
        "token",
    }
    assert all("..." in finding.snippet for finding in index.possible_secrets)


def test_build_evidence_index_accepts_parsed_notebook_container(tmp_path) -> None:
    notebook = ParsedNotebook(
        path=tmp_path / "lab.ipynb",
        cells=[
            code_cell(
                0,
                """
class SupplierOffer:
    pass
""",
            )
        ],
    )

    index = build_evidence_index(notebook)

    assert index.classes == {"SupplierOffer": [0]}


def code_cell(index: int, source: str) -> NotebookCell:
    normalized_source = source.strip()
    return NotebookCell(
        index=index,
        cell_type="code",
        source=source,
        normalized_source=normalized_source,
        code_features=extract_code_features(source),
    )

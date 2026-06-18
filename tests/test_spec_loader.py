from pathlib import Path

from app.repositories import GradingSpecRepository, load_lab_spec


SPECS_ROOT = Path("work/grading_specs")


def test_load_lab7_spec_metadata() -> None:
    spec = load_lab_spec(SPECS_ROOT, "lab7")

    assert spec.lab_id == "lab7"
    assert spec.title == "Lab 7 – Agenci z LangChain: asystent przetargowy"
    assert spec.language == "pl"
    assert spec.total_points == 100
    assert spec.expected_notebook_pattern == "lab7_*.ipynb"
    assert spec.required_files == []


def test_load_lab7_spec_preserves_part_order() -> None:
    spec = GradingSpecRepository(SPECS_ROOT).load_lab_spec("lab7")

    assert [part.part_id for part in spec.parts] == ["01", "02", "03", "04", "05", "06"]
    assert [part.title for part in spec.parts] == [
        "LangChain initialization and first agent",
        "Tools: parsing, TOPSIS, and LP allocation",
        "Structured Output with ProviderStrategy",
        "Full procurement agent pipeline",
        "API challenge: unique RFP",
        "Summary and checklist",
    ]


def test_load_lab7_first_part_requirements() -> None:
    spec = load_lab_spec(SPECS_ROOT, "lab7")
    first_part = spec.parts[0]

    assert first_part.start_heading == "## Część 1 – LangChain: inicjalizacja modelu i pierwszy agent"
    assert first_part.end_heading == "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP"
    assert first_part.code_applicable is True
    assert first_part.markdown_applicable is True
    assert first_part.results_applicable is True
    assert [requirement.id for requirement in first_part.code_requirements] == [
        "lab7_part01_llm_initialization",
        "lab7_part01_first_tool_agent",
    ]
    assert first_part.markdown_requirements[0].points == 3

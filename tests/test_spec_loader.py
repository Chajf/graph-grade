from pathlib import Path

from app.repositories import GradingSpecRepository, load_lab_spec


def write_lab7_spec(specs_root: Path) -> None:
    lab_dir = specs_root / "labs" / "lab7"
    parts_dir = lab_dir / "parts"
    parts_dir.mkdir(parents=True)
    (lab_dir / "notebook.yaml").write_text(
        """
lab_id: "lab7"
title: "Lab 7 – Agenci z LangChain: asystent przetargowy"
language: "pl"
expected_submission:
  notebook_pattern: "lab7_*.ipynb"
  required_files: []
grading:
  total_points: 100
  parts_dir: "parts"
  part_files:
    - "01_first_agent.yaml"
    - "02_tools_topsis_lp.yaml"
    - "03_structured_output.yaml"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "01_first_agent.yaml").write_text(
        """
part_id: "01"
title: "LangChain initialization and first agent"
source_heading: "## Część 1 – LangChain: inicjalizacja modelu i pierwszy agent"
cell_range:
  start_heading: "## Część 1 – LangChain: inicjalizacja modelu i pierwszy agent"
  end_heading: "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP"
requirements:
  code:
    - id: "lab7_part01_llm_initialization"
      description: "Initializes model and model_fast."
      points: 3
      evidence:
        cell_markers:
          - "init_chat_model"
    - id: "lab7_part01_first_tool_agent"
      description: "Defines a first tool agent."
      points: 4
      evidence:
        cell_markers:
          - "create_agent"
  markdown:
    - id: "lab7_part01_first_agent_reflection"
      description: "Explains the first agent."
      points: 3
      evidence:
        heading_or_text: "## Część 1 – LangChain: inicjalizacja modelu i pierwszy agent"
  results:
    - id: "lab7_part01_executed_cells"
      description: "Required code cells are executed."
      points: 0
      checks:
        - "required_code_cells_have_execution_count_or_equivalent_visible_outputs"
  code_applicability: "required"
  markdown_applicability: "required"
  results_applicability: "required"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "02_tools_topsis_lp.yaml").write_text(
        """
part_id: "02"
title: "Tools: parsing, TOPSIS, and LP allocation"
source_heading: "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP"
cell_range:
  start_heading: "## Część 2 – Narzędzia `@tool`: parsowanie, TOPSIS, LP"
  end_heading: "## Część 3 – Structured output"
requirements:
  code: []
  markdown: []
  results: []
  code_applicability: "required"
  markdown_applicability: "required"
  results_applicability: "required"
""".lstrip(),
        encoding="utf-8",
    )
    (parts_dir / "03_structured_output.yaml").write_text(
        """
part_id: "03"
title: "Structured Output with ProviderStrategy"
source_heading: "## Część 3 – Structured output"
cell_range:
  start_heading: "## Część 3 – Structured output"
  end_heading: null
requirements:
  code: []
  markdown: []
  results: []
  code_applicability: "required"
  markdown_applicability: "required"
  results_applicability: "required"
""".lstrip(),
        encoding="utf-8",
    )


def test_load_lab7_spec_metadata(tmp_path: Path) -> None:
    specs_root = tmp_path / "grading_specs"
    write_lab7_spec(specs_root)

    spec = load_lab_spec(specs_root, "lab7")

    assert spec.lab_id == "lab7"
    assert spec.title == "Lab 7 – Agenci z LangChain: asystent przetargowy"
    assert spec.language == "pl"
    assert spec.total_points == 100
    assert spec.expected_notebook_pattern == "lab7_*.ipynb"
    assert spec.required_files == []


def test_load_lab7_spec_preserves_part_order(tmp_path: Path) -> None:
    specs_root = tmp_path / "grading_specs"
    write_lab7_spec(specs_root)

    spec = GradingSpecRepository(specs_root).load_lab_spec("lab7")

    assert [part.part_id for part in spec.parts] == ["01", "02", "03"]
    assert [part.title for part in spec.parts] == [
        "LangChain initialization and first agent",
        "Tools: parsing, TOPSIS, and LP allocation",
        "Structured Output with ProviderStrategy",
    ]


def test_load_lab7_first_part_requirements(tmp_path: Path) -> None:
    specs_root = tmp_path / "grading_specs"
    write_lab7_spec(specs_root)

    spec = load_lab_spec(specs_root, "lab7")
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

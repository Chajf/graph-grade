# Graph Grade

`graph-grade` is a Python CLI for grading Jupyter notebook submissions exported from
Teams/SharePoint. It resolves student notebooks from a predictable folder layout,
loads YAML grading specifications, grades notebook sections, and writes JSON and
Markdown feedback artifacts for students and lab groups.

The first working version supports:

- parsing notebooks into a compact JSON summary;
- grading one student submission for one lab;
- grading all resolved submissions in a lab group;
- dry-running group grading to inspect notebook resolution before writing results;
- optional LLM judge refinement for code and Markdown requirements.

## Requirements

- Python 3.12 or newer
- `uv`
- notebook submissions exported into the expected `prace` folder structure
- YAML grading specs for each lab
- an OpenRouter-compatible API key only when `--llm-judges` is enabled

Install dependencies from the repository root:

```bash
uv sync
```

Run CLI commands with:

```bash
PYTHONPATH=src uv run python -m app.main --help
```

## Input Layout

### Student submissions

`graph-grade` expects SharePoint/Teams submissions under a root directory passed as
`--prace-root`.

```text
prace/
  <group-id>/
    <student-folder>/
      <lab-id>/
        Wersja 1/
          <notebook>.ipynb
          <required-files>
        Wersja 2/
          <notebook>.ipynb
          <required-files>
```

Example:

```text
prace/
  lab1/
    Jan_Kowalski/
      lab7/
        Wersja 1/
          lab7_Kowalski.ipynb
          data.csv
```

Resolution rules:

- the lab folder must match `lab_id`;
- the newest numbered `Wersja N` folder is selected;
- the notebook is matched first by the spec `notebook_pattern`, then by
  `<lab-id>*.ipynb`;
- if multiple notebooks match, the submission is marked as ambiguous;
- required files are searched in the selected version folder first, then in the lab
  folder.

### Grading specs

Specs are loaded from `--specs-dir` or `--specs-root`. If omitted, the default is
`work/grading_specs`.

```text
work/grading_specs/
  labs/
    <lab-id>/
      notebook.yaml
      parts/
        01_part.yaml
        02_part.yaml
```

Minimal `notebook.yaml`:

```yaml
lab_id: "lab7"
title: "Lab 7"
language: "pl"
expected_submission:
  notebook_pattern: "lab7_*.ipynb"
  required_files:
    - "data.csv"
grading:
  total_points: 12
  parts_dir: "parts"
  part_files:
    - "01_schema.yaml"
    - "02_reflection.yaml"
```

Minimal part file:

```yaml
part_id: "01"
title: "Schema"
source_heading: "## Part 1"
cell_range:
  start_heading: "## Part 1"
  end_heading: "## Part 2"
requirements:
  code:
    - id: "code_schema"
      description: "Defines supplier schema and parser."
      points: 4
      evidence:
        cell_markers:
          - "class SupplierOffer"
          - "def parse_supplier_offer"
  markdown: []
  results: []
```

Requirement groups:

- `code` checks implementation evidence in code cells;
- `markdown` checks written answers in Markdown cells;
- `results` checks notebook outputs and expected results;
- `code_applicability`, `markdown_applicability`, and `results_applicability` may
  be set to `required`, `optional`, or `not_applicable`.

## CLI Usage

### Inspect available commands

```bash
PYTHONPATH=src uv run python -m app.main --help
```

Commands:

- `parse-notebook` - parse one notebook and print a compact JSON summary;
- `grade-student` - grade one resolved student submission;
- `grade-group` - grade all resolved submissions for a group.

### Parse a notebook

Use this command to confirm that a notebook can be read and to inspect cell counts,
outputs, detected functions, and detected classes.

```bash
PYTHONPATH=src uv run python -m app.main parse-notebook \
  --notebook-path prace/lab1/Jan_Kowalski/lab7/Wersja\ 1/lab7_Kowalski.ipynb
```

The command prints JSON similar to:

```json
{
  "classes": ["SupplierOffer"],
  "code_cell_count": 3,
  "error_count": 0,
  "functions": ["parse_supplier_offer"],
  "markdown_cell_count": 4,
  "output_count": 2,
  "path": "prace/lab1/Jan_Kowalski/lab7/Wersja 1/lab7_Kowalski.ipynb",
  "raw_cell_count": 0,
  "total_cells": 7
}
```

### Dry-run group grading

Run a dry run before grading a full group. It loads the lab spec and reports which
students are resolved, unresolved, or ambiguous without writing grading results.

```bash
PYTHONPATH=src uv run python -m app.main grade-group \
  --dry-run \
  --prace-root prace \
  --specs-root work/grading_specs \
  --group lab1 \
  --lab lab7
```

The dry-run JSON includes:

- lab metadata and total points;
- each student folder;
- resolved notebook path;
- required files found or missing;
- issue code and candidate paths for unresolved or ambiguous submissions.

### Grade one student

```bash
PYTHONPATH=src uv run python -m app.main grade-student \
  --prace-root prace \
  --specs-root work/grading_specs \
  --output-root work/grading_results \
  --group lab1 \
  --student Jan_Kowalski \
  --lab lab7
```

On success, the command exits with code `0` and prints JSON containing paths to
the generated artifacts:

```json
{
  "feedback_path": "work/grading_results/lab7/lab1/Jan_Kowalski/feedback.md",
  "grade_path": "work/grading_results/lab7/lab1/Jan_Kowalski/grade.json",
  "group_id": "lab1",
  "lab_id": "lab7",
  "points_awarded": 12,
  "points_possible": 12,
  "status": "graded",
  "student_folder": "Jan_Kowalski",
  "student_summary_path": "work/grading_results/lab1/Jan_Kowalski/summary.md"
}
```

If the submission cannot be resolved, the command exits with code `1` and prints
the issue details as JSON.

### Grade a full group

```bash
PYTHONPATH=src uv run python -m app.main grade-group \
  --prace-root prace \
  --specs-root work/grading_specs \
  --output-root work/grading_results \
  --group lab1 \
  --lab lab7
```

`grade-group` grades resolved submissions, skips unresolved submissions, and writes
group summaries. It requires `--output-root` unless `--dry-run` is used.

The command prints JSON similar to:

```json
{
  "failed_count": 0,
  "graded_count": 20,
  "group_id": "lab1",
  "lab_id": "lab7",
  "laboratory_errors": [],
  "skipped_count": 2,
  "summary_csv_path": "work/grading_results/lab7/lab1/group_summary.csv",
  "summary_md_path": "work/grading_results/lab7/lab1/group_summary.md"
}
```

## LLM Judge Refinement

By default, grading uses deterministic checks derived from the grading spec and
notebook evidence. Add `--llm-judges` to enable LLM refinement for code and
Markdown requirements.

```bash
PYTHONPATH=src uv run python -m app.main grade-student \
  --prace-root prace \
  --specs-root work/grading_specs \
  --output-root work/grading_results \
  --group lab1 \
  --student Jan_Kowalski \
  --lab lab7 \
  --llm-judges \
  --judge-provider openrouter \
  --judge-model deepseek/deepseek-v4-flash \
  --judge-temperature 0
```

Before using LangSmith-backed OpenRouter judges, export both API keys:

```bash
export OPENROUTER_API_KEY="..."
export LANGSMITH_API_KEY="lsv2_..."
```

The judges pull the following LangSmith prompt handles by default:

- `CODE_JUDGE_PROMPT=code-judge:production`
- `MARKDOWN_JUDGE_PROMPT=markdown-judge:production`

Set either variable to override its handle, including with a LangSmith tag or
commit hash. Each remote prompt must be a `ChatPromptTemplate` containing one
system message and one human `{context}` message. If LangSmith client
initialization, a prompt pull, or prompt validation fails, grading prints a
warning to stderr and uses the equivalent in-repository prompt instead.

Judge options:

- `--llm-judges` enables LLM code and Markdown judges;
- `--judge-provider` defaults to `openrouter`;
- `--judge-model` defaults to `deepseek/deepseek-v4-flash`;
- `--judge-temperature` defaults to `0.0`.

## Output Files

For one graded student:

```text
work/grading_results/
  <lab-id>/
    <group-id>/
      <student-folder>/
        grade.json
        feedback.md
  <group-id>/
    <student-folder>/
      summary.md
```

For group grading:

```text
work/grading_results/
  <lab-id>/
    <group-id>/
      group_summary.csv
      group_summary.md
      <student-folder>/
        grade.json
        feedback.md
```

Artifact meanings:

- `grade.json` contains machine-readable final grades, section grades,
  requirement grades, statuses, evidence cells, flags, and comments;
- `feedback.md` contains student-facing lab feedback;
- `summary.md` accumulates one student's results across labs;
- `group_summary.csv` and `group_summary.md` summarize all submissions for one
  group and lab, including skipped submissions and human-review flags.

## Common Workflow

1. Export Teams/SharePoint submissions into the `prace` layout.
2. Create or update the lab YAML spec under `work/grading_specs/labs/<lab-id>/`.
3. Run `parse-notebook` on a sample notebook if the structure is uncertain.
4. Run `grade-group --dry-run` and resolve missing or ambiguous notebooks.
5. Run `grade-student` for a single known submission to validate the spec.
6. Run `grade-group` for the full group.
7. Review `group_summary.md`, `group_summary.csv`, and any rows marked for human
   review.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `missing_lab_folder` | The student folder does not contain a lab folder matching `--lab`. |
| `missing_version_folder` | The lab folder does not contain a usable `Wersja N` folder. |
| `missing_notebook` | The selected version folder has no `.ipynb` file. |
| `ambiguous_notebook` | More than one notebook matched. Remove extras or tighten `notebook_pattern`. |
| Required files are missing | Put required files in the selected `Wersja N` folder or the lab folder. |
| `grade-group requires --output-root` | Add `--output-root` or use `--dry-run`. |
| LLM judge authentication fails | Verify the provider configuration and `OPENROUTER_API_KEY`. |
| LangSmith prompt falls back locally | Verify `LANGSMITH_API_KEY`, the configured prompt handle, and its required `ChatPromptTemplate` contract. |

## Development

Run the test suite:

```bash
PYTHONPATH=src uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Key source anchors:

- CLI entry point: `src/app/main.py`
- SharePoint submission resolution: `src/app/repositories/sharepoint.py`
- grading spec loading: `src/app/repositories/grading_specs.py`
- result persistence: `src/app/nodes/result_persister.py`
- group summaries: `src/app/repositories/results.py`

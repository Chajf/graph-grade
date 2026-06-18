from __future__ import annotations

from collections.abc import Callable

from app.models import CheckResult, EvidenceIndex, RequirementSpec, SectionEvidence


CheckHandler = Callable[[SectionEvidence, EvidenceIndex], CheckResult]

OUTPUT_PRESENCE_CHECKS = {
    "model_training_outputs_present",
    "shap_outputs_present",
    "output_present_for_predict_churn_test",
    "output_present_for_agent_scenarios",
    "output_present_for_full_agent_run",
    "test_invoke_output_present",
    "agent_test_outputs_present",
    "token_usage_visible",
    "mini_rag_outputs_present",
    "metrics_outputs_present",
}

def run_named_check(
    check_name: str,
    section: SectionEvidence,
    evidence_index: EvidenceIndex,
) -> CheckResult:
    check_handler = CHECK_REGISTRY.get(check_name)
    if check_handler is None:
        return CheckResult(
            check_name=check_name,
            passed=False,
            comment=f"Unknown deterministic result check `{check_name}`.",
            severity="warning",
        )

    return check_handler(section, evidence_index)


def run_result_checks(
    section: SectionEvidence,
    requirement: RequirementSpec,
    evidence_index: EvidenceIndex,
) -> list[CheckResult]:
    return [
        run_named_check(check_name, section, evidence_index)
        for check_name in requirement.checks
    ]


def _check_required_code_cells_executed(section: SectionEvidence) -> CheckResult:
    missing_cells = [
        cell.index
        for cell in section.code_cells
        if cell.execution_count is None and not _cell_has_visible_output(cell)
    ]
    passed = bool(section.code_cells) and not missing_cells

    return CheckResult(
        check_name="required_code_cells_have_execution_count_or_equivalent_visible_outputs",
        passed=passed,
        evidence_cells=[cell.index for cell in section.code_cells if cell.index not in missing_cells],
        comment=(
            "All required code cells have execution counts or visible outputs."
            if passed
            else _missing_execution_comment(section, missing_cells)
        ),
        severity="critical" if not passed else "info",
    )


def _check_no_error_outputs(section: SectionEvidence) -> CheckResult:
    error_cells = [cell.index for cell in section.code_cells if cell.errors]
    passed = not error_cells and not section.errors

    return CheckResult(
        check_name="no_error_outputs_in_required_cells",
        passed=passed,
        evidence_cells=error_cells,
        comment=(
            "No error outputs found in required cells."
            if passed
            else f"Error outputs found in cell(s): {_format_cells(error_cells)}."
        ),
        severity="critical" if not passed else "info",
    )


def _check_api_response_visible(
    section: SectionEvidence,
    evidence_index: EvidenceIndex,
) -> CheckResult:
    section_cell_indexes = _section_cell_indexes(section)
    api_score_cells = [
        score.cell_index
        for score in evidence_index.api_scores
        if score.cell_index in section_cell_indexes
    ]
    passed = bool(api_score_cells)

    return CheckResult(
        check_name="api_response_visible",
        passed=passed,
        evidence_cells=_unique(api_score_cells),
        comment=(
            f"Visible API score output found in cell(s): {_format_cells(api_score_cells)}."
            if passed
            else "No visible API score output found in this section."
        ),
        severity="warning" if not passed else "info",
    )


def _check_no_plaintext_api_keys(
    section: SectionEvidence,
    evidence_index: EvidenceIndex,
) -> CheckResult:
    section_cell_indexes = _section_cell_indexes(section)
    secret_cells = [
        finding.cell_index
        for finding in evidence_index.possible_secrets
        if finding.cell_index in section_cell_indexes
    ]
    passed = not secret_cells

    return CheckResult(
        check_name="no_plaintext_api_keys",
        passed=passed,
        evidence_cells=_unique(secret_cells),
        comment=(
            "No likely plaintext API keys or tokens found."
            if passed
            else f"Likely plaintext secret found in cell(s): {_format_cells(secret_cells)}."
        ),
        severity="critical" if not passed else "info",
    )


def _check_output_present(section: SectionEvidence, check_name: str) -> CheckResult:
    output_cells = [
        cell.index
        for cell in section.code_cells
        if _cell_has_visible_output(cell)
    ]
    passed = bool(output_cells)

    return CheckResult(
        check_name=check_name,
        passed=passed,
        evidence_cells=output_cells,
        comment=(
            f"Visible output found in cell(s): {_format_cells(output_cells)}."
            if passed
            else "No visible output found for this result check."
        ),
        severity="warning" if not passed else "info",
    )


def _cell_has_visible_output(cell) -> bool:
    if cell.output_text.strip():
        return True
    return any(output.text.strip() or output.data for output in cell.outputs)


def _missing_execution_comment(section: SectionEvidence, missing_cells: list[int]) -> str:
    if not section.code_cells:
        return "No required code cells found in this section."
    return f"Code cell(s) lack execution count or visible output: {_format_cells(missing_cells)}."


def _section_cell_indexes(section: SectionEvidence) -> set[int]:
    return {cell.index for cell in section.cells}


def _format_cells(cell_indexes: list[int]) -> str:
    unique_cells = _unique(cell_indexes)
    if not unique_cells:
        return "none"
    return ", ".join(str(cell_index) for cell_index in unique_cells)


def _unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    unique_values: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


CHECK_REGISTRY: dict[str, CheckHandler] = {
    "required_code_cells_have_execution_count_or_equivalent_visible_outputs": (
        lambda section, evidence_index: _check_required_code_cells_executed(section)
    ),
    "no_error_outputs_in_required_cells": (
        lambda section, evidence_index: _check_no_error_outputs(section)
    ),
    "api_response_visible": _check_api_response_visible,
    "no_plaintext_api_keys": _check_no_plaintext_api_keys,
    **{
        check_name: (
            lambda section, evidence_index, name=check_name: _check_output_present(section, name)
        )
        for check_name in OUTPUT_PRESENCE_CHECKS
    },
}

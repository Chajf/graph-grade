from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.graphs.grading import create_grading_graph
from app.models import LabSpec, NotebookResolutionIssue, ParsedNotebook, SharePointStudentSubmission
from app.repositories import GradingSpecRepository, SharePointRepository
from app.services.notebook_parser import parse_notebook


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "grade-group":
        return run_grade_group(args)
    if args.command == "grade-student":
        return run_grade_student(args)
    if args.command == "parse-notebook":
        return run_parse_notebook(args)

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graph-grade",
        description="Grade student notebook submissions from Teams/SharePoint exports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    grade_group = subparsers.add_parser(
        "grade-group",
        help="Load one lab spec and resolve submissions for one group.",
    )
    grade_group.add_argument("--dry-run", action="store_true", required=True)
    grade_group.add_argument("--prace-root", type=Path, required=True)
    grade_group.add_argument("--group", required=True)
    grade_group.add_argument("--lab", required=True)
    grade_group.add_argument(
        "--specs-dir",
        "--specs-root",
        dest="specs_dir",
        type=Path,
        default=Path("work/grading_specs"),
    )

    grade_student = subparsers.add_parser(
        "grade-student",
        help="Grade one resolved student submission for one lab.",
    )
    grade_student.add_argument("--prace-root", type=Path, required=True)
    grade_student.add_argument("--output-root", type=Path, required=True)
    grade_student.add_argument("--group", required=True)
    grade_student.add_argument("--student", required=True)
    grade_student.add_argument("--lab", required=True)
    grade_student.add_argument(
        "--specs-dir",
        "--specs-root",
        dest="specs_dir",
        type=Path,
        default=Path("work/grading_specs"),
    )

    parse_notebook_parser = subparsers.add_parser(
        "parse-notebook",
        help="Parse one notebook and print a compact JSON summary.",
    )
    parse_notebook_parser.add_argument("--notebook-path", type=Path, required=True)

    return parser


def run_grade_group(args: argparse.Namespace) -> int:
    lab_spec = GradingSpecRepository(args.specs_dir).load_lab_spec(args.lab)
    repository = SharePointRepository(args.prace_root)
    submissions = repository.list_submissions(args.group, lab_spec)

    output = {
        "dry_run": args.dry_run,
        "submissions_root": str(args.prace_root),
        "group_id": args.group,
        "lab_id": lab_spec.lab_id,
        "spec": serialize_lab_spec(lab_spec),
        "submissions": [serialize_submission(submission) for submission in submissions],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_grade_student(args: argparse.Namespace) -> int:
    lab_spec = GradingSpecRepository(args.specs_dir).load_lab_spec(args.lab)
    repository = SharePointRepository(args.prace_root)
    submission = repository.resolve_student_submission(args.group, args.student, lab_spec)
    if not submission.resolved:
        print(
            json.dumps(
                {
                    "group_id": submission.group_id,
                    "issue": serialize_issue(submission.issue),
                    "lab_id": submission.lab_id,
                    "status": submission.status,
                    "student_folder": submission.student_folder,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    final_state = create_grading_graph().invoke(
        {
            "lab_spec": lab_spec,
            "submission": submission,
            "output_root": args.output_root,
        }
    )

    output = serialize_grade_student_result(final_state)
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_parse_notebook(args: argparse.Namespace) -> int:
    notebook = parse_notebook(args.notebook_path)
    print(json.dumps(serialize_notebook_summary(notebook), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def serialize_notebook_summary(notebook: ParsedNotebook) -> dict[str, Any]:
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    markdown_cells = [cell for cell in notebook.cells if cell.cell_type == "markdown"]
    raw_cells = [cell for cell in notebook.cells if cell.cell_type == "raw"]

    return {
        "path": str(notebook.path),
        "total_cells": len(notebook.cells),
        "code_cell_count": len(code_cells),
        "markdown_cell_count": len(markdown_cells),
        "raw_cell_count": len(raw_cells),
        "output_count": sum(len(cell.outputs) for cell in notebook.cells),
        "error_count": sum(len(cell.errors) for cell in notebook.cells),
        "functions": _unique_feature_values(
            function
            for cell in code_cells
            if cell.code_features is not None
            for function in cell.code_features.functions
        ),
        "classes": _unique_feature_values(
            class_name
            for cell in code_cells
            if cell.code_features is not None
            for class_name in cell.code_features.classes
        ),
    }


def serialize_lab_spec(lab_spec: LabSpec) -> dict[str, Any]:
    return {
        "expected_notebook_pattern": lab_spec.expected_notebook_pattern,
        "language": lab_spec.language,
        "part_ids": [part.part_id for part in lab_spec.parts],
        "required_files": lab_spec.required_files,
        "title": lab_spec.title,
        "total_points": lab_spec.total_points,
    }


def serialize_submission(submission: SharePointStudentSubmission) -> dict[str, Any]:
    return {
        "group_id": submission.group_id,
        "issue": serialize_issue(submission.issue),
        "lab_folder": serialize_path(submission.lab_folder),
        "lab_id": submission.lab_id,
        "missing_required_files": submission.missing_required_files,
        "notebook_path": serialize_path(submission.notebook_path),
        "required_files": [str(path) for path in submission.required_files],
        "status": submission.status,
        "student_folder": submission.student_folder,
        "version_folder": serialize_path(submission.version_folder),
    }


def serialize_grade_student_result(final_state: dict[str, Any]) -> dict[str, Any]:
    final_grade = final_state["final_grade"]
    return {
        "feedback_path": str(final_state["lab_feedback_path"]),
        "grade_path": str(final_state["lab_grade_path"]),
        "group_id": final_grade.group_id,
        "lab_id": final_grade.lab_id,
        "points_awarded": final_grade.points_awarded,
        "points_possible": final_grade.points_possible,
        "status": final_grade.status,
        "student_folder": final_grade.student_folder,
        "student_summary_path": str(final_state["student_summary_path"]),
    }


def serialize_issue(issue: NotebookResolutionIssue | None) -> dict[str, Any] | None:
    if issue is None:
        return None

    return {
        "candidates": [str(candidate) for candidate in issue.candidates],
        "code": issue.code,
        "message": issue.message,
    }


def serialize_path(path: Path | None) -> str | None:
    if path is None:
        return None

    return str(path)


def _unique_feature_values(values: Any) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)

    return unique_values


if __name__ == "__main__":
    raise SystemExit(main())

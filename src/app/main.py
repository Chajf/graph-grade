from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.models import LabSpec, NotebookResolutionIssue, SharePointStudentSubmission
from app.repositories import GradingSpecRepository, SharePointRepository


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "grade-group":
        return run_grade_group(args)

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
    grade_group.add_argument("--specs-dir", type=Path, default=Path("work/grading_specs"))

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


if __name__ == "__main__":
    raise SystemExit(main())

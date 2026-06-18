from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from app.models import LabSpec, NotebookResolutionIssue, SharePointStudentSubmission


VERSION_FOLDER_RE = re.compile(r"^Wersja\s+(\d+)$", re.IGNORECASE)


class SharePointRepository:
    def __init__(self, submissions_root: Path | str) -> None:
        self.submissions_root = Path(submissions_root)

    def list_groups(self) -> list[str]:
        if not self.submissions_root.exists():
            return []

        return [
            path.name
            for path in sorted(self.submissions_root.iterdir(), key=lambda item: item.name.casefold())
            if path.is_dir()
        ]

    def list_students(self, group_id: str) -> list[str]:
        group_dir = self.submissions_root / group_id
        if not group_dir.exists():
            return []

        return [
            path.name
            for path in sorted(group_dir.iterdir(), key=lambda item: item.name.casefold())
            if path.is_dir()
        ]

    def list_submissions(self, group_id: str, lab_spec: LabSpec) -> list[SharePointStudentSubmission]:
        return [
            self.resolve_student_submission(group_id, student_folder, lab_spec)
            for student_folder in self.list_students(group_id)
        ]

    def resolve_student_submission(
        self,
        group_id: str,
        student_folder: str,
        lab_spec: LabSpec,
    ) -> SharePointStudentSubmission:
        lab_folder = self.submissions_root / group_id / student_folder / lab_spec.lab_id
        base_kwargs = {
            "submissions_root": self.submissions_root,
            "group_id": group_id,
            "student_folder": student_folder,
            "lab_id": lab_spec.lab_id,
            "lab_folder": lab_folder,
        }

        if not lab_folder.is_dir():
            return SharePointStudentSubmission(
                **base_kwargs,
                issue=NotebookResolutionIssue(
                    code="missing_lab_folder",
                    message=f"Lab folder not found: {lab_folder}",
                ),
            )

        version_folder = self._select_version_folder(lab_folder)
        if version_folder is None:
            return SharePointStudentSubmission(
                **base_kwargs,
                issue=NotebookResolutionIssue(
                    code="missing_version_folder",
                    message=f"No usable Wersja version folder found in: {lab_folder}",
                ),
            )

        notebook_path, issue = self._resolve_notebook_path(
            version_folder=version_folder,
            lab_id=lab_spec.lab_id,
            expected_notebook_pattern=lab_spec.expected_notebook_pattern,
        )
        required_files, missing_required_files = self._resolve_required_files(
            lab_folder=lab_folder,
            version_folder=version_folder,
            required_file_names=lab_spec.required_files,
        )

        if issue is not None:
            return SharePointStudentSubmission(
                **base_kwargs,
                version_folder=version_folder,
                required_files=required_files,
                missing_required_files=missing_required_files,
                status="ambiguous" if issue.code == "ambiguous_notebook" else "unresolved",
                issue=issue,
            )

        return SharePointStudentSubmission(
            **base_kwargs,
            version_folder=version_folder,
            notebook_path=notebook_path,
            required_files=required_files,
            missing_required_files=missing_required_files,
            status="resolved",
        )

    def _select_version_folder(self, lab_folder: Path) -> Path | None:
        version_folders = [
            path
            for path in sorted(lab_folder.iterdir(), key=lambda item: item.name.casefold())
            if path.is_dir() and path.name.casefold().startswith("wersja")
        ]
        numbered_folders: list[tuple[int, Path]] = []

        for folder in version_folders:
            match = VERSION_FOLDER_RE.match(folder.name)
            if match is not None:
                numbered_folders.append((int(match.group(1)), folder))

        if numbered_folders:
            return max(numbered_folders, key=lambda item: item[0])[1]

        wersja_1 = lab_folder / "Wersja 1"
        if wersja_1.is_dir():
            return wersja_1

        return None

    def _resolve_notebook_path(
        self,
        version_folder: Path,
        lab_id: str,
        expected_notebook_pattern: str,
    ) -> tuple[Path | None, NotebookResolutionIssue | None]:
        notebook_candidates = [
            path
            for path in sorted(version_folder.iterdir(), key=lambda item: item.name.casefold())
            if path.is_file() and path.suffix == ".ipynb"
        ]

        if not notebook_candidates:
            return None, NotebookResolutionIssue(
                code="missing_notebook",
                message=f"No .ipynb files found in: {version_folder}",
            )

        for candidates in (
            _filter_by_pattern(notebook_candidates, expected_notebook_pattern),
            _filter_by_pattern(notebook_candidates, f"{lab_id}*.ipynb"),
            notebook_candidates,
        ):
            if len(candidates) == 1:
                return candidates[0], None
            if len(candidates) > 1:
                return None, NotebookResolutionIssue(
                    code="ambiguous_notebook",
                    message="Multiple notebook candidates found.",
                    candidates=candidates,
                )

        return None, NotebookResolutionIssue(
            code="missing_notebook",
            message=f"No .ipynb files found in: {version_folder}",
        )

    def _resolve_required_files(
        self,
        lab_folder: Path,
        version_folder: Path,
        required_file_names: list[str],
    ) -> tuple[list[Path], list[str]]:
        found_files: list[Path] = []
        missing_files: list[str] = []

        for file_name in required_file_names:
            version_candidate = version_folder / file_name
            lab_candidate = lab_folder / file_name

            if version_candidate.exists():
                found_files.append(version_candidate)
            elif lab_candidate.exists():
                found_files.append(lab_candidate)
            else:
                missing_files.append(file_name)

        return found_files, missing_files


def _filter_by_pattern(paths: list[Path], pattern: str) -> list[Path]:
    return [path for path in paths if fnmatch.fnmatchcase(path.name, pattern)]

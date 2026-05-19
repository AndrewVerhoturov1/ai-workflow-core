#!/usr/bin/env python3
"""
Validate the Session contract in session files and handoffs.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_SECTIONS = (
    "## Session ID",
    "## Status",
    "## Goal",
    "## Approved Plan",
    "## Active Plan Item",
    "## Runs",
    "## User Overrides",
    "## Checkpoint State",
)

SESSION_RUN_PATTERN = re.compile(r"^\s*\|\s*\d+\s*\|", re.MULTILINE)


@dataclass
class ValidationIssue:
    severity: str
    message: str
    path: Path | None = None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_value(text: str, header: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == header:
            for candidate in lines[index + 1:]:
                value = candidate.strip()
                if not value:
                    continue
                if value.startswith("## "):
                    return None
                return value.strip("`")
            return None
    return None


def has_section(text: str, header: str) -> bool:
    return header in text


def validate_session_file(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    text = read_text(path)

    if not text.strip():
        issues.append(ValidationIssue("error", "Файл пустой.", path))
        return issues

    for section in REQUIRED_SECTIONS:
        if not has_section(text, section):
            issues.append(ValidationIssue("error", f"Отсутствует обязательная секция `{section}`.", path))

    if issues:
        return issues

    session_id = section_value(text, "## Session ID")
    if session_id:
        expected_filename = path.stem
        if session_id != expected_filename:
            issues.append(
                ValidationIssue(
                    "error",
                    f"`Session ID` ({session_id}) не совпадает с именем файла ({expected_filename}).",
                    path,
                )
            )

    active_plan_item = section_value(text, "## Active Plan Item")
    if not active_plan_item:
        issues.append(ValidationIssue("error", "`Active Plan Item` не может быть пустым.", path))

    runs_section = section_value(text, "## Runs")
    if not runs_section:
        issues.append(ValidationIssue("error", "Секция `## Runs` не может быть пустой.", path))
    else:
        has_runs_header = "Session run" in runs_section or "Global task id" in runs_section
        if not has_runs_header:
            issues.append(ValidationIssue("error", "Секция `## Runs` должна содержать заголовок таблицы.", path))

        run_lines = SESSION_RUN_PATTERN.findall(text)
        for line in run_lines:
            match = re.search(r"\|\s*(\d+)\s*\|", line)
            if match:
                num = match.group(1)
                if len(num) != 3 or not num.isdigit():
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"Некорректный формат `Session run`. Ожидается формат `001`, `002` и т.д. Найдено: `{num}`.",
                            path,
                        )
                    )

    return issues


def validate_handoff_for_session(path: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    text = read_text(path)

    has_session_plan = has_section(text, "## Session plan")
    has_session_run = has_section(text, "## Session run")

    if has_session_plan and not has_session_run:
        issues.append(
            ValidationIssue(
                "warning",
                "Handoff содержит `## Session plan`, но не содержит `## Session run`.",
                path,
            )
        )

    return issues


def validate_repo(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    sessions_dir = root / ".ai" / "plans" / "sessions"
    if sessions_dir.exists():
        for session_file in sorted(sessions_dir.glob("*.md")):
            text = read_text(session_file)
            if not text.strip():
                issues.append(
                    ValidationIssue(
                        "warning",
                        "Исторический пустой session-файл пропущен.",
                        session_file,
                    )
                )
                continue
            session_issues = validate_session_file(session_file)
            for issue in session_issues:
                issue.path = session_file
            issues.extend(session_issues)

    handoffs_dir = root / ".ai" / "handoffs"
    if handoffs_dir.exists():
        for handoff_file in sorted(handoffs_dir.glob("*.md")):
            text = read_text(handoff_file)
            has_session_plan = has_section(text, "## Session plan")
            has_session_run = has_section(text, "## Session run")

            if not has_session_plan and not has_session_run:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "Исторический handoff без session-секций пропущен.",
                        handoff_file,
                    )
                )
                continue

            handoff_issues = validate_handoff_for_session(handoff_file)
            issues.extend(handoff_issues)

    return issues


def print_issues(issues: list[ValidationIssue]) -> int:
    if not issues:
        print("OK: session contract пройден.")
        return 0

    exit_code = 0
    for issue in issues:
        prefix = "ERROR" if issue.severity == "error" else "WARN"
        if issue.severity == "error":
            exit_code = 1
        location = f"{issue.path}: " if issue.path else ""
        print(f"{prefix}: {location}{issue.message}")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Проверка контракта Session contract.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    session_parser = subparsers.add_parser("session", help="Проверить один session-файл.")
    session_parser.add_argument("path", help="Путь к session-файлу.")

    repo_parser = subparsers.add_parser("repo", help="Проверить session-файлы в проекте.")
    repo_parser.add_argument(
        "--root",
        default=None,
        help="Путь к корню проекта. По умолчанию используется корень репозитория скрипта.",
    )

    return parser


def resolve_root(root_arg: str | None) -> Path:
    if root_arg:
        return Path(root_arg).resolve()
    return Path(__file__).resolve().parents[1]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "session":
        return print_issues(validate_session_file(Path(args.path).resolve()))
    if args.command == "repo":
        root = resolve_root(args.root)
        return print_issues(validate_repo(root))

    parser.error("Неизвестная команда.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
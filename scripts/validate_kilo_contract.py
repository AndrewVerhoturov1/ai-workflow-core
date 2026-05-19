#!/usr/bin/env python3
"""
Validate the Kilo mode/role contract in handoffs and launch packages.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


INTERNAL_MODES = (
    "kilo-handoff-runner",
    "kilo-debugger",
    "kilo-verifier",
    "kilo-recorder",
)

UI_MODES = (
    "Kilo Handoff Runner",
    "Kilo Debugger",
    "Kilo Verifier",
    "Kilo Recorder",
)

TASK_ROLES = (
    "Builder Agent",
    "Docs Agent",
    "Tester Agent",
    "Refactor Agent",
    "Debugger Agent",
    "Test Agent",
    "Recorder Agent",
)

FORBIDDEN_MODE_TOKENS = (
    "kilo-builder",
    "kilo-docs",
    "kilo-tester",
    "kilo-refactor",
)

ROLE_HEADERS = (
    "## Task role",
    "## Рекомендуемая роль",
)

TASK_PROFILES = (
    "tiny-docs",
    "small-code",
    "debug",
    "capability-sensitive",
    "workflow-rules-change",
    "planning-probe",
    "external-chat-package",
)

REPORT_MODES = (
    "minimal",
    "simple",
    "full",
    "forensic",
)

WORKFLOW_PATH_PREFIXES = (
    ".ai/handoffs/",
    ".ai/reports/",
    ".ai/plans/",
    ".ai/project_state.md",
    ".ai/backlog/current_sprint.md",
    ".ai/rules/",
    ".ai/prompts/",
    ".ai/README.md",
    ".ai/agent_protocol.md",
    "AGENTS.md",
)


@dataclass
class ValidationIssue:
    severity: str
    message: str
    path: Path | None = None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_value(text: str, headers: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() in headers:
            for candidate in lines[index + 1 :]:
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


def find_forbidden_tokens(text: str) -> list[str]:
    lowered = text.lower()
    return [token for token in FORBIDDEN_MODE_TOKENS if token in lowered]


def find_forbidden_tokens_in_value(value: str | None) -> list[str]:
    """Check for forbidden tokens only in a specific field value, not in prose."""
    if not value:
        return []
    lowered = value.lower()
    return [token for token in FORBIDDEN_MODE_TOKENS if token in lowered]


def validate_handoff_text(text: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    mode_value = section_value(text, ("## Рекомендуемый Kilo mode",))
    for token in find_forbidden_tokens_in_value(mode_value):
        issues.append(ValidationIssue("error", f"В поле `Рекомендуемый Kilo mode` найден запрещенный псевдо-mode `{token}`."))
    if mode_value is None:
        issues.append(ValidationIssue("error", "Не найдена секция `## Рекомендуемый Kilo mode` или в ней нет значения."))
    elif mode_value not in INTERNAL_MODES:
        issues.append(
            ValidationIssue(
                "error",
                "Поле `Рекомендуемый Kilo mode` должно быть одним из: "
                + ", ".join(f"`{mode}`" for mode in INTERNAL_MODES)
                + f". Сейчас: `{mode_value}`.",
            )
        )

    role_value = section_value(text, ROLE_HEADERS)
    if role_value is None:
        issues.append(ValidationIssue("error", "Не найдена секция `## Task role` или legacy-секция `## Рекомендуемая роль`."))
    elif role_value not in TASK_ROLES:
        issues.append(
            ValidationIssue(
                "error",
                "Поле `Task role` содержит недопустимое значение. Допустимы: "
                + ", ".join(f"`{role}`" for role in TASK_ROLES)
                + f". Сейчас: `{role_value}`.",
            )
        )

    if "## Рекомендуемая роль" in text and "## Task role" not in text:
        issues.append(ValidationIssue("warning", "Используется legacy-заголовок `## Рекомендуемая роль`. Для новых handoff используйте `## Task role`."))

    session_plan_value = section_value(text, ("## Session plan",))
    plan_item_value = section_value(text, ("## Plan item",))
    if session_plan_value and not plan_item_value:
        issues.append(ValidationIssue("error", "Указан `Session plan`, но отсутствует `Plan item`."))
    if plan_item_value and not session_plan_value:
        issues.append(ValidationIssue("error", "Указан `Plan item`, но отсутствует `Session plan`."))
    if session_plan_value:
        normalized = session_plan_value.replace("\\", "/")
        if "/.ai/plans/sessions/" not in normalized and ".ai/plans/sessions/" not in normalized:
            issues.append(ValidationIssue("warning", f"`Session plan` должен ссылаться на `.ai/plans/sessions/...`. Сейчас: `{session_plan_value}`."))

    if has_section(text, "## Task profile"):
        task_profile_value = section_value(text, ("## Task profile",))
        if task_profile_value is None:
            issues.append(ValidationIssue("error", "Не найдена секция `## Task profile` или в ней нет значения."))
        elif task_profile_value not in TASK_PROFILES:
            issues.append(
                ValidationIssue(
                    "error",
                    "Поле `Task profile` должно быть одним из: "
                    + ", ".join(f"`{profile}`" for profile in TASK_PROFILES)
                    + f". Сейчас: `{task_profile_value}`.",
                )
            )

        required_structured_sections = (
            "## Required Inputs",
            "## Lookup Inputs",
            "## Do Not Read Unless Blocked",
            "## Context Budget",
            "## Report mode",
            "## Куда записать report",
        )
        for header in required_structured_sections:
            if section_value(text, (header,)) is None:
                issues.append(ValidationIssue("warning", f"Для новых structured handoff рекомендуется непустая секция `{header}`."))

        report_mode_value = section_value(text, ("## Report mode",))
        if report_mode_value and report_mode_value not in REPORT_MODES:
            issues.append(
                ValidationIssue(
                    "error",
                    "Поле `Report mode` должно быть одним из: "
                    + ", ".join(f"`{mode}`" for mode in REPORT_MODES)
                    + f". Сейчас: `{report_mode_value}`.",
                )
            )

        report_path_value = section_value(text, ("## Куда записать report",))
        if report_path_value:
            normalized_report_path = report_path_value.replace("\\", "/")
            if "/.ai/reports/" not in normalized_report_path and ".ai/reports/" not in normalized_report_path:
                issues.append(
                    ValidationIssue(
                        "warning",
                        f"`Куда записать report` обычно должен ссылаться на `.ai/reports/...`. Сейчас: `{report_path_value}`.",
                    )
                )

        if has_section(text, "## Model policy") and section_value(text, ("## Model policy",)) is None:
            issues.append(ValidationIssue("error", "Секция `## Model policy` указана, но в ней нет содержимого."))

    return issues


def validate_launch_text(text: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    mode_lines = re.findall(r"^Kilo mode:\s*(.+)$", text, flags=re.MULTILINE)
    if len(mode_lines) != 1:
        issues.append(ValidationIssue("error", f"В launch package должна быть ровно одна строка `Kilo mode:`. Найдено: {len(mode_lines)}."))
    else:
        mode_value = mode_lines[0].strip()
        if mode_value not in UI_MODES:
            issues.append(
                ValidationIssue(
                    "error",
                    "Строка `Kilo mode:` должна использовать только UI-значения: "
                    + ", ".join(f"`{mode}`" for mode in UI_MODES)
                    + f". Сейчас: `{mode_value}`.",
                )
            )

    for role in TASK_ROLES:
        if re.search(rf"^Kilo mode:\s*{re.escape(role)}\s*$", text, flags=re.MULTILINE):
            issues.append(ValidationIssue("error", f"Role `{role}` ошибочно подставлена в `Kilo mode:`."))

    if re.search(r"^(Роль|Role|Task role):", text, flags=re.MULTILINE):
        issues.append(ValidationIssue("error", "Launch package не должен содержать отдельное поле роли."))

    return issues


def validate_path(path: Path, kind: str) -> list[ValidationIssue]:
    text = read_text(path)
    issues = validate_handoff_text(text) if kind == "handoff" else validate_launch_text(text)
    for issue in issues:
        issue.path = path
    return issues


def validate_repo(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    handoff_dir = root / ".ai" / "handoffs"
    if not handoff_dir.exists():
        issues.append(ValidationIssue("warning", "В репозитории нет `.ai/handoffs/`."))
        return issues

    for path in sorted(handoff_dir.glob("*.md")):
        text = read_text(path)
        has_mode_section = "## Рекомендуемый Kilo mode" in text
        has_role_section = any(header in text for header in ROLE_HEADERS)
        has_forbidden = bool(find_forbidden_tokens(text))

        if not has_mode_section and not has_forbidden:
            issues.append(
                ValidationIssue(
                    "warning",
                    "Исторический handoff без полного mode-контракта пропущен. Для новых handoff используйте новый шаблон.",
                    path,
                )
            )
            continue

        issues.extend(validate_path(path, "handoff"))
    return issues


def git_status_porcelain(root: Path) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return []

    entries: list[tuple[str, str]] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        status = raw_line[:2]
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        entries.append((status, path.replace("\\", "/")))
    return entries


def extract_task_id(path: str) -> str | None:
    match = re.search(r"/(\d{4})_[^/]+(?:_report)?\.md$", path)
    if match:
        return match.group(1)
    return None


def is_workflow_path(path: str) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in WORKFLOW_PATH_PREFIXES)


def validate_checkpoint(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    status_entries = git_status_porcelain(root)
    if not status_entries:
        return issues

    workflow_entries = [(status, path) for status, path in status_entries if is_workflow_path(path)]
    if not workflow_entries:
        return issues

    task_to_paths: dict[str, list[str]] = {}
    generic_paths: list[str] = []
    for _status, path in workflow_entries:
        task_id = extract_task_id(path)
        if task_id:
            task_to_paths.setdefault(task_id, []).append(path)
        else:
            generic_paths.append(path)

    for task_id, paths in sorted(task_to_paths.items()):
        issues.append(
            ValidationIssue(
                "warning",
                "Найден pending workflow checkpoint для задачи "
                f"`{task_id}`: в git status остались workflow-файлы ({', '.join(f'`{path}`' for path in paths)}). "
                "Если задача уже принята, следующий `/kilo` выдавать нельзя до отдельного checkpoint commit.",
                root / ".ai" / "handoffs",
            )
        )

    if generic_paths:
        issues.append(
            ValidationIssue(
                "warning",
                "Найден workflow-dirty state вне task-specific handoff/report: "
                + ", ".join(f"`{path}`" for path in generic_paths)
                + ". Это типичный кандидат на `Workflow: sync global Kilo rules` или другой отдельный workflow checkpoint.",
                root,
            )
        )

    return issues


def print_issues(issues: list[ValidationIssue]) -> int:
    if not issues:
        print("OK: контракт Kilo mode / Task role пройден.")
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
    parser = argparse.ArgumentParser(description="Проверка контракта Kilo mode / Task role.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    handoff_parser = subparsers.add_parser("handoff", help="Проверить один handoff.")
    handoff_parser.add_argument("path", help="Путь к handoff-файлу.")

    launch_parser = subparsers.add_parser("launch", help="Проверить launch package из файла.")
    launch_parser.add_argument("path", help="Путь к файлу с launch package.")

    repo_parser = subparsers.add_parser("repo", help="Проверить все handoff в проекте.")
    repo_parser.add_argument(
        "--root",
        default=None,
        help="Путь к корню проекта. По умолчанию используется корень репозитория скрипта.",
    )

    checkpoint_parser = subparsers.add_parser("checkpoint", help="Проверить pending workflow checkpoint в git status.")
    checkpoint_parser.add_argument(
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

    if args.command == "handoff":
        return print_issues(validate_path(Path(args.path).resolve(), "handoff"))
    if args.command == "launch":
        return print_issues(validate_path(Path(args.path).resolve(), "launch"))
    if args.command == "repo":
        root = resolve_root(args.root)
        return print_issues(validate_repo(root) + validate_checkpoint(root))
    if args.command == "checkpoint":
        return print_issues(validate_checkpoint(resolve_root(args.root)))

    parser.error("Неизвестная команда.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Проверка published-artifact contract для External Web Chat launch package.

Режим `package <path>` валидирует обязательные секции и поля published route.
Стиль: совместим с существующими валидаторами проекта.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_SECTIONS = (
    "## Static manual reference",
    "## Task bundle reference",
)

REQUIRED_STATIC_FIELDS = (
    "GitHub URL",
    "raw URL",
    "static_manual_version",
    "required static anchors",
)

REQUIRED_TASK_BUNDLE_FIELDS = (
    "external_task_id",
    "external_attempt_id",
    "handoff URL",
    "handoff raw URL",
)

REQUIRED_RECORDER_FIELDS = (
    "external_task_id",
    "external_attempt_id",
    "response_path",
    "published links",
    "recording_mode",
    "allowed_writes",
    "raw_response",
)

REQUIRED_RESPONSE_METADATA_FIELDS = (
    "Provider/Model",
    "Source request",
    "Recording mode",
    "Recorder limitations",
    "## Recorder Payload",
)

REQUIRED_STATIC_ANCHORS_MINIMAL = (
    "[EA-CORE-BOUNDARY]",
    "[EA-TRUTH-RULE]",
    "[EA-TASK-BUNDLE]",
)


@dataclass
class ValidationIssue:
    severity: str  # "error", "warning"
    message: str
    path: Path | None = None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def has_section(text: str, header: str) -> bool:
    return header in text


def section_value(text: str, header: str) -> str | None:
    """Извлечь значение первой непустой строки после заголовка секции."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == header:
            for candidate in lines[index + 1:]:
                value = candidate.strip()
                if not value:
                    continue
                if value.startswith("## "):
                    return None
                return value
            return None
    return None


def validate_package(text: str) -> list[ValidationIssue]:
    """Проверить launch package на наличие обязательных секций и полей published route."""
    issues: list[ValidationIssue] = []

    # Проверка обязательных секций
    for section in REQUIRED_SECTIONS:
        if not has_section(text, section):
            issues.append(ValidationIssue("error", f"Отсутствует обязательная секция: `{section}`."))
        else:
            # Проверить наличие ключевых полей внутри секции
            if "static manual reference" in section.lower():
                for field in REQUIRED_STATIC_FIELDS:
                    if field.lower() not in text.lower():
                        issues.append(ValidationIssue("warning", f"В секции `{section}` рекомендуется поле `{field}`."))

            if "task bundle reference" in section.lower():
                for field in REQUIRED_TASK_BUNDLE_FIELDS:
                    if field.lower() not in text.lower():
                        issues.append(ValidationIssue("warning", f"В секции `{section}` рекомендуется поле `{field}`."))

    # Проверка наличия raw URL
    has_raw_url = "raw.githubusercontent.com" in text or "raw_url" in text.lower() or "raw URL" in text
    if not has_raw_url:
        issues.append(ValidationIssue("error", "Package не содержит raw URL. Published-artifact route требует raw ссылок."))

    # Проверка static_manual_version
    if "static_manual_version" not in text.lower():
        issues.append(ValidationIssue("error", "Package не содержит `static_manual_version`. Обязательное поле published route."))

    # Проверка external_task_id и external_attempt_id
    if "external_task_id" not in text.lower():
        issues.append(ValidationIssue("error", "Package не содержит `external_task_id`. Обязательное поле published route."))
    if "external_attempt_id" not in text.lower():
        issues.append(ValidationIssue("error", "Package не содержит `external_attempt_id`. Обязательное поле published route."))

    # Проверка recorder metadata при наличии recorder-секций
    has_recorder = "recorder" in text.lower() and ("response" in text.lower() or "record" in text.lower())
    if has_recorder:
        for field in REQUIRED_RECORDER_FIELDS:
            if field.lower() not in text.lower():
                issues.append(ValidationIssue("error", f"Recorder contract: отсутствует обязательное поле `{field}`."))
        for field in REQUIRED_RESPONSE_METADATA_FIELDS:
            if field.lower() not in text.lower():
                issues.append(ValidationIssue("error", f"Recorder-ready response contract: отсутствует требование `{field}`."))
        if (
            "не должен вручную собирать metadata" not in text.lower()
            and "не собирает metadata вручную" not in text.lower()
            and "не заставляй человека вручную собирать metadata" not in text.lower()
            and "не заставлять человека вручную собирать target metadata" not in text.lower()
        ):
            issues.append(
                ValidationIssue(
                    "warning",
                    "Recorder-ready route: рекомендуется явно запретить ручную сборку metadata человеком.",
                )
            )
        if (
            "не включает секцию `## recorder payload`" not in text.lower()
            and "не включает секцию ## recorder payload" not in text.lower()
            and "не должен включать секцию `## recorder payload`" not in text.lower()
            and "не должен включать секцию ## recorder payload" not in text.lower()
        ):
            issues.append(
                ValidationIssue(
                    "warning",
                    "Recorder-ready route: рекомендуется явно указать, что `raw_response` не включает секцию `## Recorder Payload`.",
                )
            )

    # Проверка required static anchors
    missing_anchors = []
    for anchor in REQUIRED_STATIC_ANCHORS_MINIMAL:
        if anchor not in text:
            missing_anchors.append(anchor)
    if missing_anchors:
        issues.append(
            ValidationIssue(
                "warning",
                f"Отсутствуют некоторые recommended static anchors: {', '.join(f'`{a}`' for a in missing_anchors)}.",
            )
        )

    # Проверка на prompt-only (без raw URLs = legacy)
    has_published_route = ("github.com" in text.lower() or "raw.githubusercontent.com" in text) and "raw" in text.lower()
    if not has_published_route and ("static manual" in text.lower() or "external" in text.lower()):
        issues.append(
            ValidationIssue(
                "warning",
                "Package выглядит как prompt-only (без GitHub/raw ссылок). Для production-like route это устаревший non-production путь.",
            )
        )

    return issues


def validate_path(path: Path) -> list[ValidationIssue]:
    issues = validate_package(read_text(path))
    for issue in issues:
        issue.path = path
    return issues


def print_issues(issues: list[ValidationIssue]) -> int:
    if not issues:
        print("OK: published-artifact contract пройден.")
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
    parser = argparse.ArgumentParser(description="Проверка published-artifact contract для External Web Chat package.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    package_parser = subparsers.add_parser("package", help="Проверить launch package.")
    package_parser.add_argument("path", help="Путь к файлу launch package.")

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "package":
        return print_issues(validate_path(Path(args.path).resolve()))
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

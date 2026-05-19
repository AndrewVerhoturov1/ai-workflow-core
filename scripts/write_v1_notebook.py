#!/usr/bin/env python3
"""
Создать или обновить local staged notebook entry для `/v1`.

Скрипт читает notebook package, валидирует границы записи и:
- создаёт/обновляет notebook entry;
- добавляет или обновляет строку в `.ai/external_chats/V1_navigation.md`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = (
    "external_question_id",
    "notebook_entry_path",
    "v1_navigation_path",
    "allowed_writes",
    "candidate_navigation_entry",
    "raw_response",
)

QUESTION_ID_PATTERN = re.compile(r"^V1-(\d{8})-(\d{6})$")
NAV_HEADER = "| External Question ID | Date | Status | Topic | Notebook Entry Path | Summary |"
NAV_SEPARATOR = "|---|---|---|---|---|---|"
NAV_PLACEHOLDER_PREFIX = "| — | — | `staged` | Entries will appear here |"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1]
    return value.strip()


def parse_package_text(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        raise ValueError("package пустой.")

    if stripped.startswith("{"):
        data = json.loads(stripped)
        if not isinstance(data, dict):
            raise ValueError("JSON package должен быть объектом.")
        return data

    data: dict[str, object] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        raw = line.rstrip()
        stripped_line = raw.strip()

        if (
            not stripped_line
            or stripped_line.startswith("#")
            or stripped_line.startswith("```")
            or stripped_line in ("Mode: `kilo-notebook`", "Route: `/v1`")
        ):
            index += 1
            continue

        scalar_match = re.match(r"^([a-z0-9_]+):\s*(.*)$", raw)
        if not scalar_match:
            index += 1
            continue

        key = scalar_match.group(1)
        remainder = scalar_match.group(2).strip()

        if remainder == "|":
            index += 1
            block: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                if candidate.startswith("  "):
                    block.append(candidate[2:])
                    index += 1
                    continue
                if not candidate.strip():
                    block.append("")
                    index += 1
                    continue
                break
            data[key] = "\n".join(block).strip()
            continue

        if remainder == "":
            index += 1
            list_items: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                stripped_candidate = candidate.strip()
                if not stripped_candidate:
                    index += 1
                    continue
                if candidate.startswith("- ") or candidate.startswith("  - "):
                    value = candidate.split("- ", 1)[1]
                    list_items.append(normalize_scalar(value))
                    index += 1
                    continue
                break
            data[key] = list_items
            continue

        data[key] = normalize_scalar(remainder)
        index += 1

    return data


def load_package(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return parse_package_text(text)


def require_string(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Поле `{key}` должно быть непустой строкой.")
    return value.strip()


def require_string_list(data: dict, key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Поле `{key}` должно быть непустым списком.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Поле `{key}` должно содержать только непустые строки.")
        normalized.append(item.strip())
    return normalized


def ensure_required_fields(data: dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise ValueError("Отсутствуют обязательные поля: " + ", ".join(f"`{field}`" for field in missing))


def resolve_repo_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def enforce_allowed_writes(root: Path, notebook_path: Path, navigation_path: Path, allowed_writes: list[str]) -> None:
    allowed_paths = {resolve_repo_path(root, item) for item in allowed_writes}
    expected = {notebook_path, navigation_path}
    if allowed_paths != expected:
        raise ValueError(
            "`allowed_writes` должен содержать ровно два пути: notebook entry и V1_navigation.md."
        )

    notebook_dir = (root / ".ai" / "external_chats" / "notebook").resolve()
    if notebook_path.parent != notebook_dir:
        raise ValueError(f"`notebook_entry_path` должен лежать в `{notebook_dir}`.")

    expected_navigation = (root / ".ai" / "external_chats" / "V1_navigation.md").resolve()
    if navigation_path != expected_navigation:
        raise ValueError(f"`v1_navigation_path` должен указывать на `{expected_navigation}`.")


def parse_question_date(question_id: str) -> str:
    match = QUESTION_ID_PATTERN.match(question_id)
    if not match:
        raise ValueError("`external_question_id` должен иметь формат `V1-YYYYMMDD-HHMMSS`.")
    date_value = match.group(1)
    return f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"


def parse_candidate_navigation_entry(raw_text: str) -> tuple[str, str]:
    topic = ""
    summary = ""
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Topic:"):
            topic = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Summary:"):
            summary = stripped.split(":", 1)[1].strip()

    if not topic:
        raise ValueError("`candidate_navigation_entry` должен содержать строку `Topic: ...`.")
    if not summary:
        raise ValueError("`candidate_navigation_entry` должен содержать строку `Summary: ...`.")
    return topic, summary


def escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def format_context_links(links: list[str]) -> str:
    if not links:
        return "- `нет`"
    return "\n".join(f"- `{item}`" for item in links)


def build_notebook_entry(
    root: Path,
    notebook_path: Path,
    question_id: str,
    status: str,
    provider_model: str,
    context_links: list[str],
    candidate_navigation_entry: str,
    raw_response: str,
) -> str:
    relative_path = notebook_path.relative_to(root).as_posix()
    raw_response = raw_response.rstrip()
    metadata_lines = [
        f"- External Question ID: `{question_id}`",
        f"- Entry status: `{status}`",
        f"- Provider/Model: `{provider_model}`",
        f"- Notebook entry path: `{relative_path}`",
    ]
    return (
        "# Notebook Entry\n\n"
        + "\n".join(metadata_lines)
        + "\n\n"
        "## Context Links\n\n"
        f"{format_context_links(context_links)}\n\n"
        "## Candidate Navigation Entry\n\n"
        f"{candidate_navigation_entry.rstrip()}\n\n"
        "## Raw Response\n\n"
        f"{raw_response}\n"
    )


def build_navigation_row(question_id: str, date_value: str, status: str, topic: str, notebook_path: Path, root: Path, summary: str) -> str:
    relative_path = notebook_path.relative_to(root).as_posix()
    return (
        f"| {escape_table_cell(question_id)} | {escape_table_cell(date_value)} | `{escape_table_cell(status)}` | "
        f"{escape_table_cell(topic)} | `{escape_table_cell(relative_path)}` | {escape_table_cell(summary)} |"
    )


def update_navigation_file(path: Path, row: str, question_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    if NAV_HEADER not in text or NAV_SEPARATOR not in text:
        raise ValueError("В `V1_navigation.md` не найдена ожидаемая таблица entries.")

    lines = text.splitlines()
    new_lines: list[str] = []
    inserted = False
    replaced = False

    for line in lines:
        if line.startswith(f"| {question_id} |"):
            new_lines.append(row)
            replaced = True
            continue
        if line.startswith(NAV_PLACEHOLDER_PREFIX):
            if not inserted:
                new_lines.append(row)
                inserted = True
            continue
        new_lines.append(line)

    if not replaced and not inserted:
        try:
            separator_index = new_lines.index(NAV_SEPARATOR)
        except ValueError as exc:
            raise ValueError("В `V1_navigation.md` не найден разделитель таблицы.") from exc
        new_lines.insert(separator_index + 1, row)

    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def write_outputs(package_path: Path, root: Path) -> tuple[Path, Path, str]:
    data = load_package(package_path)
    ensure_required_fields(data)

    question_id = require_string(data, "external_question_id")
    notebook_path = resolve_repo_path(root, require_string(data, "notebook_entry_path"))
    navigation_path = resolve_repo_path(root, require_string(data, "v1_navigation_path"))
    allowed_writes = require_string_list(data, "allowed_writes")
    candidate_navigation_entry = require_string(data, "candidate_navigation_entry")
    raw_response = require_string(data, "raw_response")

    status = normalize_scalar(str(data.get("entry_status", "staged")))
    if status != "staged":
        raise ValueError("Для первой версии `entry_status` должен быть равен `staged`.")

    provider_model = normalize_scalar(str(data.get("provider_model", "not available")))
    context_links = require_string_list(data, "context_links") if "context_links" in data else []

    date_value = parse_question_date(question_id)
    topic, summary = parse_candidate_navigation_entry(candidate_navigation_entry)
    enforce_allowed_writes(root, notebook_path, navigation_path, allowed_writes)

    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    notebook_text = build_notebook_entry(
        root=root,
        notebook_path=notebook_path,
        question_id=question_id,
        status=status,
        provider_model=provider_model,
        context_links=context_links,
        candidate_navigation_entry=candidate_navigation_entry,
        raw_response=raw_response,
    )
    notebook_path.write_text(notebook_text, encoding="utf-8")

    navigation_row = build_navigation_row(
        question_id=question_id,
        date_value=date_value,
        status=status,
        topic=topic,
        notebook_path=notebook_path,
        root=root,
        summary=summary,
    )
    update_navigation_file(navigation_path, navigation_row, question_id)
    return notebook_path, navigation_path, navigation_row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Создать или обновить staged notebook entry и V1_navigation.md из notebook package."
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Путь к notebook package в JSON или простом markdown-шаблоне.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Путь к корню проекта. По умолчанию используется корень репозитория скрипта.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else repo_root()
    package_path = Path(args.package).resolve()

    try:
        notebook_path, navigation_path, navigation_row = write_outputs(package_path, root)
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename}")
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: notebook package processed.")
    print(f"Package: {package_path}")
    print(f"Notebook entry: {notebook_path}")
    print(f"V1 navigation: {navigation_path}")
    print(f"Navigation row: {navigation_row}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

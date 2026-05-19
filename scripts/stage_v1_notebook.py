#!/usr/bin/env python3
"""
Принять сырой `/v1` ответ внешнего чата, собрать внутренний notebook package
и записать staged notebook entry + V1_navigation.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from write_v1_notebook import NAV_HEADER, NAV_PLACEHOLDER_PREFIX, NAV_SEPARATOR, repo_root, write_outputs


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
QUESTION_ID_RE = re.compile(r"^V1-(\d{8})-(\d{6})$")
FOOTNOTE_URL_RE = re.compile(r"^\[\d+\]:\s+(https?://\S+)", re.MULTILINE)
MARKDOWN_LINK_URL_RE = re.compile(r"\((https?://[^)\s]+)\)")
INLINE_URL_RE = re.compile(r"https?://[^\s)\]]+")
FOOTNOTE_LINE_RE = re.compile(r"^\[\d+\]:\s+https?://\S+")

CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собрать internal notebook package из raw `/v1` ответа и записать staged notebook entry."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--stdin", action="store_true", help="Читать raw response из stdin.")
    source_group.add_argument("--input", help="Путь к файлу с raw external response.")
    parser.add_argument(
        "--root",
        default=None,
        help="Путь к корню проекта. По умолчанию используется корень репозитория скрипта.",
    )
    return parser.parse_args()


def read_input(args: argparse.Namespace) -> str:
    if args.stdin:
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding="utf-8")
    text = text.lstrip("\ufeff")
    if not text.strip():
        raise ValueError("raw external response пустой.")
    return text.strip() + "\n"


def parse_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        raise ValueError("Не найдены markdown-секции `## ...`.")

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[title] = body
    return sections


def require_section(sections: dict[str, str], name: str) -> str:
    value = sections.get(name, "").strip()
    if not value:
        raise ValueError(f"В raw response отсутствует обязательная секция `## {name}`.")
    return value


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def parse_question_id(text: str) -> tuple[str, str]:
    question_id = first_nonempty_line(text)
    if not QUESTION_ID_RE.match(question_id):
        raise ValueError("`External Question ID` должен иметь формат `V1-YYYYMMDD-HHMMSS`.")
    date_part = question_id.split("-")[1]
    date_value = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
    return question_id, date_value


def parse_provider_model(text: str) -> str:
    provider_model = first_nonempty_line(text)
    if not provider_model:
        raise ValueError("Секция `Provider/Model` пустая.")
    return provider_model


def extract_context_links(raw_text: str) -> list[str]:
    links: list[str] = []
    for pattern in (FOOTNOTE_URL_RE, MARKDOWN_LINK_URL_RE, INLINE_URL_RE):
        for match in pattern.finditer(raw_text):
            url = match.group(1) if match.lastindex else match.group(0)
            url = url.rstrip(").,:;")
            if url not in links:
                links.append(url)
    return links


def normalize_whitespace(text: str) -> str:
    return " ".join(text.replace("\r", "").split())


def strip_trailing_footnotes(text: str) -> str:
    kept_lines: list[str] = []
    for line in text.splitlines():
        if FOOTNOTE_LINE_RE.match(line.strip()):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip()


def derive_topic_and_summary(question_id: str, candidate_text: str) -> tuple[str, str]:
    candidate_text = strip_trailing_footnotes(candidate_text)
    candidate_text = normalize_whitespace(candidate_text)
    if not candidate_text:
        raise ValueError("Секция `Candidate Navigation Entry` пустая.")

    if "Topic:" in candidate_text and "Summary:" in candidate_text:
        topic_match = re.search(r"Topic:\s*(.+?)(?:Summary:|$)", candidate_text)
        summary_match = re.search(r"Summary:\s*(.+)$", candidate_text)
        topic = topic_match.group(1).strip(" .") if topic_match else ""
        summary = summary_match.group(1).strip() if summary_match else ""
        if topic and summary:
            return topic, summary

    prefix = f"{question_id}:"
    if candidate_text.startswith(prefix):
        candidate_text = candidate_text[len(prefix) :].strip()

    verdict_marker = "Verdict:"
    if verdict_marker in candidate_text:
        before, after = candidate_text.split(verdict_marker, 1)
        topic = before.strip(" .")
        summary = f"Verdict: {after.strip()}"
    else:
        sentences = re.split(r"(?<=[.!?])\s+", candidate_text, maxsplit=1)
        topic = sentences[0].strip(" .")
        summary = sentences[1].strip() if len(sentences) > 1 else candidate_text

    if not topic:
        topic = question_id
    if not summary:
        summary = candidate_text
    return topic, summary


def transliterate_char(char: str) -> str:
    lower = char.lower()
    if lower in CYRILLIC_TO_LATIN:
        value = CYRILLIC_TO_LATIN[lower]
        return value.upper() if char.isupper() else value
    return char


def slugify(value: str) -> str:
    transliterated = "".join(transliterate_char(char) for char in value)
    normalized = transliterated.lower()
    normalized = normalized.replace("/v1", "v1").replace("/r1", "r1")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    if not normalized:
        return "entry"
    parts = [part for part in normalized.split("-") if part]
    return "-".join(parts[:8])


def indent_block(text: str) -> str:
    return "\n".join(f"  {line}" if line else "" for line in text.rstrip().splitlines())


def build_package_text(
    question_id: str,
    date_value: str,
    slug: str,
    provider_model: str,
    context_links: list[str],
    topic: str,
    summary: str,
    raw_response: str,
) -> tuple[str, str, str]:
    notebook_entry_path = f".ai/external_chats/notebook/{date_value}_{question_id}_{slug}.md"
    package_path = f".ai/external_chats/notebook_packages/{date_value}_{question_id}_{slug}_package.md"
    navigation_path = ".ai/external_chats/V1_navigation.md"
    candidate_entry = f"Topic: {topic}\nSummary: {summary}"

    package_lines = [
        "# Notebook Package",
        "",
        "Mode: `kilo-notebook`",
        "Route: `/v1`",
        "",
        f"external_question_id: {question_id}",
        f"notebook_entry_path: {notebook_entry_path}",
        f"v1_navigation_path: {navigation_path}",
        "",
        "allowed_writes:",
        f"- {notebook_entry_path}",
        f"- {navigation_path}",
        "",
        "entry_status: staged",
        f"provider_model: {provider_model}",
        "",
        "context_links:",
    ]
    if context_links:
        package_lines.extend(f"- {item}" for item in context_links)
    else:
        package_lines.append("- нет")
    package_lines.extend(
        [
            "",
            "candidate_navigation_entry: |",
            indent_block(candidate_entry),
            "raw_response: |",
            indent_block(raw_response),
            "",
        ]
    )
    return "\n".join(package_lines), package_path, notebook_entry_path


def build_navigation_seed_text() -> str:
    return "\n".join(
        [
            "# V1 Navigation",
            "",
            "| External Question ID | Date | Status | Topic | Notebook Entry Path | Summary |",
            "|---|---|---|---|---|---|",
            "| — | — | `staged` | Entries will appear here | — | — |",
            "",
        ]
    )


def ensure_seed_files(root: Path) -> None:
    navigation_path = root / ".ai" / "external_chats" / "V1_navigation.md"
    if not navigation_path.exists():
        navigation_path.parent.mkdir(parents=True, exist_ok=True)
        navigation_path.write_text(build_navigation_seed_text(), encoding="utf-8")
        return

    text = navigation_path.read_text(encoding="utf-8")
    if NAV_HEADER not in text or NAV_SEPARATOR not in text:
        raise ValueError(
            "Существующий `V1_navigation.md` не содержит ожидаемую таблицу. "
            "Автосоздание seed выполняется только для отсутствующего файла."
        )
    if NAV_PLACEHOLDER_PREFIX not in text and "| V1-" not in text:
        raise ValueError(
            "Существующий `V1_navigation.md` не содержит ни placeholder, ни реальных V1 entries."
        )


def verify_outputs(
    root: Path,
    question_id: str,
    package_path: Path,
    notebook_path: Path,
    navigation_path: Path,
    navigation_row: str,
    source_path: Path | None,
) -> None:
    if source_path is not None and not source_path.exists():
        raise ValueError(f"Source file не найден после запуска: {source_path}")
    if not package_path.exists():
        raise ValueError(f"Package file не найден после запуска: {package_path}")
    if not notebook_path.exists():
        raise ValueError(f"Notebook entry не найден после запуска: {notebook_path}")
    if not navigation_path.exists():
        raise ValueError(f"V1_navigation.md не найден после запуска: {navigation_path}")

    notebook_text = notebook_path.read_text(encoding="utf-8")
    if question_id not in notebook_text:
        raise ValueError("Notebook entry создан, но не содержит ожидаемый External Question ID.")

    navigation_text = navigation_path.read_text(encoding="utf-8")
    if question_id not in navigation_text:
        raise ValueError("V1_navigation.md обновлён некорректно: ID не найден.")

    notebook_relpath = notebook_path.relative_to(root).as_posix()
    if notebook_relpath not in navigation_text:
        raise ValueError("V1_navigation.md не содержит путь к созданному notebook entry.")

    if navigation_row not in navigation_text:
        raise ValueError("V1_navigation.md не содержит ожидаемую строку navigation row.")


def cleanup_support_artifacts(root: Path, package_path: Path, source_path: Path | None) -> list[str]:
    deleted: list[str] = []

    package_path.unlink()
    deleted.append(str(package_path))

    if source_path is not None:
        notebook_sources_dir = (root / ".ai" / "external_chats" / "notebook_sources").resolve()
        try:
            source_path.relative_to(notebook_sources_dir)
        except ValueError:
            return deleted

        source_path.unlink()
        deleted.append(str(source_path))

    return deleted


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()
    root = Path(args.root).resolve() if args.root else repo_root()
    source_abs = Path(args.input).resolve() if args.input else None

    try:
        raw_response = read_input(args)
        sections = parse_sections(raw_response)
        question_id, date_value = parse_question_id(require_section(sections, "External Question ID"))
        provider_model = parse_provider_model(require_section(sections, "Provider/Model"))
        require_section(sections, "Answer")
        candidate_text = require_section(sections, "Candidate Navigation Entry")
        topic, summary = derive_topic_and_summary(question_id, candidate_text)
        slug = slugify(topic)
        context_links = extract_context_links(raw_response)
        ensure_seed_files(root)

        package_text, package_relpath, _ = build_package_text(
            question_id=question_id,
            date_value=date_value,
            slug=slug,
            provider_model=provider_model,
            context_links=context_links,
            topic=topic,
            summary=summary,
            raw_response=raw_response,
        )

        package_abs = (root / package_relpath).resolve()
        package_abs.parent.mkdir(parents=True, exist_ok=True)
        package_abs.write_text(package_text, encoding="utf-8")

        notebook_path, navigation_path, navigation_row = write_outputs(package_abs, root)
        verify_outputs(
            root=root,
            question_id=question_id,
            package_path=package_abs,
            notebook_path=notebook_path,
            navigation_path=navigation_path,
            navigation_row=navigation_row,
            source_path=source_abs,
        )
        deleted_paths = cleanup_support_artifacts(
            root=root,
            package_path=package_abs,
            source_path=source_abs,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename}")
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print("OK: raw response staged for kilo-notebook.")
    print(f"Notebook entry: {notebook_path}")
    print(f"V1 navigation: {navigation_path}")
    print(f"Navigation row: {navigation_row}")
    if deleted_paths:
        print("Cleanup:")
        for item in deleted_paths:
            print(f"  deleted: {item}")
    print("Verification: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

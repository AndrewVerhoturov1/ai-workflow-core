#!/usr/bin/env python3
"""
Sync canonical Kilo workflow files from central core (ai-workflow-core) into a consumer project.

This script lives in the central core repo and syncs files from central core paths
to their corresponding consumer repo paths. It is the primary sync mechanism for
keeping consumer repos up-to-date with the canonical workflow core.

Usage:
    python scripts/sync_kilo_workflow.py --target <consumer-project-path>
    python scripts/sync_kilo_workflow.py --target <path> --force-canonical
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_DIRECTORIES = (
    ".ai/handoffs",
    ".ai/reports",
    ".ai/reviews",
    ".ai/backlog",
    ".ai/plans/sessions",
    ".ai/model_tests",
    ".ai/external_chats/tasks",
    ".ai/external_chats/requests",
    ".ai/external_chats/responses",
    ".ai/external_chats/recorder_packages",
    ".ai/external_chats/reviews",
    ".ai/external_chats/notebook_sources",
    ".ai/external_chats/notebook",
)

# Central core path -> Consumer repo path mapping
CANONICAL_FILE_MAP = {
    # Root
    "AGENTS.md": "AGENTS.md",
    ".gitignore": ".gitignore",
    "ai_readme.md": ".ai/README.md",

    # Rules
    "rules/agent_protocol.md": ".ai/agent_protocol.md",
    "rules/model_roster.md": ".ai/model_roster.md",
    "rules/codex_orchestrator.md": ".ai/rules/codex_orchestrator.md",
    "rules/kilo_mode_contract.md": ".ai/rules/kilo_mode_contract.md",
    "rules/kilo_builder.md": ".ai/rules/kilo_builder.md",
    "rules/kilo_debugger.md": ".ai/rules/kilo_debugger.md",
    "rules/kilo_docs.md": ".ai/rules/kilo_docs.md",
    "rules/kilo_refactor.md": ".ai/rules/kilo_refactor.md",
    "rules/kilo_tester.md": ".ai/rules/kilo_tester.md",

    # Validators
    "validators/README.md": ".ai/validators/README.md",

    # Plans
    "plans/README.md": ".ai/plans/README.md",

    # Prompts — весь prompt-layer
    "prompts/choose_model.md": ".ai/prompts/choose_model.md",
    "prompts/create_handoff.md": ".ai/prompts/create_handoff.md",
    "prompts/create_external_question_prompt.md": ".ai/prompts/create_external_question_prompt.md",
    "prompts/create_external_chat_request.md": ".ai/prompts/create_external_chat_request.md",
    "prompts/create_block_plan.md": ".ai/prompts/create_block_plan.md",
    "prompts/create_block_orchestrator_package.md": ".ai/prompts/create_block_orchestrator_package.md",
    "prompts/record_external_chat_response.md": ".ai/prompts/record_external_chat_response.md",
    "prompts/record_external_notebook_response.md": ".ai/prompts/record_external_notebook_response.md",
    "prompts/review_agent_report.md": ".ai/prompts/review_agent_report.md",
    "prompts/review_block_report.md": ".ai/prompts/review_block_report.md",
    "prompts/0028_kilo_capabilities_inventory_prompt.md": ".ai/prompts/0028_kilo_capabilities_inventory_prompt.md",
    "prompts/0029_enable_context7_global_kilo_prompt.md": ".ai/prompts/0029_enable_context7_global_kilo_prompt.md",
    "prompts/0030_verify_context7_in_kilo_prompt.md": ".ai/prompts/0030_verify_context7_in_kilo_prompt.md",
    "prompts/0031_debug_context7_in_kilo_prompt.md": ".ai/prompts/0031_debug_context7_in_kilo_prompt.md",

    # Templates
    "templates/block_plan_template.md": ".ai/templates/block_plan_template.md",
    "templates/block_orchestrator_package_template.md": ".ai/templates/block_orchestrator_package_template.md",
    "templates/block_context_pack_template.md": ".ai/templates/block_context_pack_template.md",
    "templates/block_report_template.md": ".ai/templates/block_report_template.md",
    "templates/chunk_plan_template.md": ".ai/templates/chunk_plan_template.md",
    "templates/chunk_completion_report_template.md": ".ai/templates/chunk_completion_report_template.md",

    # Bootstrap / Portable
    "bootstrap/portable/README.md": ".ai/bootstrap/portable/README.md",
    "bootstrap/portable/manifest.md": ".ai/bootstrap/portable/manifest.md",
    "bootstrap/portable/copy_map.md": ".ai/bootstrap/portable/copy_map.md",
    "bootstrap/portable/manual_setup_checklist.md": ".ai/bootstrap/portable/manual_setup_checklist.md",
    "bootstrap/portable/verification_checklist.md": ".ai/bootstrap/portable/verification_checklist.md",
    "bootstrap/portable/templates/AGENTS.md.template": ".ai/bootstrap/portable/templates/AGENTS.md.template",
    "bootstrap/portable/templates/architecture.md.template": ".ai/bootstrap/portable/templates/architecture.md.template",
    "bootstrap/portable/templates/current_sprint.md.template": ".ai/bootstrap/portable/templates/current_sprint.md.template",
    "bootstrap/portable/templates/decisions.md.template": ".ai/bootstrap/portable/templates/decisions.md.template",
    "bootstrap/portable/templates/project_brief.md.template": ".ai/bootstrap/portable/templates/project_brief.md.template",
    "bootstrap/portable/templates/project_state.md.template": ".ai/bootstrap/portable/templates/project_state.md.template",
    "bootstrap/portable/templates/publisher_config.json.template": ".ai/bootstrap/portable/templates/publisher_config.json.template",

    # Scripts
    "scripts/validate_kilo_contract.py": "scripts/validate_kilo_contract.py",
    "scripts/validate_session_contract.py": "scripts/validate_session_contract.py",
    "scripts/validate_external_chat_package.py": "scripts/validate_external_chat_package.py",
    "scripts/external_chat_publish.py": "scripts/external_chat_publish.py",
    "scripts/sync_kilo_workflow.py": "scripts/sync_kilo_workflow.py",
    "scripts/stage_v1_notebook.py": "scripts/stage_v1_notebook.py",
    "scripts/write_v1_notebook.py": "scripts/write_v1_notebook.py",

    # External Chat
    "external_chat/manual.md": ".ai/external_chats/manual.md",
    "external_chat/external_agent_static_manual.md": ".ai/external_chats/external_agent_static_manual.md",
    "external_chat/tasks/README.md": ".ai/external_chats/tasks/README.md",
}

STARTER_FILES = {
    ".ai/project_state.md": (
        "# Project State\n\n"
        "- Проект подключен к глобальному workflow `Codex + Kilo Code`.\n"
        "- Заполните этот файл проектным состоянием до первой продуктовой задачи.\n"
    ),
    ".ai/backlog/current_sprint.md": (
        "# Current Sprint\n\n- Заполните текущие задачи проекта.\n"
    ),
    ".ai/model_tests/model_test_log.md": (
        "# Model Test Log\n\n"
        "Это ручной historical log наблюдений по моделям для `/kilo`.\n\n"
        "## Формат записи\n\n"
        "- Дата:\n- Модель:\n- Сценарий: smoke / coding / debug / verifier / recorder\n"
        "- Результат:\n- Заметки:\n"
    ),
}


def repo_root() -> Path:
    """Return the central core repo root (parent of the scripts/ directory)."""
    return Path(__file__).resolve().parents[1]


def copy_file(central_root: Path, target_root: Path, central_path: str, consumer_path: str, force: bool) -> str:
    source = central_root / central_path
    target = target_root / consumer_path
    if not source.exists():
        return f"missing_source {central_path}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        return f"skip {consumer_path}"
    shutil.copy2(source, target)
    return f"copy {central_path} -> {consumer_path}"


def write_starter_file(target_root: Path, relative_path: str, content: str, force: bool) -> str:
    target = target_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        return f"skip {relative_path}"
    target.write_text(content, encoding="utf-8")
    return f"write {relative_path}"


def sync(target_root: Path, force_canonical: bool, force_starters: bool) -> list[str]:
    central_root = repo_root()
    actions: list[str] = []

    for directory in REQUIRED_DIRECTORIES:
        path = target_root / directory
        path.mkdir(parents=True, exist_ok=True)
        actions.append(f"mkdir {directory}")

    for central_path, consumer_path in CANONICAL_FILE_MAP.items():
        actions.append(copy_file(central_root, target_root, central_path, consumer_path, force_canonical))

    for relative_path, content in STARTER_FILES.items():
        actions.append(write_starter_file(target_root, relative_path, content, force_starters))

    return actions


def git_status_summary(target_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=target_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Синхронизация canonical Kilo workflow из central core (ai-workflow-core) в consumer проект."
    )
    parser.add_argument("--target", required=True, help="Путь к целевому consumer проекту.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Устаревший alias. Соответствует `--force-canonical` и не перезаписывает project-specific starter files.",
    )
    parser.add_argument(
        "--force-canonical",
        action="store_true",
        help="Перезаписывать canonical workflow-файлы в consumer проекте из central core.",
    )
    parser.add_argument(
        "--force-starters",
        action="store_true",
        help="Перезаписывать project-specific starter files вроде `.ai/project_state.md` и `.ai/backlog/current_sprint.md`.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    target_root = Path(args.target).resolve()
    force_canonical = args.force or args.force_canonical

    central_root = repo_root()
    print(f"Central core source: {central_root}")
    print(f"Consumer target:     {target_root}")
    print()

    actions = sync(target_root, force_canonical, args.force_starters)
    for action in actions:
        print(action)

    print()
    print(f"Готово: workflow синхронизирован из central core в {target_root}")

    status_lines = git_status_summary(target_root)
    if status_lines:
        print("POST-SYNC: зафиксируйте синхронизированные workflow-файлы отдельным commit.")
        print('POST-SYNC: git commit -m "Workflow: sync global Kilo rules"')
        print("POST-SYNC: до этого проект не считается готовым к следующему /kilo.")
    else:
        print("POST-SYNC: git status чистый, отдельный workflow checkpoint не требуется.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

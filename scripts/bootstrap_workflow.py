#!/usr/bin/env python3
"""
Script-assisted portable bootstrap wrapper for Codex + Kilo consumer repos.

P1: Script-Assisted Bootstrap Wrapper — canonical core version.
Запускается ИЗ central core (ai-workflow-core) и материализует managed copies
в новый consumer repo, используя core-to-consumer mapping из CANONICAL_FILE_MAP.

Опирается на:
  - portable bootstrap package (bootstrap/portable/)
  - CANONICAL_FILE_MAP из scripts/sync_kilo_workflow.py
  - copy_map.md managed copy shortlist

Не делает:
  - migration/adoption existing repos
  - metadata-aware post-bootstrap sync/update
  - GitHub /r1 route automation

Отличие от consumer-версии:
  - Source layout = central core (rules/, prompts/, templates/, bootstrap/portable/, validators/).
  - Target layout = consumer repo (.ai/rules/, .ai/prompts/, .ai/templates/, .ai/bootstrap/portable/).
  - Mapping задаётся CANONICAL_FILE_MAP из sync_kilo_workflow.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Reuse CANONICAL_FILE_MAP from sync_kilo_workflow
# ---------------------------------------------------------------------------

try:
    from scripts.sync_kilo_workflow import CANONICAL_FILE_MAP
    _SYNC_IMPORT_OK = True
except ImportError:
    _SYNC_IMPORT_OK = False
    CANONICAL_FILE_MAP: dict[str, str] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_file(src: Path, dst: Path, overwrite: bool) -> str:
    """Copy a single file, return action description."""
    if dst.exists() and not overwrite:
        return f"skip  {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copy  {dst}"


def _git_status(target: Path) -> list[str]:
    """Return git status short lines or empty list if no git."""
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Core-to-consumer managed copy mapping
# ---------------------------------------------------------------------------

# Исключаем из managed-copy-map: AGENTS.md (seed-копия), .gitignore, scripts/ (отдельно)
def _build_managed_copy_map() -> dict[str, str]:
    """Build core→consumer mapping for managed copies, excluding special paths."""
    managed: dict[str, str] = {}
    for core_path, consumer_path in CANONICAL_FILE_MAP.items():
        if core_path == "AGENTS.md":
            continue
        if core_path == ".gitignore":
            continue
        if core_path.startswith("scripts/"):
            continue
        managed[core_path] = consumer_path
    return managed


# AGENTS.md: seed-copied, then becomes local-adapted (NOT managed after adaptation)
AGENTS_SEED = "AGENTS.md"

# Directory-level mappings for recursive copy
CORE_MANAGED_DIRS_MAP: dict[str, str] = {
    "rules": ".ai/rules",
    "prompts": ".ai/prompts",
    "templates": ".ai/templates",
    "bootstrap/portable": ".ai/bootstrap/portable",
}

# Individual managed files (not in dirs above, not scripts, not root-special)
# These are derived from CANONICAL_FILE_MAP minus dirs and special entries
INDIVIDUAL_MANAGED_FILES: dict[str, str] = {
    "ai_readme.md": ".ai/README.md",
    "validators/README.md": ".ai/validators/README.md",
    "plans/README.md": ".ai/plans/README.md",
    "external_chat_rules.md": ".ai/external_chats/external_chat_rules.md",
    "repo_navigation.md": ".ai/repo_navigation.md",
    "external_chat/manual.md": ".ai/external_chats/manual.md",
    "external_chat/external_agent_static_manual.md": ".ai/external_chats/external_agent_static_manual.md",
    "external_chat/tasks/README.md": ".ai/external_chats/tasks/README.md",
}

# Script files — materialize to scripts/ in consumer
CORE_SCRIPTS: list[str] = [
    "scripts/validate_kilo_contract.py",
    "scripts/validate_session_contract.py",
    "scripts/validate_external_chat_package.py",
    "scripts/external_chat_publish.py",
    "scripts/sync_kilo_workflow.py",
    "scripts/stage_v1_notebook.py",
    "scripts/write_v1_notebook.py",
    "scripts/bootstrap_workflow.py",
    "scripts/safe_sync_workflow.py",
]

# ---------------------------------------------------------------------------
# Backward-compatible exports for safe_sync_workflow.py
# These mirror the original consumer-repo API (consumer-path lists)
# ---------------------------------------------------------------------------

MANAGED_COPY_FILES: list[str] = list(INDIVIDUAL_MANAGED_FILES.values()) + CORE_SCRIPTS
MANAGED_COPY_DIRS: list[str] = list(CORE_MANAGED_DIRS_MAP.values())

# Core-to-consumer mapping for inventory/classification
# Keys = core source paths, Values = consumer target paths
# Used by safe_sync_workflow.py to locate central files in core layout
CORE_MANAGED_MAP: dict[str, str] = {}
CORE_MANAGED_MAP.update(INDIVIDUAL_MANAGED_FILES)
for dir_core, dir_consumer in CORE_MANAGED_DIRS_MAP.items():
    src_dir = _repo_root() / dir_core
    if src_dir.is_dir():
        for item in src_dir.rglob("*"):
            if item.is_dir():
                continue
            rel_item = item.relative_to(src_dir)
            CORE_MANAGED_MAP[f"{dir_core}/{rel_item.as_posix()}"] = f"{dir_consumer}/{rel_item.as_posix()}"
for script_path in CORE_SCRIPTS:
    CORE_MANAGED_MAP[script_path] = script_path

# ---------------------------------------------------------------------------
# Project file instantiation — from bootstrap/portable/templates/
# ---------------------------------------------------------------------------

TEMPLATE_MAP: dict[str, str] = {
    "project_brief.md.template": ".ai/project_brief.md",
    "project_state.md.template": ".ai/project_state.md",
    "architecture.md.template": ".ai/architecture.md",
    "decisions.md.template": ".ai/decisions.md",
    "current_sprint.md.template": ".ai/backlog/current_sprint.md",
    "publisher_config.json.template": ".ai/external_chats/publisher_config.json",
}

PLACEHOLDER_MAP: dict[str, str] = {
    "{{PROJECT_NAME}}": "project_name",
    "{{PROJECT_TYPE}}": "project_type",
    "{{PRIMARY_LANGUAGE}}": "primary_language",
    "{{TEST_COMMANDS}}": "test_commands",
    "{{BUILD_COMMANDS}}": "build_commands",
    "{{HIGH_RISK_AREAS}}": "high_risk_areas",
    "{{PROJECT_RULES}}": "project_rules",
    "{{GITHUB_REPO}}": "github_repo",
    "{{GITHUB_BRANCH}}": "github_branch",
    "{{STATIC_MANUAL_VERSION}}": "static_manual_version",
    "{{CREATION_DATE}}": "creation_date",
    "{{BOOTSTRAP_MODE}}": "bootstrap_mode",
}

# ---------------------------------------------------------------------------
# Runtime directories — created empty
# ---------------------------------------------------------------------------

RUNTIME_DIRS: list[str] = [
    ".ai/handoffs",
    ".ai/reports",
    ".ai/reviews",
    ".ai/backlog",
    ".ai/plans/sessions",
    ".ai/plans/chunks",
    ".ai/plans/master",
    ".ai/model_tests",
    ".ai/external_chats/tasks",
    ".ai/external_chats/requests",
    ".ai/external_chats/responses",
    ".ai/external_chats/recorder_packages",
    ".ai/external_chats/reviews",
    ".ai/external_chats/notebook_sources",
    ".ai/external_chats/notebook",
]

# ---------------------------------------------------------------------------
# Bootstrap metadata paths
# ---------------------------------------------------------------------------

BOOTSTRAP_STATE_DIR = ".ai/bootstrap/state"
BOOTSTRAP_RUNS_DIR = ".ai/bootstrap/runs"
CORE_SYNC_STATE_FILE = ".ai/bootstrap/state/core_sync_state.yml"


# ===================================================================
# Preflight
# ===================================================================

def _preflight(target: Path) -> dict:
    """Check target dir state before any writes. Return preflight summary dict."""
    result: dict = {
        "target": str(target),
        "exists": target.exists(),
        "is_dir": target.is_dir() if target.exists() else False,
        "is_empty": False,
        "is_git_repo": False,
        "has_git_remote": False,
        "has_agents_md": False,
        "has_dot_ai": False,
        "has_scripts_dir": False,
        "existing_project_files": [],
        "existing_managed_files": [],
        "conflict_summary": [],
        "target_class": "unknown",
    }

    if not result["is_dir"]:
        result["target_class"] = "new_directory"
        return result

    contents = list(target.iterdir())
    result["is_empty"] = len(contents) == 0

    # Git detection
    git_dir = target / ".git"
    result["is_git_repo"] = git_dir.exists() and git_dir.is_dir()
    if result["is_git_repo"]:
        remotes = subprocess.run(
            ["git", "remote", "-v"],
            cwd=target,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        result["has_git_remote"] = bool(remotes.stdout.strip())

    # Existing workflow markers
    result["has_agents_md"] = (target / "AGENTS.md").exists()
    result["has_dot_ai"] = (target / ".ai").exists() and (target / ".ai").is_dir()
    result["has_scripts_dir"] = (target / "scripts").exists() and (target / "scripts").is_dir()

    # Existing project-specific files
    project_files = [
        ".ai/project_brief.md",
        ".ai/project_state.md",
        ".ai/architecture.md",
        ".ai/decisions.md",
        ".ai/backlog/current_sprint.md",
        ".ai/external_chats/publisher_config.json",
    ]
    for pf in project_files:
        if (target / pf).exists():
            result["existing_project_files"].append(pf)

    # Existing managed files (overlap check) — check consumer paths
    all_consumer_paths = list(INDIVIDUAL_MANAGED_FILES.values())
    for dir_core, dir_consumer in CORE_MANAGED_DIRS_MAP.items():
        src_dir = _repo_root() / dir_core
        if src_dir.is_dir():
            for item in src_dir.rglob("*"):
                if item.is_dir():
                    continue
                rel_item = item.relative_to(src_dir)
                all_consumer_paths.append(f"{dir_consumer}/{rel_item.as_posix()}")
    for script_path in CORE_SCRIPTS:
        all_consumer_paths.append(script_path)
    for mf in all_consumer_paths:
        if (target / mf).exists():
            result["existing_managed_files"].append(mf)

    # Conflict detection
    if result["existing_project_files"]:
        result["conflict_summary"].append(
            f"Обнаружены существующие project-specific файлы: {result['existing_project_files']}"
        )
    if result["existing_managed_files"]:
        result["conflict_summary"].append(
            f"Обнаружены существующие managed файлы: {result['existing_managed_files']}"
        )
    if result["has_agents_md"]:
        result["conflict_summary"].append("Существует AGENTS.md — потребуется решение: сохранить/заменить/sidecar")

    # Classify target
    if result["is_empty"]:
        result["target_class"] = "empty_directory"
    elif result["is_git_repo"] and (result["has_dot_ai"] or result["has_agents_md"]):
        result["target_class"] = "existing_workflow_repo"
    elif result["is_git_repo"]:
        result["target_class"] = "existing_git_repo_no_workflow"
    elif result["has_dot_ai"] or result["has_agents_md"]:
        result["target_class"] = "partial_workflow_no_git"
    else:
        result["target_class"] = "non_empty_directory"

    return result


def _print_preflight(preflight: dict) -> None:
    """Human-readable preflight summary."""
    print("=" * 60)
    print("PREFLIGHT — анализ целевой директории")
    print("=" * 60)
    print(f"  Целевая директория: {preflight['target']}")
    print(f"  Класс цели:         {preflight['target_class']}")
    print(f"  Существует:         {preflight['exists']}")
    print(f"  Пустая:             {preflight['is_empty']}")
    print(f"  Git repo:           {preflight['is_git_repo']}")
    print(f"  Git remote:         {preflight['has_git_remote']}")
    print(f"  AGENTS.md:          {preflight['has_agents_md']}")
    print(f"  .ai/:               {preflight['has_dot_ai']}")
    print(f"  scripts/:           {preflight['has_scripts_dir']}")

    if preflight["existing_project_files"]:
        print(f"\n  Существующие project-файлы:")
        for f in preflight["existing_project_files"]:
            print(f"    - {f}")

    if preflight["existing_managed_files"]:
        print(f"\n  Существующие managed-файлы:")
        for f in preflight["existing_managed_files"]:
            print(f"    - {f}")

    if preflight["conflict_summary"]:
        print(f"\n  ⚠ Конфликты:")
        for c in preflight["conflict_summary"]:
            print(f"    {c}")
    else:
        print(f"\n  ✓ Конфликтов не обнаружено")

    print()


# ===================================================================
# Phase 1: Materialize core managed copies
# ===================================================================

def _materialize_managed_copies(
    source_root: Path,
    target: Path,
    *,
    overwrite: bool,
    dry_run: bool,
) -> list[str]:
    """Materialize managed copies from core source to consumer target. Return action log."""
    actions: list[str] = []

    # AGENTS.md — seed copy
    src = source_root / AGENTS_SEED
    if src.exists():
        dst = target / AGENTS_SEED
        if dry_run:
            action = "would-copy" if not dst.exists() or overwrite else "would-skip"
            actions.append(f"{action}  {AGENTS_SEED}")
        else:
            act = _copy_file(src, dst, overwrite)
            actions.append(f"{act}  {AGENTS_SEED}")
    else:
        actions.append(f"warn   AGENTS.md отсутствует в source — пропущен")

    # Individual managed files (core→consumer mapping)
    for core_path, consumer_path in INDIVIDUAL_MANAGED_FILES.items():
        src = source_root / core_path
        dst = target / consumer_path
        if not src.exists():
            actions.append(f"warn   source missing: {core_path} → {consumer_path}")
            continue
        if dry_run:
            action = "would-copy" if not dst.exists() or overwrite else "would-skip"
            actions.append(f"{action}  {core_path} → {consumer_path}")
        else:
            act = _copy_file(src, dst, overwrite)
            actions.append(f"{act}  {core_path} → {consumer_path}")

    # Managed directory trees (core→consumer mapping)
    for dir_core, dir_consumer in CORE_MANAGED_DIRS_MAP.items():
        src_dir = source_root / dir_core
        dst_dir = target / dir_consumer
        if not src_dir.exists() or not src_dir.is_dir():
            actions.append(f"warn   source dir missing: {dir_core} → {dir_consumer}")
            continue
        for item in sorted(src_dir.rglob("*")):
            if item.is_dir():
                continue
            rel_item = item.relative_to(src_dir)
            src_item = src_dir / rel_item
            dst_item = dst_dir / rel_item
            if dry_run:
                action = "would-copy" if not dst_item.exists() or overwrite else "would-skip"
                actions.append(f"{action}  {dir_core}/{rel_item.as_posix()} → {dir_consumer}/{rel_item.as_posix()}")
            else:
                act = _copy_file(src_item, dst_item, overwrite)
                actions.append(f"{act}  {dir_core}/{rel_item.as_posix()} → {dir_consumer}/{rel_item.as_posix()}")

    # Script files (same path in both layouts)
    for script_rel in CORE_SCRIPTS:
        src = source_root / script_rel
        dst = target / script_rel
        if not src.exists():
            actions.append(f"warn   source script missing: {script_rel}")
            continue
        if dry_run:
            action = "would-copy" if not dst.exists() or overwrite else "would-skip"
            actions.append(f"{action}  {script_rel}")
        else:
            act = _copy_file(src, dst, overwrite)
            actions.append(f"{act}  {script_rel}")

    return actions


# ===================================================================
# Phase 2: Instantiate project files from templates
# ===================================================================

def _render_template(text: str, values: dict[str, str]) -> str:
    """Replace {{PLACEHOLDER}} tokens with values."""
    for placeholder, key in PLACEHOLDER_MAP.items():
        if placeholder in text:
            text = text.replace(placeholder, values.get(key, placeholder))
    return text


def _instantiate_project_files(
    source_root: Path,
    target: Path,
    values: dict[str, str],
    *,
    dry_run: bool,
) -> list[str]:
    """Create project-specific files from portable templates. Return action log."""
    actions: list[str] = []
    # Templates live at bootstrap/portable/templates/ in core (NOT .ai/bootstrap/portable/templates/)
    templates_root = source_root / "bootstrap" / "portable" / "templates"

    for template_name, dest_rel in TEMPLATE_MAP.items():
        template_path = templates_root / template_name
        dest = target / dest_rel

        if not template_path.exists():
            actions.append(f"warn   template missing: {template_name}")
            continue

        if dest.exists():
            actions.append(f"skip  {dest_rel} (уже существует — human gate)")
            continue

        if dry_run:
            actions.append(f"would-create  {dest_rel}")
        else:
            raw = template_path.read_text(encoding="utf-8")
            rendered = _render_template(raw, values)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(rendered, encoding="utf-8")
            actions.append(f"create  {dest_rel}")

    return actions


# ===================================================================
# Phase 3: Create runtime directories
# ===================================================================

def _create_runtime_dirs(
    target: Path,
    *,
    dry_run: bool,
) -> list[str]:
    """Create empty runtime directories. Return action log."""
    actions: list[str] = []
    for rel in RUNTIME_DIRS:
        d = target / rel
        if d.exists():
            actions.append(f"skip-dir  {rel} (уже существует)")
            continue
        if dry_run:
            actions.append(f"would-mkdir  {rel}")
        else:
            d.mkdir(parents=True, exist_ok=True)
            actions.append(f"mkdir  {rel}")
    return actions


# ===================================================================
# Phase 4: Write bootstrap metadata
# ===================================================================

def _compute_checksum(path: Path) -> str:
    """SHA-256 hex digest of file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_consumer_managed_files_list() -> list[str]:
    """Build list of all consumer-path managed files for metadata recording."""
    result: list[str] = []
    for consumer_path in INDIVIDUAL_MANAGED_FILES.values():
        result.append(consumer_path)
    for dir_core, dir_consumer in CORE_MANAGED_DIRS_MAP.items():
        src_dir = _repo_root() / dir_core
        if src_dir.is_dir():
            for item in src_dir.rglob("*"):
                if item.is_dir():
                    continue
                rel_item = item.relative_to(src_dir)
                result.append(f"{dir_consumer}/{rel_item.as_posix()}")
    for script_path in CORE_SCRIPTS:
        result.append(script_path)
    return result


def _write_core_sync_state(
    target: Path,
    source_root: Path,
    *,
    project_name: str,
    bootstrap_mode: str,
    source_revision: str,
    source_url: str,
    dry_run: bool,
) -> str:
    """Write core_sync_state.yml. Return action description."""
    dest = target / CORE_SYNC_STATE_FILE
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    managed_entries: list[dict] = []

    # Individual managed files
    for core_path, consumer_path in INDIVIDUAL_MANAGED_FILES.items():
        dst_file = target / consumer_path
        if dst_file.exists():
            managed_entries.append({
                "source": core_path,
                "destination": consumer_path,
                "placement": "hybrid",
                "local_edit_policy": "do-not-edit",
                "checksum": _compute_checksum(dst_file) if not dry_run else "dry-run",
            })

    # Managed directory trees
    for dir_core, dir_consumer in CORE_MANAGED_DIRS_MAP.items():
        src_dir = source_root / dir_core
        dst_dir = target / dir_consumer
        if not src_dir.is_dir() or not dst_dir.is_dir():
            continue
        for item in sorted(src_dir.rglob("*")):
            if item.is_dir():
                continue
            rel_item = item.relative_to(src_dir)
            dst_item = dst_dir / rel_item
            if dst_item.exists():
                managed_entries.append({
                    "source": f"{dir_core}/{rel_item.as_posix()}",
                    "destination": f"{dir_consumer}/{rel_item.as_posix()}",
                    "placement": "hybrid",
                    "local_edit_policy": "do-not-edit",
                    "checksum": _compute_checksum(dst_item) if not dry_run else "dry-run",
                })

    # Script files
    for script_rel in CORE_SCRIPTS:
        dst_file = target / script_rel
        if dst_file.exists():
            managed_entries.append({
                "source": script_rel,
                "destination": script_rel,
                "placement": "hybrid",
                "local_edit_policy": "do-not-edit",
                "checksum": _compute_checksum(dst_file) if not dry_run else "dry-run",
            })

    yaml_lines = [
        f"schema_version: 1",
        f"canonical_source:",
        f"  repo: ai-workflow-core",
        f"  url: {source_url}",
        f"  revision: {source_revision}",
        f"materialized_from:",
        f"  path: {source_root.as_posix()}",
        f"  repo: {source_root.name}",
        f"sync_direction: central_to_consumer",
        f"bootstrap_package: portable",
        f"bootstrap_mode: {bootstrap_mode}",
        f"project_name: {project_name}",
        f"created_at: {now_iso}",
        f"last_sync_at: {now_iso}",
        f"managed_files:",
    ]

    if managed_entries:
        for entry in managed_entries:
            yaml_lines.append(f"  - source: {entry['source']}")
            yaml_lines.append(f"    destination: {entry['destination']}")
            yaml_lines.append(f"    placement: {entry['placement']}")
            yaml_lines.append(f"    local_edit_policy: {entry['local_edit_policy']}")
            yaml_lines.append(f"    checksum: {entry['checksum']}")
    else:
        yaml_lines.append(f"  []")

    yaml_lines.extend([
        f"adapted_files:",
        f"  - path: AGENTS.md",
        f"    status: seed-copied",
        f"project_files:",
    ])
    for _, dest_rel in TEMPLATE_MAP.items():
        yaml_lines.append(f"  - path: {dest_rel}")
        yaml_lines.append(f"    source: template")
        yaml_lines.append(f"    overwrite_policy: never-without-human")
    yaml_lines.extend([
        f"github:",
        f"  mode: none",
        f"  repo_url: null",
        f"  default_branch: null",
        f"external_route:",
        f"  r1_enabled: false",
        f"  static_manual_url: null",
        f"  status: deferred",
    ])

    content = "\n".join(yaml_lines) + "\n"

    if dry_run:
        return f"would-write  {CORE_SYNC_STATE_FILE}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return f"write  {CORE_SYNC_STATE_FILE}"


def _get_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _write_bootstrap_report(
    target: Path,
    *,
    run_id: str,
    project_name: str,
    preflight: dict,
    all_actions: list[str],
    verification_results: list[dict],
    dry_run: bool,
) -> str:
    """Write bootstrap report markdown. Return action description."""
    report_path = f"{BOOTSTRAP_RUNS_DIR}/{run_id}/bootstrap_report.md"
    dest = target / report_path

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# Bootstrap Report: {project_name}",
        f"",
        f"- Run ID: `{run_id}`",
        f"- Дата: {now_iso}",
        f"- Режим: {'dry-run' if dry_run else 'apply'}",
        f"- Целевая директория: {preflight['target']}",
        f"- Класс цели: {preflight['target_class']}",
        f"- Source: central core (ai-workflow-core)",
        f"",
        f"## Preflight Summary",
        f"",
        f"```text",
        f"  target_class:      {preflight['target_class']}",
        f"  is_empty:          {preflight['is_empty']}",
        f"  is_git_repo:       {preflight['is_git_repo']}",
        f"  has_git_remote:    {preflight['has_git_remote']}",
        f"  has_agents_md:     {preflight['has_agents_md']}",
        f"  has_dot_ai:        {preflight['has_dot_ai']}",
        f"```",
        f"",
    ]

    if preflight["conflict_summary"]:
        lines.append("## Конфликты (preflight)")
        lines.append("")
        for c in preflight["conflict_summary"]:
            lines.append(f"- {c}")
        lines.append("")

    lines.append("## Actions")
    lines.append("")
    lines.append("```text")
    for action in all_actions:
        lines.append(action)
    lines.append("```")
    lines.append("")

    if verification_results:
        lines.append("## Verification")
        lines.append("")
        lines.append("| Script | OK | Return code |")
        lines.append("| --- | --- | --- |")
        for vr in verification_results:
            lines.append(f"| {vr['script']} | {vr['ok']} | {vr['returncode']} |")
        lines.append("")

    lines.append("## Что НЕ внедрено в этом chunk")
    lines.append("")
    lines.append("- **Safe sync/update layer**: metadata-aware post-bootstrap sync с diff/classify/preserve flow.")
    lines.append("- **Migration/adoption layer**: inventory/classification/backfill для existing consumer repos.")
    lines.append("- **GitHub /r1 route automation**: GitHub repo creation, static manual publish, publisher_config автозаполнение.")
    lines.append("- **Kilo UI modes**: ручная настройка режимов в интерфейсе остаётся за человеком.")
    lines.append("- **AGENTS.md локальная адаптация**: seed-копия создана, но semantic adaptation требует ручного review.")
    lines.append("")

    lines.append("## Manual Follow-Up")
    lines.append("")
    lines.append("1. Проверить/настроить Kilo UI modes: Kilo Handoff Runner, Kilo Debugger, Kilo Verifier, Kilo Recorder, Kilo Notebook.")
    lines.append("2. Адаптировать `AGENTS.md` под конкретный проект.")
    lines.append("3. Заполнить project-specific templates: project_brief, architecture, decisions, current_sprint.")
    lines.append("4. При необходимости настроить GitHub remote и published external route.")
    lines.append("5. Пройти verification checklist из `.ai/bootstrap/portable/verification_checklist.md`.")
    lines.append("6. Создать первый session file и выполнить workflow smoke.")
    lines.append("")

    content = "\n".join(lines)

    if dry_run:
        return f"would-write  {report_path}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return f"write  {report_path}"


def _write_actions_jsonl(
    target: Path,
    run_id: str,
    all_actions: list[str],
    *,
    dry_run: bool,
) -> str:
    """Write actions.jsonl for machine-readable trace. Return action description."""
    actions_path = f"{BOOTSTRAP_RUNS_DIR}/{run_id}/actions.jsonl"
    dest = target / actions_path

    if dry_run:
        return f"would-write  {actions_path}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        for action in all_actions:
            f.write(json.dumps({"action": action}, ensure_ascii=False) + "\n")
    return f"write  {actions_path}"


# ===================================================================
# Verification helpers
# ===================================================================

def _run_script_help(target: Path, rel_script: str) -> dict:
    """Run script --help in target dir, return result dict."""
    script_path = target / rel_script
    if not script_path.exists():
        return {
            "script": rel_script,
            "ok": False,
            "returncode": -1,
            "error": "file not found",
        }
    proc = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=target,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return {
        "script": rel_script,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
    }


# ===================================================================
# Main bootstrap flow
# ===================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""\
            Script-assisted portable bootstrap для Codex + Kilo consumer repos.

            Запускается из central core (ai-workflow-core). Материализует managed copies
            из core layout (rules/, prompts/, templates/, bootstrap/portable/) в consumer
            layout (.ai/rules/, .ai/prompts/, .ai/templates/, .ai/bootstrap/portable/).

            Выполняет preflight, materialize managed copies, instantiate project files,
            создаёт runtime dirs, пишет bootstrap metadata и делает базовую verification.

            Не автоматизирует GitHub /r1 route.
            Не внедряет migration/adoption.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target_dir",
        help="Целевая директория consumer repo (будет создана при необходимости).",
    )
    parser.add_argument(
        "--source-repo",
        help="Путь к central source repo (ai-workflow-core или локальный клон). "
             "По умолчанию: корень текущего repo (ai-workflow-core).",
    )
    parser.add_argument(
        "--project-name",
        help="Человеко-читаемое имя проекта. По умолчанию: имя target_dir.",
    )
    parser.add_argument(
        "--bootstrap-mode",
        choices=["local-only", "github-aware"],
        default="local-only",
        help="Режим bootstrap: local-only (по умолчанию) или github-aware.",
    )
    parser.add_argument(
        "--source-revision",
        default="main",
        help="Ревизия central source (branch/tag/commit). По умолчанию: main.",
    )
    parser.add_argument(
        "--source-url",
        default="https://github.com/AndrewVerhoturov1/ai-workflow-core",
        help="URL central source repo.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать план действий, не выполнять запись.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписывать существующие managed файлы. "
             "Project-specific файлы НЕ перезаписываются даже с --force.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Пропустить verification после bootstrap.",
    )
    parser.add_argument(
        "--skip-preflight-check",
        action="store_true",
        help="Пропустить preflight и применить bootstrap даже при конфликтах. "
             "Только для clean/empty target или явно approved случаев.",
    )
    return parser


def _is_core_layout(path: Path) -> bool:
    """Check if path looks like a central core repo (has rules/ directory)."""
    return (path / "rules").is_dir()


def bootstrap(args: argparse.Namespace) -> int:
    target = Path(args.target_dir).expanduser().resolve()
    explicit_source = args.source_repo is not None
    source_root = Path(args.source_repo).expanduser().resolve() if explicit_source else _repo_root()

    if not source_root.exists():
        print(f"ОШИБКА: source repo не существует: {source_root}", file=sys.stderr)
        return 1

    # Guard: if running from a consumer-local copy without explicit --source-repo,
    # the default _repo_root() points to the consumer repo which lacks core layout.
    if not explicit_source and not _is_core_layout(source_root):
        print(
            "ОШИБКА: этот скрипт запущен из consumer repo, а не из central core.",
            file=sys.stderr,
        )
        print(
            f"  Текущий repo ({source_root}) не содержит core layout (rules/, prompts/, bootstrap/).",
            file=sys.stderr,
        )
        print(
            "  Укажите явный путь к central core через --source-repo:",
            file=sys.stderr,
        )
        print(
            "    python scripts/bootstrap_workflow.py <target_dir> --source-repo <путь-к-ai-workflow-core>",
            file=sys.stderr,
        )
        print(
            "  Либо запустите скрипт непосредственно из central core (ai-workflow-core).",
            file=sys.stderr,
        )
        return 1

    project_name = args.project_name or target.name
    bootstrap_mode = args.bootstrap_mode
    run_id = _get_run_id()
    all_actions: list[str] = []

    # ---- Phase 0: Preflight ----
    preflight = _preflight(target)
    _print_preflight(preflight)

    if not args.skip_preflight_check:
        if preflight["target_class"] not in ("empty_directory", "new_directory"):
            reasons: list[str] = []
            if preflight["is_git_repo"]:
                reasons.append("содержит git-репозиторий")
            if preflight["has_agents_md"]:
                reasons.append("содержит AGENTS.md")
            if preflight["has_dot_ai"]:
                reasons.append("содержит .ai/")
            if preflight["existing_project_files"]:
                reasons.append(f"содержит project-файлы: {', '.join(preflight['existing_project_files'])}")
            if preflight["existing_managed_files"]:
                reasons.append(f"содержит managed-файлы: {', '.join(preflight['existing_managed_files'])}")
            if not preflight["is_empty"] and not reasons:
                try:
                    sample = [p.name for p in sorted(Path(preflight["target"]).iterdir())[:8]]
                    reasons.append(f"содержит посторонние файлы/папки: {', '.join(sample)}")
                except Exception:
                    reasons.append("не пуста")
            print(
                "БЛОКИРОВКА: clean bootstrap требует пустую целевую директорию.",
                file=sys.stderr,
            )
            print(f"  Причина: {target}", file=sys.stderr)
            for reason in reasons:
                print(f"    - {reason}", file=sys.stderr)
            print(
                "  Для clean bootstrap укажите пустую папку или используйте --skip-preflight-check",
                file=sys.stderr,
            )
            print(
                "  Для существующего проекта: используйте safe_sync_workflow.py (P2-P3).",
                file=sys.stderr,
            )
            return 1

    # ---- Phase 1: Materialize core managed copies ----
    if not args.dry_run:
        print("--- Phase 1: Materialize core managed copies ---")
    managed_actions = _materialize_managed_copies(
        source_root, target,
        overwrite=args.force,
        dry_run=args.dry_run,
    )
    all_actions.extend(managed_actions)

    # ---- Phase 2: Instantiate project files ----
    if not args.dry_run:
        print("--- Phase 2: Instantiate project files ---")
    template_values = {
        "project_name": project_name,
        "project_type": "не указан",
        "primary_language": "русский",
        "test_commands": "не заданы",
        "build_commands": "не заданы",
        "high_risk_areas": "уточнить для проекта",
        "project_rules": "уточнить для проекта",
        "github_repo": "{{GITHUB_REPO}}",
        "github_branch": "main",
        "static_manual_version": "{{STATIC_MANUAL_VERSION}}",
        "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "bootstrap_mode": bootstrap_mode,
    }
    template_actions = _instantiate_project_files(
        source_root, target, template_values,
        dry_run=args.dry_run,
    )
    all_actions.extend(template_actions)

    # ---- Phase 3: Create runtime dirs ----
    if not args.dry_run:
        print("--- Phase 3: Create runtime directories ---")
    runtime_actions = _create_runtime_dirs(target, dry_run=args.dry_run)
    all_actions.extend(runtime_actions)

    # ---- Phase 4: Write bootstrap metadata ----
    if not args.dry_run:
        print("--- Phase 4: Write bootstrap metadata ---")
    sync_state_action = _write_core_sync_state(
        target, source_root,
        project_name=project_name,
        bootstrap_mode=bootstrap_mode,
        source_revision=args.source_revision,
        source_url=args.source_url,
        dry_run=args.dry_run,
    )
    all_actions.append(sync_state_action)

    # ---- Verification (before report to capture results) ----
    verification_results: list[dict] = []
    if not args.no_verify and not args.dry_run:
        print("--- Verification: script --help checks ---")
        script_checks = [
            "scripts/validate_kilo_contract.py",
            "scripts/validate_session_contract.py",
            "scripts/validate_external_chat_package.py",
            "scripts/external_chat_publish.py",
        ]
        for rel_script in script_checks:
            result = _run_script_help(target, rel_script)
            verification_results.append(result)
            status = "✓" if result["ok"] else "✗"
            print(f"  {status} {rel_script} (rc={result['returncode']})")

    # ---- Bootstrap report ----
    report_action = _write_bootstrap_report(
        target,
        run_id=run_id,
        project_name=project_name,
        preflight=preflight,
        all_actions=all_actions,
        verification_results=verification_results,
        dry_run=args.dry_run,
    )
    all_actions.append(report_action)

    # ---- Actions JSONL ----
    jsonl_action = _write_actions_jsonl(
        target, run_id, all_actions,
        dry_run=args.dry_run,
    )
    all_actions.append(jsonl_action)

    # ---- Summary ----
    print()
    print("=" * 60)
    print(f"BOOTSTRAP {'DRY-RUN' if args.dry_run else 'COMPLETE'} — {project_name}")
    print("=" * 60)
    print(f"  Run ID:        {run_id}")
    print(f"  Режим:         {'dry-run' if args.dry_run else 'apply'}")
    print(f"  Цель:          {target}")
    print(f"  Источник:      {source_root}")
    print(f"  Bootstrap:     {bootstrap_mode}")

    copied = sum(1 for a in all_actions if a.startswith("copy") or a.startswith("would-copy"))
    created = sum(1 for a in all_actions if a.startswith("create") or a.startswith("would-create"))
    skipped = sum(1 for a in all_actions if a.startswith("skip"))
    dirs = sum(1 for a in all_actions if "mkdir" in a)
    print(f"  Действий:      {len(all_actions)} (copy: {copied}, create: {created}, skip: {skipped}, dirs: {dirs})")

    if not args.dry_run:
        # Git status if available
        status_lines = _git_status(target)
        if status_lines:
            print(f"\n  Git status ({target}):")
            for line in status_lines[:20]:
                print(f"    {line}")
            if len(status_lines) > 20:
                print(f"    ... и ещё {len(status_lines) - 20} файлов")
        else:
            print(f"\n  Git status: не применимо (нет git repo или нет изменений)")

    print()
    if args.dry_run:
        print("Dry-run завершён. Для реального bootstrap запустите без --dry-run.")
    else:
        print("Bootstrap завершён.")
        print(f"Отчёт: {target / BOOTSTRAP_RUNS_DIR / run_id / 'bootstrap_report.md'}")
        print()
        print("Следующие шаги (manual):")
        print("  1. Проверить содержимое целевой директории.")
        print("  2. Адаптировать AGENTS.md под проект.")
        print("  3. Заполнить project-specific .md файлы.")
        print("  4. Настроить Kilo UI modes вручную.")
        print("  5. При необходимости подключить GitHub и external route.")
        print("  6. Выполнить workflow checkpoint commit.")

    return 0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(bootstrap(args))


if __name__ == "__main__":
    main()

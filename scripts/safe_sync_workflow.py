#!/usr/bin/env python3
"""
P2: Metadata-Aware Safe Sync — dry-run (P2.1) + apply (P2.2 + P2.3).
P3.1: Conservative Adoption Assessment — assessment-only для pre-P1 repos.
P3.2: Metadata-Only Backfill Execution — controlled backfill из candidate plan.
P3.3: Absent Candidate Restore — восстановление только missing managed files.
P3.4: Local Variant Review Paths — human-reviewed review для local_variant / divergent local managed files.
P3.5: Local Variant Decision Execution — human-approved decision для local_variant cases.
P3.6: Local Variant Resolution Pack — единый resolution для keep/defer/adopt local_variant cases.

P2.1 (dry-run, по умолчанию):
  Читает P1 bootstrap metadata из consumer repo, переиспользует canonical map
  из bootstrap_workflow.py, считает local/central checksums,
  классифицирует managed-copy state и пишет report-only artifacts.
  Не меняет managed files.

P2.2 (apply, флаг --apply):
  Использует тот же classifier, обновляет только файлы со статусом
  stale_central_available, пропускает protected/edited/missing/out-of-scope,
  пересчитывает checksums, обновляет P1 metadata baseline,
  пишет apply report и machine-readable apply artifact.
  Не делает merge/sidecar.

P2.3 (apply, флаг --apply):
  Выполняется вместе с P2.2. Добавляет safe review paths:
  - safe restore для local_missing (managed copy, P1 baseline, central доступен);
  - sidecar artifacts для local_edited и protected_agents (без overwrite);
  - blocked/manual-review для central_missing и metadata_missing.
  Не делает auto-merge, force-overwrite или migration.

P3.1 (assessment-only, флаг --assess-adoption):
  Выполняет inventory + classification candidate managed paths для consumer repo
  БЕЗ P1 baseline metadata. Классифицирует adoption/backfill readiness.
  Пишет только report artifacts. НЕ меняет managed files.
  НЕ пишет P1 metadata. НЕ выполняет migration.
  Результат: human-readable report + machine-readable JSON + optional
  candidate_backfill_plan (non-executable).

P3.2 (metadata-only backfill, флаг --backfill-metadata):
  Принимает candidate_backfill_plan.json от P3.1, валидирует контракт,
  перепроверяет local-vs-central equality, отбирает только unmanaged_clean_match
  кандидатов, пишет metadata baseline state.
  НЕ меняет content managed files.
  НЕ восстанавливает absent_candidate.
  НЕ auto-merge-ит local variants.
  Результат: metadata baseline + human-readable backfill report +
  machine-readable backfill results JSON.

P3.3 (absent restore, флаг --restore-absent):
   Принимает adoption assessment (или dedicated restore plan),
   валидирует narrow restore contract, отбирает только absent_candidate
   с exists_central=True, materialize-ит missing local file из central source,
   обновляет metadata baseline/state.
   НЕ overwrite-ит существующие локальные файлы.
   НЕ auto-merge-ит local variants.
   НЕ трогает protected/project-specific/runtime-history paths.
   Результат: human-readable restore report + machine-readable
   absent_restore_results.json.

P3.4 (local variant review, флаг --review-local-variant):
   Принимает adoption assessment из P3.1, валидирует provenance/shape,
   отбирает только unmanaged_local_variant items с exists_local=True
   и exists_central=True.
   Для каждого item собирает review data: local/central checksums,
   reason codes, compare status.
   Сохраняет central sidecar/snapshot только внутри run-artifacts.
   НЕ overwrite-ит существующие локальные файлы.
   НЕ auto-merge-ит local variants.
   НЕ записывает metadata baseline (конфликт не решён).
   НЕ трогает protected/project-specific/runtime-history paths.
   Результат: human-readable local variant review report + machine-readable
   local_variant_review.json + optional sidecar snapshots.

P3.5 (local variant decision execution, флаг --execute-local-variant-decision):
   Принимает P3.4 local_variant_review.json и отдельный human-approved decision plan.
   Валидирует provenance/shape обоих артефактов.
   Допускает только decision type keep_local_as_adapted и defer_manual_resolution.
   Перепроверяет, что local и central checksums не изменились с момента P3.4 review.
   При успехе: записывает metadata/state о том, что локальный файл оставлен как
   adapted/project-owned.
   НЕ overwrite-ит существующие локальные файлы.
   НЕ auto-merge-ит local variants.
   НЕ применяет central content.
   Результат: human-readable decision execution report + machine-readable
   local_variant_decision_execution.json.

P3.6 (local variant resolution pack, флаг --execute-local-variant-resolution):
   Принимает P3.4 local_variant_review.json и human-approved P3.6 resolution plan.
   Валидирует provenance/shape обоих артефактов.
   Допускает три decision type:
   - keep_local_as_adapted (оставить локальный файл как adapted)
   - defer_manual_resolution (отложить решение)
   - adopt_central_with_overwrite_explicit (перезаписать локальный файл central
     контентом — ТОЛЬКО для явно выбранных путей, ТОЛЬКО после повторной проверки
     provenance/checksums)
   После overwrite: пересчитывает local checksum, обновляет metadata/state так,
   чтобы путь перешёл из adapted/local-authority в central-managed.
   НЕ auto-merge-ит local variants.
   НЕ делает массовый overwrite.
   НЕ трогает protected/project-specific/runtime-history paths.
   Результат: human-readable resolution execution report + machine-readable
   local_variant_resolution_execution.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path so we can import scripts.* modules
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Reuse managed-copy definitions from bootstrap_workflow.py (P1)
# ---------------------------------------------------------------------------

from scripts.bootstrap_workflow import MANAGED_COPY_FILES, MANAGED_COPY_DIRS, CORE_MANAGED_MAP

# AGENTS.md: seed-copied, then becomes local-adapted (NOT managed after adaptation)
AGENTS_SEED = "AGENTS.md"

P1_METADATA_PATH = ".ai/bootstrap/state/core_sync_state.yml"

# Reverse lookup: consumer_path → core_path (for central source file location)
_CONSUMER_TO_CORE: dict[str, str] = {v: k for k, v in CORE_MANAGED_MAP.items()}

# ---------------------------------------------------------------------------
# Out-of-scope classification rules
# ---------------------------------------------------------------------------

PROJECT_SPECIFIC_FILES: list[str] = [
    ".ai/project_brief.md",
    ".ai/architecture.md",
    ".ai/decisions.md",
    ".ai/project_state.md",
    ".ai/backlog/current_sprint.md",
    ".ai/external_chats/publisher_config.json",
]

RUNTIME_HISTORY_DIRS: list[str] = [
    ".ai/handoffs",
    ".ai/reports",
    ".ai/reviews",
    ".ai/plans/sessions",
    ".ai/plans/chunks",
    ".ai/plans/master",
    ".ai/model_tests",
    ".ai/external_chats/tasks",
    ".ai/external_chats/requests",
    ".ai/external_chats/responses",
    ".ai/external_chats/recorder_packages",
    ".ai/external_chats/reviews",
    ".ai/external_chats/notebook",
    ".ai/external_chats/notebook_sources",
    ".ai/external_chats/notebook_packages",
    ".ai/sync",
]

RUNTIME_HISTORY_FILES: list[str] = [
    ".ai/external_chats/V1_navigation.md",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_checksum(path: Path) -> str:
    """SHA-256 hex digest of file content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_p1_metadata(yaml_text: str) -> dict[str, str]:
    """Parse P1 core_sync_state.yml into a flat dict.

    P1 writes nested YAML structure:
      canonical_source:
        repo: ...
        url: ...
        revision: ...
      materialized_from:
        path: ...
        repo: ...

    Returns flat keys (canonical_source_repo, etc.) + _managed_entries list.
    """
    result: dict = {
        "canonical_source_repo": "",
        "canonical_source_url": "",
        "canonical_source_revision": "",
        "materialized_from_path": "",
        "materialized_from_repo": "",
        "sync_direction": "",
        "bootstrap_package": "",
        "bootstrap_mode": "",
        "project_name": "",
        "schema_version": "",
        "created_at": "",
        "last_sync_at": "",
    }
    managed_entries: list[dict] = []
    current_entry: Optional[dict] = None

    # Simple top-level keys — detect by (no leading spaces, colon, value)
    SIMPLE_KEYS = {
        "schema_version": "schema_version",
        "sync_direction": "sync_direction",
        "bootstrap_package": "bootstrap_package",
        "bootstrap_mode": "bootstrap_mode",
        "project_name": "project_name",
        "created_at": "created_at",
        "last_sync_at": "last_sync_at",
    }

    lines = yaml_text.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].rstrip()
        i += 1

        if not stripped or stripped.startswith("#"):
            continue

        # Top-level simple keys
        for yaml_key, result_key in SIMPLE_KEYS.items():
            prefix = f"{yaml_key}: "
            if stripped.startswith(prefix) and not stripped.startswith(" "):
                result[result_key] = stripped[len(prefix):].strip().strip('"')
                break

        # Nested: canonical_source:
        if stripped == "canonical_source:" and not stripped.startswith(" "):
            while i < len(lines):
                sub = lines[i].rstrip()
                i += 1
                if sub.startswith("  repo: "):
                    result["canonical_source_repo"] = sub[len("  repo: "):].strip().strip('"')
                elif sub.startswith("  url: "):
                    result["canonical_source_url"] = sub[len("  url: "):].strip().strip('"')
                elif sub.startswith("  revision: "):
                    result["canonical_source_revision"] = sub[len("  revision: "):].strip().strip('"')
                elif sub and not sub.startswith("  "):
                    i -= 1  # unread this line
                    break
                elif not sub:
                    continue
                else:
                    break

        # Nested: materialized_from:
        if stripped == "materialized_from:" and not stripped.startswith(" "):
            while i < len(lines):
                sub = lines[i].rstrip()
                i += 1
                if sub.startswith("  path: "):
                    result["materialized_from_path"] = sub[len("  path: "):].strip().strip('"')
                elif sub.startswith("  repo: "):
                    result["materialized_from_repo"] = sub[len("  repo: "):].strip().strip('"')
                elif sub and not sub.startswith("  "):
                    i -= 1
                    break
                elif not sub:
                    continue
                else:
                    break

        # managed_files list entries
        if stripped.startswith("  - source: "):
            current_entry = {"source": stripped[len("  - source: "):].strip().strip('"')}
        elif stripped.startswith("    destination: ") and current_entry is not None:
            current_entry["destination"] = stripped[len("    destination: "):].strip().strip('"')
        elif stripped.startswith("    placement: ") and current_entry is not None:
            current_entry["placement"] = stripped[len("    placement: "):].strip().strip('"')
        elif stripped.startswith("    local_edit_policy: ") and current_entry is not None:
            current_entry["local_edit_policy"] = stripped[len("    local_edit_policy: "):].strip().strip('"')
        elif stripped.startswith("    checksum: ") and current_entry is not None:
            current_entry["checksum"] = stripped[len("    checksum: "):].strip().strip('"')
            managed_entries.append(current_entry)
            current_entry = None

    result["_managed_entries"] = managed_entries  # type: ignore
    return result


def _build_managed_inventory(target: Path, source_root: Path) -> list[dict]:
    """Build full managed file inventory from core source repo tree.

    Uses core→consumer mapping (CORE_MANAGED_MAP) to locate central files
    in core layout (rules/, prompts/, templates/, bootstrap/portable/)
    while checking local existence at consumer layout paths (.ai/rules/, ...).
    """
    inventory: list[dict] = []

    # Consumer→core reverse dir mapping for directory trees
    _CONSUMER_DIR_TO_CORE: dict[str, str] = {
        v: k for k, v in {
            "rules": ".ai/rules",
            "prompts": ".ai/prompts",
            "templates": ".ai/templates",
            "bootstrap/portable": ".ai/bootstrap/portable",
        }.items()
    }

    # Individual managed files — use reverse lookup for core paths
    for consumer_rel in MANAGED_COPY_FILES:
        core_rel = _CONSUMER_TO_CORE.get(consumer_rel, consumer_rel)
        dst = target / consumer_rel
        src = source_root / core_rel
        inventory.append({
            "local_path": consumer_rel,
            "central_path": core_rel,
            "exists_local": dst.is_file(),
            "exists_central": src.is_file(),
            "category": "managed_copy_file",
            "local_edit_policy": "do-not-edit",
        })

    # Managed directory trees — discover from core source, map to consumer
    for consumer_dir in MANAGED_COPY_DIRS:
        core_dir = _CONSUMER_DIR_TO_CORE.get(consumer_dir, consumer_dir)
        src_dir = source_root / core_dir
        if not src_dir.is_dir():
            continue
        for item in sorted(src_dir.rglob("*")):
            if item.is_dir():
                continue
            rel_item = item.relative_to(src_dir)
            core_full = f"{core_dir}/{rel_item.as_posix()}"
            consumer_full = f"{consumer_dir}/{rel_item.as_posix()}"
            dst = target / consumer_full
            src = source_root / core_full
            inventory.append({
                "local_path": consumer_full,
                "central_path": core_full,
                "exists_local": dst.is_file(),
                "exists_central": src.is_file(),
                "category": "managed_copy_dir",
                "local_edit_policy": "do-not-edit",
            })

    return inventory


def _classify_file(
    entry: dict,
    target: Path,
    source_root: Path,
    p1_metadata: dict,
    p1_managed_map: dict[str, str],
) -> dict:
    """Classify a single managed file entry. Returns classification dict."""
    local_path = entry["local_path"]
    central_path = entry["central_path"]
    local_file = target / local_path
    central_file = source_root / central_path

    classification = {
        "local_path": local_path,
        "central_path": central_path,
        "exists_local": local_file.is_file(),
        "exists_central": central_file.is_file(),
        "status": "unknown_unmanaged",
        "local_checksum": None,
        "central_checksum": None,
        "p1_checksum": None,
        "local_edit_policy": entry.get("local_edit_policy", "do-not-edit"),
        "would_update": False,
        "detail": "",
    }

    # Compute checksums
    if classification["exists_local"]:
        classification["local_checksum"] = _compute_checksum(local_file)
    if classification["exists_central"]:
        classification["central_checksum"] = _compute_checksum(central_file)

    # P1 checksum from metadata
    p1_checksum = p1_managed_map.get(local_path)
    if p1_checksum:
        classification["p1_checksum"] = p1_checksum

    # Classification logic
    if not classification["exists_local"]:
        if classification["exists_central"]:
            classification["status"] = "local_missing"
            classification["detail"] = "Файл отсутствует локально, но есть в central source."
        else:
            classification["status"] = "central_missing"
            classification["detail"] = "Файл отсутствует и локально, и в central source."
    elif not classification["exists_central"]:
        classification["status"] = "central_missing"
        classification["detail"] = "Файл есть локально, но отсутствует в central source."
    elif p1_checksum is None:
        # No P1 metadata for this file
        classification["status"] = "metadata_missing"
        classification["detail"] = "Отсутствует P1 metadata для этого файла."
    else:
        local_eq_p1 = classification["local_checksum"] == p1_checksum
        local_eq_central = classification["local_checksum"] == classification["central_checksum"]

        if local_eq_p1 and local_eq_central:
            classification["status"] = "clean"
            classification["detail"] = "Локальный файл совпадает с P1 materialized и с current central."
        elif local_eq_p1 and not local_eq_central:
            classification["status"] = "stale_central_available"
            classification["detail"] = "Локальный файл совпадает с P1 materialized, но central изменился. Central update доступен."
            classification["would_update"] = True
        elif not local_eq_p1 and local_eq_central:
            classification["status"] = "clean"
            classification["detail"] = "Локальный файл отличается от P1 materialized, но совпадает с current central (возможно, уже обновлён вручную)."
        else:
            classification["status"] = "local_edited"
            classification["detail"] = "Локальный файл отличается и от P1 materialized, и от current central."

    return classification


def _classify_protected_and_oos(target: Path) -> list[dict]:
    """Build classification entries for protected and out-of-scope paths."""
    items: list[dict] = []

    # AGENTS.md — protected
    agents = target / AGENTS_SEED
    items.append({
        "local_path": AGENTS_SEED,
        "central_path": AGENTS_SEED,
        "exists_local": agents.is_file(),
        "exists_central": True,
        "status": "protected_agents",
        "local_checksum": _compute_checksum(agents) if agents.is_file() else None,
        "central_checksum": None,
        "p1_checksum": None,
        "local_edit_policy": "sidecar-only",
        "would_update": False,
        "detail": "AGENTS.md: seed-copy после локальной адаптации. Никогда не auto-overwrite. Central update — через sidecar.",
    })

    # Project-specific files
    for rel in PROJECT_SPECIFIC_FILES:
        f = target / rel
        items.append({
            "local_path": rel,
            "central_path": "",
            "exists_local": f.is_file(),
            "exists_central": False,
            "status": "out_of_scope_project_specific",
            "local_checksum": _compute_checksum(f) if f.is_file() else None,
            "central_checksum": None,
            "p1_checksum": None,
            "local_edit_policy": "never-overwrite",
            "would_update": False,
            "detail": "Project-specific файл. Не managed copy. Никогда не overwrite через central sync.",
        })

    # Runtime/history files
    for rel in RUNTIME_HISTORY_FILES:
        f = target / rel
        if f.is_file():
            items.append({
                "local_path": rel,
                "central_path": "",
                "exists_local": True,
                "exists_central": False,
                "status": "out_of_scope_runtime_history",
                "local_checksum": _compute_checksum(f),
                "central_checksum": None,
                "p1_checksum": None,
                "local_edit_policy": "never-touch",
                "would_update": False,
                "detail": "Runtime/history артефакт. Не managed copy. Никогда не трогать через central sync.",
            })

    # Runtime/history dirs — note existence
    for rel in RUNTIME_HISTORY_DIRS:
        d = target / rel
        if d.is_dir():
            file_count = sum(1 for _ in d.rglob("*") if _.is_file())
            items.append({
                "local_path": f"{rel}/ (директория, {file_count} файлов)",
                "central_path": "",
                "exists_local": True,
                "exists_central": False,
                "status": "out_of_scope_runtime_history",
                "local_checksum": None,
                "central_checksum": None,
                "p1_checksum": None,
                "local_edit_policy": "never-touch",
                "would_update": False,
                "detail": "Runtime/history директория. Содержимое не managed copy. Никогда не трогать.",
            })

    return items


def _run_dry_run(target: Path, source_root: Path) -> dict:
    """Execute full report-only sync dry-run. Returns result dict."""
    run_id = _get_run_id()
    result: dict = {
        "run_id": run_id,
        "mode": "dry_run",
        "outcome": "report_only",
        "target": str(target),
        "source": str(source_root),
        "p1_metadata_found": False,
        "p1_metadata_summary": {},
        "summary": {
            "managed_scanned": 0,
            "clean": 0,
            "stale_central_available": 0,
            "local_edited": 0,
            "local_missing": 0,
            "central_missing": 0,
            "protected_agents": 0,
            "out_of_scope_project_specific": 0,
            "out_of_scope_runtime_history": 0,
            "metadata_missing": 0,
            "unknown_unmanaged": 0,
            "would_update_count": 0,
        },
        "files": [],
        "errors": [],
    }

    # --- Read P1 metadata ---
    p1_path = target / P1_METADATA_PATH
    p1_raw: dict = {}
    p1_managed_map: dict[str, str] = {}
    if p1_path.is_file():
        try:
            yaml_text = p1_path.read_text(encoding="utf-8")
            p1_raw = _parse_p1_metadata(yaml_text)
            result["p1_metadata_found"] = True
            result["p1_metadata_summary"] = {
                "canonical_source_repo": p1_raw.get("canonical_source_repo", ""),
                "canonical_source_url": p1_raw.get("canonical_source_url", ""),
                "canonical_source_revision": p1_raw.get("canonical_source_revision", ""),
                "materialized_from_path": p1_raw.get("materialized_from_path", ""),
                "materialized_from_repo": p1_raw.get("materialized_from_repo", ""),
                "bootstrap_mode": p1_raw.get("bootstrap_mode", ""),
                "project_name": p1_raw.get("project_name", ""),
                "created_at": p1_raw.get("created_at", ""),
                "last_sync_at": p1_raw.get("last_sync_at", ""),
            }
            managed_entries = p1_raw.get("_managed_entries", [])
            for me in managed_entries:
                if isinstance(me, dict):
                    src = me.get("source", me.get("destination", ""))
                    cs = me.get("checksum", "")
                    if src and cs:
                        p1_managed_map[src] = cs
        except Exception as e:
            result["errors"].append(f"Ошибка чтения P1 metadata: {e}")

    # --- Build managed inventory ---
    managed_inventory = _build_managed_inventory(target, source_root)
    result["summary"]["managed_scanned"] = len(managed_inventory)

    # --- Classify managed files ---
    for entry in managed_inventory:
        classification = _classify_file(entry, target, source_root, p1_raw, p1_managed_map)
        result["files"].append(classification)

        # Update summary counts
        status = classification["status"]
        if status in result["summary"]:
            result["summary"][status] += 1
        if classification.get("would_update"):
            result["summary"]["would_update_count"] += 1

    # --- Classify protected and out-of-scope ---
    protected_items = _classify_protected_and_oos(target)
    for item in protected_items:
        result["files"].append(item)
        status = item["status"]
        if status in result["summary"]:
            result["summary"][status] += 1

    return result


def _write_report(result: dict, target: Path) -> str:
    """Write human-readable sync_dry_run_report.md. Return report path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sync_dry_run_report.md"

    summary = result["summary"]
    p1 = result["p1_metadata_summary"]

    lines = [
        "# Safe Sync Dry-Run Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (report-only, без изменения managed files)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **P1 metadata найден:** {'да' if result['p1_metadata_found'] else 'нет'}",
        "",
    ]

    if result["errors"]:
        lines.append("## Ошибки")
        lines.append("")
        for e in result["errors"]:
            lines.append(f"- ⚠ {e}")
        lines.append("")

    # P1 metadata section
    if result["p1_metadata_found"]:
        lines.append("## P1 Bootstrap Metadata")
        lines.append("")
        lines.append(f"- **Canonical source repo:** `{p1.get('canonical_source_repo', '')}`")
        lines.append(f"- **Canonical source URL:** `{p1.get('canonical_source_url', '')}`")
        lines.append(f"- **Canonical source revision:** `{p1.get('canonical_source_revision', '')}`")
        lines.append(f"- **Materialized from path:** `{p1.get('materialized_from_path', '')}`")
        lines.append(f"- **Materialized from repo:** `{p1.get('materialized_from_repo', '')}`")
        lines.append(f"- **Bootstrap mode:** `{p1.get('bootstrap_mode', '')}`")
        lines.append(f"- **Project name:** `{p1.get('project_name', '')}`")
        lines.append(f"- **Created at:** `{p1.get('created_at', '')}`")
        lines.append(f"- **Last sync at:** `{p1.get('last_sync_at', '')}`")
        lines.append("")
    else:
        lines.append("## P1 Bootstrap Metadata")
        lines.append("")
        lines.append("⚠ **P1 metadata не найден.** Файл `.ai/bootstrap/state/core_sync_state.yml` отсутствует или не читаем.")
        lines.append("Dry-run не может достоверно определить baseline для сравнения managed copies.")
        lines.append("")

    # Summary
    lines.append("## Сводка")
    lines.append("")
    lines.append(f"| Категория | Количество |")
    lines.append(f"| --- | --- |")
    lines.append(f"| Всего managed files отсканировано | {summary['managed_scanned']} |")
    lines.append(f"| Clean | {summary['clean']} |")
    lines.append(f"| Stale (central update available) | {summary['stale_central_available']} |")
    lines.append(f"| Local edited | {summary['local_edited']} |")
    lines.append(f"| Local missing | {summary['local_missing']} |")
    lines.append(f"| Central missing | {summary['central_missing']} |")
    lines.append(f"| Protected (AGENTS.md) | {summary['protected_agents']} |")
    lines.append(f"| Out-of-scope: project-specific | {summary['out_of_scope_project_specific']} |")
    lines.append(f"| Out-of-scope: runtime/history | {summary['out_of_scope_runtime_history']} |")
    lines.append(f"| Metadata missing | {summary['metadata_missing']} |")
    lines.append(f"| Unknown/unmanaged | {summary['unknown_unmanaged']} |")
    lines.append(f"| **Would update (если включить update mode)** | **{summary['would_update_count']}** |")
    lines.append("")

    # File classification table
    lines.append("## Классификация файлов")
    lines.append("")
    lines.append("| Local path | Status | Local checksum | Central checksum | P1 checksum | Would update | Detail |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for f in result["files"]:
        lc = f["local_checksum"][:12] + "..." if f["local_checksum"] else "—"
        cc = f["central_checksum"][:12] + "..." if f["central_checksum"] else "—"
        pc = f["p1_checksum"][:12] + "..." if f["p1_checksum"] else "—"
        wu = "✓" if f.get("would_update") else "—"
        detail = f["detail"][:80] + ("..." if len(f.get("detail", "")) > 80 else "")
        lines.append(f"| `{f['local_path']}` | `{f['status']}` | {lc} | {cc} | {pc} | {wu} | {detail} |")

    lines.append("")

    # Protected paths section
    lines.append("## Protected Paths")
    lines.append("")
    lines.append("- **AGENTS.md** — seed-copy после локальной адаптации. Никогда не auto-overwrite. Central update — только через sidecar + human review.")
    lines.append("- **Project overlays** — `.ai/project_brief.md`, `.ai/project_state.md`, `.ai/architecture.md`, `.ai/decisions.md`, `.ai/backlog/current_sprint.md` — никогда не overwrite через central sync.")
    lines.append("- **Runtime/history** — `.ai/handoffs/`, `.ai/reports/`, `.ai/reviews/`, `.ai/plans/sessions/`, `.ai/external_chats/**` — никогда не трогать.")
    lines.append("- **Publisher config** — `.ai/external_chats/publisher_config.json` — project-specific, не managed copy.")
    lines.append("")

    # Would update section
    would_update = [f for f in result["files"] if f.get("would_update") and f["status"] == "stale_central_available"]
    if would_update:
        lines.append("## Would Update (если включить update mode)")
        lines.append("")
        lines.append("| Local path | Central checksum | Local checksum |")
        lines.append("| --- | --- | --- |")
        for f in would_update:
            lc = f["local_checksum"][:12] + "..." if f["local_checksum"] else "—"
            cc = f["central_checksum"][:12] + "..." if f["central_checksum"] else "—"
            lines.append(f"| `{f['local_path']}` | {cc} | {lc} |")
        lines.append("")
        lines.append("⚠ **В этом chunk обновления НЕ выполняются.** Это только preview.")
        lines.append("")

    # Blockers
    blockers = [f for f in result["files"] if f["status"] in ("local_edited", "local_missing", "central_missing", "metadata_missing")]
    if blockers:
        lines.append("## Would Block / Requires Human Review")
        lines.append("")
        lines.append("| Local path | Status | Detail |")
        lines.append("| --- | --- | --- |")
        for f in blockers:
            lines.append(f"| `{f['local_path']}` | `{f['status']}` | {f['detail']} |")
        lines.append("")

    # Not in scope
    lines.append("## Что НЕ внедрено в этом chunk (P2.1)")
    lines.append("")
    lines.append("- **Real update managed files** — dry-run только читает и классифицирует.")
    lines.append("- **Auto-update для clean managed copies** — `would_update` показывает что обновилось бы, но обновлений нет.")
    lines.append("- **Sidecar merge flow** — для `local_edited` или `protected_agents`.")
    lines.append("- **Three-way merge** — при конфликтах central vs local.")
    lines.append("- **Commit/PR automation**.")
    lines.append("- **Migration/adoption для pre-P1 repos**.")
    lines.append("- **Metadata repair для corrupted P1 metadata**.")
    lines.append("")

    lines.append("## Verification")
    lines.append("")
    lines.append("- [ ] После dry-run checksums managed files не изменились.")
    lines.append("- [ ] Ни один managed file не был перезаписан.")
    lines.append("- [ ] AGENTS.md классифицирован как `protected_agents`.")
    lines.append("- [ ] Project-specific файлы вне scope.")
    lines.append("- [ ] Runtime/history директории вне scope.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P2.1), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_classification_json(result: dict, target: Path) -> str:
    """Write machine-readable classification.json. Return path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "classification.json"

    payload = {
        "run_id": result["run_id"],
        "mode": result["mode"],
        "outcome": result["outcome"],
        "target": result["target"],
        "source": result["source"],
        "p1_metadata_found": result["p1_metadata_found"],
        "summary": result["summary"],
        "files": result["files"],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def _write_inventory_json(result: dict, target: Path) -> str:
    """Write machine-readable inventory.json. Return path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "inventory.json"

    inventory = {
        "run_id": result["run_id"],
        "managed_copy_files": MANAGED_COPY_FILES,
        "managed_copy_dirs": MANAGED_COPY_DIRS,
        "protected": [AGENTS_SEED],
        "out_of_scope_project_specific": PROJECT_SPECIFIC_FILES,
        "out_of_scope_runtime_history_dirs": RUNTIME_HISTORY_DIRS,
        "out_of_scope_runtime_history_files": RUNTIME_HISTORY_FILES,
        "p1_metadata_path": P1_METADATA_PATH,
    }
    json_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


# ---------------------------------------------------------------------------
# P2.2: Apply mode — limited update for clean managed copies only
# ---------------------------------------------------------------------------

def _can_apply_file(classification: dict, target: Path) -> tuple[bool, str]:
    """Validate update allowlist for a single file. Returns (allowed, reason)."""
    local_path = classification["local_path"]
    status = classification["status"]

    # Only stale_central_available
    if status != "stale_central_available":
        return False, f"Статус {status}, не stale_central_available."

    # Must have local and central checksums
    if not classification["local_checksum"] or not classification["central_checksum"]:
        return False, "Отсутствует local или central checksum."

    # Local must match P1 baseline
    p1_cs = classification.get("p1_checksum")
    if not p1_cs:
        return False, "Отсутствует P1 baseline checksum."
    if classification["local_checksum"] != p1_cs:
        return False, f"Local checksum не совпадает с P1 baseline (файл мог быть локально изменён после классификации)."

    # Central must differ (otherwise nothing to update)
    if classification["local_checksum"] == classification["central_checksum"]:
        return False, "Local и central совпадают — нечего обновлять."

    # AGENTS.md — protected
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path."

    # Project-specific files
    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл."

    # Runtime/history files
    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл."

    # Runtime/history dirs
    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория."

    # Must actually exist locally
    local_file = target / local_path
    if not local_file.is_file():
        return False, "Файл отсутствует локально."

    return True, ""


def _can_restore_missing(
    classification: dict,
    target: Path,
    source_root: Path,
    p1_managed_map: dict[str, str],
) -> tuple[bool, str]:
    """Validate safe restore conditions for a local_missing file.

    Restore allowed only if ALL conditions are true:
    - file is a managed copy;
    - central file exists;
    - P1 metadata baseline exists for this path;
    - path is not AGENTS.md;
    - path is not project-specific;
    - path is not runtime/history.
    Returns (allowed, reason).
    """
    local_path = classification["local_path"]

    # Must be local_missing
    if classification["status"] != "local_missing":
        return False, f"Статус {classification['status']}, не local_missing."

    # Central must exist
    if not classification["exists_central"]:
        return False, "Central source file отсутствует."

    # P1 metadata baseline must exist
    if classification["local_path"] not in p1_managed_map:
        return False, "Отсутствует P1 metadata baseline для этого файла."

    # AGENTS.md — protected, never auto-restore
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path, не auto-restore."

    # Project-specific files — never restore
    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл."

    # Runtime/history files — never restore
    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл."

    # Runtime/history dirs — never restore
    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория."

    # Only managed copy files/dirs (from the known inventory)
    is_managed = False
    for mf in MANAGED_COPY_FILES:
        if local_path == mf:
            is_managed = True
            break
    if not is_managed:
        for md in MANAGED_COPY_DIRS:
            if local_path.startswith(md + "/"):
                is_managed = True
                break
    if not is_managed:
        return False, "Не managed copy."

    return True, ""


def _create_sidecar(
    local_path: str,
    central_file: Path,
    run_id: str,
    target: Path,
    reason: str,
) -> str:
    """Create a sidecar artifact with the current central version.

    Places the sidecar in .ai/sync/runs/<run_id>/sidecars/.
    The sidecar filename is derived from local_path with slashes replaced.
    Returns the sidecar path string.
    """
    sidecar_dir = target / ".ai" / "sync" / "runs" / run_id / "sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    # Derive sidecar filename: replace / with _ and add .sidecar extension
    safe_name = local_path.replace("/", "_").replace("\\", "_")
    sidecar_path = sidecar_dir / f"{safe_name}.sidecar.md"

    central_hash = _compute_checksum(central_file)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        f"# Sidecar: `{local_path}`",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Создан:** {now_iso}",
        f"- **Причина:** {reason}",
        f"- **Central checksum:** `{central_hash}`",
        "",
        "## Central Version Content",
        "",
        "```",
    ]
    try:
        content = central_file.read_text(encoding="utf-8")
        lines.append(content)
    except Exception:
        lines.append(f"(бинарный файл или ошибка чтения: {central_file})")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("*Sidecar создан `scripts/safe_sync_workflow.py` (P2.3). Локальный файл НЕ изменён.*")

    sidecar_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(sidecar_path)


def _perform_p2_3_actions(
    result: dict,
    target: Path,
    source_root: Path,
    p1_managed_map: dict[str, str],
) -> dict:
    """Perform P2.3 safe review actions for non-clean managed states.

    Handles:
    - local_missing → safe restore (if conditions met)
    - local_edited → sidecar (no local overwrite)
    - protected_agents → sidecar for AGENTS.md
    - central_missing → blocked/manual-review
    - metadata_missing → blocked/manual-review

    Returns p2_3_outcome dict.
    """
    run_id = result["run_id"]
    restored: list[dict] = []
    sidecars_created: list[dict] = []
    blocked_manual_review: list[dict] = []
    errors: list[dict] = []

    # Process local_missing
    missing_files = [f for f in result["files"]
                     if f.get("status") == "local_missing"]
    for classification in missing_files:
        local_path = classification["local_path"]
        central_file = source_root / classification["central_path"]
        local_file = target / local_path

        allowed, reason = _can_restore_missing(
            classification, target, source_root, p1_managed_map
        )

        if not allowed:
            blocked_manual_review.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": classification["status"],
                "category": "local_missing_blocked",
                "reason": reason,
                "detail": classification.get("detail", ""),
            })
            continue

        # Perform safe restore
        try:
            central_content = central_file.read_bytes()
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_bytes(central_content)
            new_checksum = _compute_checksum(local_file)

            restored.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "restored_missing",
                "central_checksum": classification["central_checksum"],
                "new_checksum": new_checksum,
                "detail": f"Файл восстановлен из central source.",
            })
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "restore_error",
                "error": str(e),
                "detail": f"Ошибка при восстановлении: {e}",
            })

    # Process local_edited
    edited_files = [f for f in result["files"]
                    if f.get("status") == "local_edited"]
    for classification in edited_files:
        local_path = classification["local_path"]
        central_file = source_root / classification["central_path"]

        if not classification["exists_central"] or not central_file.is_file():
            blocked_manual_review.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": classification["status"],
                "category": "local_edited_no_central",
                "reason": "Central source file отсутствует для sidecar.",
                "detail": classification.get("detail", ""),
            })
            continue

        try:
            sidecar_path = _create_sidecar(
                local_path, central_file, run_id, target,
                reason=f"local_edited: локальный файл изменён, central версия сохранена для review",
            )
            sidecars_created.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "sidecar_created_for_local_edited",
                "sidecar_path": sidecar_path,
                "local_checksum": classification["local_checksum"],
                "central_checksum": classification["central_checksum"],
                "detail": "Sidecar создан с current central версией. Локальный файл НЕ изменён. Требуется human review.",
            })
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "sidecar_error",
                "error": str(e),
                "detail": f"Ошибка при создании sidecar: {e}",
            })

    # Process protected_agents (AGENTS.md)
    protected_files = [f for f in result["files"]
                       if f.get("status") == "protected_agents"]
    for classification in protected_files:
        local_path = classification["local_path"]
        central_file = source_root / AGENTS_SEED

        if not central_file.is_file():
            blocked_manual_review.append({
                "local_path": local_path,
                "central_path": AGENTS_SEED,
                "status": classification["status"],
                "category": "protected_no_central",
                "reason": "Central AGENTS.md отсутствует для sidecar.",
                "detail": classification.get("detail", ""),
            })
            continue

        try:
            sidecar_path = _create_sidecar(
                local_path, central_file, run_id, target,
                reason=f"protected_agents: AGENTS.md защищён, central версия сохранена для review",
            )
            sidecars_created.append({
                "local_path": local_path,
                "central_path": AGENTS_SEED,
                "status": "sidecar_created_for_protected_agents",
                "sidecar_path": sidecar_path,
                "local_checksum": classification["local_checksum"],
                "central_checksum": _compute_checksum(central_file),
                "detail": "Sidecar создан с current central AGENTS.md. Локальный AGENTS.md НЕ изменён. Требуется human review.",
            })
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "central_path": AGENTS_SEED,
                "status": "sidecar_error",
                "error": str(e),
                "detail": f"Ошибка при создании sidecar для AGENTS.md: {e}",
            })

    # Process central_missing
    central_missing_files = [f for f in result["files"]
                             if f.get("status") == "central_missing"]
    for classification in central_missing_files:
        blocked_manual_review.append({
            "local_path": classification["local_path"],
            "central_path": classification.get("central_path", ""),
            "status": "central_missing",
            "category": "central_missing_blocked",
            "reason": "Central source file отсутствует. Ничего не восстанавливаем и не удаляем автоматически.",
            "detail": classification.get("detail", ""),
        })

    # Process metadata_missing
    metadata_missing_files = [f for f in result["files"]
                              if f.get("status") == "metadata_missing"]
    for classification in metadata_missing_files:
        blocked_manual_review.append({
            "local_path": classification["local_path"],
            "central_path": classification.get("central_path", ""),
            "status": "metadata_missing",
            "category": "metadata_missing_blocked",
            "reason": "Отсутствует P1 metadata baseline. Без baseline невозможно безопасно определить отношение local↔central.",
            "detail": classification.get("detail", ""),
        })

    return {
        "restored": restored,
        "sidecars_created": sidecars_created,
        "blocked_manual_review": blocked_manual_review,
        "errors": errors,
        "summary": {
            "restored_count": len(restored),
            "sidecars_created_count": len(sidecars_created),
            "blocked_manual_review_count": len(blocked_manual_review),
            "error_count": len(errors),
        },
    }


def _perform_apply_updates(
    result: dict,
    target: Path,
    source_root: Path,
    p1_metadata_path: Path,
) -> dict:
    """Perform limited apply: update stale_central_available files only.

    Returns apply_outcome dict with summary and per-file results.
    """
    updated: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []

    stale_files = [f for f in result["files"]
                   if f.get("status") == "stale_central_available"]

    for classification in stale_files:
        local_path = classification["local_path"]
        local_file = target / local_path
        central_file = source_root / classification["central_path"]

        allowed, reason = _can_apply_file(classification, target)

        if not allowed:
            blocked.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": classification["status"],
                "reason": reason,
                "local_checksum": classification["local_checksum"],
                "central_checksum": classification["central_checksum"],
                "p1_checksum": classification.get("p1_checksum"),
            })
            continue

        # Perform the actual file update
        try:
            old_checksum = classification["local_checksum"]
            central_content = central_file.read_bytes()
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_bytes(central_content)
            new_checksum = _compute_checksum(local_file)

            updated.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "updated",
                "old_checksum": old_checksum,
                "new_checksum": new_checksum,
                "central_checksum": classification["central_checksum"],
                "p1_checksum": classification.get("p1_checksum"),
                "detail": f"Файл обновлён из central source.",
            })
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "central_path": classification["central_path"],
                "status": "error",
                "error": str(e),
                "detail": f"Ошибка при обновлении: {e}",
            })

    # Also collect all files that are NOT stale_central_available and NOT handled by P2.3 as skipped
    P2_3_STATUSES = {
        "local_missing", "local_edited", "central_missing",
        "metadata_missing", "protected_agents",
    }
    for f in result["files"]:
        if f.get("status") != "stale_central_available" and f.get("status") not in (
            "out_of_scope_project_specific", "out_of_scope_runtime_history",
            "protected_agents", "unknown_unmanaged",
        ) and f.get("status") not in P2_3_STATUSES:
            skipped.append({
                "local_path": f["local_path"],
                "central_path": f.get("central_path", ""),
                "status": f["status"],
                "reason": f"Статус {f['status']} — вне scope apply.",
                "detail": f.get("detail", ""),
            })

    return {
        "updated": updated,
        "skipped": skipped,
        "blocked": blocked,
        "errors": errors,
        "summary": {
            "updated_count": len(updated),
            "skipped_count": len(skipped),
            "blocked_count": len(blocked),
            "error_count": len(errors),
        },
    }


def _update_p1_metadata_after_apply(
    p1_path: Path,
    updated_files: list[dict],
    run_id: str,
) -> bool:
    """Update P1 core_sync_state.yml checksums and last_sync_at after apply.

    Reads the existing YAML, updates checksums for files in updated_files,
    and writes back. Returns True on success.
    """
    if not p1_path.is_file():
        return False

    try:
        yaml_text = p1_path.read_text(encoding="utf-8")
    except Exception:
        return False

    # Build a map of path → new_checksum
    updates: dict[str, str] = {}
    for entry in updated_files:
        lp = entry["local_path"]
        nc = entry.get("new_checksum", "")
        if lp and nc:
            updates[lp] = nc

    if not updates:
        return True  # nothing to update

    # Rebuild YAML with updated checksums
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_lines: list[str] = []
    in_managed_section = False
    current_checksum_line = False

    for line in yaml_text.splitlines():
        stripped = line.rstrip()

        # Detect managed_files section
        if stripped == "managed_files:" and not stripped.startswith(" "):
            in_managed_section = True
            new_lines.append(line)
            continue

        if in_managed_section and stripped.startswith("adapted_files:"):
            in_managed_section = False

        # Track source line to match with checksum line
        if in_managed_section and stripped.startswith("  - source: "):
            current_source = stripped[len("  - source: "):].strip().strip('"')
            new_lines.append(line)
            continue

        if in_managed_section and stripped.startswith("    destination: "):
            current_dest = stripped[len("    destination: "):].strip().strip('"')
            new_lines.append(line)
            continue

        # Update checksum if this file was updated
        if in_managed_section and stripped.startswith("    checksum: "):
            path_key = current_dest if 'current_dest' in dir() else current_source if 'current_source' in dir() else ""
            # Determine the path to look up: prefer destination, fallback to source
            lookup_path = None
            # We need the actual path — try both source and destination
            for lp in updates:
                if lp == current_source or lp == current_dest:
                    lookup_path = lp
                    break
            if lookup_path and lookup_path in updates:
                indent = "    checksum: "
                new_lines.append(f"{indent}{updates[lookup_path]}")
            else:
                new_lines.append(line)
            continue

        # Update last_sync_at
        if stripped.startswith("last_sync_at: ") and not stripped.startswith(" "):
            new_lines.append(f"last_sync_at: {now_iso}")
            continue

        new_lines.append(line)

    try:
        p1_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def _write_apply_report(
    result: dict,
    apply_outcome: dict,
    target: Path,
    p1_updated: bool,
    p2_3_outcome: Optional[dict] = None,
) -> str:
    """Write human-readable sync_apply_report.md (P2.2+P2.3). Return report path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sync_apply_report.md"

    summary = apply_outcome["summary"]
    p1 = result["p1_metadata_summary"]

    lines = [
        "# Safe Sync Apply Report (P2.2 + P2.3)",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `apply` (P2.2: limited update stale_central_available + P2.3: safe review paths)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **P1 metadata найден:** {'да' if result['p1_metadata_found'] else 'нет'}",
        f"- **P1 metadata обновлён после apply:** {'да' if p1_updated else 'нет'}",
        "",
    ]

    # P1 metadata context
    if result["p1_metadata_found"]:
        lines.append("## P1 Bootstrap Metadata")
        lines.append("")
        lines.append(f"- **Canonical source repo:** `{p1.get('canonical_source_repo', '')}`")
        lines.append(f"- **Canonical source URL:** `{p1.get('canonical_source_url', '')}`")
        lines.append(f"- **Canonical source revision:** `{p1.get('canonical_source_revision', '')}`")
        lines.append(f"- **Materialized from path:** `{p1.get('materialized_from_path', '')}`")
        lines.append(f"- **Materialized from repo:** `{p1.get('materialized_from_repo', '')}`")
        lines.append(f"- **Bootstrap mode:** `{p1.get('bootstrap_mode', '')}`")
        lines.append(f"- **Project name:** `{p1.get('project_name', '')}`")
        lines.append(f"- **Last sync at:** `{p1.get('last_sync_at', '')}`")
        lines.append("")
    else:
        lines.append("## P1 Bootstrap Metadata")
        lines.append("")
        lines.append("⚠ **P1 metadata не найден.** Apply невозможен без baseline.")
        lines.append("")

    # Summary
    lines.append("## Сводка Apply (P2.2)")
    lines.append("")
    lines.append(f"| Категория | Количество |")
    lines.append(f"| --- | --- |")
    lines.append(f"| **Updated (P2.2)** | **{summary['updated_count']}** |")
    lines.append(f"| Blocked | {summary['blocked_count']} |")
    lines.append(f"| Skipped | {summary['skipped_count']} |")
    lines.append(f"| Errors | {summary['error_count']} |")
    lines.append(f"| Managed scanned (dry-run) | {result['summary']['managed_scanned']} |")
    lines.append(f"| Stale central available (dry-run) | {result['summary']['stale_central_available']} |")
    lines.append("")

    # P2.3 Summary
    if p2_3_outcome is not None:
        p23_summary = p2_3_outcome["summary"]
        lines.append("## Сводка Safe Review Paths (P2.3)")
        lines.append("")
        lines.append(f"| Категория | Количество |")
        lines.append(f"| --- | --- |")
        lines.append(f"| **Restored (local_missing)** | **{p23_summary['restored_count']}** |")
        lines.append(f"| **Sidecars created (local_edited + protected_agents)** | **{p23_summary['sidecars_created_count']}** |")
        lines.append(f"| Blocked / Manual review | {p23_summary['blocked_manual_review_count']} |")
        lines.append(f"| Errors | {p23_summary['error_count']} |")
        lines.append("")

    # Updated files
    if apply_outcome["updated"]:
        lines.append("## Обновлённые файлы (P2.2)")
        lines.append("")
        lines.append("| Local path | Old checksum | New checksum | Central checksum |")
        lines.append("| --- | --- | --- | --- |")
        for u in apply_outcome["updated"]:
            oc = u["old_checksum"][:12] + "..." if u.get("old_checksum") else "—"
            nc = u["new_checksum"][:12] + "..." if u.get("new_checksum") else "—"
            cc = u["central_checksum"][:12] + "..." if u.get("central_checksum") else "—"
            lines.append(f"| `{u['local_path']}` | {oc} | {nc} | {cc} |")
        lines.append("")

    # Restored files (P2.3)
    if p2_3_outcome is not None and p2_3_outcome["restored"]:
        lines.append("## Восстановленные файлы (P2.3: local_missing → restored)")
        lines.append("")
        lines.append("| Local path | Central checksum | New checksum | Detail |")
        lines.append("| --- | --- | --- | --- |")
        for r in p2_3_outcome["restored"]:
            cc = r["central_checksum"][:12] + "..." if r.get("central_checksum") else "—"
            nc = r["new_checksum"][:12] + "..." if r.get("new_checksum") else "—"
            lines.append(f"| `{r['local_path']}` | {cc} | {nc} | {r.get('detail', '')} |")
        lines.append("")

    # Sidecars created (P2.3)
    if p2_3_outcome is not None and p2_3_outcome["sidecars_created"]:
        lines.append("## Sidecar Artifacts (P2.3: local_edited + protected_agents)")
        lines.append("")
        lines.append("| Local path | Status | Sidecar path | Detail |")
        lines.append("| --- | --- | --- | --- |")
        for s in p2_3_outcome["sidecars_created"]:
            sp = s.get("sidecar_path", "—")
            lines.append(f"| `{s['local_path']}` | `{s['status']}` | `{sp}` | {s.get('detail', '')} |")
        lines.append("")
        lines.append("⚠ **Локальные файлы НЕ изменены.** Sidecar содержит current central версию для human review.")
        lines.append("")

    # Blocked / manual review (P2.3)
    if p2_3_outcome is not None and p2_3_outcome["blocked_manual_review"]:
        lines.append("## Blocked / Manual Review (P2.3)")
        lines.append("")
        lines.append("| Local path | Status | Category | Reason |")
        lines.append("| --- | --- | --- | --- |")
        for b in p2_3_outcome["blocked_manual_review"]:
            lines.append(f"| `{b['local_path']}` | `{b['status']}` | `{b.get('category', '')}` | {b.get('reason', '')} |")
        lines.append("")
        lines.append("⚠ Эти файлы требуют ручного решения. Никаких автоматических действий не выполнено.")
        lines.append("")

    # Blocked files (P2.2)
    if apply_outcome["blocked"]:
        lines.append("## Заблокировано (P2.2 — не обновлено)")
        lines.append("")
        lines.append("| Local path | Reason |")
        lines.append("| --- | --- |")
        for b in apply_outcome["blocked"]:
            lines.append(f"| `{b['local_path']}` | {b['reason']} |")
        lines.append("")

    # Errors (combined)
    all_errors = list(apply_outcome.get("errors", []))
    if p2_3_outcome is not None:
        all_errors.extend(p2_3_outcome.get("errors", []))
    if all_errors:
        lines.append("## Ошибки")
        lines.append("")
        for e in all_errors:
            lp = e.get("local_path", "N/A")
            err = e.get("error", str(e))
            lines.append(f"- ⚠ `{lp}`: {err}")
        lines.append("")

    # Protected paths
    lines.append("## Protected Paths (не тронуты)")
    lines.append("")
    lines.append("- **AGENTS.md** — seed-copy, protected. Central update — только через sidecar + human review.")
    lines.append("- **Project overlays** — `.ai/project_brief.md`, `.ai/project_state.md`, `.ai/architecture.md`, `.ai/decisions.md`, `.ai/backlog/current_sprint.md` — никогда не overwrite.")
    lines.append("- **Runtime/history** — `.ai/handoffs/`, `.ai/reports/`, `.ai/reviews/`, `.ai/plans/sessions/`, `.ai/external_chats/**` — никогда не трогать.")
    lines.append("")

    # Что внедрено в P2
    lines.append("## Что внедрено в P2 (P2.1 + P2.2 + P2.3)")
    lines.append("")
    lines.append("- ✅ **P2.1:** Dry-run: detect/compare/classify + report-only artifacts.")
    lines.append("- ✅ **P2.2:** Limited apply для `stale_central_available` (clean managed copies).")
    lines.append("- ✅ **P2.3:** Safe restore для `local_missing` (managed copy, есть P1 baseline, central доступен).")
    lines.append("- ✅ **P2.3:** Sidecar artifacts для `local_edited` (central версия для review, локальный файл не тронут).")
    lines.append("- ✅ **P2.3:** Sidecar artifacts для `protected_agents` (AGENTS.md central версия, локальный файл не тронут).")
    lines.append("- ✅ **P2.3:** Blocked/manual-review для `central_missing` и `metadata_missing`.")

    # Что сознательно оставлено на P3
    lines.append("")
    lines.append("## Что сознательно оставлено на P3 Migration")
    lines.append("")
    lines.append("- ❌ **Auto-merge `local_edited`** — только sidecar, не merge.")
    lines.append("- ❌ **Force mode** — перезапись без проверки baseline.")
    lines.append("- ❌ **Three-way merge** — при конфликтах central vs local.")
    lines.append("- ❌ **Auto-resolve `central_missing`** — ничего не удаляем и не восстанавливаем.")
    lines.append("- ❌ **Auto-resolve `metadata_missing`** — без P1 baseline безопасный sync невозможен.")
    lines.append("- ❌ **Commit/PR automation**.")
    lines.append("- ❌ **Migration/adoption для pre-P1 repos** (основная задача P3).")
    lines.append("")

    # Verification checklist
    lines.append("## Verification")
    lines.append("")
    lines.append("### P2.2")
    lines.append("")
    lines.append(f"- [ ] Файлов обновлено (P2.2): {summary['updated_count']}")
    lines.append(f"- [ ] Файлов заблокировано (P2.2): {summary['blocked_count']}")
    if p2_3_outcome is not None:
        p23s = p2_3_outcome["summary"]
        lines.append("")
        lines.append("### P2.3")
        lines.append("")
        lines.append(f"- [ ] Файлов восстановлено (local_missing): {p23s['restored_count']}")
        lines.append(f"- [ ] Sidecar создано (local_edited + protected): {p23s['sidecars_created_count']}")
        lines.append(f"- [ ] Blocked/manual-review: {p23s['blocked_manual_review_count']}")
        lines.append(f"- [ ] AGENTS.md не overwrite-нут.")
        lines.append(f"- [ ] Локальные edited файлы не тронуты.")
        lines.append(f"- [ ] central_missing/metadata_missing честно идут в blocked.")
    lines.append(f"- [ ] P1 metadata обновлён: {'да' if p1_updated else 'нет'}")
    lines.append(f"- [ ] Project-specific файлы не тронуты.")
    lines.append(f"- [ ] Runtime/history не тронуты.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P2.2+P2.3), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_apply_results_json(
    result: dict,
    apply_outcome: dict,
    target: Path,
    p2_3_outcome: Optional[dict] = None,
) -> str:
    """Write machine-readable apply_results.json (P2.2+P2.3). Return path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "apply_results.json"

    payload = {
        "run_id": result["run_id"],
        "mode": "apply",
        "outcome": "P2.2_limited_update_plus_P2.3_safe_review_paths",
        "target": result["target"],
        "source": result["source"],
        "p1_metadata_found": result["p1_metadata_found"],
        "dry_run_summary": result["summary"],
        "apply_summary": apply_outcome["summary"],
        "updated": apply_outcome["updated"],
        "blocked": apply_outcome["blocked"],
        "skipped": apply_outcome["skipped"],
        "errors": apply_outcome["errors"],
    }
    if p2_3_outcome is not None:
        payload["p2_3_summary"] = p2_3_outcome["summary"]
        payload["p2_3_restored"] = p2_3_outcome["restored"]
        payload["p2_3_sidecars_created"] = p2_3_outcome["sidecars_created"]
        payload["p2_3_blocked_manual_review"] = p2_3_outcome["blocked_manual_review"]
        if p2_3_outcome["errors"]:
            payload["errors"] = payload["errors"] + p2_3_outcome["errors"]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def _run_apply(target: Path, source_root: Path) -> dict:
    """Execute full apply: classify, P2.2 update, P2.3 safe review paths.

    Reuses the same detect/compare/classify layer from _run_dry_run(),
    then applies:
    - P2.2: updates stale_central_available files
    - P2.3: safe restore local_missing, sidecars for local_edited/protected_agents,
            blocked/manual-review for central_missing/metadata_missing
    Returns result dict.
    """
    # Phase 1: Run the same dry-run classifier
    result = _run_dry_run(target, source_root)
    result["mode"] = "apply"
    result["outcome"] = "P2.2_limited_update_plus_P2.3_safe_review_paths"

    if not result["p1_metadata_found"]:
        result["apply_outcome"] = {
            "updated": [],
            "skipped": [],
            "blocked": [],
            "errors": [{
                "local_path": "N/A",
                "central_path": "N/A",
                "status": "no_p1_metadata",
                "error": "P1 metadata не найден — apply невозможен.",
                "detail": "Файл .ai/bootstrap/state/core_sync_state.yml отсутствует или не читаем.",
            }],
            "summary": {"updated_count": 0, "skipped_count": 0, "blocked_count": 0, "error_count": 1},
        }
        result["p1_metadata_updated"] = False
        result["p2_3_outcome"] = None
        return result

    # Build P1 managed map for safe restore validation
    p1_path = target / P1_METADATA_PATH
    p1_managed_map: dict[str, str] = {}
    if p1_path.is_file():
        try:
            yaml_text = p1_path.read_text(encoding="utf-8")
            p1_raw = _parse_p1_metadata(yaml_text)
            managed_entries = p1_raw.get("_managed_entries", [])
            for me in managed_entries:
                if isinstance(me, dict):
                    src = me.get("source", me.get("destination", ""))
                    cs = me.get("checksum", "")
                    if src and cs:
                        p1_managed_map[src] = cs
        except Exception:
            pass

    # Phase 2: P2.2 — Apply updates to stale_central_available files
    apply_outcome = _perform_apply_updates(result, target, source_root, p1_path)
    result["apply_outcome"] = apply_outcome

    # Phase 3: P2.3 — Safe review paths for non-clean states
    p2_3_outcome = _perform_p2_3_actions(result, target, source_root, p1_managed_map)
    result["p2_3_outcome"] = p2_3_outcome

    # Phase 4: Update P1 metadata for updated AND restored files
    all_updated_for_metadata = list(apply_outcome["updated"])
    if p2_3_outcome["restored"]:
        all_updated_for_metadata.extend(p2_3_outcome["restored"])
    p1_updated = False
    if all_updated_for_metadata:
        p1_updated = _update_p1_metadata_after_apply(
            p1_path, all_updated_for_metadata, result["run_id"]
        )
        if not p1_updated:
            apply_outcome["errors"].append({
                "local_path": "N/A",
                "central_path": "N/A",
                "status": "metadata_update_failed",
                "error": "Не удалось обновить P1 metadata после apply (P2.2+P2.3).",
                "detail": "Managed files обновлены/восстановлены, но core_sync_state.yml не переписан.",
            })
            apply_outcome["summary"]["error_count"] = apply_outcome["summary"].get("error_count", 0) + 1
    result["p1_metadata_updated"] = p1_updated

    return result


# ---------------------------------------------------------------------------
# P3.1: Conservative Adoption Assessment — assessment-only для pre-P1 repos
# ---------------------------------------------------------------------------

def _classify_p3_1(
    entry: dict,
    target: Path,
    source_root: Path,
) -> dict:
    """Классифицирует один candidate managed path для P3.1 pre-P1 assessment.

    Возвращает classification dict с полями:
    - local_path, central_path, exists_local, exists_central
    - local_checksum, central_checksum
    - p1_metadata_state: 'missing' | 'present_but_incomplete'
    - content_relation_to_central: 'match' | 'differs' | 'unknown'
    - protection_state: 'not_protected' | 'protected_agents' | 'project_specific' | 'runtime_history'
    - classification: одна из семи P3.1 classes
    - decision_bucket: safe_to_consider_for_later_backfill | manual_review_required | excluded_from_backfill | insufficient_information
    - reason_codes: list[str]
    - recommended_next_action: str
    """
    local_path = entry["local_path"]
    central_path = entry["central_path"]
    local_file = target / local_path
    central_file = source_root / central_path

    classification: dict = {
        "local_path": local_path,
        "central_path": central_path,
        "exists_local": local_file.is_file(),
        "exists_central": central_file.is_file(),
        "local_checksum": None,
        "central_checksum": None,
        "p1_metadata_state": "missing",
        "content_relation_to_central": "unknown",
        "protection_state": "not_protected",
        "classification": "unknown_unclassified",
        "decision_bucket": "insufficient_information",
        "reason_codes": [],
        "recommended_next_action": "manual_inspection",
        "allowed_in_p3_1": ["report", "summarize"],
        "forbidden_in_p3_1": ["overwrite", "auto_merge", "metadata_write", "migration"],
    }

    # --- Checksums ---
    if classification["exists_local"]:
        classification["local_checksum"] = _compute_checksum(local_file)
    if classification["exists_central"]:
        classification["central_checksum"] = _compute_checksum(central_file)

    # --- Protection classification ---
    # AGENTS.md
    if local_path == AGENTS_SEED:
        classification["protection_state"] = "protected_agents"
        classification["classification"] = "project_owned_or_protected"
        classification["decision_bucket"] = "excluded_from_backfill"
        classification["reason_codes"].append("protected_agents_seed")
        classification["recommended_next_action"] = "exclude_from_automatic_adoption"
        return classification

    # Project-specific files
    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            classification["protection_state"] = "project_specific"
            classification["classification"] = "project_owned_or_protected"
            classification["decision_bucket"] = "excluded_from_backfill"
            classification["reason_codes"].append("project_specific_path")
            classification["recommended_next_action"] = "exclude_from_automatic_adoption"
            return classification

    # Runtime/history files
    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            classification["protection_state"] = "runtime_history"
            classification["classification"] = "project_owned_or_protected"
            classification["decision_bucket"] = "excluded_from_backfill"
            classification["reason_codes"].append("runtime_history_path")
            classification["recommended_next_action"] = "exclude_from_automatic_adoption"
            return classification

    # Runtime/history dirs
    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            classification["protection_state"] = "runtime_history"
            classification["classification"] = "project_owned_or_protected"
            classification["decision_bucket"] = "excluded_from_backfill"
            classification["reason_codes"].append("runtime_history_path")
            classification["recommended_next_action"] = "exclude_from_automatic_adoption"
            return classification

    # --- Content relation analysis ---
    if not classification["exists_local"]:
        # Missing locally
        if classification["exists_central"]:
            classification["classification"] = "absent_candidate"
            classification["decision_bucket"] = "safe_to_consider_for_later_backfill"
            classification["reason_codes"].append("absent_locally_central_available")
            classification["recommended_next_action"] = "candidate_for_later_restore"
        else:
            classification["classification"] = "absent_candidate"
            classification["decision_bucket"] = "insufficient_information"
            classification["reason_codes"].append("absent_locally_and_centrally")
            classification["recommended_next_action"] = "verify_central_path_expectation"
        return classification

    if not classification["exists_central"]:
        classification["classification"] = "unknown_unclassified"
        classification["decision_bucket"] = "insufficient_information"
        classification["reason_codes"].append("central_source_missing")
        classification["recommended_next_action"] = "verify_central_path_expectation"
        return classification

    # Both exist — compare checksums
    local_cs = classification["local_checksum"]
    central_cs = classification["central_checksum"]

    if local_cs == central_cs:
        classification["content_relation_to_central"] = "match"
        classification["classification"] = "unmanaged_clean_match"
        classification["decision_bucket"] = "safe_to_consider_for_later_backfill"
        classification["reason_codes"].append("content_matches_central")
        classification["reason_codes"].append("missing_p1_metadata")
        classification["recommended_next_action"] = "candidate_for_metadata_only_backfill"
    else:
        classification["content_relation_to_central"] = "differs"
        classification["classification"] = "unmanaged_local_variant"
        classification["decision_bucket"] = "manual_review_required"
        classification["reason_codes"].append("local_content_differs_from_central")
        classification["reason_codes"].append("missing_p1_metadata")
        classification["recommended_next_action"] = "human_review_before_any_backfill"

    return classification


def _run_adoption_assessment(target: Path, source_root: Path) -> dict:
    """Execute P3.1 adoption assessment for a repo WITHOUT P1 baseline metadata.

    Builds managed inventory from central source, classifies each candidate path
    using P3.1 model, and returns result dict. NO writes to managed files.
    NO P1 metadata writes. Assessment-only.
    """
    run_id = _get_run_id()
    result: dict = {
        "run_id": run_id,
        "mode": "assessment_only",
        "outcome": "assessment_only",
        "schema": "ai-workflow-core.p3_1_adoption_assessment",
        "schema_version": "0.1",
        "execution_performed": False,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "p1_metadata_found": False,
        "p1_metadata_summary": {},
        "assumptions": [
            "P3.1 работает из consumer repo working tree",
            "Central candidate path list доступен локальному tool",
            "Оценка не требует P1 baseline metadata",
        ],
        "inputs": {
            "central_baseline_ref": str(source_root),
            "consumer_repo_ref": str(target),
            "p1_metadata_present": False,
        },
        "summary": {
            "total_paths_scanned": 0,
            "absent_candidate": 0,
            "unmanaged_clean_match": 0,
            "unmanaged_local_variant": 0,
            "project_owned_or_protected": 0,
            "unknown_unclassified": 0,
            "metadata_present_but_incomplete": 0,
            "conflict_with_p2_safety": 0,
        },
        "decision_summary": {
            "safe_to_consider_for_later_backfill": 0,
            "manual_review_required": 0,
            "excluded_from_backfill": 0,
            "insufficient_information": 0,
        },
        "paths": [],
        "blockers": [],
        "errors": [],
    }

    # Check for P1 metadata
    p1_path = target / P1_METADATA_PATH
    if p1_path.is_file():
        try:
            yaml_text = p1_path.read_text(encoding="utf-8")
            p1_raw = _parse_p1_metadata(yaml_text)
            result["p1_metadata_found"] = True
            result["p1_metadata_summary"] = {
                "canonical_source_repo": p1_raw.get("canonical_source_repo", ""),
                "canonical_source_url": p1_raw.get("canonical_source_url", ""),
                "canonical_source_revision": p1_raw.get("canonical_source_revision", ""),
                "materialized_from_path": p1_raw.get("materialized_from_path", ""),
                "materialized_from_repo": p1_raw.get("materialized_from_repo", ""),
                "bootstrap_mode": p1_raw.get("bootstrap_mode", ""),
                "project_name": p1_raw.get("project_name", ""),
                "created_at": p1_raw.get("created_at", ""),
                "last_sync_at": p1_raw.get("last_sync_at", ""),
            }
            result["inputs"]["p1_metadata_present"] = True
            result["assumptions"].append(
                "P1 metadata найден в target. P3.1 работает как assessment, "
                "игнорируя P1 baseline для классификации candidate paths."
            )
        except Exception as e:
            result["errors"].append(f"Ошибка чтения P1 metadata: {e}")

    # --- Build managed inventory (same as P2) ---
    managed_inventory = _build_managed_inventory(target, source_root)
    result["summary"]["total_paths_scanned"] = len(managed_inventory)

    # --- Classify each managed path using P3.1 model ---
    for entry in managed_inventory:
        c = _classify_p3_1(entry, target, source_root)
        result["paths"].append(c)

        # Update summary counts
        cl = c["classification"]
        if cl in result["summary"]:
            result["summary"][cl] += 1

        db = c["decision_bucket"]
        if db in result["decision_summary"]:
            result["decision_summary"][db] += 1

    # --- Classify protected and out-of-scope paths ---
    protected_items = _classify_protected_and_oos(target)
    for item in protected_items:
        # Map P2 protection statuses to P3.1 classification
        status = item["status"]
        path_entry = {
            "local_path": item["local_path"],
            "central_path": item.get("central_path", ""),
            "exists_local": item["exists_local"],
            "exists_central": item.get("exists_central", False),
            "local_checksum": item.get("local_checksum"),
            "central_checksum": item.get("central_checksum"),
            "p1_metadata_state": "not_applicable",
            "content_relation_to_central": "not_applicable",
            "protection_state": (
                "protected_agents" if status == "protected_agents"
                else "project_specific" if status == "out_of_scope_project_specific"
                else "runtime_history"
            ),
            "classification": "project_owned_or_protected",
            "decision_bucket": "excluded_from_backfill",
            "reason_codes": [f"p2_status_{status}"],
            "recommended_next_action": "exclude_from_automatic_adoption",
            "allowed_in_p3_1": ["report", "summarize"],
            "forbidden_in_p3_1": ["overwrite", "auto_merge", "metadata_write", "migration"],
            "detail": item.get("detail", ""),
        }
        result["paths"].append(path_entry)
        result["summary"]["project_owned_or_protected"] += 1
        result["decision_summary"]["excluded_from_backfill"] += 1

    return result


def _write_adoption_assessment_md(result: dict, target: Path) -> str:
    """Write human-readable P3.1 adoption assessment report. Return path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "adoption_assessment.md"

    summary = result["summary"]
    ds = result["decision_summary"]

    lines = [
        "# P3.1 Conservative Adoption Assessment",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (assessment-only, без изменения managed files)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **P1 metadata найден:** {'да' if result['p1_metadata_found'] else 'нет'}",
        f"- **Writes performed:** `{result['writes_performed']}`",
        f"- **Execution performed:** `{result['execution_performed']}`",
        "",
        "## Executive Summary",
        "",
    ]

    if result["p1_metadata_found"]:
        lines.append("⚠ P1 metadata обнаружен в target. P3.1 выполнил assessment, игнорируя P1 baseline для чистоты pre-P1 анализа.")
    else:
        lines.append("P1 metadata НЕ обнаружен в target. Выполнена полная pre-P1 adoption assessment candidate managed paths.")

    lines.extend([
        "",
        f"- Всего candidate paths отсканировано: **{summary['total_paths_scanned']}**",
        f"- Unmanaged clean match (кандидаты на metadata-only backfill): **{summary['unmanaged_clean_match']}**",
        f"- Unmanaged local variant (требуют human review): **{summary['unmanaged_local_variant']}**",
        f"- Absent candidate (можно восстановить потом): **{summary['absent_candidate']}**",
        f"- Project owned/protected (исключены): **{summary['project_owned_or_protected']}**",
        f"- Unknown/unclassified: **{summary['unknown_unclassified']}**",
        "",
        "## Decision Summary",
        "",
        f"| Decision Bucket | Count |",
        f"| --- | --- |",
        f"| safe_to_consider_for_later_backfill | {ds['safe_to_consider_for_later_backfill']} |",
        f"| manual_review_required | {ds['manual_review_required']} |",
        f"| excluded_from_backfill | {ds['excluded_from_backfill']} |",
        f"| insufficient_information | {ds['insufficient_information']} |",
        "",
    ])

    # Candidates for later backfill
    backfill_candidates = [p for p in result["paths"]
                           if p["decision_bucket"] == "safe_to_consider_for_later_backfill"]
    if backfill_candidates:
        lines.append("## Candidates for Later Backfill")
        lines.append("")
        lines.append("| Local path | Classification | Reason codes | Recommended action |")
        lines.append("| --- | --- | --- | --- |")
        for p in backfill_candidates:
            rc = ", ".join(p["reason_codes"])
            lines.append(f"| `{p['local_path']}` | `{p['classification']}` | {rc} | {p['recommended_next_action']} |")
        lines.append("")

    # Manual review required
    review_items = [p for p in result["paths"]
                    if p["decision_bucket"] == "manual_review_required"]
    if review_items:
        lines.append("## Manual Review Required")
        lines.append("")
        lines.append("| Local path | Classification | Reason codes | Recommended action |")
        lines.append("| --- | --- | --- | --- |")
        for p in review_items:
            rc = ", ".join(p["reason_codes"])
            lines.append(f"| `{p['local_path']}` | `{p['classification']}` | {rc} | {p['recommended_next_action']} |")
        lines.append("")

    # Excluded
    excluded = [p for p in result["paths"]
                if p["decision_bucket"] == "excluded_from_backfill"]
    if excluded:
        lines.append("## Excluded from Backfill")
        lines.append("")
        lines.append("| Local path | Protection | Reason codes |")
        lines.append("| --- | --- | --- |")
        for p in excluded:
            rc = ", ".join(p["reason_codes"])
            lines.append(f"| `{p['local_path']}` | `{p['protection_state']}` | {rc} |")
        lines.append("")

    # Insufficient information
    insufficient = [p for p in result["paths"]
                    if p["decision_bucket"] == "insufficient_information"]
    if insufficient:
        lines.append("## Insufficient Information")
        lines.append("")
        lines.append("| Local path | Classification | Reason codes |")
        lines.append("| --- | --- | --- |")
        for p in insufficient:
            rc = ", ".join(p["reason_codes"])
            lines.append(f"| `{p['local_path']}` | `{p['classification']}` | {rc} |")
        lines.append("")

    # Errors
    if result["errors"]:
        lines.append("## Ошибки")
        lines.append("")
        for e in result["errors"]:
            lines.append(f"- ⚠ {e}")
        lines.append("")

    # Assumptions
    lines.append("## Assumptions")
    lines.append("")
    for a in result["assumptions"]:
        lines.append(f"- {a}")
    lines.append("")

    # Что сознательно НЕ сделано
    lines.append("## Что сознательно НЕ сделано в P3.1")
    lines.append("")
    lines.append("- ❌ Ни один candidate managed path не изменён локально.")
    lines.append("- ❌ P1 metadata не записана и не обновлена.")
    lines.append("- ❌ Auto-merge не выполнялся.")
    lines.append("- ❌ Force-overwrite не выполнялся.")
    lines.append("- ❌ Full migration engine не запускался.")
    lines.append("- ❌ Protected/project-specific paths не тронуты.")
    lines.append("")

    # Что оставлено на следующие P3 chunks
    lines.append("## Что оставлено на следующие P3 chunks")
    lines.append("")
    lines.append("- Human-approved metadata backfill execution.")
    lines.append("- Explicit migration command.")
    lines.append("- Per-path adoption confirmation workflow.")
    lines.append("- Conflict resolution UX.")
    lines.append("- Integration с P2 apply logic.")
    lines.append("")

    # Verification checklist
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- [ ] Candidate paths отсканировано: {summary['total_paths_scanned']}")
    lines.append(f"- [ ] Ни один managed file не изменён (writes_performed: {result['writes_performed']})")
    lines.append(f"- [ ] Каждый path получил ровно один classification.")
    lines.append(f"- [ ] Protected/project-specific paths исключены из backfill.")
    lines.append(f"- [ ] Local variants идут в manual_review_required, не в safe_to_consider.")
    lines.append(f"- [ ] P1 metadata не записана.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.1), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_adoption_assessment_json(result: dict, target: Path) -> str:
    """Write machine-readable P3.1 adoption assessment JSON. Return path."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "adoption_assessment.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "assumptions": result["assumptions"],
        "inputs": result["inputs"],
        "target": result["target"],
        "source": result["source"],
        "p1_metadata_found": result["p1_metadata_found"],
        "summary": result["summary"],
        "decision_summary": result["decision_summary"],
        "paths": result["paths"],
        "blockers": result["blockers"],
        "errors": result["errors"],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def _write_candidate_backfill_plan(result: dict, target: Path) -> str:
    """Write optional non-executable candidate backfill plan JSON. Return path.

    Этот artifact является ЧИСТО кандидатным планом.
    execution_allowed: false, requires_human_approval: true.
    """
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "candidate_backfill_plan.json"

    # Собираем только safe_to_consider кандидатов
    backfill_candidates = [
        {
            "local_path": p["local_path"],
            "classification": p["classification"],
            "reason_codes": p["reason_codes"],
            "recommended_next_action": p["recommended_next_action"],
            "exists_local": p["exists_local"],
            "exists_central": p["exists_central"],
        }
        for p in result["paths"]
        if p["decision_bucket"] == "safe_to_consider_for_later_backfill"
    ]

    payload = {
        "artifact_kind": "candidate_backfill_plan",
        "execution_allowed": False,
        "requires_human_approval": True,
        "run_id": result["run_id"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "description": (
            "Candidate backfill plan для consumer repo без P1 baseline metadata. "
            "Этот план является ЧИСТО кандидатным. Он НЕ выполняет migration, "
            "НЕ пишет metadata и НЕ меняет managed files. "
            "Требуется human approval для любого последующего шага."
        ),
        "candidate_count": len(backfill_candidates),
        "candidates": backfill_candidates,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


# ---------------------------------------------------------------------------
# P3.2: Metadata-Only Backfill Execution
# ---------------------------------------------------------------------------

def _validate_backfill_plan(plan_path: Path) -> dict:
    """Загружает и валидирует candidate_backfill_plan.json.

    Возвращает dict с полями:
    - valid: bool
    - plan: dict (если валиден) / None
    - errors: list[str]
    """
    errors: list[str] = []

    if not plan_path.is_file():
        return {"valid": False, "plan": None, "errors": [f"Файл плана не найден: {plan_path}"]}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "plan": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    if plan.get("artifact_kind") != "candidate_backfill_plan":
        errors.append("artifact_kind должен быть 'candidate_backfill_plan'")

    # Non-executable contract: execution_allowed MUST be False
    if plan.get("execution_allowed") is not False:
        errors.append(
            "execution_allowed должен быть false — "
            "P3.1 генерирует non-executable candidate plan. "
            "P3.2 является human-approved explicit run поверх этого плана."
        )

    # Human-approval gate: requires_human_approval MUST be True
    if plan.get("requires_human_approval") is not True:
        errors.append(
            "requires_human_approval должен быть true — "
            "candidate backfill plan требует human approval до любого execution."
        )

    # Provenance: run_id
    if not plan.get("run_id"):
        errors.append("Отсутствует run_id (provenance)")

    # Shape: generated_at
    if not plan.get("generated_at"):
        errors.append("Отсутствует generated_at (shape check)")

    if "candidates" not in plan:
        errors.append("Отсутствует поле 'candidates'")
        return {"valid": False, "plan": None, "errors": errors}

    candidates = plan["candidates"]
    if not isinstance(candidates, list) or len(candidates) == 0:
        errors.append("Поле 'candidates' пусто или не является списком")
        return {"valid": False, "plan": None, "errors": errors}

    if errors:
        return {"valid": False, "plan": None, "errors": errors}

    return {"valid": True, "plan": plan, "errors": []}


def _can_backfill_candidate(
    candidate: dict,
    target: Path,
    source_root: Path,
) -> tuple[bool, str]:
    """Валидирует одного кандидата для metadata-only backfill.

    Проверяет narrow execution contract per handoff 0141:
    - classification == unmanaged_clean_match
    - exists_local == True, exists_central == True
    - local-vs-central re-check: local checksum == central checksum НА МОМЕНТ execution
    - path не AGENTS.md
    - path не protected/project-specific/runtime-history

    Returns (allowed, reason).
    """
    local_path = candidate.get("local_path", "")

    if candidate.get("classification") != "unmanaged_clean_match":
        return False, f"Классификация {candidate.get('classification')}, не unmanaged_clean_match."

    if not candidate.get("exists_local"):
        return False, "Файл отсутствует локально (absent_candidate)."
    if not candidate.get("exists_central"):
        return False, "Файл отсутствует в central source."

    # Protection checks BEFORE file re-checks (path-based, not content-based)
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path."

    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл."

    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл."

    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория."

    # Re-check local file existence
    local_file = target / local_path
    if not local_file.is_file():
        return False, "Файл отсутствует локально на момент re-check."

    # Re-check central file existence
    central_file = source_root / local_path
    if not central_file.is_file():
        return False, "Central source file отсутствует на момент re-check."

    try:
        local_cs = _compute_checksum(local_file)
        central_cs = _compute_checksum(central_file)
    except Exception as e:
        return False, f"Ошибка вычисления checksum: {e}"

    if local_cs != central_cs:
        return False, f"Local content drifted from central before execution (local={local_cs[:12]}..., central={central_cs[:12]}...)"

    return True, ""


# ---------------------------------------------------------------------------
# P3.3: Absent Candidate Restore Execution
# ---------------------------------------------------------------------------

def _can_restore_absent_candidate(
    candidate: dict,
    target: Path,
    source_root: Path,
) -> tuple[bool, str]:
    """Валидирует narrow execution contract для absent_candidate restore.

    Handoff 0142 narrow contract — restore ТОЛЬКО если одновременно верно:
    - classification == absent_candidate
    - exists_local == False (по данным плана)
    - exists_central == True (по данным плана)
    - central source file существует на момент execution
    - local path всё ещё отсутствует на момент execution
    - path не AGENTS.md
    - path не protected/project-specific/runtime-history

    Returns (allowed, reason).
    """
    local_path = candidate.get("local_path", "")

    # --- Classification gate ---
    if candidate.get("classification") != "absent_candidate":
        return False, f"Классификация {candidate.get('classification')}, не absent_candidate."

    # --- Plan-level existence gates ---
    if candidate.get("exists_local") is not False:
        return False, "exists_local не False в плане — кандидат не absent."
    if candidate.get("exists_central") is not True:
        return False, "exists_central не True в плане — central source недоступен."

    # --- Protection checks BEFORE file re-checks (path-based) ---
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path, не auto-restore."

    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл — restore запрещён."

    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл — restore запрещён."

    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория — restore запрещён."

    # --- Runtime re-checks (момент execution) ---
    # Re-check: central source file всё ещё существует?
    central_file = source_root / local_path
    if not central_file.is_file():
        return False, "Central source file отсутствует на момент execution."

    # Re-check: local path всё ещё отсутствует?
    local_file = target / local_path
    if local_file.exists():
        return False, "Файл появился локально до execution — restore отменён (race condition)."

    return True, ""


def _run_absent_restore(
    target: Path,
    source_root: Path,
    plan: dict,
) -> dict:
    """Выполняет P3.3 absent candidate restore execution.

    Принимает adoption assessment (или dedicated restore plan).
    Для каждого absent_candidate:
    - проверяет narrow execution contract через _can_restore_absent_candidate
    - при успехе: materialize-ит файл из central source
    - при неуспехе: кладёт в skipped/blocked с reason code

    Возвращает result dict.
    """
    run_id = _get_run_id()
    candidates = plan.get("paths", plan.get("candidates", []))

    result: dict = {
        "run_id": run_id,
        "mode": "absent_candidate_restore",
        "outcome": "P3.3_absent_candidate_restore",
        "schema": "ai-workflow-core.p3_3_absent_restore_execution",
        "schema_version": "0.1",
        "execution_performed": True,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "plan_source": plan.get("run_id", "unknown"),
        "plan_total_paths": len(candidates),
        "assumptions": [
            "P3.3 работает из consumer repo working tree",
            "Restore intent подтверждён human review (план передан в --restore-plan)",
            "Восстанавливаются только absent_candidate из P3.1 assessment context",
            "Каждый candidate перепроверяется на absent + central-available перед restore",
            "Existing local files НЕ overwrite-ятся",
            "local_variant НЕ трогается автоматически",
            "Protected/project-specific/runtime-history paths НЕ восстанавливаются",
        ],
        "summary": {
            "total_candidates_in_plan": len(candidates),
            "restored": 0,
            "skipped_not_absent_candidate": 0,
            "skipped_central_missing_at_execution": 0,
            "skipped_local_appeared_before_execution": 0,
            "skipped_protected_path": 0,
            "skipped_other": 0,
            "blocked": 0,
            "errors": 0,
        },
        "restored": [],
        "skipped": [],
        "blocked": [],
        "errors": [],
        "preexisting_p1_baseline_blocked": False,
    }

    # --- Pre-check: existing P1 baseline blocks restore BEFORE any content write ---
    p1_existing = target / P1_METADATA_PATH
    if p1_existing.is_file():
        result["summary"]["blocked"] = len(candidates)
        result["preexisting_p1_baseline_blocked"] = True
        for candidate in candidates:
            local_path = candidate.get("local_path", "<unknown>")
            result["blocked"].append({
                "local_path": local_path,
                "classification": candidate.get("classification", ""),
                "reason": (
                    f"P1 baseline уже существует: {P1_METADATA_PATH}. "
                    "P3.3 absent restore не выполняет restore при существующем P1 baseline. "
                    "Необходим отдельный safe update существующего P1 baseline."
                ),
                "outcome": "blocked_existing_p1_baseline",
            })
        # Write artifacts anyway (report + JSON) so the blocked result is visible
        return result

    restored: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []

    for candidate in candidates:
        local_path = candidate.get("local_path", "<unknown>")
        classification = candidate.get("classification")

        # Quick pre-filter: только absent_candidate
        if classification != "absent_candidate":
            skipped.append({
                "local_path": local_path,
                "classification": classification,
                "reason": f"Классификация {classification}, не absent_candidate — restore в P3.3 не применим.",
                "outcome": "skipped_not_absent_candidate",
            })
            result["summary"]["skipped_not_absent_candidate"] += 1
            continue

        # Narrow contract validation
        allowed, reason = _can_restore_absent_candidate(candidate, target, source_root)

        if not allowed:
            # Categorize skip/block reason
            if "central" in reason.lower() and "отсутствует" in reason.lower():
                outcome = "skipped_central_missing_at_execution"
                result["summary"]["skipped_central_missing_at_execution"] += 1
            elif "появился" in reason.lower() or "race" in reason.lower():
                outcome = "skipped_local_appeared_before_execution"
                result["summary"]["skipped_local_appeared_before_execution"] += 1
            elif "protected" in reason.lower() or "project-specific" in reason.lower() or "runtime" in reason.lower():
                outcome = "skipped_protected_path"
                result["summary"]["skipped_protected_path"] += 1
            else:
                outcome = "blocked"
                result["summary"]["blocked"] += 1

            if outcome == "blocked":
                blocked.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            else:
                skipped.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            continue

        # --- Perform restore ---
        try:
            central_file = source_root / local_path
            local_file = target / local_path

            central_content = central_file.read_bytes()
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_bytes(central_content)
            new_checksum = _compute_checksum(local_file)
            central_checksum = _compute_checksum(central_file)

            restored.append({
                "local_path": local_path,
                "central_path": local_path,
                "classification": classification,
                "central_checksum": central_checksum,
                "new_checksum": new_checksum,
                "checksum_match": new_checksum == central_checksum,
                "outcome": "restored_from_central",
                "detail": "Файл восстановлен из central source. Checksum совпадает с central.",
            })
            result["summary"]["restored"] += 1
            result["writes_performed"] = True
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "classification": classification,
                "error": str(e),
                "outcome": "restore_error",
            })
            result["summary"]["errors"] += 1

    result["restored"] = restored
    result["skipped"] = skipped
    result["restored"] = restored
    result["skipped"] = skipped
    result["blocked"] = blocked
    result["errors"] = errors

    # --- Metadata baseline write after successful restore ---
    # Only if no pre-existing P1 baseline (checked before loop)
    if restored:
        metadata_path = _write_p3_3_metadata_baseline(restored, target, source_root, run_id)
        result["metadata_baseline_path"] = metadata_path

    return result


def _validate_restore_plan(plan_path: Path) -> dict:
    """Загружает и валидирует restore plan (adoption_assessment.json из P3.1).

    P3.3 restore plan должен быть принятым adoption_assessment.json из P3.1.
    Проверяет provenance contract:
    - schema == "ai-workflow-core.p3_1_adoption_assessment"
    - mode == "assessment_only"
    - execution_performed == False (P3.1 только assessment)
    - writes_performed == False
    - paths существует и является списком

    Возвращает dict с полями:
    - valid: bool
    - plan: dict (если валиден) / None
    - errors: list[str]
    """
    errors: list[str] = []

    if not plan_path.is_file():
        return {"valid": False, "plan": None, "errors": [f"Файл плана не найден: {plan_path}"]}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "plan": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    # Provenance: must be P3.1 adoption assessment
    schema = plan.get("schema", "")
    if schema != "ai-workflow-core.p3_1_adoption_assessment":
        errors.append(
            f"schema должен быть 'ai-workflow-core.p3_1_adoption_assessment', "
            f"получено: '{schema}'. "
            f"P3.3 restore принимает только adoption_assessment.json из P3.1."
        )

    # Mode: assessment_only
    mode = plan.get("mode", "")
    if mode != "assessment_only":
        errors.append(
            f"mode должен быть 'assessment_only', получено: '{mode}'. "
            f"P3.3 restore принимает только неисполненный assessment из P3.1."
        )

    # Execution gate: P3.1 должен быть assessment-only (не выполнено writes)
    if plan.get("execution_performed") is not False:
        errors.append(
            "execution_performed должен быть False — "
            "P3.3 restore принимает только assessment, где writes ещё не выполнялись."
        )

    if plan.get("writes_performed") is not False:
        errors.append(
            "writes_performed должен быть False — "
            "P3.3 restore принимает только assessment, где content writes ещё не выполнялись."
        )

    # Provenance: run_id
    if not plan.get("run_id"):
        errors.append("Отсутствует run_id (provenance)")

    # Shape: paths must exist and be a non-empty list
    paths = plan.get("paths")
    if not isinstance(paths, list) or len(paths) == 0:
        errors.append("Поле 'paths' отсутствует, пусто или не является списком")
        return {"valid": False, "plan": None, "errors": errors}

    if errors:
        return {"valid": False, "plan": None, "errors": errors}

    return {"valid": True, "plan": plan, "errors": []}


def _write_absent_restore_report(result: dict, target: Path) -> str:
    """Записывает human-readable P3.3 absent candidate restore report. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "absent_restore_report.md"

    summary = result["summary"]

    lines = [
        "# P3.3 Absent Candidate Restore Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (восстановление только absent_candidate / missing managed files)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **Plan source (run_id):** `{result.get('plan_source', 'unknown')}`",
        f"- **Writes performed:** `{result['writes_performed']}`",
        "",
        "## Executive Summary",
        "",
        f"P3.3 absent candidate restore выполнил контролируемое восстановление {summary['restored']} отсутствующих managed files.",
        f"Из {summary['total_candidates_in_plan']} путей в плане:",
        f"- **Восстановлено (restored from central):** {summary['restored']}",
        f"- **Пропущено (не absent_candidate):** {summary['skipped_not_absent_candidate']}",
        f"- **Пропущено (central missing на момент execution):** {summary['skipped_central_missing_at_execution']}",
        f"- **Пропущено (local появился до execution):** {summary['skipped_local_appeared_before_execution']}",
        f"- **Пропущено (protected path):** {summary['skipped_protected_path']}",
        f"- **Пропущено (прочее):** {summary['skipped_other']}",
        f"- **Заблокировано:** {summary['blocked']}",
        f"- **Ошибки:** {summary['errors']}",
        "",
    ]

    if result.get("assumptions"):
        lines.append("## Допущения")
        lines.append("")
        for a in result["assumptions"]:
            lines.append(f"- {a}")
        lines.append("")

    if result["restored"]:
        lines.append("## Восстановленные файлы (Restored from Central)")
        lines.append("")
        lines.append("| Local path | Central checksum | New checksum | Checksum match | Detail |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in result["restored"]:
            cc = item["central_checksum"][:12] + "..." if item.get("central_checksum") else "—"
            nc = item["new_checksum"][:12] + "..." if item.get("new_checksum") else "—"
            cm = "✓" if item.get("checksum_match") else "✗"
            lines.append(f"| `{item['local_path']}` | {cc} | {nc} | {cm} | {item.get('detail', '')} |")
        lines.append("")
        lines.append(f"✓ Все {len(result['restored'])} файлов восстановлены из central source. Checksums совпадают.")
        lines.append("")

    if result["skipped"]:
        lines.append("## Пропущено / Skipped")
        lines.append("")
        lines.append("| Local path | Outcome | Reason |")
        lines.append("| --- | --- | --- |")
        for item in result["skipped"]:
            lines.append(f"| `{item['local_path']}` | `{item['outcome']}` | {item.get('reason', '')} |")
        lines.append("")

    if result["blocked"]:
        lines.append("## Заблокировано / Blocked")
        lines.append("")
        lines.append("| Local path | Reason |")
        lines.append("| --- | --- |")
        for item in result["blocked"]:
            lines.append(f"| `{item['local_path']}` | {item.get('reason', '')} |")
        lines.append("")
        lines.append("⚠ Эти файлы требуют ручного решения. Никаких автоматических действий не выполнено.")
        lines.append("")

    if result["errors"]:
        lines.append("## Ошибки")
        lines.append("")
        for item in result["errors"]:
            lines.append(f"- ⚠ `{item.get('local_path', 'N/A')}`: {item.get('error', str(item))}")
        lines.append("")

    lines.append("## Что сознательно НЕ сделано в P3.3")
    lines.append("")
    lines.append("- ❌ Ни один existing local content file не overwrite-нут.")
    lines.append("- ❌ local_variant не тронуты автоматически.")
    lines.append("- ❌ Auto-merge не выполнялся.")
    lines.append("- ❌ Force-overwrite не выполнялся.")
    lines.append("- ❌ Full migration engine не запускался.")
    lines.append("- ❌ Protected/project-specific/runtime-history paths не восстановлены.")
    lines.append("- ❌ AGENTS.md не восстановлен автоматически.")
    lines.append("")

    lines.append("## Что оставлено на следующие P3/P4 chunks")
    lines.append("")
    lines.append("- Обработка local variants (human review + selective adoption).")
    lines.append("- Full migration/adoption engine.")
    lines.append("- Conflict resolution UX.")
    lines.append("- Интеграция с P2 apply logic после полного P3 adoption.")
    lines.append("")

    lines.append("## Verification")
    lines.append("")
    lines.append(f"- [ ] Восстановлено absent candidate: {summary['restored']}")
    lines.append(f"- [ ] Пропущено (central missing): {summary['skipped_central_missing_at_execution']}")
    lines.append(f"- [ ] Пропущено (local appeared): {summary['skipped_local_appeared_before_execution']}")
    lines.append(f"- [ ] Пропущено (protected): {summary['skipped_protected_path']}")
    lines.append(f"- [ ] Existing local files НЕ overwrite-нуты.")
    lines.append(f"- [ ] Restored file checksums совпадают с central.")
    lines.append("- [ ] P2.1 dry-run не сломан.")
    lines.append("- [ ] P3.1 assessment mode не сломан.")
    lines.append("- [ ] P3.2 metadata-only backfill не сломан.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.3), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_absent_restore_results_json(result: dict, target: Path) -> str:
    """Записывает machine-readable P3.3 absent restore execution JSON. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "absent_restore_results.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "target": result["target"],
        "source": result["source"],
        "plan_source": result["plan_source"],
        "plan_total_paths": result["plan_total_paths"],
        "summary": result["summary"],
        "assumptions": result["assumptions"],
        "restored": result["restored"],
        "skipped": result["skipped"],
        "blocked": result["blocked"],
        "errors": result["errors"],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def _write_p3_3_metadata_baseline(
    restored: list[dict],
    target: Path,
    source_root: Path,
    run_id: str,
) -> str:
    """Записывает P1-совместимый metadata baseline (core_sync_state.yml) из P3.3 restore.

    Отличается от _write_metadata_baseline (P3.2) собственной идентичностью:
    - bootstrap_package: p3_3_absent_candidate_restore
    - bootstrap_mode: absent_candidate_restore
    - revision: p3_3_restore_<run_id>
    - footer: End P3.3 metadata baseline

    Возвращает путь к записанному файлу.
    """
    metadata_path = target / P1_METADATA_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo_name = target.resolve().name

    lines = [
        f"# P1 Bootstrap Metadata — создан P3.3 absent candidate restore",
        f"# Run ID: {run_id}",
        f"schema_version: \"0.1\"",
        f"sync_direction: \"central-to-consumer\"",
        f"bootstrap_package: \"p3_3_absent_candidate_restore\"",
        f"bootstrap_mode: \"absent_candidate_restore\"",
        f"project_name: \"{repo_name}\"",
        f"created_at: \"{now_iso}\"",
        f"last_sync_at: \"{now_iso}\"",
        "",
        "canonical_source:",
        f"  repo: \"AndrewVerhoturov1/ai-workflow-core\"",
        f"  url: \"https://github.com/AndrewVerhoturov1/ai-workflow-core\"",
        f"  revision: \"p3_3_restore_{run_id}\"",
        "",
        "materialized_from:",
        f"  path: \"{source_root.resolve().as_posix()}\"",
        f"  repo: \"local\"",
        "",
        "managed_files:",
    ]

    for item in restored:
        lp = item["local_path"]
        cs = item["new_checksum"]
        placement = "copy-as-is"
        for mf in MANAGED_COPY_FILES:
            if lp == mf:
                placement = "copy-as-is"
                break
        for md in MANAGED_COPY_DIRS:
            if lp.startswith(md + "/"):
                placement = "copy-as-is"
                break

        lines.append(f"  - source: \"{lp}\"")
        lines.append(f"    destination: \"{lp}\"")
        lines.append(f"    placement: \"{placement}\"")
        lines.append(f"    local_edit_policy: \"do-not-edit\"")
        lines.append(f"    checksum: {cs}")

    lines.append("")
    lines.append("adapted_files: []")
    lines.append("")
    lines.append("# --- End P3.3 metadata baseline ---")

    content = "\n".join(lines) + "\n"
    metadata_path.write_text(content, encoding="utf-8")
    return str(metadata_path)


# ---------------------------------------------------------------------------
# P3.4: Local Variant Review Paths — human-reviewed review для divergent local managed files
# ---------------------------------------------------------------------------

def _validate_review_plan(plan_path: Path) -> dict:
    """Загружает и валидирует review plan (adoption_assessment.json из P3.1).

    P3.4 review plan должен быть принятым adoption_assessment.json из P3.1.
    Проверяет provenance contract:
    - schema == "ai-workflow-core.p3_1_adoption_assessment"
    - mode == "assessment_only"
    - execution_performed == False (P3.1 только assessment)
    - writes_performed == False
    - paths существует и является списком
    - каждый элемент paths имеет обязательные поля (local_path, classification, exists_local, exists_central)
    - classification в paths — одно из известных значений P3.1
    - присутствуют обязательные верхнеуровневые блоки: schema_version, summary, decision_summary

    Возвращает dict с полями:
    - valid: bool
    - plan: dict (если валиден) / None
    - errors: list[str]
    """
    errors: list[str] = []

    if not plan_path.is_file():
        return {"valid": False, "plan": None, "errors": [f"Файл плана не найден: {plan_path}"]}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "plan": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    # Provenance: must be P3.1 adoption assessment
    schema = plan.get("schema", "")
    if schema != "ai-workflow-core.p3_1_adoption_assessment":
        errors.append(
            f"schema должен быть 'ai-workflow-core.p3_1_adoption_assessment', "
            f"получено: '{schema}'. "
            f"P3.4 local variant review принимает только adoption_assessment.json из P3.1."
        )

    # Mode: assessment_only
    mode = plan.get("mode", "")
    if mode != "assessment_only":
        errors.append(
            f"mode должен быть 'assessment_only', получено: '{mode}'. "
            f"P3.4 review принимает только неисполненный assessment из P3.1."
        )

    # Execution gate: P3.1 должен быть assessment-only (не выполнено writes)
    if plan.get("execution_performed") is not False:
        errors.append(
            "execution_performed должен быть False — "
            "P3.4 review принимает только assessment, где writes ещё не выполнялись."
        )

    if plan.get("writes_performed") is not False:
        errors.append(
            "writes_performed должен быть False — "
            "P3.4 review принимает только assessment, где content writes ещё не выполнялись."
        )

    # Provenance: run_id
    if not plan.get("run_id"):
        errors.append("Отсутствует run_id (provenance)")

    # Shape: paths must exist and be a non-empty list
    paths = plan.get("paths")
    if not isinstance(paths, list) or len(paths) == 0:
        errors.append("Поле 'paths' отсутствует, пусто или не является списком")
        return {"valid": False, "plan": None, "errors": errors}

    # --- Structure validation: каждый элемент paths должен иметь обязательные поля ---
    required_path_fields = ["local_path", "classification", "exists_local", "exists_central"]
    known_classes = {
        "unmanaged_clean_match", "unmanaged_local_variant",
        "absent_candidate", "project_owned_or_protected",
        "unknown_unclassified",
    }
    for i, p in enumerate(paths):
        if not isinstance(p, dict):
            errors.append(f"paths[{i}]: не является dict, получено {type(p).__name__}")
            continue

        # --- Обязательные поля ---
        for f in required_path_fields:
            if f not in p:
                errors.append(f"paths[{i}]: отсутствует обязательное поле '{f}'")

        # --- Типы обязательных полей ---
        lp = p.get("local_path")
        if lp is not None and not isinstance(lp, str):
            errors.append(f"paths[{i}]: local_path должен быть str, получено {type(lp).__name__}")
        elif lp is not None and isinstance(lp, str) and lp.strip() == "":
            errors.append(f"paths[{i}]: local_path не может быть пустой строкой")

        cl = p.get("classification")
        if cl is not None and not isinstance(cl, str):
            errors.append(f"paths[{i}]: classification должен быть str, получено {type(cl).__name__}")
        elif cl is not None and isinstance(cl, str):
            if cl.strip() == "":
                errors.append(f"paths[{i}]: classification не может быть пустой строкой")
            elif cl not in known_classes:
                errors.append(
                    f"paths[{i}]: неизвестная classification '{cl}'. "
                    f"Ожидается одна из: {', '.join(sorted(known_classes))}"
                )

        for bool_field in ("exists_local", "exists_central"):
            val = p.get(bool_field)
            if val is not None and not isinstance(val, bool):
                errors.append(
                    f"paths[{i}]: {bool_field} должен быть bool, "
                    f"получено {type(val).__name__} = {val!r}"
                )

    # --- Structure validation: обязательные верхнеуровневые поля P3.1 assessment ---
    if not plan.get("schema_version"):
        errors.append("Отсутствует schema_version (shape check)")

    summary = plan.get("summary")
    if not isinstance(summary, dict):
        errors.append("Поле 'summary' отсутствует или не является dict (структура P3.1 assessment)")
    else:
        expected_summary_keys = [
            "total_paths_scanned", "unmanaged_clean_match",
            "unmanaged_local_variant", "absent_candidate",
            "project_owned_or_protected", "unknown_unclassified",
        ]
        for k in expected_summary_keys:
            if k not in summary:
                errors.append(f"summary: отсутствует ожидаемый ключ '{k}'")

    decision_summary = plan.get("decision_summary")
    if not isinstance(decision_summary, dict):
        errors.append("Поле 'decision_summary' отсутствует или не является dict (структура P3.1 assessment)")
    else:
        expected_ds_keys = [
            "safe_to_consider_for_later_backfill",
            "manual_review_required",
            "excluded_from_backfill",
            "insufficient_information",
        ]
        for k in expected_ds_keys:
            if k not in decision_summary:
                errors.append(f"decision_summary: отсутствует ожидаемый ключ '{k}'")

    inputs = plan.get("inputs")
    if inputs is not None and not isinstance(inputs, dict):
        errors.append("Поле 'inputs' присутствует, но не является dict")

    assumptions = plan.get("assumptions")
    if assumptions is not None and not isinstance(assumptions, list):
        errors.append("Поле 'assumptions' присутствует, но не является list")

    if errors:
        return {"valid": False, "plan": None, "errors": errors}

    return {"valid": True, "plan": plan, "errors": []}


def _can_review_local_variant(
    candidate: dict,
    target: Path,
    source_root: Path,
) -> tuple[bool, str]:
    """Валидирует narrow execution contract для local_variant review.

    Handoff 0143 narrow contract — review ТОЛЬКО если одновременно верно:
    - classification == unmanaged_local_variant
    - exists_local == True (по данным плана)
    - exists_central == True (по данным плана)
    - local path существует на момент execution
    - central source file существует на момент execution
    - content_relation_to_central == 'differs'
    - path не AGENTS.md
    - path не protected/project-specific/runtime-history

    Returns (allowed, reason).
    """
    local_path = candidate.get("local_path", "")

    # --- Classification gate ---
    if candidate.get("classification") != "unmanaged_local_variant":
        return False, f"Классификация {candidate.get('classification')}, не unmanaged_local_variant."

    # --- Plan-level existence gates ---
    if candidate.get("exists_local") is not True:
        return False, "exists_local не True в плане — не local_variant."
    if candidate.get("exists_central") is not True:
        return False, "exists_central не True в плане — central source недоступен."

    # --- Content relation gate ---
    if candidate.get("content_relation_to_central") != "differs":
        return False, (
            f"content_relation_to_central = '{candidate.get('content_relation_to_central')}', "
            f"не 'differs' — файл не отличается от central."
        )

    # --- Protection checks BEFORE file re-checks (path-based) ---
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path, не review local_variant."

    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл — review local_variant запрещён."

    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл — review local_variant запрещён."

    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория — review local_variant запрещён."

    # --- Runtime re-checks (момент execution) ---
    # Re-check: local path всё ещё существует?
    local_file = target / local_path
    if not local_file.is_file():
        return False, "Локальный файл отсутствует на момент execution — не local_variant."

    # Re-check: central source file всё ещё существует?
    central_file = source_root / local_path
    if not central_file.is_file():
        return False, "Central source file отсутствует на момент execution."

    # --- Runtime checksum re-check: действительно ли файлы отличаются? ---
    # План мог быть создан раньше, и к моменту execution файлы могли совпасть.
    # Если содержимое совпадает — это НЕ local_variant, пропускаем как identical.
    local_checksum = _compute_checksum(local_file)
    central_checksum = _compute_checksum(central_file)
    if local_checksum == central_checksum:
        return False, (
            "Local и central файлы идентичны на момент execution "
            "(checksums совпадают). Не local_variant — skipped как identical."
        )

    return True, ""


def _run_local_variant_review(
    target: Path,
    source_root: Path,
    plan: dict,
) -> dict:
    """Выполняет P3.4 local variant review.

    Принимает adoption assessment из P3.1.
    Для каждого unmanaged_local_variant:
    - проверяет narrow execution contract через _can_review_local_variant
    - при успехе: собирает review data, сохраняет central sidecar в run-artifacts
    - при неуспехе: кладёт в skipped/blocked с reason code

    НЕ overwrite-ит существующие локальные файлы.
    НЕ auto-merge-ит.
    НЕ записывает metadata baseline.

    Возвращает result dict.
    """
    run_id = _get_run_id()
    candidates = plan.get("paths", plan.get("candidates", []))

    result: dict = {
        "run_id": run_id,
        "mode": "local_variant_review",
        "outcome": "P3.4_local_variant_review_paths",
        "schema": "ai-workflow-core.p3_4_local_variant_review",
        "schema_version": "0.1",
        "execution_performed": True,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "plan_source": plan.get("run_id", "unknown"),
        "plan_total_paths": len(candidates),
        "assumptions": [
            "P3.4 работает из consumer repo working tree",
            "Review intent подтверждён human review (план передан в --review-plan)",
            "Рассматриваются только unmanaged_local_variant из P3.1 assessment context",
            "Каждый candidate перепроверяется на local_variant + exists перед review",
            "Existing local files НЕ overwrite-ятся",
            "Central snapshots сохраняются только в run-artifacts",
            "Metadata baseline НЕ записывается (конфликт не решён)",
            "Protected/project-specific/runtime-history paths НЕ попадают в review",
        ],
        "summary": {
            "total_candidates_in_plan": len(candidates),
            "reviewed": 0,
            "skipped_not_local_variant": 0,
            "skipped_identical_content": 0,
            "skipped_central_missing_at_execution": 0,
            "skipped_local_missing_at_execution": 0,
            "skipped_protected_path": 0,
            "skipped_other": 0,
            "blocked": 0,
            "errors": 0,
        },
        "reviewed": [],
        "skipped": [],
        "blocked": [],
        "errors": [],
        "sidecar_dir": "",
    }

    # --- Create sidecar directory inside run-artifacts ---
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    sidecar_dir = report_dir / "local_variant_sidecars"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    result["sidecar_dir"] = str(sidecar_dir)

    reviewed: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []

    for candidate in candidates:
        local_path = candidate.get("local_path", "<unknown>")
        classification = candidate.get("classification")

        # Quick pre-filter: только unmanaged_local_variant
        if classification != "unmanaged_local_variant":
            skipped.append({
                "local_path": local_path,
                "classification": classification,
                "reason": f"Классификация {classification}, не unmanaged_local_variant — P3.4 review не применим.",
                "outcome": "skipped_not_local_variant",
            })
            result["summary"]["skipped_not_local_variant"] += 1
            continue

        # Narrow contract validation
        allowed, reason = _can_review_local_variant(candidate, target, source_root)

        if not allowed:
            # Categorize skip/block reason
            if "identical" in reason.lower() or "не отличается" in reason.lower():
                outcome = "skipped_identical_content"
                result["summary"]["skipped_identical_content"] += 1
            elif "central" in reason.lower() and "отсутствует" in reason.lower():
                outcome = "skipped_central_missing_at_execution"
                result["summary"]["skipped_central_missing_at_execution"] += 1
            elif "локальный файл отсутствует" in reason.lower():
                outcome = "skipped_local_missing_at_execution"
                result["summary"]["skipped_local_missing_at_execution"] += 1
            elif "protected" in reason.lower() or "project-specific" in reason.lower() or "runtime" in reason.lower():
                outcome = "skipped_protected_path"
                result["summary"]["skipped_protected_path"] += 1
            else:
                outcome = "blocked"
                result["summary"]["blocked"] += 1

            if outcome == "blocked":
                blocked.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            else:
                skipped.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            continue

        # --- Collect review data ---
        try:
            local_file = target / local_path
            central_file = source_root / local_path

            local_checksum = _compute_checksum(local_file)
            central_checksum = _compute_checksum(central_file)
            checksums_match = local_checksum == central_checksum

            # --- Runtime checksum re-check (defense-in-depth) ---
            # Даже если _can_review_local_variant пропустил, перепроверяем здесь:
            # identical на момент execution → skipped, не reviewed.
            if checksums_match:
                skipped.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": (
                        "Local и central файлы идентичны на момент execution "
                        "(checksums совпадают). Не local_variant — skipped как identical."
                    ),
                    "outcome": "skipped_identical_content",
                    "local_checksum": local_checksum,
                    "central_checksum": central_checksum,
                })
                result["summary"]["skipped_identical_content"] += 1
                continue

            # Determine compare status
            compare_status = "divergent"

            # Save central sidecar/snapshot inside run-artifacts
            sidecar_rel = f"{local_path.replace('/', '_').replace(chr(92), '_')}.central_snapshot"
            sidecar_path = sidecar_dir / sidecar_rel
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_content = central_file.read_bytes()
            sidecar_path.write_bytes(sidecar_content)

            # Collect reason codes from assessment
            reason_codes = candidate.get("reason_codes", [])

            review_entry = {
                "local_path": local_path,
                "central_path": local_path,
                "classification": classification,
                "local_checksum": local_checksum,
                "central_checksum": central_checksum,
                "checksums_match": False,
                "compare_status": compare_status,
                "reason_codes": reason_codes,
                "sidecar_path": str(sidecar_path),
                "outcome": "reviewed",
                "detail": (
                    f"Local variant review: local и central расходятся. "
                    f"Central snapshot сохранён в {sidecar_path}. "
                    f"Локальный файл НЕ изменён. Требуется human review."
                ),
            }

            reviewed.append(review_entry)
            result["summary"]["reviewed"] += 1
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "classification": classification,
                "error": str(e),
                "outcome": "review_error",
            })
            result["summary"]["errors"] += 1

    result["reviewed"] = reviewed
    result["skipped"] = skipped
    result["blocked"] = blocked
    result["errors"] = errors

    return result


def _write_local_variant_review_report(result: dict, target: Path) -> str:
    """Записывает human-readable P3.4 local variant review report. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "local_variant_review_report.md"

    summary = result["summary"]

    lines = [
        "# P3.4 Local Variant Review Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (human-reviewed review только для unmanaged_local_variant)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **Plan source (run_id):** `{result.get('plan_source', 'unknown')}`",
        f"- **Writes performed:** `{result['writes_performed']}`",
        "",
        "## Executive Summary",
        "",
        f"P3.4 local variant review собрал review data для {summary['reviewed']} divergent local managed files.",
        f"Из {summary['total_candidates_in_plan']} путей в плане:",
        f"- **Рассмотрено (reviewed):** {summary['reviewed']}",
        f"- **Пропущено (не local_variant):** {summary['skipped_not_local_variant']}",
        f"- **Пропущено (identical content):** {summary['skipped_identical_content']}",
        f"- **Пропущено (central missing):** {summary['skipped_central_missing_at_execution']}",
        f"- **Пропущено (local missing):** {summary['skipped_local_missing_at_execution']}",
        f"- **Пропущено (protected path):** {summary['skipped_protected_path']}",
        f"- **Пропущено (прочее):** {summary['skipped_other']}",
        f"- **Заблокировано:** {summary['blocked']}",
        f"- **Ошибки:** {summary['errors']}",
        "",
        "⚠ **Внимание:** Этот отчёт является review artifact, а не execution result.",
        "Ни один локальный файл не был изменён. Central snapshots сохранены только в run-artifacts.",
        "Metadata baseline НЕ записан. Конфликты НЕ разрешены автоматически.",
        "Требуется human review для каждого divergent файла.",
        "",
    ]

    if result.get("assumptions"):
        lines.append("## Допущения")
        lines.append("")
        for a in result["assumptions"]:
            lines.append(f"- {a}")
        lines.append("")

    if result["reviewed"]:
        lines.append("## Рассмотренные файлы (Local Variant Review)")
        lines.append("")
        lines.append("| Local path | Local checksum | Central checksum | Compare | Reason codes | Sidecar |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in result["reviewed"]:
            lc = item["local_checksum"][:12] + "..." if item.get("local_checksum") else "—"
            cc = item["central_checksum"][:12] + "..." if item.get("central_checksum") else "—"
            cs = "✓ match" if item.get("checksums_match") else "✗ divergent"
            rc = ", ".join(item.get("reason_codes", [])) or "—"
            sp = item.get("sidecar_path", "—")
            lines.append(f"| `{item['local_path']}` | {lc} | {cc} | {cs} | {rc} | `{sp}` |")
        lines.append("")
        lines.append(f"✓ Все {len(result['reviewed'])} файлов рассмотрены. Central snapshots сохранены в `{result.get('sidecar_dir', '')}`.")
        lines.append("")

    if result.get("sidecar_dir"):
        lines.append("## Central Sidecar Snapshots")
        lines.append("")
        lines.append(f"Central версии файлов сохранены в: `{result['sidecar_dir']}`")
        lines.append("")
        lines.append("Эти snapshot-ы предназначены только для human review.")
        lines.append("Они не являются restore target и не overwrite-ят локальные файлы.")
        lines.append("")

    if result["skipped"]:
        lines.append("## Пропущено / Skipped")
        lines.append("")
        lines.append("| Local path | Outcome | Reason |")
        lines.append("| --- | --- | --- |")
        for item in result["skipped"]:
            lines.append(f"| `{item['local_path']}` | `{item['outcome']}` | {item.get('reason', '')} |")
        lines.append("")

    if result["blocked"]:
        lines.append("## Заблокировано / Blocked")
        lines.append("")
        lines.append("| Local path | Reason |")
        lines.append("| --- | --- |")
        for item in result["blocked"]:
            lines.append(f"| `{item['local_path']}` | {item.get('reason', '')} |")
        lines.append("")
        lines.append("⚠ Эти файлы требуют ручного решения. Никаких автоматических действий не выполнено.")
        lines.append("")

    if result["errors"]:
        lines.append("## Ошибки")
        lines.append("")
        for item in result["errors"]:
            lines.append(f"- ⚠ `{item.get('local_path', 'N/A')}`: {item.get('error', str(item))}")
        lines.append("")

    lines.append("## Что сознательно НЕ сделано в P3.4")
    lines.append("")
    lines.append("- ❌ Ни один existing local content file не overwrite-нут.")
    lines.append("- ❌ Auto-merge local variants не выполнялся.")
    lines.append("- ❌ Force-overwrite не выполнялся.")
    lines.append("- ❌ Metadata baseline НЕ записан (конфликт не решён).")
    lines.append("- ❌ Full migration engine не запускался.")
    lines.append("- ❌ Protected/project-specific/runtime-history paths не тронуты.")
    lines.append("- ❌ AGENTS.md не тронут.")
    lines.append("")

    lines.append("## Что оставлено на следующие P3/P4 chunks")
    lines.append("")
    lines.append("- Human review каждого divergent файла.")
    lines.append("- Selective adoption / merge для отдельных local variants.")
    lines.append("- Full migration/adoption engine.")
    lines.append("- Conflict resolution UX.")
    lines.append("")

    lines.append("## Verification")
    lines.append("")
    lines.append(f"- [ ] Рассмотрено local_variant: {summary['reviewed']}")
    lines.append(f"- [ ] Пропущено (не local_variant): {summary['skipped_not_local_variant']}")
    lines.append(f"- [ ] Пропущено (identical): {summary['skipped_identical_content']}")
    lines.append(f"- [ ] Пропущено (central missing): {summary['skipped_central_missing_at_execution']}")
    lines.append(f"- [ ] Пропущено (protected): {summary['skipped_protected_path']}")
    lines.append(f"- [ ] Existing local files НЕ overwrite-нуты.")
    lines.append(f"- [ ] Central snapshots только в run-artifacts.")
    lines.append(f"- [ ] Metadata baseline НЕ записан.")
    lines.append("- [ ] P2.1 dry-run не сломан.")
    lines.append("- [ ] P3.1 assessment mode не сломан.")
    lines.append("- [ ] P3.2 metadata-only backfill не сломан.")
    lines.append("- [ ] P3.3 absent restore не сломан.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.4), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_local_variant_review_json(result: dict, target: Path) -> str:
    """Записывает machine-readable P3.4 local variant review JSON. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "local_variant_review.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "target": result["target"],
        "source": result["source"],
        "plan_source": result["plan_source"],
        "plan_total_paths": result["plan_total_paths"],
        "summary": result["summary"],
        "assumptions": result["assumptions"],
        "reviewed": result["reviewed"],
        "skipped": result["skipped"],
        "blocked": result["blocked"],
        "errors": result["errors"],
        "sidecar_dir": result.get("sidecar_dir", ""),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def _write_metadata_baseline(
    backfilled: list[dict],
    target: Path,
    source_root: Path,
    run_id: str,
) -> str:
    """Записывает P1-совместимый metadata baseline (core_sync_state.yml).

    Создаёт или обновляет .ai/bootstrap/state/core_sync_state.yml
    с checksums для каждого backfill-нутого файла.

    Возвращает путь к записанному файлу.
    """
    metadata_path = target / P1_METADATA_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo_name = target.resolve().name

    lines = [
        f"# P1 Bootstrap Metadata — создан P3.2 metadata-only backfill",
        f"# Run ID: {run_id}",
        f"schema_version: \"0.1\"",
        f"sync_direction: \"central-to-consumer\"",
        f"bootstrap_package: \"p3_2_metadata_only_backfill\"",
        f"bootstrap_mode: \"metadata_only_backfill\"",
        f"project_name: \"{repo_name}\"",
        f"created_at: \"{now_iso}\"",
        f"last_sync_at: \"{now_iso}\"",
        "",
        "canonical_source:",
        f"  repo: \"AndrewVerhoturov1/ai-workflow-core\"",
        f"  url: \"https://github.com/AndrewVerhoturov1/ai-workflow-core\"",
        f"  revision: \"p3_2_backfill_{run_id}\"",
        "",
        "materialized_from:",
        f"  path: \"{source_root.resolve().as_posix()}\"",
        f"  repo: \"local\"",
        "",
        "managed_files:",
    ]

    for item in backfilled:
        lp = item["local_path"]
        cs = item["new_checksum"]
        placement = "copy-as-is"
        for mf in MANAGED_COPY_FILES:
            if lp == mf:
                placement = "copy-as-is"
                break
        for md in MANAGED_COPY_DIRS:
            if lp.startswith(md + "/"):
                placement = "copy-as-is"
                break

        lines.append(f"  - source: \"{lp}\"")
        lines.append(f"    destination: \"{lp}\"")
        lines.append(f"    placement: \"{placement}\"")
        lines.append(f"    local_edit_policy: \"do-not-edit\"")
        lines.append(f"    checksum: {cs}")

    lines.append("")
    lines.append("adapted_files: []")
    lines.append("")
    lines.append("# --- End P3.2 metadata baseline ---")

    content = "\n".join(lines) + "\n"
    metadata_path.write_text(content, encoding="utf-8")
    return str(metadata_path)


def _run_backfill(target: Path, source_root: Path, plan: dict) -> dict:
    """Выполняет metadata-only backfill execution.

    Принимает валидированный candidate_backfill_plan.
    Для каждого candidate:
    - проверяет narrow execution contract через _can_backfill_candidate
    - при успехе: фиксирует checksums для metadata baseline
    - при неуспехе: кладёт в skipped/blocked с reason code

    Возвращает result dict.
    """
    run_id = _get_run_id()
    candidates = plan.get("candidates", [])

    result: dict = {
        "run_id": run_id,
        "mode": "metadata_only_backfill",
        "outcome": "P3.2_metadata_only_backfill",
        "schema": "ai-workflow-core.p3_2_backfill_execution",
        "schema_version": "0.1",
        "execution_performed": True,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "plan_source": plan.get("run_id", "unknown"),
        "plan_candidate_count": len(candidates),
        "assumptions": [
            "P3.2 работает из consumer repo working tree",
            "Candidate backfill plan предоставлен из P3.1 assessment",
            "Metadata-only backfill: пишем metadata baseline, НЕ content managed files",
            "Каждый candidate перепроверяется на local-vs-central equality перед записью",
        ],
        "summary": {
            "total_candidates_in_plan": len(candidates),
            "executed": 0,
            "skipped_not_unmanaged_clean_match": 0,
            "skipped_absent_candidate": 0,
            "skipped_content_drifted": 0,
            "skipped_protected_path": 0,
            "skipped_other": 0,
            "blocked": 0,
            "errors": 0,
        },
        "executed": [],
        "skipped": [],
        "blocked": [],
        "errors": [],
        "metadata_baseline_path": None,
    }

    executed: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []

    for candidate in candidates:
        local_path = candidate.get("local_path", "<unknown>")
        classification = candidate.get("classification")

        if classification != "unmanaged_clean_match":
            skipped.append({
                "local_path": local_path,
                "classification": classification,
                "reason": f"Классификация {classification}, не unmanaged_clean_match.",
                "outcome": "skipped_not_unmanaged_clean_match",
            })
            result["summary"]["skipped_not_unmanaged_clean_match"] += 1
            continue

        if not candidate.get("exists_local"):
            skipped.append({
                "local_path": local_path,
                "classification": classification,
                "reason": "absent_candidate — backfill в P3.2 не разрешён.",
                "outcome": "skipped_absent_candidate",
            })
            result["summary"]["skipped_absent_candidate"] += 1
            continue

        allowed, reason = _can_backfill_candidate(candidate, target, source_root)

        if not allowed:
            if "drifted" in reason.lower():
                outcome = "skipped_content_drifted"
                result["summary"]["skipped_content_drifted"] += 1
                skipped.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            elif "protected" in reason.lower() or "project-specific" in reason.lower() or "runtime" in reason.lower():
                outcome = "skipped_protected_path"
                result["summary"]["skipped_protected_path"] += 1
                skipped.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            else:
                outcome = "blocked"
                result["summary"]["blocked"] += 1
                blocked.append({
                    "local_path": local_path,
                    "classification": classification,
                    "reason": reason,
                    "outcome": outcome,
                })
            continue

        try:
            local_file = target / local_path
            central_file = source_root / local_path
            local_cs = _compute_checksum(local_file)
            central_cs = _compute_checksum(central_file)

            executed.append({
                "local_path": local_path,
                "central_path": local_path,
                "classification": classification,
                "local_checksum": local_cs,
                "central_checksum": central_cs,
                "new_checksum": local_cs,
                "outcome": "executed_metadata_only",
                "detail": "Metadata backfill выполнен: checksum зафиксирован, content файл НЕ изменён.",
            })
            result["summary"]["executed"] += 1
        except Exception as e:
            errors.append({
                "local_path": local_path,
                "classification": classification,
                "error": str(e),
                "outcome": "error",
            })
            result["summary"]["errors"] += 1

    result["executed"] = executed
    result["skipped"] = skipped
    result["blocked"] = blocked
    result["errors"] = errors

    # Guard: не перезаписывать существующий P1 baseline
    p1_existing = target / P1_METADATA_PATH
    if executed and p1_existing.is_file():
        errors.append({
            "local_path": "N/A",
            "classification": "N/A",
            "error": (
                f"P1 baseline уже существует: {P1_METADATA_PATH}. "
                "P3.2 предназначен для pre-P1 repo (без existing baseline). "
                "Перезапись существующего baseline запрещена в этом chunk. "
                "Необходим отдельный chunk для safe update существующего P1 baseline."
            ),
            "outcome": "blocked_existing_p1_baseline",
        })
        result["summary"]["blocked"] += len(executed)
        # Move executed items to blocked
        for item in executed:
            result["blocked"].append({
                "local_path": item["local_path"],
                "classification": item.get("classification", ""),
                "reason": "P1 baseline уже существует — backfill заблокирован в P3.2.",
                "outcome": "blocked_existing_p1_baseline",
            })
        result["executed"] = []
        result["summary"]["executed"] = 0
        result["writes_performed"] = False
    elif executed:
        metadata_path = _write_metadata_baseline(executed, target, source_root, run_id)
        result["metadata_baseline_path"] = metadata_path
        result["writes_performed"] = True

    return result


def _write_backfill_report(result: dict, target: Path) -> str:
    """Записывает human-readable P3.2 backfill execution report. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "backfill_execution_report.md"

    summary = result["summary"]

    lines = [
        "# P3.2 Metadata-Only Backfill Execution Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (metadata-only backfill, content files НЕ изменены)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **Plan source (run_id):** `{result.get('plan_source', 'unknown')}`",
        f"- **Writes performed:** `{result['writes_performed']}`",
        f"- **Metadata baseline:** {'записан' if result.get('metadata_baseline_path') else 'НЕ записан'}",
        "",
        "## Executive Summary",
        "",
        f"P3.2 metadata-only backfill выполнил контролируемую запись metadata baseline для {summary['executed']} файлов.",
        f"Из {summary['total_candidates_in_plan']} кандидатов в плане:",
        f"- **Выполнено (metadata backfill):** {summary['executed']}",
        f"- **Пропущено (не unmanaged_clean_match):** {summary['skipped_not_unmanaged_clean_match']}",
        f"- **Пропущено (absent_candidate):** {summary['skipped_absent_candidate']}",
        f"- **Пропущено (content drifted):** {summary['skipped_content_drifted']}",
        f"- **Пропущено (protected path):** {summary['skipped_protected_path']}",
        f"- **Пропущено (прочее):** {summary['skipped_other']}",
        f"- **Заблокировано:** {summary['blocked']}",
        f"- **Ошибки:** {summary['errors']}",
        "",
    ]

    if result.get("assumptions"):
        lines.append("## Допущения")
        lines.append("")
        for a in result["assumptions"]:
            lines.append(f"- {a}")
        lines.append("")

    if result["executed"]:
        lines.append("## Выполненные Metadata Backfill")
        lines.append("")
        lines.append("| Local path | Local checksum | Central checksum | Detail |")
        lines.append("| --- | --- | --- | --- |")
        for item in result["executed"]:
            lc = item["local_checksum"][:12] + "..." if item.get("local_checksum") else "—"
            cc = item["central_checksum"][:12] + "..." if item.get("central_checksum") else "—"
            lines.append(f"| `{item['local_path']}` | {lc} | {cc} | {item.get('detail', '')} |")
        lines.append("")
        lines.append(f"✓ Все {len(result['executed'])} файлов: записан только metadata baseline. Content файлы НЕ изменены.")
        lines.append("")

    if result["skipped"]:
        lines.append("## Пропущено / Skipped")
        lines.append("")
        lines.append("| Local path | Outcome | Reason |")
        lines.append("| --- | --- | --- |")
        for item in result["skipped"]:
            lines.append(f"| `{item['local_path']}` | `{item['outcome']}` | {item.get('reason', '')} |")
        lines.append("")

    if result["blocked"]:
        lines.append("## Заблокировано / Blocked")
        lines.append("")
        lines.append("| Local path | Reason |")
        lines.append("| --- | --- |")
        for item in result["blocked"]:
            lines.append(f"| `{item['local_path']}` | {item.get('reason', '')} |")
        lines.append("")

    if result["errors"]:
        lines.append("## Ошибки")
        lines.append("")
        for item in result["errors"]:
            lines.append(f"- ⚠ `{item.get('local_path', 'N/A')}`: {item.get('error', str(item))}")
        lines.append("")

    if result.get("metadata_baseline_path"):
        lines.append("## Metadata Baseline")
        lines.append("")
        lines.append(f"- **Путь:** `{result['metadata_baseline_path']}`")
        lines.append(f"- **Формат:** P1-совместимый `core_sync_state.yml`")
        lines.append(f"- **Записанных entries:** {summary['executed']}")
        lines.append("")

    lines.append("## Что сознательно НЕ сделано в P3.2")
    lines.append("")
    lines.append("- ❌ Ни один content managed file не изменён.")
    lines.append("- ❌ absent_candidate не восстановлены.")
    lines.append("- ❌ local variants не backfill-нуты автоматически.")
    lines.append("- ❌ Auto-merge не выполнялся.")
    lines.append("- ❌ Force-overwrite не выполнялся.")
    lines.append("- ❌ Full migration engine не запускался.")
    lines.append("- ❌ Protected/project-specific/runtime-history paths не тронуты.")
    lines.append("")

    lines.append("## Что оставлено на следующие P3 chunks")
    lines.append("")
    lines.append("- Backfill absent_candidate (восстановление отсутствующих managed files).")
    lines.append("- Обработка local variants (human review + selective adoption).")
    lines.append("- Full migration/adoption engine.")
    lines.append("- Интеграция с P2 apply logic после появления P1 baseline.")
    lines.append("")

    lines.append("## Verification")
    lines.append("")
    lines.append(f"- [ ] Выполнено metadata backfill: {summary['executed']}")
    lines.append(f"- [ ] Пропущено (drifted): {summary['skipped_content_drifted']}")
    lines.append(f"- [ ] Пропущено (protected): {summary['skipped_protected_path']}")
    lines.append(f"- [ ] Пропущено (absent): {summary['skipped_absent_candidate']}")
    lines.append(f"- [ ] Content managed files НЕ изменены.")
    lines.append("- [ ] P3.1 assessment mode не сломан.")
    lines.append("- [ ] P2.1 dry-run не сломан.")
    lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.2), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_backfill_results_json(result: dict, target: Path) -> str:
    """Записывает machine-readable P3.2 backfill execution JSON. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "backfill_execution_results.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "target": result["target"],
        "source": result["source"],
        "plan_source": result["plan_source"],
        "plan_candidate_count": result["plan_candidate_count"],
        "summary": result["summary"],
        "assumptions": result["assumptions"],
        "executed": result["executed"],
        "skipped": result["skipped"],
        "blocked": result["blocked"],
        "errors": result["errors"],
        "metadata_baseline_path": result.get("metadata_baseline_path"),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


# ---------------------------------------------------------------------------
# P3.5: Local Variant Decision Execution — human-approved decision
#       для keep_local_as_adapted / defer_manual_resolution
# ---------------------------------------------------------------------------

def _validate_decision_plan(plan_path: Path) -> dict:
    """Загружает и валидирует P3.5 decision plan.

    Decision plan должен быть human-approved JSON со структурой:
    - plan_type: "p3_5_local_variant_decision"
    - schema: "ai-workflow-core.p3_5_decision_plan"
    - schema_version: "0.1"
    - review_artifact_run_id: str (ссылка на P3.4 run)
    - decisions: list[dict] с local_path, decision_type, rationale

    Допустимые decision_type: keep_local_as_adapted, defer_manual_resolution.

    Возвращает dict с полями valid, plan, errors.
    """
    errors: list[str] = []

    if not plan_path.is_file():
        return {"valid": False, "plan": None, "errors": [f"Файл плана не найден: {plan_path}"]}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "plan": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    # Provenance: P3.5 decision plan
    schema = plan.get("schema", "")
    if schema != "ai-workflow-core.p3_5_decision_plan":
        errors.append(
            f"schema должен быть 'ai-workflow-core.p3_5_decision_plan', "
            f"получено: '{schema}'."
        )

    plan_type = plan.get("plan_type", "")
    if plan_type != "p3_5_local_variant_decision":
        errors.append(
            f"plan_type должен быть 'p3_5_local_variant_decision', "
            f"получено: '{plan_type}'."
        )

    if not plan.get("schema_version"):
        errors.append("Отсутствует schema_version")

    if not plan.get("review_artifact_run_id"):
        errors.append("Отсутствует review_artifact_run_id (ссылка на P3.4 review)")

    decisions = plan.get("decisions")
    if not isinstance(decisions, list) or len(decisions) == 0:
        errors.append("Поле 'decisions' отсутствует, пусто или не является списком")
        return {"valid": False, "plan": None, "errors": errors}

    allowed_decision_types = {"keep_local_as_adapted", "defer_manual_resolution"}
    for i, d in enumerate(decisions):
        if not isinstance(d, dict):
            errors.append(f"decisions[{i}]: не является dict, получено {type(d).__name__}")
            continue
        if "local_path" not in d:
            errors.append(f"decisions[{i}]: отсутствует обязательное поле 'local_path'")
        dt = d.get("decision_type", "")
        if dt not in allowed_decision_types:
            errors.append(
                f"decisions[{i}]: недопустимый decision_type '{dt}'. "
                f"Разрешены только: {', '.join(sorted(allowed_decision_types))}"
            )
        if not d.get("rationale"):
            errors.append(f"decisions[{i}]: отсутствует rationale")

    if errors:
        return {"valid": False, "plan": None, "errors": errors}

    return {"valid": True, "plan": plan, "errors": []}


def _validate_review_artifact(artifact_path: Path) -> dict:
    """Загружает и валидирует P3.4 local_variant_review.json.

    Проверяет:
    - schema == "ai-workflow-core.p3_4_local_variant_review"
    - executed_performed == True
    - reviewed является списком
    - каждый reviewed item имеет local_path, local_checksum, central_checksum, outcome

    Возвращает dict с полями valid, artifact, errors.
    """
    errors: list[str] = []

    if not artifact_path.is_file():
        return {"valid": False, "artifact": None, "errors": [f"Файл review artifact не найден: {artifact_path}"]}

    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "artifact": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    schema = artifact.get("schema", "")
    if schema != "ai-workflow-core.p3_4_local_variant_review":
        errors.append(
            f"schema должен быть 'ai-workflow-core.p3_4_local_variant_review', "
            f"получено: '{schema}'."
        )

    if artifact.get("execution_performed") is not True:
        errors.append("execution_performed должен быть True (P3.4 review был выполнен)")

    reviewed = artifact.get("reviewed")
    if not isinstance(reviewed, list):
        errors.append("Поле 'reviewed' отсутствует или не является списком")
        return {"valid": False, "artifact": None, "errors": errors}

    for i, r in enumerate(reviewed):
        if not isinstance(r, dict):
            errors.append(f"reviewed[{i}]: не является dict")
            continue
        for f in ("local_path", "local_checksum", "central_checksum", "outcome"):
            if f not in r:
                errors.append(f"reviewed[{i}]: отсутствует обязательное поле '{f}'")
        if r.get("outcome") != "reviewed":
            errors.append(
                f"reviewed[{i}]: outcome должен быть 'reviewed', "
                f"получено '{r.get('outcome')}'"
            )

    if not artifact.get("run_id"):
        errors.append("Отсутствует run_id в review artifact")

    if errors:
        return {"valid": False, "artifact": None, "errors": errors}

    return {"valid": True, "artifact": artifact, "errors": []}


def _can_execute_decision(
    item: dict,
    review_entry: dict,
    decision_type: str,
    target: Path,
    source_root: Path,
) -> tuple[bool, str]:
    """Валидирует narrow execution contract для P3.5 decision.

    Handoff 0144 narrow contract — execute ТОЛЬКО если одновременно верно:
    - item пришёл из accepted P3.4 review artifact
    - review entry имеет outcome 'reviewed'
    - decision_type = keep_local_as_adapted или defer_manual_resolution
    - local path не protected/project-specific/runtime-history
    - local path не AGENTS.md
    - local file всё ещё существует
    - central source file всё ещё существует
    - local checksum на момент execution совпадает с checksum из P3.4 review
    - central checksum на момент execution совпадает с checksum из P3.4 review

    Returns (allowed, reason).
    """
    local_path = item.get("local_path", "")

    # --- Decision type gate ---
    if decision_type not in ("keep_local_as_adapted", "defer_manual_resolution"):
        return False, f"Запрещённый decision_type: '{decision_type}'. P3.5 допускает только keep_local_as_adapted и defer_manual_resolution."

    # --- Review outcome gate ---
    if review_entry.get("outcome") != "reviewed":
        return False, f"Review entry outcome не 'reviewed': '{review_entry.get('outcome')}'."

    # --- Protection checks ---
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path, решение запрещено."

    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл — решение запрещено."

    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл — решение запрещено."

    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория — решение запрещено."

    # --- Runtime file existence re-checks ---
    local_file = target / local_path
    if not local_file.is_file():
        return False, "Локальный файл отсутствует на момент execution."

    central_file = source_root / local_path
    if not central_file.is_file():
        return False, "Central source file отсутствует на момент execution."

    # --- Runtime checksum re-checks (provenance from P3.4) ---
    current_local_cs = _compute_checksum(local_file)
    current_central_cs = _compute_checksum(central_file)

    p34_local_cs = review_entry.get("local_checksum", "")
    p34_central_cs = review_entry.get("central_checksum", "")

    if current_local_cs != p34_local_cs:
        return False, (
            f"Local checksum изменился после P3.4 review: "
            f"P3.4={p34_local_cs[:12]}..., current={current_local_cs[:12]}..."
        )

    if current_central_cs != p34_central_cs:
        return False, (
            f"Central checksum изменился после P3.4 review: "
            f"P3.4={p34_central_cs[:12]}..., current={current_central_cs[:12]}..."
        )

    return True, ""


def _run_local_variant_decision_execution(
    target: Path,
    source_root: Path,
    review_artifact: dict,
    decision_plan: dict,
) -> dict:
    """Выполняет P3.5 local variant decision execution.

    Принимает P3.4 local_variant_review.json и human-approved decision plan.
    Для каждого decision:
    - находит соответствующий review entry в P3.4 artifact
    - проверяет narrow execution contract через _can_execute_decision
    - при успехе для keep_local_as_adapted: фиксирует adapted decision в metadata
    - при успехе для defer_manual_resolution: no-op
    - при неуспехе: кладёт в skipped/blocked с reason code

    НЕ overwrite-ит существующие локальные файлы.
    НЕ auto-merge-ит.
    Записывает metadata/state только для keep_local_as_adapted.

    Возвращает result dict.
    """
    run_id = _get_run_id()
    decisions = decision_plan.get("decisions", [])
    reviewed_entries = review_artifact.get("reviewed", [])

    # Build lookup by local_path
    review_lookup: dict[str, dict] = {}
    for r in reviewed_entries:
        lp = r.get("local_path", "")
        if lp:
            review_lookup[lp] = r

    # --- Provenance cross-check: decision plan MUST reference the same review run ---
    plan_review_run_id = decision_plan.get("review_artifact_run_id", "")
    actual_review_run_id = review_artifact.get("run_id", "")
    if plan_review_run_id != actual_review_run_id:
        # Early blocked: весь decision plan не соответствует этому review artifact
        run_id = _get_run_id()
        return {
            "run_id": run_id,
            "mode": "local_variant_decision_execution",
            "outcome": "P3.5_blocked_provenance_mismatch",
            "schema": "ai-workflow-core.p3_5_decision_execution",
            "schema_version": "0.1",
            "execution_performed": False,
            "writes_performed": False,
            "target": str(target),
            "source": str(source_root),
            "review_artifact_run_id": actual_review_run_id,
            "decision_plan_total": len(decisions),
            "assumptions": [
                "P3.5 provenance check: decision_plan.review_artifact_run_id MUST match review_artifact.run_id",
            ],
            "summary": {
                "total_decisions": len(decisions),
                "executed_keep_local_as_adapted": 0,
                "executed_defer_manual_resolution": 0,
                "skipped_not_in_review": 0,
                "skipped_checksum_drift_local": 0,
                "skipped_checksum_drift_central": 0,
                "skipped_protected_path": 0,
                "skipped_local_missing": 0,
                "skipped_central_missing": 0,
                "skipped_other": 0,
                "blocked_forbidden_decision_type": 0,
                "blocked_provenance_mismatch": len(decisions),
                "blocked_other": 0,
                "errors": 0,
            },
            "executed": [],
            "skipped": [],
            "blocked": [
                {
                    "local_path": "ALL",
                    "decision_type": "N/A",
                    "reason": (
                        f"Provenance mismatch: decision_plan.review_artifact_run_id="
                        f"'{plan_review_run_id}' не совпадает с review_artifact.run_id="
                        f"'{actual_review_run_id}'. Decision plan предназначен для "
                        f"другого P3.4 review run."
                    ),
                    "outcome": "blocked_provenance_mismatch",
                }
            ],
            "errors": [],
            "metadata_baseline_path": "",
        }

    result: dict = {
        "run_id": run_id,
        "mode": "local_variant_decision_execution",
        "outcome": "P3.5_local_variant_decision_execution",
        "schema": "ai-workflow-core.p3_5_decision_execution",
        "schema_version": "0.1",
        "execution_performed": True,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "review_artifact_run_id": review_artifact.get("run_id", "unknown"),
        "decision_plan_total": len(decisions),
        "assumptions": [
            "P3.5 работает из consumer repo working tree",
            "Decision plan — human-approved (передан через --decision-plan)",
            "Review artifact — accepted P3.4 local_variant_review.json",
            "Каждый decision перепроверяется: outcome, checksums, protection, existence",
            "Existing local files НЕ overwrite-ятся",
            "Central content НЕ применяется",
            "Auto-merge НЕ выполняется",
            "Только keep_local_as_adapted и defer_manual_resolution допускаются",
            "Запрещённые decision types (overwrite_with_central, merge, delete) — blocked",
        ],
        "summary": {
            "total_decisions": len(decisions),
            "executed_keep_local_as_adapted": 0,
            "executed_defer_manual_resolution": 0,
            "skipped_not_in_review": 0,
            "skipped_checksum_drift_local": 0,
            "skipped_checksum_drift_central": 0,
            "skipped_protected_path": 0,
            "skipped_local_missing": 0,
            "skipped_central_missing": 0,
            "skipped_other": 0,
            "blocked_forbidden_decision_type": 0,
            "blocked_provenance_mismatch": 0,
            "blocked_other": 0,
            "errors": 0,
        },
        "executed": [],
        "skipped": [],
        "blocked": [],
        "errors": [],
        "metadata_baseline_path": "",
    }

    executed: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []
    adapted_entries: list[dict] = []

    for decision in decisions:
        local_path = decision.get("local_path", "<unknown>")
        decision_type = decision.get("decision_type", "")
        rationale = decision.get("rationale", "")

        # Find matching review entry
        review_entry = review_lookup.get(local_path)
        if review_entry is None:
            skipped.append({
                "local_path": local_path,
                "decision_type": decision_type,
                "reason": "Путь не найден в reviewed entries P3.4 review artifact.",
                "outcome": "skipped_not_in_review",
            })
            result["summary"]["skipped_not_in_review"] += 1
            continue

        # Check for forbidden decision types early
        forbidden_types = {
            "overwrite_with_central", "merge_local_and_central",
            "delete_local_file", "adopt_central_silently",
        }
        if decision_type in forbidden_types:
            blocked.append({
                "local_path": local_path,
                "decision_type": decision_type,
                "reason": f"Запрещённый decision_type для P3.5: '{decision_type}'. "
                          f"Разрешены только keep_local_as_adapted и defer_manual_resolution.",
                "outcome": "blocked_forbidden_decision_type",
            })
            result["summary"]["blocked_forbidden_decision_type"] += 1
            continue

        # Narrow contract validation
        allowed, reason = _can_execute_decision(
            decision, review_entry, decision_type, target, source_root
        )

        if not allowed:
            # Categorize skip/block reason
            if "checksum изменился" in reason.lower() or "checksum drift" in reason.lower():
                if "local" in reason.lower():
                    outcome = "skipped_checksum_drift_local"
                    result["summary"]["skipped_checksum_drift_local"] += 1
                else:
                    outcome = "skipped_checksum_drift_central"
                    result["summary"]["skipped_checksum_drift_central"] += 1
            elif "protected" in reason.lower() or "project-specific" in reason.lower() or "runtime" in reason.lower():
                outcome = "skipped_protected_path"
                result["summary"]["skipped_protected_path"] += 1
            elif "локальный файл отсутствует" in reason.lower():
                outcome = "skipped_local_missing"
                result["summary"]["skipped_local_missing"] += 1
            elif "central source file отсутствует" in reason.lower():
                outcome = "skipped_central_missing"
                result["summary"]["skipped_central_missing"] += 1
            elif "запрещённый" in reason.lower() or "forbidden" in reason.lower():
                outcome = "blocked_forbidden_decision_type"
                result["summary"]["blocked_forbidden_decision_type"] += 1
            elif "outcome не 'reviewed'" in reason.lower():
                outcome = "blocked_other"
                result["summary"]["blocked_other"] += 1
            else:
                outcome = "skipped_other"
                result["summary"]["skipped_other"] += 1

            if "blocked" in outcome:
                blocked.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "reason": reason,
                    "outcome": outcome,
                })
            else:
                skipped.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "reason": reason,
                    "outcome": outcome,
                })
            continue

        # --- Execute decision ---
        if decision_type == "keep_local_as_adapted":
            try:
                local_file = target / local_path
                central_file = source_root / local_path
                current_local_cs = _compute_checksum(local_file)
                current_central_cs = _compute_checksum(central_file)

                exec_entry = {
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "rationale": rationale,
                    "local_checksum": current_local_cs,
                    "central_checksum": current_central_cs,
                    "p34_local_checksum": review_entry.get("local_checksum", ""),
                    "p34_central_checksum": review_entry.get("central_checksum", ""),
                    "outcome": "executed_keep_local_as_adapted",
                    "detail": (
                        "Локальный файл оставлен как adapted/project-owned. "
                        "Central версия НЕ применена. "
                        "Metadata/state зафиксирован."
                    ),
                }
                executed.append(exec_entry)
                adapted_entries.append(exec_entry)
                result["summary"]["executed_keep_local_as_adapted"] += 1
                result["writes_performed"] = True  # metadata write
            except Exception as e:
                errors.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "error": str(e),
                    "outcome": "execution_error",
                })
                result["summary"]["errors"] += 1

        elif decision_type == "defer_manual_resolution":
            exec_entry = {
                "local_path": local_path,
                "decision_type": decision_type,
                "rationale": rationale,
                "outcome": "executed_defer_manual_resolution",
                "detail": "Решение отложено. Никакие файлы или metadata не изменены.",
            }
            executed.append(exec_entry)
            result["summary"]["executed_defer_manual_resolution"] += 1

    result["executed"] = executed
    result["skipped"] = skipped
    result["blocked"] = blocked
    result["errors"] = errors

    # --- Record adapted metadata if any keep_local_as_adapted ---
    if adapted_entries:
        metadata_path = _record_adapted_decision_metadata(
            adapted_entries, target, source_root, run_id, review_artifact
        )
        result["metadata_baseline_path"] = metadata_path

    return result


def _record_adapted_decision_metadata(
    adapted_entries: list[dict],
    target: Path,
    source_root: Path,
    run_id: str,
    review_artifact: dict,
) -> str:
    """Записывает или обновляет metadata/state для adapted/local-authority решений.

    Если core_sync_state.yml уже существует, обновляет его узко:
    - добавляет adapted_files блок
    - не ломает managed_files
    - не трогает checksums ранее принятых clean/backfill/restore paths

    Если baseline отсутствует, создаёт минимальный P1-совместимый metadata file
    с явным указанием, что это только adapted decisions, а не полный managed baseline.

    Возвращает путь к записанному файлу.
    """
    metadata_path = target / P1_METADATA_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo_name = target.resolve().name
    review_run_id = review_artifact.get("run_id", "unknown")

    if metadata_path.is_file():
        # --- Update existing baseline ---
        existing = metadata_path.read_text(encoding="utf-8")

        # Build adapted_files block as YAML fragment
        adapted_block_lines = [
            "# P3.5 adapted_files — local files kept as project-owned / adapted",
            f"# Decision run ID: {run_id}",
            f"# Based on P3.4 review: {review_run_id}",
            f"adapted_files:",
        ]
        for e in adapted_entries:
            lp = e["local_path"]
            lcs = e.get("local_checksum", "")
            ccs = e.get("central_checksum", "")
            adapted_block_lines.append(f"  - path: \"{lp}\"")
            adapted_block_lines.append(f"    status: keep_local_as_adapted")
            adapted_block_lines.append(f"    adapted_at: \"{now_iso}\"")
            adapted_block_lines.append(f"    local_checksum: \"{lcs}\"")
            adapted_block_lines.append(f"    central_checksum: \"{ccs}\"")
            adapted_block_lines.append(f"    p3_5_run_id: \"{run_id}\"")

        adapted_block = "\n".join(adapted_block_lines)

        # Check if adapted_files: already exists — if yes, replace that section
        if "\nadapted_files:" in existing:
            # Strip from "adapted_files:" to end of file (or next top-level key)
            idx = existing.index("\nadapted_files:")
            # Keep everything before the adapted_files: line
            prefix = existing[:idx].rstrip("\n")
            new_content = prefix + "\n\n" + adapted_block + "\n"
        else:
            new_content = existing.rstrip("\n") + "\n\n" + adapted_block + "\n"

        metadata_path.write_text(new_content, encoding="utf-8")
    else:
        # --- Create minimal P3.5-only metadata baseline ---
        lines = [
            "# P1 Bootstrap Metadata — создан P3.5 local variant decision execution",
            "# ⚠ Это МИНИМАЛЬНЫЙ metadata file только для adapted/local-authority решений.",
            "# ⚠ managed_files намеренно пуст — baseline НЕ притворяется, будто все",
            "#   managed files уже baseline-нуты.",
            f"# Decision run ID: {run_id}",
            f"# Based on P3.4 review: {review_run_id}",
            f"schema_version: \"0.1\"",
            f"sync_direction: \"central-to-consumer\"",
            f"bootstrap_package: \"p3_5_minimal_adapted\"",
            f"bootstrap_mode: \"p3_5_local_variant_decision_execution\"",
            f"project_name: \"{repo_name}\"",
            f"created_at: \"{now_iso}\"",
            f"last_sync_at: \"{now_iso}\"",
            "",
            "canonical_source:",
            f"  repo: \"{source_root.resolve().name}\"",
            f"  url: \"file:///{source_root.resolve().as_posix()}\"",
            f"  revision: \"local\"",
            "",
            "materialized_from:",
            f"  path: \"{source_root.resolve().as_posix()}\"",
            f"  repo: \"{source_root.resolve().name}\"",
            "",
            "# managed_files намеренно пуст — baseline только для adapted решений",
            "managed_files: []",
            "",
            "# P3.5 adapted_files — local files kept as project-owned / adapted",
            "adapted_files:",
        ]
        for e in adapted_entries:
            lp = e["local_path"]
            lcs = e.get("local_checksum", "")
            ccs = e.get("central_checksum", "")
            lines.append(f"  - path: \"{lp}\"")
            lines.append(f"    status: keep_local_as_adapted")
            lines.append(f"    adapted_at: \"{now_iso}\"")
            lines.append(f"    local_checksum: \"{lcs}\"")
            lines.append(f"    central_checksum: \"{ccs}\"")
            lines.append(f"    p3_5_run_id: \"{run_id}\"")

        content = "\n".join(lines) + "\n"
        metadata_path.write_text(content, encoding="utf-8")

    return str(metadata_path)


def _write_decision_execution_report(result: dict, target: Path) -> str:
    """Записывает human-readable P3.5 decision execution report. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "local_variant_decision_execution_report.md"

    summary = result["summary"]

    lines = [
        "# P3.5 Local Variant Decision Execution Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (human-approved decision для local_variant cases)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **P3.4 Review Run ID:** `{result['review_artifact_run_id']}`",
        "",
        "## Executive Summary",
        "",
        f"P3.5 decision execution обработал {summary['total_decisions']} human-approved решений.",
        f"- **keep_local_as_adapted:** {summary['executed_keep_local_as_adapted']} исполнено",
        f"- **defer_manual_resolution:** {summary['executed_defer_manual_resolution']} исполнено (no-op)",
        f"- **skipped:** {sum(summary[k] for k in summary if k.startswith('skipped_'))}",
        f"- **blocked:** {sum(summary[k] for k in summary if k.startswith('blocked_'))}",
        f"- **errors:** {summary['errors']}",
        "",
        "## Assumptions",
        "",
    ]
    for a in result.get("assumptions", []):
        lines.append(f"- {a}")

    lines.append("")
    lines.append("## Executed Decisions")
    lines.append("")

    if result["executed"]:
        lines.append("| local_path | decision_type | outcome | detail |")
        lines.append("| --- | --- | --- | --- |")
        for e in result["executed"]:
            lines.append(
                f"| `{e['local_path']}` | {e['decision_type']} | {e['outcome']} | "
                f"{e.get('detail', e.get('rationale', ''))} |"
            )
    else:
        lines.append("*Нет исполненных решений.*")

    lines.append("")

    if result["skipped"]:
        lines.append("## Skipped Items")
        lines.append("")
        lines.append("| local_path | decision_type | reason |")
        lines.append("| --- | --- | --- |")
        for s in result["skipped"]:
            lines.append(f"| `{s['local_path']}` | {s.get('decision_type', '-')} | {s['reason']} |")
        lines.append("")

    if result["blocked"]:
        lines.append("## Blocked Items")
        lines.append("")
        lines.append("| local_path | decision_type | reason |")
        lines.append("| --- | --- | --- |")
        for b in result["blocked"]:
            lines.append(f"| `{b['local_path']}` | {b.get('decision_type', '-')} | {b['reason']} |")
        lines.append("")

    if result["errors"]:
        lines.append("## Errors")
        lines.append("")
        for e in result["errors"]:
            lines.append(f"- `{e.get('local_path', 'N/A')}`: {e.get('error', str(e))}")
        lines.append("")

    lines.append("## Что сознательно НЕ сделано в P3.5")
    lines.append("")
    lines.append("- ❌ Auto-merge local и central")
    lines.append("- ❌ Overwrite существующих local files")
    lines.append("- ❌ Применение central content в рабочий файл")
    lines.append("- ❌ Full conflict-resolution engine")
    lines.append("- ❌ Broad metadata redesign")
    lines.append("- ❌ Docs/P4 не обновлены")

    lines.append("")
    if result.get("metadata_baseline_path"):
        lines.append(f"## Metadata Baseline")
        lines.append(f"")
        lines.append(f"Записан/обновлён: `{result['metadata_baseline_path']}`")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.5), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_decision_execution_json(result: dict, target: Path) -> str:
    """Записывает machine-readable P3.5 decision execution JSON. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "local_variant_decision_execution.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "target": result["target"],
        "source": result["source"],
        "review_artifact_run_id": result["review_artifact_run_id"],
        "decision_plan_total": result["decision_plan_total"],
        "summary": result["summary"],
        "assumptions": result["assumptions"],
        "executed": result["executed"],
        "skipped": result["skipped"],
        "blocked": result["blocked"],
        "errors": result["errors"],
        "metadata_baseline_path": result.get("metadata_baseline_path", ""),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


# ---------------------------------------------------------------------------
# P3.6: Local Variant Resolution Pack — единый resolution
#       для keep_local_as_adapted / defer_manual_resolution /
#       adopt_central_with_overwrite_explicit
# ---------------------------------------------------------------------------

def _validate_p36_resolution_plan(plan_path: Path) -> dict:
    """Загружает и валидирует P3.6 resolution plan.

    Resolution plan должен быть human-approved JSON со структурой:
    - plan_type: "p3_6_local_variant_resolution"
    - schema: "ai-workflow-core.p3_6_resolution_plan"
    - schema_version: "0.1"
    - review_artifact_run_id: str (ссылка на P3.4 run)
    - decisions: list[dict] с local_path, decision_type, rationale

    Допустимые decision_type:
    - keep_local_as_adapted
    - defer_manual_resolution
    - adopt_central_with_overwrite_explicit

    Возвращает dict с полями valid, plan, errors.
    """
    errors: list[str] = []

    if not plan_path.is_file():
        return {"valid": False, "plan": None, "errors": [f"Файл плана не найден: {plan_path}"]}

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "plan": None, "errors": [f"Ошибка чтения JSON: {e}"]}

    # Provenance: P3.6 resolution plan
    schema = plan.get("schema", "")
    if not isinstance(schema, str) or schema != "ai-workflow-core.p3_6_resolution_plan":
        errors.append(
            f"schema должен быть 'ai-workflow-core.p3_6_resolution_plan', "
            f"получено: '{schema}'."
        )

    plan_type = plan.get("plan_type", "")
    if not isinstance(plan_type, str) or plan_type != "p3_6_local_variant_resolution":
        errors.append(
            f"plan_type должен быть 'p3_6_local_variant_resolution', "
            f"получено: '{plan_type}'."
        )

    schema_version = plan.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        errors.append("schema_version должен быть непустой строкой")

    review_artifact_run_id = plan.get("review_artifact_run_id")
    if not isinstance(review_artifact_run_id, str) or not review_artifact_run_id:
        errors.append(
            "review_artifact_run_id должен быть непустой строкой (ссылка на P3.4 review)"
        )

    decisions = plan.get("decisions")
    if not isinstance(decisions, list) or len(decisions) == 0:
        errors.append("Поле 'decisions' отсутствует, пусто или не является списком")
        return {"valid": False, "plan": None, "errors": errors}

    allowed_decision_types = {
        "keep_local_as_adapted",
        "defer_manual_resolution",
        "adopt_central_with_overwrite_explicit",
    }
    for i, d in enumerate(decisions):
        if not isinstance(d, dict):
            errors.append(f"decisions[{i}]: не является dict, получено {type(d).__name__}")
            continue
        lp = d.get("local_path")
        if not isinstance(lp, str) or not lp:
            errors.append(
                f"decisions[{i}]: 'local_path' должен быть непустой строкой, "
                f"получено {type(lp).__name__}: {repr(lp)}"
            )
        dt = d.get("decision_type", "")
        if not isinstance(dt, str) or dt not in allowed_decision_types:
            errors.append(
                f"decisions[{i}]: недопустимый decision_type '{dt}'. "
                f"Разрешены только: {', '.join(sorted(allowed_decision_types))}"
            )
        rationale = d.get("rationale")
        if not isinstance(rationale, str) or not rationale:
            errors.append(
                f"decisions[{i}]: 'rationale' должен быть непустой строкой, "
                f"получено {type(rationale).__name__}: {repr(rationale)}"
            )

    if errors:
        return {"valid": False, "plan": None, "errors": errors}

    return {"valid": True, "plan": plan, "errors": []}


def _can_execute_p36_resolution(
    item: dict,
    review_entry: dict,
    decision_type: str,
    target: Path,
    source_root: Path,
) -> tuple[bool, str]:
    """Валидирует narrow execution contract для P3.6 resolution.

    Handoff 0145 narrow contract — execute ТОЛЬКО если одновременно верно:
    - item пришёл из accepted P3.4 review artifact
    - review entry имеет outcome 'reviewed'
    - decision_type ∈ {keep_local_as_adapted, defer_manual_resolution,
                       adopt_central_with_overwrite_explicit}
    - local path не protected/project-specific/runtime-history
    - local path не AGENTS.md
    - local file всё ещё существует
    - central source file всё ещё существует
    - local checksum на момент execution совпадает с checksum из P3.4 review
    - central checksum на момент execution совпадает с checksum из P3.4 review

    Returns (allowed, reason).
    """
    local_path = item.get("local_path", "")

    # --- Decision type gate ---
    allowed_types = {
        "keep_local_as_adapted",
        "defer_manual_resolution",
        "adopt_central_with_overwrite_explicit",
    }
    if decision_type not in allowed_types:
        return False, (
            f"Запрещённый decision_type: '{decision_type}'. "
            f"P3.6 допускает только keep_local_as_adapted, "
            f"defer_manual_resolution и adopt_central_with_overwrite_explicit."
        )

    # --- Review outcome gate ---
    if review_entry.get("outcome") != "reviewed":
        return False, f"Review entry outcome не 'reviewed': '{review_entry.get('outcome')}'."

    # --- Protection checks ---
    if local_path == AGENTS_SEED:
        return False, "AGENTS.md: protected path, решение запрещено."

    for psf in PROJECT_SPECIFIC_FILES:
        if local_path == psf or local_path.startswith(psf + "/"):
            return False, "Project-specific файл — решение запрещено."

    for rhf in RUNTIME_HISTORY_FILES:
        if local_path == rhf:
            return False, "Runtime/history файл — решение запрещено."

    for rhd in RUNTIME_HISTORY_DIRS:
        if local_path.startswith(rhd + "/") or local_path == rhd:
            return False, "Runtime/history директория — решение запрещено."

    # --- Runtime file existence re-checks ---
    local_file = target / local_path
    if not local_file.is_file():
        return False, "Локальный файл отсутствует на момент execution."

    central_file = source_root / local_path
    if not central_file.is_file():
        return False, "Central source file отсутствует на момент execution."

    # --- Runtime checksum re-checks (provenance from P3.4) ---
    current_local_cs = _compute_checksum(local_file)
    current_central_cs = _compute_checksum(central_file)

    p34_local_cs = review_entry.get("local_checksum", "")
    p34_central_cs = review_entry.get("central_checksum", "")

    if current_local_cs != p34_local_cs:
        return False, (
            f"Local checksum изменился после P3.4 review: "
            f"P3.4={p34_local_cs[:12]}..., current={current_local_cs[:12]}..."
        )

    if current_central_cs != p34_central_cs:
        return False, (
            f"Central checksum изменился после P3.4 review: "
            f"P3.4={p34_central_cs[:12]}..., current={current_central_cs[:12]}..."
        )

    return True, ""


def _run_p36_local_variant_resolution(
    target: Path,
    source_root: Path,
    review_artifact: dict,
    resolution_plan: dict,
) -> dict:
    """Выполняет P3.6 local variant resolution.

    Принимает P3.4 local_variant_review.json и human-approved resolution plan.
    Для каждого decision:
    - находит соответствующий review entry в P3.4 artifact
    - проверяет narrow execution contract через _can_execute_p36_resolution
    - keep_local_as_adapted: фиксирует adapted decision в metadata
    - defer_manual_resolution: no-op
    - adopt_central_with_overwrite_explicit:
      * повторно проверяет provenance/checksums
      * overwrite-ит локальный файл central контентом
      * пересчитывает local checksum
      * обновляет metadata: путь переходит из adapted в central-managed

    НЕ auto-merge-ит.
    НЕ overwrite-ит без explicit decision.
    НЕ трогает protected/project-specific/runtime-history paths.

    Возвращает result dict.
    """
    run_id = _get_run_id()
    decisions = resolution_plan.get("decisions", [])
    reviewed_entries = review_artifact.get("reviewed", [])

    # Build lookup by local_path
    review_lookup: dict[str, dict] = {}
    for r in reviewed_entries:
        lp = r.get("local_path", "")
        if lp:
            review_lookup[lp] = r

    # --- Provenance cross-check: resolution plan MUST reference the same review run ---
    plan_review_run_id = resolution_plan.get("review_artifact_run_id", "")
    actual_review_run_id = review_artifact.get("run_id", "")
    if plan_review_run_id != actual_review_run_id:
        run_id = _get_run_id()
        return {
            "run_id": run_id,
            "mode": "local_variant_resolution",
            "outcome": "P3.6_blocked_provenance_mismatch",
            "schema": "ai-workflow-core.p3_6_resolution_execution",
            "schema_version": "0.1",
            "execution_performed": False,
            "writes_performed": False,
            "target": str(target),
            "source": str(source_root),
            "review_artifact_run_id": actual_review_run_id,
            "decision_plan_total": len(decisions),
            "assumptions": [
                "P3.6 provenance check: resolution_plan.review_artifact_run_id MUST match review_artifact.run_id",
            ],
            "summary": {
                "total_decisions": len(decisions),
                "executed_keep_local_as_adapted": 0,
                "executed_defer_manual_resolution": 0,
                "executed_adopt_central_with_overwrite": 0,
                "skipped_not_in_review": 0,
                "skipped_checksum_drift_local": 0,
                "skipped_checksum_drift_central": 0,
                "skipped_protected_path": 0,
                "skipped_local_missing": 0,
                "skipped_central_missing": 0,
                "skipped_other": 0,
                "blocked_forbidden_decision_type": 0,
                "blocked_provenance_mismatch": len(decisions),
                "blocked_other": 0,
                "errors": 0,
            },
            "executed": [],
            "skipped": [],
            "blocked": [
                {
                    "local_path": "ALL",
                    "decision_type": "N/A",
                    "reason": (
                        f"Provenance mismatch: resolution_plan.review_artifact_run_id="
                        f"'{plan_review_run_id}' не совпадает с review_artifact.run_id="
                        f"'{actual_review_run_id}'. Resolution plan предназначен для "
                        f"другого P3.4 review run."
                    ),
                    "outcome": "blocked_provenance_mismatch",
                }
            ],
            "errors": [],
            "metadata_baseline_path": "",
        }

    result: dict = {
        "run_id": run_id,
        "mode": "local_variant_resolution",
        "outcome": "P3.6_local_variant_resolution",
        "schema": "ai-workflow-core.p3_6_resolution_execution",
        "schema_version": "0.1",
        "execution_performed": True,
        "writes_performed": False,
        "target": str(target),
        "source": str(source_root),
        "review_artifact_run_id": review_artifact.get("run_id", "unknown"),
        "decision_plan_total": len(decisions),
        "assumptions": [
            "P3.6 работает из consumer repo working tree",
            "Resolution plan — human-approved (передан через --resolution-plan)",
            "Review artifact — accepted P3.4 local_variant_review.json",
            "Каждый decision перепроверяется: outcome, checksums, protection, existence",
            "adopt_central_with_overwrite_explicit: overwrite только после повторной проверки",
            "adopt_central_with_overwrite_explicit: только для явно выбранных путей",
            "keep_local_as_adapted: local content не трогается",
            "defer_manual_resolution: no-op",
            "Auto-merge НЕ выполняется",
        ],
        "summary": {
            "total_decisions": len(decisions),
            "executed_keep_local_as_adapted": 0,
            "executed_defer_manual_resolution": 0,
            "executed_adopt_central_with_overwrite": 0,
            "skipped_not_in_review": 0,
            "skipped_checksum_drift_local": 0,
            "skipped_checksum_drift_central": 0,
            "skipped_protected_path": 0,
            "skipped_local_missing": 0,
            "skipped_central_missing": 0,
            "skipped_other": 0,
            "blocked_forbidden_decision_type": 0,
            "blocked_provenance_mismatch": 0,
            "blocked_other": 0,
            "errors": 0,
        },
        "executed": [],
        "skipped": [],
        "blocked": [],
        "errors": [],
        "metadata_baseline_path": "",
    }

    executed: list[dict] = []
    skipped: list[dict] = []
    blocked: list[dict] = []
    errors: list[dict] = []
    adapted_entries: list[dict] = []
    adopt_entries: list[dict] = []

    for decision in decisions:
        local_path = decision.get("local_path", "<unknown>")
        decision_type = decision.get("decision_type", "")
        rationale = decision.get("rationale", "")

        # Find matching review entry
        review_entry = review_lookup.get(local_path)
        if review_entry is None:
            skipped.append({
                "local_path": local_path,
                "decision_type": decision_type,
                "reason": "Путь не найден в reviewed entries P3.4 review artifact.",
                "outcome": "skipped_not_in_review",
            })
            result["summary"]["skipped_not_in_review"] += 1
            continue

        # Check for forbidden decision types early
        forbidden_types = {
            "overwrite_with_central", "merge_local_and_central",
            "delete_local_file", "adopt_central_silently",
        }
        if decision_type in forbidden_types:
            blocked.append({
                "local_path": local_path,
                "decision_type": decision_type,
                "reason": f"Запрещённый decision_type для P3.6: '{decision_type}'. "
                          f"Разрешены: keep_local_as_adapted, defer_manual_resolution, "
                          f"adopt_central_with_overwrite_explicit.",
                "outcome": "blocked_forbidden_decision_type",
            })
            result["summary"]["blocked_forbidden_decision_type"] += 1
            continue

        # Narrow contract validation
        allowed, reason = _can_execute_p36_resolution(
            decision, review_entry, decision_type, target, source_root
        )

        if not allowed:
            # Categorize skip/block reason
            if "checksum изменился" in reason.lower() or "checksum drift" in reason.lower():
                if "local" in reason.lower():
                    outcome = "skipped_checksum_drift_local"
                    result["summary"]["skipped_checksum_drift_local"] += 1
                else:
                    outcome = "skipped_checksum_drift_central"
                    result["summary"]["skipped_checksum_drift_central"] += 1
            elif "protected" in reason.lower() or "project-specific" in reason.lower() or "runtime" in reason.lower():
                outcome = "skipped_protected_path"
                result["summary"]["skipped_protected_path"] += 1
            elif "локальный файл отсутствует" in reason.lower():
                outcome = "skipped_local_missing"
                result["summary"]["skipped_local_missing"] += 1
            elif "central source file отсутствует" in reason.lower():
                outcome = "skipped_central_missing"
                result["summary"]["skipped_central_missing"] += 1
            elif "запрещённый" in reason.lower() or "forbidden" in reason.lower():
                outcome = "blocked_forbidden_decision_type"
                result["summary"]["blocked_forbidden_decision_type"] += 1
            elif "outcome не 'reviewed'" in reason.lower():
                outcome = "blocked_other"
                result["summary"]["blocked_other"] += 1
            else:
                outcome = "skipped_other"
                result["summary"]["skipped_other"] += 1

            if "blocked" in outcome:
                blocked.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "reason": reason,
                    "outcome": outcome,
                })
            else:
                skipped.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "reason": reason,
                    "outcome": outcome,
                })
            continue

        # --- Execute decision ---
        if decision_type == "keep_local_as_adapted":
            try:
                local_file = target / local_path
                central_file = source_root / local_path
                current_local_cs = _compute_checksum(local_file)
                current_central_cs = _compute_checksum(central_file)

                exec_entry = {
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "rationale": rationale,
                    "local_checksum": current_local_cs,
                    "central_checksum": current_central_cs,
                    "p34_local_checksum": review_entry.get("local_checksum", ""),
                    "p34_central_checksum": review_entry.get("central_checksum", ""),
                    "outcome": "executed_keep_local_as_adapted",
                    "detail": (
                        "Локальный файл оставлен как adapted/project-owned. "
                        "Central версия НЕ применена. "
                        "Metadata/state зафиксирован."
                    ),
                }
                executed.append(exec_entry)
                adapted_entries.append(exec_entry)
                result["summary"]["executed_keep_local_as_adapted"] += 1
                result["writes_performed"] = True  # metadata write
            except Exception as e:
                errors.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "error": str(e),
                    "outcome": "execution_error",
                })
                result["summary"]["errors"] += 1

        elif decision_type == "defer_manual_resolution":
            exec_entry = {
                "local_path": local_path,
                "decision_type": decision_type,
                "rationale": rationale,
                "outcome": "executed_defer_manual_resolution",
                "detail": "Решение отложено. Никакие файлы или metadata не изменены.",
            }
            executed.append(exec_entry)
            result["summary"]["executed_defer_manual_resolution"] += 1

        elif decision_type == "adopt_central_with_overwrite_explicit":
            try:
                # --- Defense-in-depth: повторная проверка provenance/checksums перед overwrite ---
                local_file = target / local_path
                central_file = source_root / local_path

                # Re-verify file existence
                if not local_file.is_file():
                    errors.append({
                        "local_path": local_path,
                        "decision_type": decision_type,
                        "error": "Локальный файл исчез после guard check — overwrite отменён.",
                        "outcome": "execution_error",
                    })
                    result["summary"]["errors"] += 1
                    continue

                if not central_file.is_file():
                    errors.append({
                        "local_path": local_path,
                        "decision_type": decision_type,
                        "error": "Central source file исчез после guard check — overwrite отменён.",
                        "outcome": "execution_error",
                    })
                    result["summary"]["errors"] += 1
                    continue

                # Re-verify checksums (defense-in-depth)
                pre_overwrite_local_cs = _compute_checksum(local_file)
                pre_overwrite_central_cs = _compute_checksum(central_file)

                p34_local_cs = review_entry.get("local_checksum", "")
                p34_central_cs = review_entry.get("central_checksum", "")

                if pre_overwrite_local_cs != p34_local_cs:
                    errors.append({
                        "local_path": local_path,
                        "decision_type": decision_type,
                        "error": (
                            f"Local checksum изменился перед overwrite: "
                            f"P3.4={p34_local_cs[:12]}..., "
                            f"pre_overwrite={pre_overwrite_local_cs[:12]}..."
                        ),
                        "outcome": "execution_error",
                    })
                    result["summary"]["errors"] += 1
                    continue

                if pre_overwrite_central_cs != p34_central_cs:
                    errors.append({
                        "local_path": local_path,
                        "decision_type": decision_type,
                        "error": (
                            f"Central checksum изменился перед overwrite: "
                            f"P3.4={p34_central_cs[:12]}..., "
                            f"pre_overwrite={pre_overwrite_central_cs[:12]}..."
                        ),
                        "outcome": "execution_error",
                    })
                    result["summary"]["errors"] += 1
                    continue

                # --- Perform overwrite ---
                central_content = central_file.read_bytes()
                local_file.write_bytes(central_content)

                # --- Recompute post-overwrite checksum ---
                post_overwrite_local_cs = _compute_checksum(local_file)

                # Verify overwrite was successful: local checksum should now match central
                if post_overwrite_local_cs != pre_overwrite_central_cs:
                    errors.append({
                        "local_path": local_path,
                        "decision_type": decision_type,
                        "error": (
                            f"Overwrite verification failed: "
                            f"post_overwrite_local={post_overwrite_local_cs[:12]}..., "
                            f"central={pre_overwrite_central_cs[:12]}..."
                        ),
                        "outcome": "execution_error",
                    })
                    result["summary"]["errors"] += 1
                    continue

                exec_entry = {
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "rationale": rationale,
                    "pre_overwrite_local_checksum": pre_overwrite_local_cs,
                    "central_checksum": pre_overwrite_central_cs,
                    "post_overwrite_local_checksum": post_overwrite_local_cs,
                    "p34_local_checksum": p34_local_cs,
                    "p34_central_checksum": p34_central_cs,
                    "outcome": "executed_adopt_central_with_overwrite",
                    "detail": (
                        "Локальный файл перезаписан central контентом. "
                        "Local checksum теперь совпадает с central. "
                        "Metadata/state: путь переведён из adapted в central-managed."
                    ),
                }
                executed.append(exec_entry)
                adopt_entries.append(exec_entry)
                result["summary"]["executed_adopt_central_with_overwrite"] += 1
                result["writes_performed"] = True  # content overwrite + metadata write
            except Exception as e:
                errors.append({
                    "local_path": local_path,
                    "decision_type": decision_type,
                    "error": str(e),
                    "outcome": "execution_error",
                })
                result["summary"]["errors"] += 1

    result["executed"] = executed
    result["skipped"] = skipped
    result["blocked"] = blocked
    result["errors"] = errors

    # --- Record metadata if any keep or adopt decisions ---
    if adapted_entries or adopt_entries:
        metadata_path = _record_p36_resolution_metadata(
            adapted_entries, adopt_entries, target, source_root, run_id, review_artifact
        )
        result["metadata_baseline_path"] = metadata_path

    return result


def _record_p36_resolution_metadata(
    adapted_entries: list[dict],
    adopt_entries: list[dict],
    target: Path,
    source_root: Path,
    run_id: str,
    review_artifact: dict,
) -> str:
    """Записывает или обновляет metadata/state для P3.6 resolution.

    Для keep_local_as_adapted:
    - добавляет в adapted_files (как P3.5)

    Для adopt_central_with_overwrite_explicit:
    - удаляет путь из adapted_files (если был)
    - добавляет в managed_files с новым post-overwrite checksum
    - фиксирует статус central_managed

    Если core_sync_state.yml уже существует, обновляет его узко.
    Если baseline отсутствует, создаёт минимальный P1-совместимый metadata file.

    Возвращает путь к записанному файлу.
    """
    metadata_path = target / P1_METADATA_PATH
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo_name = target.resolve().name
    review_run_id = review_artifact.get("run_id", "unknown")

    if metadata_path.is_file():
        # --- Update existing baseline ---
        # Strategy: parse existing entries as full line-blocks (preserving all fields),
        # update only P3.6-affected entries, emit unchanged entries verbatim.
        existing = metadata_path.read_text(encoding="utf-8")

        # === Phase 1: Parse existing entries as path → list of original lines ===
        # managed_blocks: path → list of lines (including "- path:" line and sub-fields)
        # adapted_blocks: path → list of lines
        managed_blocks: dict[str, list[str]] = {}
        adapted_blocks: dict[str, list[str]] = {}

        def _parse_yaml_section(content: str, section_key: str) -> dict[str, list[str]]:
            """Parse a YAML section like managed_files: or adapted_files: into
            {path: [original lines for this entry]}."""
            result: dict[str, list[str]] = {}
            marker = f"\n{section_key}:"
            if marker not in content:
                return result
            idx = content.index(marker)
            # Skip past the section header line
            line_end = content.index("\n", idx + 1) if "\n" in content[idx + 1:] else len(content)
            section = content[line_end + 1:]
            current_path: str | None = None
            current_lines: list[str] = []
            for line in section.splitlines():
                stripped = line.strip()
                # Stop at the next top-level key even on compact YAML without
                # blank separators, otherwise entries from the next section can
                # bleed into the current one.
                if stripped and not line.startswith((" ", "\t")) and not stripped.startswith("#") and ":" in stripped:
                    if current_path is not None:
                        result[current_path] = current_lines
                        current_path = None
                        current_lines = []
                    break
                if stripped.startswith("- path:"):
                    # Save previous entry
                    if current_path is not None:
                        result[current_path] = current_lines
                    current_path = stripped.split('"')[1] if '"' in stripped else stripped.split(": ", 1)[1]
                    current_lines = [line]
                elif stripped.startswith("#"):
                    # Comment — attach to current entry if any, skip otherwise
                    if current_path is not None:
                        current_lines.append(line)
                elif not stripped:
                    # Empty line — section separator, end current entry
                    if current_path is not None:
                        result[current_path] = current_lines
                        current_path = None
                        current_lines = []
                elif current_path is not None:
                    # Sub-field of current entry (indented)
                    if line.startswith("  ") or line.startswith("\t"):
                        current_lines.append(line)
                    else:
                        # Non-indented line with value — section ended
                        result[current_path] = current_lines
                        current_path = None
                        current_lines = []
                elif stripped and ":" in stripped and not line.startswith(" "):
                    # Top-level key outside any entry — section ended
                    break
            # Save last entry
            if current_path is not None:
                result[current_path] = current_lines
            return result

        managed_blocks = _parse_yaml_section(existing, "managed_files")
        adapted_blocks = _parse_yaml_section(existing, "adapted_files")

        # === Phase 2: Update entries for P3.6-affected paths ===
        adopt_paths: set[str] = set()
        keep_paths: set[str] = set()

        for e in adopt_entries:
            lp = e.get("local_path", "")
            if lp:
                adopt_paths.add(lp)
                post_cs = e.get("post_overwrite_local_checksum", "")
                central_cs = e.get("central_checksum", "")
                managed_blocks[lp] = [
                    f'  - path: "{lp}"',
                    f"    status: central_managed",
                    f"    adopted_at: \"{now_iso}\"",
                    f"    checksum: \"{post_cs}\"",
                    f"    central_checksum: \"{central_cs}\"",
                    f"    p3_6_run_id: \"{run_id}\"",
                    f"    p3_4_review_run_id: \"{review_run_id}\"",
                ]
                # Remove from adapted if it was there
                adapted_blocks.pop(lp, None)

        for e in adapted_entries:
            lp = e.get("local_path", "")
            if lp:
                keep_paths.add(lp)
                lcs = e.get("local_checksum", "")
                ccs = e.get("central_checksum", "")
                adapted_blocks[lp] = [
                    f'  - path: "{lp}"',
                    f"    status: keep_local_as_adapted",
                    f"    adapted_at: \"{now_iso}\"",
                    f"    local_checksum: \"{lcs}\"",
                    f"    central_checksum: \"{ccs}\"",
                    f"    p3_6_run_id: \"{run_id}\"",
                ]

        # === Phase 3: Strip BOTH sections from new_content ===
        new_content = existing.rstrip("\n")

        while True:
            adapted_idx = new_content.index("\nadapted_files:") if "\nadapted_files:" in new_content else -1
            managed_idx = new_content.index("\nmanaged_files:") if "\nmanaged_files:" in new_content else -1

            if adapted_idx == -1 and managed_idx == -1:
                break

            if adapted_idx >= 0 and (managed_idx == -1 or adapted_idx < managed_idx):
                new_content = new_content[:adapted_idx].rstrip("\n")
            elif managed_idx >= 0:
                new_content = new_content[:managed_idx].rstrip("\n")

        # === Phase 4: Emit updated blocks preserving original fields ===
        if managed_blocks:
            lines = [
                "",
                "# P3.6 managed_files — central-controlled files (including adopted from local variants)",
                f"# Resolution run ID: {run_id}",
                f"# Based on P3.4 review: {review_run_id}",
                "managed_files:",
            ]
            for lp in sorted(managed_blocks.keys()):
                lines.extend(managed_blocks[lp])
            new_content = new_content.rstrip("\n") + "\n" + "\n".join(lines) + "\n"

        if adapted_blocks:
            lines = [
                "",
                "# P3.6 adapted_files — local files kept as project-owned / adapted",
                f"# Resolution run ID: {run_id}",
                f"# Based on P3.4 review: {review_run_id}",
                "adapted_files:",
            ]
            for lp in sorted(adapted_blocks.keys()):
                lines.extend(adapted_blocks[lp])
            new_content = new_content.rstrip("\n") + "\n" + "\n".join(lines) + "\n"

        metadata_path.write_text(new_content, encoding="utf-8")
    else:
        # --- Create minimal P3.6 metadata baseline ---
        lines = [
            "# P1 Bootstrap Metadata — создан P3.6 local variant resolution",
            "# ⚠ Это metadata file для adapted и central-managed решений.",
            f"# Resolution run ID: {run_id}",
            f"# Based on P3.4 review: {review_run_id}",
            "schema_version: \"0.1\"",
            "sync_direction: \"central-to-consumer\"",
            "bootstrap_package: \"p3_6_resolution\"",
            "bootstrap_mode: \"p3_6_local_variant_resolution\"",
            f"project_name: \"{repo_name}\"",
            f"created_at: \"{now_iso}\"",
            f"last_sync_at: \"{now_iso}\"",
            "",
            "canonical_source:",
            f"  repo: \"{source_root.resolve().name}\"",
            f"  url: \"file:///{source_root.resolve().as_posix()}\"",
            f"  revision: \"local\"",
            "",
            "materialized_from:",
            f"  path: \"{source_root.resolve().as_posix()}\"",
            f"  repo: \"{source_root.resolve().name}\"",
            "",
        ]

        # Managed files from adopt decisions
        adopt_paths: list[str] = []
        adopt_data: dict[str, dict] = {}
        for e in adopt_entries:
            lp = e.get("local_path", "")
            if lp:
                adopt_paths.append(lp)
                adopt_data[lp] = e

        if adopt_paths:
            lines.append("# P3.6 managed_files — central-controlled files (adopted from local variants)")
            lines.append("managed_files:")
            for lp in sorted(adopt_paths):
                lines.append(f'  - path: "{lp}"')
                if lp in adopt_data:
                    e = adopt_data[lp]
                    post_cs = e.get("post_overwrite_local_checksum", "")
                    central_cs = e.get("central_checksum", "")
                    lines.append(f"    status: central_managed")
                    lines.append(f"    adopted_at: \"{now_iso}\"")
                    lines.append(f"    checksum: \"{post_cs}\"")
                    lines.append(f"    central_checksum: \"{central_cs}\"")
                    lines.append(f"    p3_6_run_id: \"{run_id}\"")
                    lines.append(f"    p3_4_review_run_id: \"{review_run_id}\"")
            lines.append("")
        else:
            lines.append("# managed_files намеренно пуст — нет adopt решений")
            lines.append("managed_files: []")
            lines.append("")

        # Adapted files from keep decisions
        if adapted_entries:
            lines.append("# P3.6 adapted_files — local files kept as project-owned / adapted")
            lines.append("adapted_files:")
            for e in adapted_entries:
                lp = e["local_path"]
                lcs = e.get("local_checksum", "")
                ccs = e.get("central_checksum", "")
                lines.append(f'  - path: "{lp}"')
                lines.append(f"    status: keep_local_as_adapted")
                lines.append(f"    adapted_at: \"{now_iso}\"")
                lines.append(f"    local_checksum: \"{lcs}\"")
                lines.append(f"    central_checksum: \"{ccs}\"")
                lines.append(f"    p3_6_run_id: \"{run_id}\"")
            lines.append("")

        content = "\n".join(lines) + "\n"
        metadata_path.write_text(content, encoding="utf-8")

    return str(metadata_path)


def _write_p36_resolution_report(result: dict, target: Path) -> str:
    """Записывает human-readable P3.6 resolution execution report. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "local_variant_resolution_execution_report.md"

    summary = result["summary"]

    lines = [
        "# P3.6 Local Variant Resolution Execution Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- **Режим:** `{result['mode']}` (единый resolution для local_variant cases)",
        f"- **Target:** `{result['target']}`",
        f"- **Central source:** `{result['source']}`",
        f"- **P3.4 Review Run ID:** `{result['review_artifact_run_id']}`",
        "",
        "## Executive Summary",
        "",
        f"P3.6 resolution execution обработал {summary['total_decisions']} human-approved решений.",
        f"- **keep_local_as_adapted:** {summary['executed_keep_local_as_adapted']} исполнено",
        f"- **defer_manual_resolution:** {summary['executed_defer_manual_resolution']} исполнено (no-op)",
        f"- **adopt_central_with_overwrite:** {summary['executed_adopt_central_with_overwrite']} исполнено",
        f"- **skipped:** {sum(summary[k] for k in summary if k.startswith('skipped_'))}",
        f"- **blocked:** {sum(summary[k] for k in summary if k.startswith('blocked_'))}",
        f"- **errors:** {summary['errors']}",
        "",
        "## Assumptions",
        "",
    ]
    for a in result.get("assumptions", []):
        lines.append(f"- {a}")

    lines.append("")
    lines.append("## Executed Resolutions")
    lines.append("")

    if result["executed"]:
        lines.append("| local_path | decision_type | outcome | detail |")
        lines.append("| --- | --- | --- | --- |")
        for e in result["executed"]:
            detail = e.get('detail', e.get('rationale', ''))
            if len(detail) > 120:
                detail = detail[:117] + "..."
            lines.append(
                f"| `{e['local_path']}` | {e['decision_type']} | {e['outcome']} | "
                f"{detail} |"
            )
    else:
        lines.append("*Нет исполненных решений.*")

    lines.append("")

    if result["skipped"]:
        lines.append("## Skipped Items")
        lines.append("")
        lines.append("| local_path | decision_type | reason |")
        lines.append("| --- | --- | --- |")
        for s in result["skipped"]:
            lines.append(f"| `{s['local_path']}` | {s.get('decision_type', '-')} | {s['reason']} |")
        lines.append("")

    if result["blocked"]:
        lines.append("## Blocked Items")
        lines.append("")
        lines.append("| local_path | decision_type | reason |")
        lines.append("| --- | --- | --- |")
        for b in result["blocked"]:
            lines.append(f"| `{b['local_path']}` | {b.get('decision_type', '-')} | {b['reason']} |")
        lines.append("")

    if result["errors"]:
        lines.append("## Errors")
        lines.append("")
        for e in result["errors"]:
            lines.append(f"- `{e.get('local_path', 'N/A')}`: {e.get('error', str(e))}")
        lines.append("")

    lines.append("## Что сознательно НЕ сделано в P3.6")
    lines.append("")
    lines.append("- ❌ Auto-merge local и central")
    lines.append("- ❌ Overwrite без explicit human-approved decision")
    lines.append("- ❌ Массовый overwrite всех divergent files")
    lines.append("- ❌ Full conflict-resolution engine")
    lines.append("- ❌ Broad metadata redesign")
    lines.append("- ❌ Docs/P4 не обновлены")
    lines.append("- ❌ Protected/project-specific/runtime-history paths не тронуты")

    lines.append("")
    if result.get("metadata_baseline_path"):
        lines.append("## Metadata Baseline")
        lines.append("")
        lines.append(f"Записан/обновлён: `{result['metadata_baseline_path']}`")
        lines.append("")

    lines.append("---")
    lines.append(f"*Report сгенерирован `scripts/safe_sync_workflow.py` (P3.6), run_id: `{run_id}`.*")

    content = "\n".join(lines) + "\n"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def _write_p36_resolution_json(result: dict, target: Path) -> str:
    """Записывает machine-readable P3.6 resolution execution JSON. Возвращает путь."""
    run_id = result["run_id"]
    report_dir = target / ".ai" / "sync" / "runs" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "local_variant_resolution_execution.json"

    payload = {
        "schema": result["schema"],
        "schema_version": result["schema_version"],
        "run_id": result["run_id"],
        "mode": result["mode"],
        "execution_performed": result["execution_performed"],
        "writes_performed": result["writes_performed"],
        "target": result["target"],
        "source": result["source"],
        "review_artifact_run_id": result["review_artifact_run_id"],
        "decision_plan_total": result["decision_plan_total"],
        "summary": result["summary"],
        "assumptions": result["assumptions"],
        "executed": result["executed"],
        "skipped": result["skipped"],
        "blocked": result["blocked"],
        "errors": result["errors"],
        "metadata_baseline_path": result.get("metadata_baseline_path", ""),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=textwrap.dedent("""\
            P2: Metadata-Aware Safe Sync — dry-run (P2.1) + apply (P2.2 + P2.3).
            P3.1: Conservative Adoption Assessment — assessment-only для pre-P1 repos.
            P3.2: Metadata-Only Backfill Execution — controlled metadata backfill.
            P3.3: Absent Candidate Restore — восстановление missing managed files.
            P3.4: Local Variant Review — human-reviewed review для divergent local files.
            P3.5: Local Variant Decision Execution — human-approved decision для local_variant.
            P3.6: Local Variant Resolution Pack — единый resolution keep/defer/adopt.

            Dry-run (по умолчанию):
              Читает P1 bootstrap metadata, строит inventory managed files,
              считает local/central checksums, классифицирует managed-copy state,
              и пишет report-only artifacts. НЕ меняет managed files.

            Apply (--apply):
              Выполняет тот же classify, затем:
              - P2.2: обновляет stale_central_available файлы;
              - P2.3: safe restore local_missing, sidecar для local_edited/protected_agents,
                      blocked/manual-review для central_missing/metadata_missing.
              Не делает auto-merge/force-overwrite/migration.

            Adoption Assessment (--assess-adoption):
              Выполняет inventory + classification candidate managed paths
              для consumer repo БЕЗ P1 baseline metadata.
              Классифицирует adoption/backfill readiness.
              Пишет только report artifacts. НЕ меняет managed files.
              НЕ пишет P1 metadata. НЕ выполняет migration.
              Не требует P1 baseline и не падает при его отсутствии.

            Metadata-Only Backfill (--backfill-metadata):
              Принимает candidate_backfill_plan.json от P3.1,
              перепроверяет local-vs-central equality,
              выполняет metadata-only backfill для unmanaged_clean_match кандидатов.
              Пишет metadata baseline. НЕ меняет content managed files.
              НЕ восстанавливает absent_candidate. НЕ auto-merge-ит local variants.
              Требует --backfill-plan.

            Absent Candidate Restore (--restore-absent):
              Принимает adoption assessment или dedicated restore plan,
              валидирует narrow restore contract, отбирает только absent_candidate
              с exists_central=True, materialize-ит missing local file из central source.
              НЕ overwrite существующие локальные файлы. НЕ auto-merge local variants.
              Требует --restore-plan.

            Local Variant Review (--review-local-variant):
              Принимает adoption assessment из P3.1, отбирает unmanaged_local_variant
              items, собирает review data (checksums, reason codes, compare status).
              Сохраняет central sidecar/snapshot только внутри run-artifacts.
              НЕ overwrite локальные файлы. НЕ auto-merge. НЕ записывает metadata baseline.
              Требует --review-plan.

            Local Variant Decision Execution (--execute-local-variant-decision):
              Принимает P3.4 local_variant_review.json и human-approved decision plan.
              Допускает keep_local_as_adapted и defer_manual_resolution.
              НЕ overwrite локальные файлы. НЕ auto-merge. НЕ применяет central content.
              Требует --decision-plan и --review-artifact.

            Local Variant Resolution Pack (--execute-local-variant-resolution):
              Принимает P3.4 local_variant_review.json и human-approved P3.6 resolution plan.
              Допускает keep_local_as_adapted, defer_manual_resolution,
              adopt_central_with_overwrite_explicit (только для явно одобренных paths).
              После overwrite: пересчитывает checksum, обновляет metadata/state.
              Требует --resolution-plan и --review-artifact.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Путь к consumer repo (целевая директория).",
    )
    parser.add_argument(
        "--source",
        help="Путь к central source repo (ai-workflow-core или локальный клон). "
             "По умолчанию: корень текущего repo (ai-workflow-core). ",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Включить apply mode (P2.2 + P2.3): обновить stale_central_available, "
             "safe restore, sidecar, blocked/manual-review. "
             "Без этого флага — только dry-run (P2.1).",
    )
    parser.add_argument(
        "--assess-adoption",
        action="store_true",
        help="Включить P3.1 adoption assessment mode: inventory + classification "
             "candidate managed paths без P1 baseline metadata. Assessment-only, "
             "без изменения managed files и без записи P1 metadata. "
             "Взаимоисключающий с --apply и --backfill-metadata.",
    )
    parser.add_argument(
        "--backfill-metadata",
        action="store_true",
        help="Включить P3.2 metadata-only backfill mode: выполнить backfill "
             "из candidate_backfill_plan.json. Только metadata baseline, "
             "content managed files НЕ изменяются. "
             "Требует --backfill-plan. "
             "Взаимоисключающий с --apply и --assess-adoption.",
    )
    parser.add_argument(
        "--backfill-plan",
        help="Путь к candidate_backfill_plan.json (из P3.1) для P3.2 backfill. "
             "Требуется только с --backfill-metadata.",
    )
    parser.add_argument(
        "--restore-absent",
        action="store_true",
        help="Включить P3.3 absent candidate restore mode: восстановить только "
             "missing managed files (absent_candidate) из central source. "
             "НЕ overwrite существующие файлы. НЕ auto-merge local variants. "
             "Требует --restore-plan. "
             "Взаимоисключающий с --apply, --assess-adoption и --backfill-metadata.",
    )
    parser.add_argument(
        "--restore-plan",
        help="Путь к adoption_assessment.json (из P3.1) или dedicated restore plan "
             "для P3.3 absent restore. "
             "Требуется только с --restore-absent.",
    )
    parser.add_argument(
        "--review-local-variant",
        action="store_true",
        help="Включить P3.4 local variant review mode: собрать review data "
             "только для unmanaged_local_variant items из P3.1 assessment. "
             "Пишет review report + JSON + sidecar snapshots в run-artifacts. "
             "НЕ overwrite существующие файлы. НЕ auto-merge. НЕ записывает metadata baseline. "
             "Требует --review-plan. "
             "Взаимоисключающий с --apply, --assess-adoption, --backfill-metadata, "
             "--restore-absent и --execute-local-variant-decision.",
    )
    parser.add_argument(
        "--review-plan",
        help="Путь к adoption_assessment.json (из P3.1) для P3.4 local variant review. "
             "Требуется только с --review-local-variant.",
    )
    parser.add_argument(
        "--execute-local-variant-decision",
        action="store_true",
        help="Включить P3.5 local variant decision execution mode: исполнить "
             "human-approved решения для local_variant cases из P3.4 review. "
             "Допускает только keep_local_as_adapted и defer_manual_resolution. "
             "Пишет decision execution report + JSON. "
             "НЕ overwrite существующие файлы. НЕ auto-merge. НЕ применяет central content. "
             "Требует --decision-plan и --review-artifact. "
             "Взаимоисключающий с --apply, --assess-adoption, --backfill-metadata, "
             "--restore-absent и --review-local-variant.",
    )
    parser.add_argument(
        "--decision-plan",
        help="Путь к P3.5 decision plan (JSON) с human-approved решениями. "
             "Требуется только с --execute-local-variant-decision.",
    )
    parser.add_argument(
        "--review-artifact",
        help="Путь к P3.4 local_variant_review.json. "
             "Требуется с --execute-local-variant-decision или --execute-local-variant-resolution.",
    )
    parser.add_argument(
        "--execute-local-variant-resolution",
        action="store_true",
        help="Включить P3.6 local variant resolution mode: исполнить "
             "единый resolution pack для local_variant cases из P3.4 review. "
             "Допускает keep_local_as_adapted, defer_manual_resolution и "
             "adopt_central_with_overwrite_explicit. "
             "adopt_central_with_overwrite_explicit перезаписывает локальный файл "
             "central контентом ТОЛЬКО после повторной проверки provenance/checksums. "
             "Пишет resolution execution report + JSON. "
             "Требует --resolution-plan и --review-artifact. "
             "Взаимоисключающий с --apply, --assess-adoption, --backfill-metadata, "
             "--restore-absent, --review-local-variant и --execute-local-variant-decision.",
    )
    parser.add_argument(
        "--resolution-plan",
        help="Путь к P3.6 resolution plan (JSON) с human-approved решениями. "
             "Допустимые decision_type: keep_local_as_adapted, defer_manual_resolution, "
             "adopt_central_with_overwrite_explicit. "
             "Требуется только с --execute-local-variant-resolution.",
    )
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = _build_parser()
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    explicit_source = args.source is not None
    source_root = Path(args.source).expanduser().resolve() if explicit_source else _repo_root()

    if not target.exists() or not target.is_dir():
        print(f"ОШИБКА: target директория не существует: {target}", file=sys.stderr)
        sys.exit(1)

    if not source_root.exists() or not source_root.is_dir():
        print(f"ОШИБКА: source директория не существует: {source_root}", file=sys.stderr)
        sys.exit(1)

    # Guard: if running from a consumer-local copy without explicit --source,
    # the default _repo_root() points to the consumer repo which lacks core layout.
    if not explicit_source and not (source_root / "rules").is_dir():
        print(
            "ОШИБКА: этот скрипт запущен из consumer repo, а не из central core.",
            file=sys.stderr,
        )
        print(
            f"  Текущий repo ({source_root}) не содержит core layout (rules/, prompts/, bootstrap/).",
            file=sys.stderr,
        )
        print(
            "  Укажите явный путь к central core через --source:",
            file=sys.stderr,
        )
        print(
            "    python scripts/safe_sync_workflow.py --target <consumer-path> --source <путь-к-ai-workflow-core>",
            file=sys.stderr,
        )
        print(
            "  Либо запустите скрипт непосредственно из central core (ai-workflow-core).",
            file=sys.stderr,
        )
        sys.exit(1)

    # --apply, --assess-adoption, --backfill-metadata, --restore-absent, --review-local-variant,
    # --execute-local-variant-decision и --execute-local-variant-resolution взаимоисключающие
    mode_count = sum([args.apply, args.assess_adoption, args.backfill_metadata, args.restore_absent, args.review_local_variant, args.execute_local_variant_decision, args.execute_local_variant_resolution])
    if mode_count > 1:
        print(
            "ОШИБКА: --apply, --assess-adoption, --backfill-metadata, --restore-absent, "
            "--review-local-variant, --execute-local-variant-decision "
            "и --execute-local-variant-resolution "
            "взаимоисключающие. Выберите ровно один режим.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --backfill-metadata требует --backfill-plan
    if args.backfill_metadata and not args.backfill_plan:
        print(
            "ОШИБКА: --backfill-metadata требует --backfill-plan с путём "
            "к candidate_backfill_plan.json.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --restore-absent требует --restore-plan
    if args.restore_absent and not args.restore_plan:
        print(
            "ОШИБКА: --restore-absent требует --restore-plan с путём "
            "к adoption_assessment.json или dedicated restore plan.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --review-local-variant требует --review-plan
    if args.review_local_variant and not args.review_plan:
        print(
            "ОШИБКА: --review-local-variant требует --review-plan с путём "
            "к adoption_assessment.json из P3.1.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --execute-local-variant-decision требует --decision-plan и --review-artifact
    if args.execute_local_variant_decision:
        if not args.decision_plan:
            print(
                "ОШИБКА: --execute-local-variant-decision требует --decision-plan с путём "
                "к P3.5 decision plan JSON.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not args.review_artifact:
            print(
                "ОШИБКА: --execute-local-variant-decision требует --review-artifact с путём "
                "к P3.4 local_variant_review.json.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --execute-local-variant-resolution требует --resolution-plan и --review-artifact
    if args.execute_local_variant_resolution:
        if not args.resolution_plan:
            print(
                "ОШИБКА: --execute-local-variant-resolution требует --resolution-plan с путём "
                "к P3.6 resolution plan JSON.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not args.review_artifact:
            print(
                "ОШИБКА: --execute-local-variant-resolution требует --review-artifact с путём "
                "к P3.4 local_variant_review.json.",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.execute_local_variant_resolution:
        mode_label = "P3.6: Local Variant Resolution Pack — единый resolution для local_variant cases"
    elif args.execute_local_variant_decision:
        mode_label = "P3.5: Local Variant Decision Execution — human-approved decision для local_variant cases"
    elif args.review_local_variant:
        mode_label = "P3.4: Local Variant Review Paths — human-reviewed review для divergent local managed files"
    elif args.restore_absent:
        mode_label = "P3.3: Absent Candidate Restore — restore only missing managed files"
    elif args.backfill_metadata:
        mode_label = "P3.2: Metadata-Only Backfill Execution"
    elif args.assess_adoption:
        mode_label = "P3.1: Conservative Adoption Assessment — assessment-only"
    elif args.apply:
        mode_label = "P2.2+P2.3: Safe Sync Apply — limited update + safe review paths"
    else:
        mode_label = "P2.1: Safe Sync Dry-Run — report-only"

    print("=" * 60)
    print(mode_label)
    print("=" * 60)
    print(f"  Target:    {target}")
    print(f"  Source:    {source_root}")
    print()

    if args.execute_local_variant_resolution:
        # --- P3.6 Local Variant Resolution Pack mode ---
        resolution_plan_path = Path(args.resolution_plan).expanduser().resolve()
        review_artifact_path = Path(args.review_artifact).expanduser().resolve()

        # Validate resolution plan
        rp_validation = _validate_p36_resolution_plan(resolution_plan_path)
        if not rp_validation["valid"]:
            print(
                "ОШИБКА: невалидный resolution plan. "
                "P3.6 принимает только human-approved resolution plan JSON "
                "(schema=ai-workflow-core.p3_6_resolution_plan, plan_type=p3_6_local_variant_resolution).",
                file=sys.stderr,
            )
            for e in rp_validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        # Validate review artifact
        ra_validation = _validate_review_artifact(review_artifact_path)
        if not ra_validation["valid"]:
            print(
                "ОШИБКА: невалидный review artifact. "
                "P3.6 принимает только P3.4 local_variant_review.json "
                "(schema=ai-workflow-core.p3_4_local_variant_review).",
                file=sys.stderr,
            )
            for e in ra_validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        resolution_plan = rp_validation["plan"]
        review_artifact = ra_validation["artifact"]
        result = _run_p36_local_variant_resolution(
            target, source_root, review_artifact, resolution_plan
        )

        # Write artifacts
        resolution_report_path = _write_p36_resolution_report(result, target)
        resolution_json_path = _write_p36_resolution_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  P3.4 Review Run ID:  {result.get('review_artifact_run_id', 'unknown')}")
        print(f"  --- P3.6 Resolution Execution Results ---")
        print(f"  Total decisions in plan:         {summary['total_decisions']}")
        print(f"  Executed keep_local_as_adapted:   {summary['executed_keep_local_as_adapted']}")
        print(f"  Executed defer_manual_resolution: {summary['executed_defer_manual_resolution']}")
        print(f"  Executed adopt_central_overwrite: {summary['executed_adopt_central_with_overwrite']}")
        print(f"  Skipped (not in review):          {summary['skipped_not_in_review']}")
        print(f"  Skipped (local checksum drift):   {summary['skipped_checksum_drift_local']}")
        print(f"  Skipped (central checksum drift): {summary['skipped_checksum_drift_central']}")
        print(f"  Skipped (protected path):         {summary['skipped_protected_path']}")
        print(f"  Skipped (local missing):          {summary['skipped_local_missing']}")
        print(f"  Skipped (central missing):        {summary['skipped_central_missing']}")
        print(f"  Skipped (other):                  {summary['skipped_other']}")
        print(f"  Blocked (forbidden decision type):{summary['blocked_forbidden_decision_type']}")
        print(f"  Blocked (provenance mismatch):     {summary.get('blocked_provenance_mismatch', 0)}")
        print(f"  Blocked (other):                  {summary['blocked_other']}")
        print(f"  Errors:                           {summary['errors']}")

        if result["errors"]:
            print(f"  Errors list:")
            for e in result["errors"]:
                print(f"    - {e.get('local_path', 'N/A')}: {e.get('error', str(e))}")

        if result["executed"]:
            print()
            for e in result["executed"]:
                dt = e["decision_type"]
                lo = e["outcome"]
                icon = "✓"
                if "overwrite" in lo:
                    icon = "⚡"
                print(f"  {icon} P3.6 executed: {e['local_path']} ({dt} → {lo})")

        if result["skipped"]:
            print()
            for s in result["skipped"]:
                print(f"  → P3.6 skipped: {s['local_path']} ({s['outcome']})")

        if result["blocked"]:
            print()
            for b in result["blocked"]:
                print(f"  ✗ P3.6 blocked: {b['local_path']} ({b['outcome']})")

        print()
        print("Artifacts:")
        print(f"  Resolution execution report (MD):   {resolution_report_path}")
        print(f"  Resolution execution results (JSON): {resolution_json_path}")
        if result.get("metadata_baseline_path"):
            print(f"  Metadata baseline:                   {result['metadata_baseline_path']}")
        print()
        print("P3.6 Local Variant Resolution завершён.")
        print(f"Исполнено keep_local_as_adapted: {summary['executed_keep_local_as_adapted']}.")
        print(f"Исполнено defer_manual_resolution: {summary['executed_defer_manual_resolution']}.")
        print(f"Исполнено adopt_central_with_overwrite: {summary['executed_adopt_central_with_overwrite']}.")
        print("Auto-merge НЕ выполнялся.")
        if summary['executed_adopt_central_with_overwrite'] > 0:
            print("⚡ Локальные файлы перезаписаны central контентом (только явно выбранные).")
            print("⚡ Metadata: пути переведены из adapted в central-managed.")
        print()

        if result["errors"]:
            sys.exit(1)

    elif args.execute_local_variant_decision:
        # --- P3.5 Local Variant Decision Execution mode ---
        decision_plan_path = Path(args.decision_plan).expanduser().resolve()
        review_artifact_path = Path(args.review_artifact).expanduser().resolve()

        # Validate decision plan
        dp_validation = _validate_decision_plan(decision_plan_path)
        if not dp_validation["valid"]:
            print(
                "ОШИБКА: невалидный decision plan. "
                "P3.5 принимает только human-approved decision plan JSON "
                "(schema=ai-workflow-core.p3_5_decision_plan, plan_type=p3_5_local_variant_decision).",
                file=sys.stderr,
            )
            for e in dp_validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        # Validate review artifact
        ra_validation = _validate_review_artifact(review_artifact_path)
        if not ra_validation["valid"]:
            print(
                "ОШИБКА: невалидный review artifact. "
                "P3.5 принимает только P3.4 local_variant_review.json "
                "(schema=ai-workflow-core.p3_4_local_variant_review).",
                file=sys.stderr,
            )
            for e in ra_validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        decision_plan = dp_validation["plan"]
        review_artifact = ra_validation["artifact"]
        result = _run_local_variant_decision_execution(
            target, source_root, review_artifact, decision_plan
        )

        # Write artifacts
        decision_report_path = _write_decision_execution_report(result, target)
        decision_json_path = _write_decision_execution_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  P3.4 Review Run ID:  {result.get('review_artifact_run_id', 'unknown')}")
        print(f"  --- P3.5 Decision Execution Results ---")
        print(f"  Total decisions in plan:         {summary['total_decisions']}")
        print(f"  Executed keep_local_as_adapted:   {summary['executed_keep_local_as_adapted']}")
        print(f"  Executed defer_manual_resolution: {summary['executed_defer_manual_resolution']}")
        print(f"  Skipped (not in review):          {summary['skipped_not_in_review']}")
        print(f"  Skipped (local checksum drift):   {summary['skipped_checksum_drift_local']}")
        print(f"  Skipped (central checksum drift): {summary['skipped_checksum_drift_central']}")
        print(f"  Skipped (protected path):         {summary['skipped_protected_path']}")
        print(f"  Skipped (local missing):          {summary['skipped_local_missing']}")
        print(f"  Skipped (central missing):        {summary['skipped_central_missing']}")
        print(f"  Skipped (other):                  {summary['skipped_other']}")
        print(f"  Blocked (forbidden decision type):{summary['blocked_forbidden_decision_type']}")
        print(f"  Blocked (provenance mismatch):     {summary.get('blocked_provenance_mismatch', 0)}")
        print(f"  Blocked (other):                  {summary['blocked_other']}")
        print(f"  Errors:                           {summary['errors']}")

        if result["errors"]:
            print(f"  Errors list:")
            for e in result["errors"]:
                print(f"    - {e.get('local_path', 'N/A')}: {e.get('error', str(e))}")

        if result["executed"]:
            print()
            for e in result["executed"]:
                dt = e["decision_type"]
                lo = e["outcome"]
                print(f"  ✓ P3.5 executed: {e['local_path']} ({dt} → {lo})")

        if result["skipped"]:
            print()
            for s in result["skipped"]:
                print(f"  → P3.5 skipped: {s['local_path']} ({s['outcome']})")

        if result["blocked"]:
            print()
            for b in result["blocked"]:
                print(f"  ✗ P3.5 blocked: {b['local_path']} ({b['outcome']})")

        print()
        print("Artifacts:")
        print(f"  Decision execution report (MD):   {decision_report_path}")
        print(f"  Decision execution results (JSON): {decision_json_path}")
        if result.get("metadata_baseline_path"):
            print(f"  Metadata baseline:                 {result['metadata_baseline_path']}")
        print()
        print("P3.5 Local Variant Decision Execution завершён.")
        print(f"Исполнено keep_local_as_adapted: {summary['executed_keep_local_as_adapted']}.")
        print(f"Исполнено defer_manual_resolution: {summary['executed_defer_manual_resolution']}.")
        print("Existing local files НЕ overwrite-нуты.")
        print("Central content НЕ применён.")
        print("Auto-merge НЕ выполнялся.")
        print()
        print("⚠ Решение зафиксировано в metadata. Локальные файлы сохранены как adapted.")

        if result["errors"]:
            sys.exit(1)

    elif args.backfill_metadata:
        # --- P3.2 Metadata-Only Backfill mode ---
        plan_path = Path(args.backfill_plan).expanduser().resolve()
        validation = _validate_backfill_plan(plan_path)

        if not validation["valid"]:
            print(f"ОШИБКА: невалидный candidate_backfill_plan.json", file=sys.stderr)
            for e in validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        plan = validation["plan"]
        result = _run_backfill(target, source_root, plan)

        # Write artifacts
        backfill_report_path = _write_backfill_report(result, target)
        backfill_json_path = _write_backfill_results_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  Plan source:         {result.get('plan_source', 'unknown')}")
        print(f"  --- P3.2 Backfill Results ---")
        print(f"  Candidates in plan:          {summary['total_candidates_in_plan']}")
        print(f"  Executed (metadata backfill): {summary['executed']}")
        print(f"  Skipped (not clean match):    {summary['skipped_not_unmanaged_clean_match']}")
        print(f"  Skipped (absent candidate):   {summary['skipped_absent_candidate']}")
        print(f"  Skipped (content drifted):    {summary['skipped_content_drifted']}")
        print(f"  Skipped (protected path):     {summary['skipped_protected_path']}")
        print(f"  Skipped (other):              {summary['skipped_other']}")
        print(f"  Blocked:                      {summary['blocked']}")
        print(f"  Errors:                       {summary['errors']}")

        if result["errors"]:
            print(f"  Errors list:")
            for e in result["errors"]:
                print(f"    - {e.get('local_path', 'N/A')}: {e.get('error', str(e))}")

        print()
        print("Artifacts:")
        print(f"  Backfill report (MD):   {backfill_report_path}")
        print(f"  Backfill results (JSON): {backfill_json_path}")
        if result.get("metadata_baseline_path"):
            print(f"  Metadata baseline:      {result['metadata_baseline_path']}")
        print()
        print("P3.2 Metadata-Only Backfill завершён.")
        print(f"Metadata baseline записан для {summary['executed']} файлов.")
        print("Content managed files НЕ изменены.")
        print("absent_candidate, local variants, protected paths — не тронуты.")

        if result["errors"]:
            sys.exit(1)

    elif args.restore_absent:
        # --- P3.3 Absent Candidate Restore mode ---
        plan_path = Path(args.restore_plan).expanduser().resolve()

        validation = _validate_restore_plan(plan_path)

        if not validation["valid"]:
            print(
                "ОШИБКА: невалидный restore plan. "
                "P3.3 принимает только adoption_assessment.json из P3.1 "
                "(schema=ai-workflow-core.p3_1_adoption_assessment, mode=assessment_only).",
                file=sys.stderr,
            )
            for e in validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        plan = validation["plan"]
        result = _run_absent_restore(target, source_root, plan)

        # Write artifacts
        restore_report_path = _write_absent_restore_report(result, target)
        restore_json_path = _write_absent_restore_results_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  Plan source:         {result.get('plan_source', 'unknown')}")
        print(f"  --- P3.3 Absent Restore Results ---")
        print(f"  Total paths in plan:         {summary['total_candidates_in_plan']}")
        print(f"  Restored from central:        {summary['restored']}")
        print(f"  Skipped (not absent_candidate):{summary['skipped_not_absent_candidate']}")
        print(f"  Skipped (central missing):    {summary['skipped_central_missing_at_execution']}")
        print(f"  Skipped (local appeared):     {summary['skipped_local_appeared_before_execution']}")
        print(f"  Skipped (protected path):     {summary['skipped_protected_path']}")
        print(f"  Skipped (other):              {summary['skipped_other']}")
        print(f"  Blocked:                      {summary['blocked']}")
        print(f"  Errors:                       {summary['errors']}")

        if result["errors"]:
            print(f"  Errors list:")
            for e in result["errors"]:
                print(f"    - {e.get('local_path', 'N/A')}: {e.get('error', str(e))}")

        if result["restored"]:
            print()
            for r in result["restored"]:
                cm = "✓ checksum match" if r.get("checksum_match") else "✗ checksum mismatch"
                print(f"  ✓ P3.3 restored: {r['local_path']} ({cm})")

        print()
        print("Artifacts:")
        print(f"  Absent restore report (MD):   {restore_report_path}")
        print(f"  Absent restore results (JSON): {restore_json_path}")
        if result.get("metadata_baseline_path"):
            print(f"  Metadata baseline:            {result['metadata_baseline_path']}")
        print()
        print("P3.3 Absent Candidate Restore завершён.")
        print(f"Восстановлено файлов: {summary['restored']}.")
        print("Existing local files НЕ overwrite-нуты.")
        print("local_variant, protected paths — не тронуты.")
        print("Restore только absent_candidate с exists_central=True.")

        if result["errors"]:
            sys.exit(1)

    elif args.review_local_variant:
        # --- P3.4 Local Variant Review Paths mode ---
        plan_path = Path(args.review_plan).expanduser().resolve()

        validation = _validate_review_plan(plan_path)

        if not validation["valid"]:
            print(
                "ОШИБКА: невалидный review plan. "
                "P3.4 local variant review принимает только adoption_assessment.json из P3.1 "
                "(schema=ai-workflow-core.p3_1_adoption_assessment, mode=assessment_only).",
                file=sys.stderr,
            )
            for e in validation["errors"]:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        plan = validation["plan"]
        result = _run_local_variant_review(target, source_root, plan)

        # Write artifacts
        review_report_path = _write_local_variant_review_report(result, target)
        review_json_path = _write_local_variant_review_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  Plan source:         {result.get('plan_source', 'unknown')}")
        print(f"  --- P3.4 Local Variant Review Results ---")
        print(f"  Total paths in plan:         {summary['total_candidates_in_plan']}")
        print(f"  Reviewed (local_variant):     {summary['reviewed']}")
        print(f"  Skipped (not local_variant):  {summary['skipped_not_local_variant']}")
        print(f"  Skipped (identical content):  {summary['skipped_identical_content']}")
        print(f"  Skipped (central missing):    {summary['skipped_central_missing_at_execution']}")
        print(f"  Skipped (local missing):      {summary['skipped_local_missing_at_execution']}")
        print(f"  Skipped (protected path):     {summary['skipped_protected_path']}")
        print(f"  Skipped (other):              {summary['skipped_other']}")
        print(f"  Blocked:                      {summary['blocked']}")
        print(f"  Errors:                       {summary['errors']}")

        if result["errors"]:
            print(f"  Errors list:")
            for e in result["errors"]:
                print(f"    - {e.get('local_path', 'N/A')}: {e.get('error', str(e))}")

        if result["reviewed"]:
            print()
            for r in result["reviewed"]:
                cs = "✓ match" if r.get("checksums_match") else "✗ divergent"
                print(f"  ✓ P3.4 reviewed: {r['local_path']} ({cs})")

        print()
        print("Artifacts:")
        print(f"  Local variant review report (MD):   {review_report_path}")
        print(f"  Local variant review results (JSON): {review_json_path}")
        if result.get("sidecar_dir"):
            print(f"  Central sidecar snapshots:           {result['sidecar_dir']}")
        print()
        print("P3.4 Local Variant Review завершён.")
        print(f"Рассмотрено local_variant файлов: {summary['reviewed']}.")
        print("Existing local files НЕ overwrite-нуты.")
        print("Central snapshots сохранены только в run-artifacts.")
        print("Metadata baseline НЕ записан — конфликты не решены автоматически.")
        print("Требуется human review для каждого divergent файла.")
        print()
        print("⚠ Это review artifact, а не execution result. Никакие файлы не изменены.")

        if result["errors"]:
            sys.exit(1)

    elif args.assess_adoption:
        # --- P3.1 Adoption Assessment mode ---
        result = _run_adoption_assessment(target, source_root)

        # Write artifacts
        assessment_md_path = _write_adoption_assessment_md(result, target)
        assessment_json_path = _write_adoption_assessment_json(result, target)
        backfill_plan_path = _write_candidate_backfill_plan(result, target)

        # Summary output
        summary = result["summary"]
        ds = result["decision_summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  P1 metadata:         {'найден (игнорируется для P3.1)' if result['p1_metadata_found'] else 'НЕ НАЙДЕН (pre-P1 assessment)'}")
        print(f"  --- P3.1 Classification ---")
        print(f"  Total paths scanned: {summary['total_paths_scanned']}")
        print(f"  Unmanaged clean match:   {summary['unmanaged_clean_match']}")
        print(f"  Unmanaged local variant: {summary['unmanaged_local_variant']}")
        print(f"  Absent candidate:        {summary['absent_candidate']}")
        print(f"  Project owned/protected: {summary['project_owned_or_protected']}")
        print(f"  Unknown/unclassified:    {summary['unknown_unclassified']}")
        print(f"  --- Decision Buckets ---")
        print(f"  safe_to_consider_for_later_backfill: {ds['safe_to_consider_for_later_backfill']}")
        print(f"  manual_review_required:              {ds['manual_review_required']}")
        print(f"  excluded_from_backfill:              {ds['excluded_from_backfill']}")
        print(f"  insufficient_information:            {ds['insufficient_information']}")

        if result["errors"]:
            print(f"  Errors:              {len(result['errors'])}")
            for e in result["errors"]:
                print(f"    - {e}")

        print()
        print("Artifacts:")
        print(f"  Assessment report (MD):  {assessment_md_path}")
        print(f"  Assessment results (JSON): {assessment_json_path}")
        backfill_count = len([p for p in result["paths"]
                              if p["decision_bucket"] == "safe_to_consider_for_later_backfill"])
        if backfill_count > 0:
            print(f"  Candidate backfill plan:  {backfill_plan_path} ({backfill_count} кандидатов)")
        print()
        print("P3.1 Adoption Assessment завершён.")
        print("Managed files НЕ изменены. P1 metadata НЕ записана.")
        print("Writes performed: False. Execution performed: False.")
        print("Все candidate backfill планы — non-executable, требуют human approval.")

        if result["errors"]:
            sys.exit(1)

    elif args.apply:
        # --- P2.2 + P2.3 Apply mode ---
        result = _run_apply(target, source_root)

        p2_3_outcome = result.get("p2_3_outcome")

        # Write artifacts
        apply_report_path = _write_apply_report(
            result, result["apply_outcome"], target,
            result.get("p1_metadata_updated", False), p2_3_outcome,
        )
        apply_json_path = _write_apply_results_json(
            result, result["apply_outcome"], target, p2_3_outcome,
        )
        classification_path = _write_classification_json(result, target)
        inventory_path = _write_inventory_json(result, target)

        # Summary output
        dry_summary = result["summary"]
        apply_summary = result["apply_outcome"]["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  P1 metadata:         {'найден' if result['p1_metadata_found'] else 'НЕ НАЙДЕН'}")
        print(f"  --- Dry-run classification ---")
        print(f"  Managed scanned:     {dry_summary['managed_scanned']}")
        print(f"  Clean:               {dry_summary['clean']}")
        print(f"  Stale (update avail):{dry_summary['stale_central_available']}")
        print(f"  Local edited:        {dry_summary['local_edited']}")
        print(f"  Local missing:       {dry_summary['local_missing']}")
        print(f"  Protected (AGENTS):  {dry_summary['protected_agents']}")
        print(f"  Central missing:     {dry_summary['central_missing']}")
        print(f"  Metadata missing:    {dry_summary['metadata_missing']}")
        print(f"  --- P2.2 Apply results ---")
        print(f"  Updated:             {apply_summary['updated_count']}")
        print(f"  Blocked:             {apply_summary['blocked_count']}")
        print(f"  Skipped:             {apply_summary['skipped_count']}")
        print(f"  Errors:              {apply_summary['error_count']}")
        if p2_3_outcome is not None:
            p23_summary = p2_3_outcome["summary"]
            print(f"  --- P2.3 Safe Review Paths ---")
            print(f"  Restored (missing):  {p23_summary['restored_count']}")
            print(f"  Sidecars created:    {p23_summary['sidecars_created_count']}")
            print(f"  Blocked/manual rev:  {p23_summary['blocked_manual_review_count']}")
            print(f"  Errors:              {p23_summary['error_count']}")
        print(f"  P1 metadata updated: {'да' if result.get('p1_metadata_updated') else 'нет'}")

        if result["errors"]:
            print(f"  Dry-run errors:      {len(result['errors'])}")
            for e in result["errors"]:
                print(f"    - {e}")

        print()
        print("Artifacts:")
        print(f"  Apply report:     {apply_report_path}")
        print(f"  Apply results:    {apply_json_path}")
        print(f"  Classification:   {classification_path}")
        print(f"  Inventory:        {inventory_path}")
        if p2_3_outcome is not None and p2_3_outcome["sidecars_created"]:
            sidecar_dir = target / ".ai" / "sync" / "runs" / result["run_id"] / "sidecars"
            print(f"  Sidecars dir:     {sidecar_dir}")
        print()

        # Print outcome summary
        parts = []
        if apply_summary["updated_count"] > 0:
            parts.append(f"обновлено: {apply_summary['updated_count']}")
            files_updated = [u["local_path"] for u in result["apply_outcome"]["updated"]]
            for fu in files_updated:
                print(f"  ✓ P2.2 updated: {fu}")
        if p2_3_outcome is not None:
            if p2_3_outcome["summary"]["restored_count"] > 0:
                parts.append(f"восстановлено: {p2_3_outcome['summary']['restored_count']}")
                for r in p2_3_outcome["restored"]:
                    print(f"  ✓ P2.3 restored: {r['local_path']}")
            if p2_3_outcome["summary"]["sidecars_created_count"] > 0:
                parts.append(f"sidecar: {p2_3_outcome['summary']['sidecars_created_count']}")
                for s in p2_3_outcome["sidecars_created"]:
                    print(f"  📎 P2.3 sidecar: {s['local_path']} → {s['sidecar_path']}")
            if p2_3_outcome["summary"]["blocked_manual_review_count"] > 0:
                parts.append(f"blocked/manual-review: {p2_3_outcome['summary']['blocked_manual_review_count']}")
        if parts:
            print(f"\nApply завершён: {', '.join(parts)}.")
        else:
            print("\nApply завершён. Нет файлов для обработки (все clean или вне safe subset).")
        print()
        print("Local edited, protected и blocked файлы НЕ тронуты. Sidecar-ы созданы для review.")

        # Collect all error counts
        total_errors = apply_summary.get("error_count", 0)
        if p2_3_outcome is not None:
            total_errors += p2_3_outcome["summary"].get("error_count", 0)
        total_updated_restored = apply_summary["updated_count"]
        if p2_3_outcome is not None:
            total_updated_restored += p2_3_outcome["summary"]["restored_count"]

        # Fail if dry-run errors, apply errors, or metadata update failed after files were updated/restored
        has_metadata_failure = (
            total_updated_restored > 0
            and not result.get("p1_metadata_updated", True)
        )
        if result["errors"] or total_errors > 0 or has_metadata_failure:
            if has_metadata_failure and total_errors == 0:
                print("ОШИБКА: файлы обновлены/восстановлены, но P1 metadata не переписана.", file=sys.stderr)
            sys.exit(1)
    else:
        # --- P2.1 Dry-run mode (original) ---
        result = _run_dry_run(target, source_root)

        # Write artifacts
        report_path = _write_report(result, target)
        classification_path = _write_classification_json(result, target)
        inventory_path = _write_inventory_json(result, target)

        # Summary output
        summary = result["summary"]
        print(f"  Run ID:              {result['run_id']}")
        print(f"  P1 metadata:         {'найден' if result['p1_metadata_found'] else 'НЕ НАЙДЕН'}")
        print(f"  Managed scanned:     {summary['managed_scanned']}")
        print(f"  Clean:               {summary['clean']}")
        print(f"  Stale (update avail):{summary['stale_central_available']}")
        print(f"  Local edited:        {summary['local_edited']}")
        print(f"  Local missing:       {summary['local_missing']}")
        print(f"  Protected (AGENTS):  {summary['protected_agents']}")
        print(f"  OOS project:         {summary['out_of_scope_project_specific']}")
        print(f"  OOS runtime/history: {summary['out_of_scope_runtime_history']}")
        print(f"  Would update:        {summary['would_update_count']}")
        if result["errors"]:
            print(f"  Errors:              {len(result['errors'])}")
            for e in result["errors"]:
                print(f"    - {e}")

        print()
        print("Artifacts:")
        print(f"  Report:         {report_path}")
        print(f"  Classification: {classification_path}")
        print(f"  Inventory:      {inventory_path}")
        print()
        print("Dry-run завершён. Managed files НЕ изменены.")
        print("Для включения update mode используйте --apply.")

        if result["errors"]:
            sys.exit(1)


if __name__ == "__main__":
    main()

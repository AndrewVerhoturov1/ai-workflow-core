#!/usr/bin/env python3
"""
Published-artifact workflow для External Web Chat.

Использует `gh api` для взаимодействия с GitHub без clone.
Subcommands: verify-static, publish-task, show-links, cleanup-task.

CLI contract (CHUNK-008 canon):
    verify-static [--config PATH]
    publish-task --task-dir PATH [--main-file NAME] [--config PATH] [--manifest PATH]
    show-links --manifest PATH [--config PATH]
    cleanup-task --manifest PATH [--config PATH]
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import re
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = repo_root() / ".ai" / "external_chats" / "publisher_config.json"
    if not config_path.exists():
        print(f"ERROR: config not found: {config_path}")
        raise SystemExit(1)
    return json.loads(config_path.read_text(encoding="utf-8"))


def gh_api(method: str, endpoint: str, data: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Вызвать `gh api` с заданным методом, эндпоинтом и опциональным телом."""
    cmd = ["gh", "api", "--method", method, endpoint]
    if data is not None:
        cmd.extend(["--input", "-"])
    result = subprocess.run(
        cmd,
        input=json.dumps(data) if data else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if check and result.returncode != 0:
        print(f"ERROR: gh api failed for {method} {endpoint}")
        print(f"STDERR: {result.stderr}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
    return result


def gh_api_json(method: str, endpoint: str, data: dict | None = None) -> dict:
    """Вызвать `gh api`, вернуть распарсенный JSON или выйти с ошибкой."""
    result = gh_api(method, endpoint, data, check=False)
    if result.returncode != 0:
        print(f"ERROR: gh api call failed.")
        print(f"STDERR: {result.stderr}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        raise SystemExit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"ERROR: failed to parse JSON response: {exc}")
        print(f"STDOUT: {result.stdout}")
        raise SystemExit(1)


def build_urls(config: dict, path: str) -> tuple[str, str]:
    """Построить blob URL и raw URL для заданного пути в репозитории."""
    repo = config["repo"]
    branch = config["branch"]
    blob_url = f"https://github.com/{repo}/blob/{branch}/{path}"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    return blob_url, raw_url


def _extract_task_id(task_dir: Path) -> str:
    """Извлечь external_task_id из имени task-dir."""
    return task_dir.name


def _extract_attempt_id(task_dir: Path, main_file_name: str | None = None) -> str:
    """Извлечь external_attempt_id из имени основного handoff файла.
    
    Ожидаемый паттерн: <attempt_id>_handoff.md
    Если main_file_name задан, используем его; иначе ищем в task-dir.
    """
    if main_file_name:
        candidate = main_file_name
    else:
        # Ищем *_handoff.md в task-dir
        candidates = sorted(task_dir.glob("*_handoff.md"))
        if not candidates:
            print(f"ERROR: no *_handoff.md found in task-dir {task_dir}")
            raise SystemExit(1)
        if len(candidates) > 1:
            print(f"ERROR: multiple *_handoff.md files in task-dir {task_dir}: {[c.name for c in candidates]}")
            raise SystemExit(1)
        candidate = candidates[0].name

    # Извлекаем attempt_id: <attempt_id>_handoff.md → attempt_id
    m = re.match(r"^(.+)_handoff\.md$", candidate)
    if not m:
        print(f"ERROR: cannot extract attempt_id from filename: {candidate}")
        print("Expected pattern: <attempt_id>_handoff.md")
        raise SystemExit(1)
    return m.group(1)


def verify_static(config: dict) -> int:
    """Проверить доступность static manual и совпадение версии через корректный GitHub API flow."""
    repo = config["repo"]
    branch = config["branch"]
    static_path = config["static_manual_path"]
    expected_version = config["static_manual_version"]

    print(f"verify-static: checking {repo}/{branch}/{static_path}")

    # Шаг 1: получить содержимое файла через Contents API (корректный эндпоинт)
    contents_endpoint = f"repos/{repo}/contents/{static_path}?ref={branch}"
    try:
        file_info = gh_api_json("GET", contents_endpoint)
    except SystemExit:
        return 1

    sha = file_info.get("sha", "unknown")
    print(f"  SHA: {sha}")

    # Шаг 2: получить raw-содержимое для проверки версии
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{static_path}"
    result = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github.v3.raw", contents_endpoint],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: failed to fetch raw content for static manual")
        print(f"STDERR: {result.stderr}")
        return 1

    content = result.stdout
    if expected_version not in content:
        print(f"ERROR: expected version `{expected_version}` not found in static manual content.")
        print(f"First 200 chars: {content[:200]}")
        return 1

    # Шаг 3: проверить raw URL доступность (HEAD-запрос к raw.githubusercontent.com)
    raw_check = subprocess.run(
        ["gh", "api", "--method", "HEAD", raw_url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if raw_check.returncode != 0:
        print(f"WARN: raw URL not directly accessible via gh api HEAD: {raw_url}")
        print(f"  (это допустимо — raw.githubusercontent.com может не поддерживать HEAD через gh api)")
        print(f"  Blob URL: https://github.com/{repo}/blob/{branch}/{static_path}")
    else:
        print(f"  Raw URL accessible: {raw_url}")

    print(f"OK: static manual accessible. SHA: {sha}, version: {expected_version}")
    return 0


def publish_task(config: dict, task_dir: str, main_file: str | None = None, manifest_path: str | None = None) -> int:
    """Опубликовать локальную task dir в remote temp subtree.
    
    Определяет external_task_id по имени task-dir, external_attempt_id по main handoff filename.
    """
    repo = config["repo"]
    branch = config["branch"]
    temp_root = config["temp_root"]
    local_base = Path(task_dir).resolve()

    if not local_base.is_dir():
        print(f"ERROR: task dir not found: {local_base}")
        return 1

    # Извлечь task_id и attempt_id из task-dir
    task_id = _extract_task_id(local_base)
    attempt_id = _extract_attempt_id(local_base, main_file)

    remote_prefix = f"{temp_root}{task_id}/"
    print(f"publish-task: {local_base} -> {repo}/{branch}/{remote_prefix}")
    print(f"  external_task_id: {task_id}")
    print(f"  external_attempt_id: {attempt_id}")

    published_files: list[dict] = []
    main_handoff_relpath: str | None = None

    # Собрать все файлы для публикации
    local_files: list[Path] = []
    for fpath in sorted(local_base.rglob("*")):
        if fpath.is_file() and ".git" not in fpath.parts:
            local_files.append(fpath)

    if not local_files:
        print("ERROR: no files to publish in task dir")
        return 1

    for local_file in local_files:
        rel = local_file.relative_to(local_base).as_posix()
        remote_path = f"{remote_prefix}{rel}"
        content_bytes = local_file.read_bytes()
        content_b64 = base64.b64encode(content_bytes).decode("ascii")

        # Проверить, существует ли уже файл
        check_endpoint = f"repos/{repo}/contents/{remote_path}?ref={branch}"
        existing_sha: str | None = None
        check_result = gh_api("GET", check_endpoint, check=False)
        if check_result.returncode == 0:
            try:
                existing = json.loads(check_result.stdout)
                existing_sha = existing.get("sha")
            except json.JSONDecodeError:
                pass

        put_data = {
            "message": f"publish: {task_id}/{attempt_id} — {rel}",
            "content": content_b64,
            "branch": branch,
        }
        if existing_sha:
            put_data["sha"] = existing_sha

        put_endpoint = f"repos/{repo}/contents/{remote_path}"
        result = gh_api("PUT", put_endpoint, put_data, check=False)
        if result.returncode != 0:
            print(f"ERROR: failed to publish {remote_path}")
            print(f"STDERR: {result.stderr}")
            return 1

        try:
            resp = json.loads(result.stdout)
            file_sha = resp.get("content", {}).get("sha", "unknown")
        except json.JSONDecodeError:
            file_sha = "unknown"

        blob_url, raw_url = build_urls(config, remote_path)

        file_entry = {
            "repo_path": remote_path,
            "blob_url": blob_url,
            "raw_url": raw_url,
            "sha": file_sha,
        }
        published_files.append(file_entry)
        print(f"  published: {remote_path}")

        # Определить основной handoff
        if "_handoff.md" in rel and not main_handoff_relpath:
            main_handoff_relpath = remote_path

    # Построить manifest
    static_blob, static_raw = build_urls(config, config["static_manual_path"])
    manifest = {
        "repo": repo,
        "branch": branch,
        "temp_root": temp_root,
        "external_task_id": task_id,
        "external_attempt_id": attempt_id,
        "static_manual_version": config["static_manual_version"],
        "static_manual_url": static_blob,
        "static_manual_raw_url": static_raw,
        "main_handoff_relpath": main_handoff_relpath,
        "main_handoff_url": build_urls(config, main_handoff_relpath)[0] if main_handoff_relpath else None,
        "main_handoff_raw_url": build_urls(config, main_handoff_relpath)[1] if main_handoff_relpath else None,
        "attached_artifacts": [],
        "published_files": published_files,
    }

    # Записать manifest локально как sidecar: <task-dir>.publish-manifest.json
    if manifest_path:
        manifest_out = Path(manifest_path).resolve()
    else:
        # Sidecar: если task_dir = /path/to/EXT-0001, то manifest = /path/to/EXT-0001.publish-manifest.json
        manifest_out = local_base.parent / f"{local_base.name}.publish-manifest.json"
    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  manifest saved: {manifest_out}")

    return 0


def show_links(config: dict, manifest_path: str) -> int:
    """Показать ссылки из manifest."""
    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.exists():
        print(f"ERROR: manifest not found: {manifest_file}")
        print("Run publish-task first.")
        return 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    print(f"=== Published Links for {manifest['external_task_id']} ===")
    print(f"Repo: {manifest['repo']}")
    print(f"Branch: {manifest['branch']}")
    print(f"Static manual version: {manifest['static_manual_version']}")
    print()
    print("--- Static Manual ---")
    print(f"  Blob: {manifest['static_manual_url']}")
    print(f"  Raw:  {manifest['static_manual_raw_url']}")
    print()
    print("--- Task Bundle ---")
    print(f"  Task ID:    {manifest['external_task_id']}")
    print(f"  Attempt ID: {manifest['external_attempt_id']}")
    if manifest.get("main_handoff_url"):
        print(f"  Handoff Blob: {manifest['main_handoff_url']}")
    if manifest.get("main_handoff_raw_url"):
        print(f"  Handoff Raw:  {manifest['main_handoff_raw_url']}")
    print()
    print("--- Published Files ---")
    for pf in manifest.get("published_files", []):
        print(f"  {pf['repo_path']}")
        print(f"    Blob: {pf['blob_url']}")
        print(f"    Raw:  {pf['raw_url']}")
        print(f"    SHA:  {pf['sha']}")

    return 0


def cleanup_task(config: dict, manifest_path: str) -> int:
    """Удалить remote temp subtree для task_id на основе manifest.
    
    Перед удалением валидирует каждый candidate path:
    - path должен лежать строго внутри external-agent-tmp/<external_task_id>/
    - path не может совпадать со static_manual_path
    - при первом нарушении — ошибка без удаления.
    """
    repo = config["repo"]
    branch = config["branch"]
    temp_root = config["temp_root"]
    static_path = config["static_manual_path"]

    manifest_file = Path(manifest_path).resolve()
    if not manifest_file.exists():
        print(f"ERROR: manifest not found: {manifest_file}")
        return 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    task_id = manifest["external_task_id"]

    # Безопасность: проверить task_id
    if ".." in task_id or "/" in task_id or "\\" in task_id:
        print(f"ERROR: unsafe task_id in manifest: {task_id}")
        return 1

    expected_prefix = f"{temp_root}{task_id}/"

    # Безопасность: remote_prefix не должен совпадать со static manual
    if expected_prefix == static_path or expected_prefix.startswith(static_path.rstrip("/") + "/"):
        print(f"ERROR: cleanup prefix {expected_prefix} would affect static manual {static_path}")
        return 1

    if not expected_prefix.startswith(temp_root):
        print(f"ERROR: cleanup prefix {expected_prefix} is outside temp_root {temp_root}")
        return 1

    # Валидация каждого candidate path из manifest
    published_files = manifest.get("published_files", [])
    if not published_files:
        print(f"No files to delete for {task_id}")
        return 0

    for pf in published_files:
        repo_path = pf["repo_path"]

        # Проверка 1: path должен лежать строго внутри external-agent-tmp/<task_id>/
        if not repo_path.startswith(expected_prefix):
            print(f"ERROR: candidate path {repo_path} is outside subtree {expected_prefix}")
            print("cleanup aborted: no files deleted.")
            return 1

        # Проверка 2: path не может совпадать со static_manual_path
        if repo_path == static_path:
            print(f"ERROR: candidate path {repo_path} matches static_manual_path {static_path}")
            print("cleanup aborted: no files deleted.")
            return 1

    print(f"cleanup-task: deleting files for {task_id} from {repo}/{branch}/{expected_prefix}")

    # Удалить каждый файл
    for pf in published_files:
        remote_path = pf["repo_path"]

        # Получить SHA файла
        get_endpoint = f"repos/{repo}/contents/{remote_path}?ref={branch}"
        get_result = gh_api("GET", get_endpoint, check=False)
        if get_result.returncode != 0:
            print(f"  skip (not found): {remote_path}")
            continue

        try:
            file_info = json.loads(get_result.stdout)
            file_sha = file_info.get("sha")
        except json.JSONDecodeError:
            print(f"  skip (parse error): {remote_path}")
            continue

        if not file_sha:
            print(f"  skip (no sha): {remote_path}")
            continue

        delete_data = {
            "message": f"cleanup: {task_id} — remove {remote_path}",
            "sha": file_sha,
            "branch": branch,
        }
        del_endpoint = f"repos/{repo}/contents/{remote_path}"
        del_result = gh_api("DELETE", del_endpoint, delete_data, check=False)
        if del_result.returncode == 0:
            print(f"  deleted: {remote_path}")
        else:
            print(f"  ERROR deleting {remote_path}: {del_result.stderr}")

    print(f"cleanup-task: done for {task_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Published-artifact workflow для External Web Chat.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # verify-static [--config PATH]
    verify_parser = subparsers.add_parser("verify-static", help="Проверить доступность static manual и версию.")
    verify_parser.add_argument("--config", help="Путь к publisher_config.json (по умолчанию .ai/external_chats/publisher_config.json).")

    # publish-task --task-dir PATH [--main-file NAME] [--config PATH] [--manifest PATH]
    publish_parser = subparsers.add_parser("publish-task", help="Опубликовать локальную task dir.")
    publish_parser.add_argument("--task-dir", required=True, help="Путь к локальной task dir.")
    publish_parser.add_argument("--main-file", help="Имя основного handoff файла (по умолчанию <attempt_id>_handoff.md).")
    publish_parser.add_argument("--config", help="Путь к publisher_config.json.")
    publish_parser.add_argument("--manifest", help="Путь для выходного manifest (по умолчанию sidecar <task-dir>.publish-manifest.json).")

    # show-links --manifest PATH [--config PATH]
    show_parser = subparsers.add_parser("show-links", help="Показать ссылки из manifest.")
    show_parser.add_argument("--manifest", required=True, help="Путь к publish-manifest.json.")
    show_parser.add_argument("--config", help="Путь к publisher_config.json.")

    # cleanup-task --manifest PATH [--config PATH]
    cleanup_parser = subparsers.add_parser("cleanup-task", help="Удалить remote temp subtree.")
    cleanup_parser.add_argument("--manifest", required=True, help="Путь к publish-manifest.json.")
    cleanup_parser.add_argument("--config", help="Путь к publisher_config.json.")

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if getattr(args, "config", None) else None

    try:
        config = load_config(config_path)
    except SystemExit:
        return 1

    if args.command == "verify-static":
        return verify_static(config)
    elif args.command == "publish-task":
        return publish_task(config, args.task_dir, getattr(args, "main_file", None), getattr(args, "manifest", None))
    elif args.command == "show-links":
        return show_links(config, args.manifest)
    elif args.command == "cleanup-task":
        return cleanup_task(config, args.manifest)
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

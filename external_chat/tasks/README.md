# Task Bundle Contract (CHUNK-008)

Этот файл описывает local task bundle contract для published-artifact workflow External Web Chat.

## Task dir naming

Task dir размещается в `.ai/external_chats/tasks/` или в любом пути, переданном в `publish-task --task-dir`.

Имя task-dir используется как `external_task_id`. Пример: `EXT-0001`, `TASK-002`.

## Main handoff

Основной handoff файл: `<external_attempt_id>_handoff.md`.

Пример: `EXT-0001_handoff.md`, где `EXT-0001` — попытка (attempt_id).

Если публикуется несколько попыток одной задачи, каждая попытка — отдельный publish.

Скрипт `publish-task` автоматически извлекает `external_task_id` из имени директории и `external_attempt_id` из `*_handoff.md` файла внутри неё.

## Side-files

Side-files допускаются только при явном перегрузе (explicit overload) основного handoff.

По умолчанию публикуется только `*_handoff.md` и файлы, явно присутствующие в task-dir.

## Manifest

После публикации `publish-task` создаёт sidecar manifest: `<task-dir>.publish-manifest.json`.

Пример: если task-dir = `EXT-0001`, manifest = `EXT-0001.publish-manifest.json` рядом с директорией.

Manifest содержит:
- `repo`, `branch`, `temp_root`
- `external_task_id`, `external_attempt_id`
- `static_manual_version`, `static_manual_url`, `static_manual_raw_url`
- `main_handoff_relpath`, `main_handoff_url`, `main_handoff_raw_url`
- `attached_artifacts`
- `published_files` — список всех опубликованных файлов с `repo_path`, `blob_url`, `raw_url`, `sha`

## Cleanup

Cleanup читает manifest и удаляет remote файлы из `external-agent-tmp/<task_id>/`.

Перед удалением валидирует каждый candidate path:
- path должен лежать строго внутри `external-agent-tmp/<task_id>/`
- path не может совпадать со `static_manual_path`
- при первом нарушении — ошибка, удаление не производится

## CLI reference

```
verify-static [--config PATH]
publish-task --task-dir PATH [--main-file NAME] [--config PATH] [--manifest PATH]
show-links --manifest PATH [--config PATH]
cleanup-task --manifest PATH [--config PATH]
```

## Связь с другими документами

- [publisher_config.json](../publisher_config.json) — canonical publish target
- [../README.md](../README.md) — общий файловый контракт external_chats
- [../../scripts/external_chat_publish.py](../../scripts/external_chat_publish.py) — publish/cleanup/show-links скрипт

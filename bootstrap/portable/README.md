# Portable Bootstrap Package

Этот пакет — официальный ручной bootstrap contract для переноса workflow `Codex + Kilo Code` в новый проект без копирования всей исторической project memory.

## Что это решает

Пакет фиксирует четыре класса материалов:

- `copy-as-is core` — переносится как есть.
- `instantiate-from-template` — создается заново из шаблонов.
- `manual setup` — настраивается руками вне простого копирования файлов.
- `do-not-copy historical/project-specific` — не переносится как ядро нового проекта.

Ключевое правило: одной только `.ai/` недостаточно. Для рабочего переноса нужны также корневой `AGENTS.md`, набор `scripts/`, ручная настройка Kilo modes и published route для `External Web Chat`.

## Быстрый порядок запуска

1. Прочитайте [manifest.md](./manifest.md).
2. Примените [copy_map.md](./copy_map.md).
3. Создайте project-specific файлы из [templates/](./templates/).
4. Пройдите [manual_setup_checklist.md](./manual_setup_checklist.md).
5. Выполните [verification_checklist.md](./verification_checklist.md).

## Что входит в package

- README и operator guide: этот файл.
- Manifest переносимых материалов: [manifest.md](./manifest.md).
- Практическая карта копирования: [copy_map.md](./copy_map.md).
- Ручной setup checklist: [manual_setup_checklist.md](./manual_setup_checklist.md).
- Verification checklist после переноса: [verification_checklist.md](./verification_checklist.md).
- Starter templates для project-specific state: [templates/](./templates/).

## Что package не делает

- Не ставит ничего автоматически.
- Не копирует master/session history как канон нового проекта.
- Не переносит handoff/report/review history как стартовую память.
- Не настраивает Kilo UI modes вместо человека.
- Не публикует static manual и temporary task bundle автоматически вместо человека.

## Что считается обязательным ядром

- Корневой `AGENTS.md`.
- Канонические `.ai`-документы orchestration.
- Валидаторы и publish-скрипты из `scripts/`.
- Core prompts и workflow templates.
- Источник static manual для external route.

## Что должно создаваться заново

- `project_brief.md`
- `project_state.md`
- `architecture.md`
- `decisions.md`
- `current_sprint.md`
- runtime-папки и runtime-артефакты
- session/master history нового проекта
- capability state нового проекта, если он зависит от текущего окружения и ручного подтверждения

## Что нельзя считать portable core

- backlog и текущее состояние конкретного проекта
- handoffs, reports, reviews
- session files и master plans
- external chat requests, responses, tasks, recorder packages
- historical logs и legacy traces

## Правило для нового проекта

Если возникает вопрос «копировать ли это как часть bootstrap?», ответ по умолчанию такой:

- если файл задает workflow canon или tooling contract, он обычно входит в `copy-as-is core`;
- если файл описывает состояние именно этого проекта, он должен быть `instantiate-from-template` или `do-not-copy`;
- если для работы нужен UI, внешний сервис или публикация, это `manual setup`.

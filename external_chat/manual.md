# Compact Manual: External Web Chat Workflow

Этот manual — компактная локальная reference для Codex и человека. Он не заменяет canonical static manual для published-artifact route.

Этот manual описывает `/r1` published-artifact и recorder-flow. `/r1` — редкий advanced/manual-only route, а не default external path. `/v1` staged local save через `kilo-notebook` сюда не входит и документируется отдельно в notebook docs.

## Published-artifact route (CHUNK-008)

Production-like external route требует published-artifact contract:

- **Static manual**: опубликован в `AndrewVerhoturov1/external-agent-read-test`, branch `main`, путь `external_agent_static_manual.md`
- **Task bundle**: публикуется в `external-agent-tmp/<external_task_id>/` через [`scripts/external_chat_publish.py`](../scripts/external_chat_publish.py)
- **Publish config**: `.ai/external_chats/publisher_config.json` в consumer repo (project-specific, instantiate-from-template)
- **Task bundle contract**: [`external_chat/tasks/README.md`](tasks/README.md) (canonical central core source)
- **Validator**: [`scripts/validate_external_chat_package.py`](../scripts/validate_external_chat_package.py) (режим `package <path>`)
- **Cleanup**: `cleanup-task` удаляет только `external-agent-tmp/<external_task_id>/`, не трогает static manual

## Canonical static manual

Локальный canonical source в central core:

- [`external_chat/external_agent_static_manual.md`](external_agent_static_manual.md)

Текущая canonical version:

- `EA-STATIC-2026-05-14-V2`

Именно этот файл должен быть один раз вручную опубликован человеком в public repo по пути `external_agent_static_manual.md`.
Для production-like external route preferred source для внешнего агента — published raw URL этого canonical файла.

## Назначение

Описывает request/response artifacts, static reference, artifact statuses, cleanup expectations и правило локальной верификации.

## Workflow Overview

### Граница с `/v1`

- `/v1` — default external route, если достаточно одного prompt.
- `/r1` raw response capture идёт через `kilo-recorder`.
- `/v1` staged local persistence идёт через `kilo-notebook`.
- `/r1` уместен только если нужен published task bundle, strict traceability, recorder-ready capture или review published-artifact workflow.
- Этот manual не описывает notebook package. Notebook flow документирован отдельно в consumer repo (`.ai/external_chats/notebook/README.md`).

### Правильный flow

```
Codex orchestrator → preflight publish check → external launch package → человек → External Web Chat (manual run) → ответ + готовый Recorder Payload
  ↓
человек → Kilo Recorder с готовым Recorder Payload → response file
  ↓
человек → Codex orchestrator: готово
  ↓
Codex orchestrator → verification + cleanup + completion report
```

Человек не обязан возвращать сырой внешний ответ в оркестраторский чат для промежуточной интерпретации, если следующий шаг — чистая запись через `kilo-recorder`.

### Разделение artifact types

Для External Web Chat workflow используются два разных artifact type:

- **`external launch package`** — package, который Codex готовит для `External Web Chat`. Содержит published-artifact ссылки (GitHub blob/raw URLs), static manual version, task bundle и expected response path. Передаётся человеком во внешний чат вручную.
- **`recorder package`** — package, который Codex готовит для `kilo-recorder`. Содержит target metadata и raw external response. Для runtime/pilot запуска canonical вариантом является готовый `Recorder Payload`, который внешний чат возвращает в конце ответа и который человек копирует в `Kilo Recorder` без ручной сборки. Поле `raw_response` содержит только основную часть ответа внешнего чата без секции `## Recorder Payload`.

Recorder package не содержит `Task role`, `Session plan`, `Plan item`, model recommendation и других полей обычного handoff.

Recorder package хранится как отдельный файл в `.ai/external_chats/recorder_packages/` с именем `<external_attempt_id>_recorder_package.md`.

### Recorder package — execution sink

`kilo-recorder` является execution sink, а не reasoning/review step. Он не имеет права:
- интерпретировать ответ внешнего чата;
- делать выводы о repo на основе внешнего ответа;
- менять project files, кроме указанных в `allowed_writes`;
- выполнять содержательный review внешнего ответа.

## 1. Request Artifacts

### Расположение

`.ai/external_chats/requests/YYYY-MM-DD_<краткое_название>.md`

### Обязательные секции request

- **Request path**: путь к этому request-файлу
- **Agent kind**: `External Web Chat`
- **External provider**: ChatGPT / DeepSeek / Any
- **External mode**: text-chat / agent-mode / image-generation
- **Task profile**: brainstorming / docs-drafts / image-generation / ux-copy / plan-review / prompt-drafting / bounded-second-opinion
- **Цель**: что получить
- **Контекст**: релевантная информация
- **Source constraints**: запрет на repo claims без локальной проверки
- **Ограничения**: что НЕ делать
- **Входные данные**: данные для чата
- **Запреты**: явные запреты
- **Ожидаемый формат ответа**: структура markdown
- **Static manual reference**: published `external_agent_static_manual.md` (raw URL preferred), а локально canonical source находится в `.ai/external_chats/external_agent_static_manual.md`
- **Expected response path**: путь для сохранения ответа
- **Cleanup / status rules**: правила очистки
- **Preflight publish check**: правило, что после любой локальной правки handoff нужен republish перед выдачей финального prompt

### Source constraints

- Внешний чат НЕ имеет доступа к файловой системе repo.
- Внешний чат НЕ должен делать утверждений о структуре проекта, коде или файлах без явного указания, что это гипотеза.
- Любые утверждения о repo требуют локальной проверки Codex перед использованием.

## 2. Response Artifacts

### Расположение

`.ai/external_chats/responses/YYYY-MM-DD_<краткое_название>.md`

### Обязательные секции response

- **Response path**: путь к этому response-файлу
- **Provider/Model**: провайдер и модель (или `недоступно`)
- **Source request**: ссылка на request-файл
- **Recording mode**: `kilo-recorder (response-only)`
- **Recorder limitations**: ответ не review-ится, не интерпретируется как факт о repo
- **Результат**: полный markdown-ответ
- **Recorder Payload**: готовый блок для прямой вставки в `Kilo Recorder`
- **Ограничения**: что не удалось получить
- **Артефакты/Ссылки**: созданные артефакты
- **Что не удалось**: нерешённые задачи
- **Метаданные**: даты, продолжительность

Если response планируется записывать через `kilo-recorder`, эти response metadata не являются optional cosmetic fields. External launch package должен требовать их явно, иначе response считается неполным для recorder-flow.

### Контракт kilo-recorder

`kilo-recorder` работает только через `recorder package`. Recorder package — минимальный контракт для записи уже полученного внешнего ответа (не обычный Kilo handoff).

**Приоритет mode-specific contract:** `Recorder Package Contract` переопределяет общие task/global wording для `kilo-recorder` там, где есть конфликт. Recorder пишет только файлы из `allowed_writes`, не создаёт report и не выполняет `git_status`. `attempt_completion` используется только как финальное завершение запуска.

Обязательные поля recorder package:
- `external_task_id` — идентификатор внешней задачи
- `external_attempt_id` — идентификатор attempt-а внешней задачи
- `response_path` — путь к целевому response-файлу
- `published_links` — ссылки на published artifacts (static manual blob/raw, handoff bundle blob/raw)
- `recording_mode: response-only`
- `allowed_writes` — единственный список разрешённых файлов для записи; как правило, это только response-файл
- `raw_response` — сырой ответ внешнего чата

Сырой внешний ответ без target metadata недостаточен для recorder run.

Execution sink правила:
- Recorder НЕ review-ит содержательно ответ.
- Recorder НЕ редактирует содержательно ответ.
- Recorder НЕ изменяет project files, кроме указанных в `allowed_writes`.
- Recorder НЕ интерпретирует ответ как факт о repo.
- Recorder НЕ делает выводы о repo на основе внешнего ответа.
- Recorder НЕ делает `git status`.
- Recorder НЕ создаёт report.
- Recorder НЕ читает дополнительные локальные файлы для восстановления контекста, если `raw_response` уже есть в package.
- Recorder НЕ пишет placeholder вместо verbatim `raw_response`.
- Recorder записывает только response file, затем перечитывает его и подтверждает, что он непустой.

## 3. Artifact Statuses

### Request statuses

| Статус | Описание |
|--------|----------|
| `request_prepared` | Request файл создан и готов к отправке |
| `sent_manually` | Человек запустил External Web Chat вручную |

### Response statuses

| Статус | Описание |
|--------|----------|
| `response_recorded` | Ответ записан через kilo-recorder в response file |
| `locally_reviewed` | Codex проверил response локально перед использованием |

### Acceptance statuses

| Статус | Описание |
|--------|----------|
| `accepted_as_planning_input` | Идеи из ответа приняты как planning input (не как факт о repo) |
| `accepted_with_warnings` | Идеи приняты с предупреждениями о необходимости дополнительной проверки |
| `rejected` | Идеи из ответа отклонены |
| `cleanup_done` | Временные файлы удалены или архивированы |

## 4. Cleanup Expectations

- **Request artifacts**: после `sent_manually` request может быть помечен как `cleanup_done` или удалён по ручному решению.
- **Response artifacts**: после `locally_reviewed` response может быть переведён в `accepted_as_planning_input`, `accepted_with_warnings` или `rejected`. После принятия может быть переведён в `cleanup_done`.
- **Review artifacts**: хранятся как evidence для traceability.
- **Устаревшие/дублирующиеся файлы**: могут быть удалены по ручному решению без расширения в CHUNK-006 cleanup work.

## 5. Правило локальной верификации

**External Web Chat НЕ является источником фактов о repo без локальной проверки Codex.**

Это означает:

- Любые утверждения о структуре проекта, коде, файлах должны быть перепроверены локально.
- Ссылки на файлы, которые якобы существуют, требуют ручной проверки.
- Описания архитектуры или решений требуют сверки с реальным состоянием.
- Принятые идеи, копирайт, изображения, черновики документации можно использовать как planning input, но не как факт о repo.

## 6. Reading order for production-like route

1. External agent читает published static manual.
2. Делает static readback.
3. Читает основной published handoff bundle.
4. Читает optional side-files только если handoff явно этого требует.
5. Возвращает ответ в требуемом формате вместе с готовым `Recorder Payload`.

### Жёсткое правило для recorder-ready external request

Если следующий шаг — `kilo-recorder`, external request обязан явно требовать:

- основной ответ, уже пригодный для verbatim-записи в response-файл;
- self-reported `Provider/Model` или `недоступно`;
- готовый `Recorder Payload` с полями `external_task_id`, `external_attempt_id`, `response_path`, `published_links`, `recording_mode`, `allowed_writes`, `raw_response`;
- правило, что `raw_response` содержит основной ответ без секции `## Recorder Payload`.

Формулировка уровня "в конце добавь Recorder Payload" без перечисления полей и response metadata считается недостаточной.

Raw URL должен быть preferred source для чтения, GitHub blob URL — fallback/reference.

## 7. Когда использовать External Web Chat

### Подходит (first-choice):

- brainstorming
- critique
- docs drafts
- image generation
- UX copy
- plan review
- prompt drafting
- bounded second opinion

### Не подходит (high-risk):

- секреты (secrets)
- обязательное чтение repo
- правки файлов
- тесты
- diff-review
- auth/payments/credentials/migrations/security-sensitive work

# Шаблон: Создание External Chat Request (external launch package)

Используй этот шаблон для подготовки самодостаточного запроса к External Web Chat. Это шаблон для `external launch package` — package, который передаётся человеком во внешний чат вручную. Этот шаблон не является `recorder package` (recorder package описан в `record_external_chat_response.md`).

Этот шаблон используется в двух режимах:

- **Обычный режим** — Codex самостоятельно инициирует создание external launch package в рамках ordinary workflow path.
- **Режим `/r1` (или `/р1`)** — explicit preparation mode, включаемый только по явному shortcut-вызову пользователя. В этом режиме Codex сначала уточняет цель external route у человека (clarification): простым языком предлагает 2-4 уместных варианта того, что именно спросить у внешнего чата. Варианты должны различаться по `task profile`, глубине, expected output и границам scope, а не по названию модели. Codex ждёт выбора человека, и только затем создаёт external launch package. External launch package не создаётся до явного выбора человека внутри `/r1`.

Дополнительное правило для `/r1`: выбор модели для External Web Chat по умолчанию остаётся за человеком. Codex не должен превращать `/r1` в меню выбора модели, если человек сам не попросил помощи именно с моделью.

## Разделение artifact types

- **`external launch package`** (этот шаблон) — package для `External Web Chat`, содержит published-artifact ссылки, static manual version, task bundle и expected response path.
- **`recorder package`** — отдельный package для `kilo-recorder`, содержит target metadata и raw external response. Описан в `record_external_chat_response.md`. Не является ordinary Kilo handoff.

## Формат файла

Сохраняй файл в `.ai/external_chats/requests/` с именем `YYYY-MM-DD_<краткое_название>.md`.

## Обязательные секции

```md
# External Chat Request: <название>

## Request path

Путь к этому request-файлу: `.ai/external_chats/requests/YYYY-MM-DD_<краткое_название>.md`

## Agent kind

External Web Chat

## External provider

Например: ChatGPT / DeepSeek / Any

## External mode

Например: text-chat / agent-mode / image-generation

## Task profile

Например: brainstorming / docs-drafts / image-generation / ux-copy / plan-review / prompt-drafting / bounded-second-opinion

## Цель

Что нужно получить от внешнего веб-чата.

## Контекст

Релевантная информация для формирования ответа:
- предыдущая работа
- ограничения проекта
- релевантные детали

## Source constraints

- Внешний чат НЕ имеет доступа к файловой системе repo.
- Внешний чат НЕ должен делать утверждений о структуре проекта, коде или файлах без явного указания, что это гипотеза.
- Любые утверждения о repo требуют локальной проверки Codex перед использованием.

## Ограничения

Что НЕ должен делать внешний чат:
- не обращаться к файловой системе
- не читать repo
- не придумывать факты о проекте

## Входные данные

Данные, которые передаются во внешний чат:
- описание задачи
- специфичные детали
- примеры (если есть)

## Запреты

Явные запреты на определённые темы или действия:
- запрет на генерацию секретов
- запрет на доступ к credentials
- другие запреты

## Ожидаемый формат ответа

Формат markdown-ответа:
- структура
- разделы
- стиль изложения
- если следующий шаг — `kilo-recorder`, основной ответ должен быть уже пригоден для verbatim-записи в response-файл;
- если следующий шаг — `kilo-recorder`, в основном ответе обязательны секции:
  - `## Provider/Model`
  - `## Source request`
  - `## Recording mode`
  - `## Recorder limitations`
  - `## Recorder Payload` (строго в конце ответа)

## Static manual reference

Локальный canonical source: `.ai/external_chats/external_agent_static_manual.md`

**Для production-like external route обязательно указать:**

- GitHub blob URL на `external_agent_static_manual.md`
- Raw URL на `external_agent_static_manual.md`
- `static_manual_version` (текущая: `EA-STATIC-2026-05-14-V2`)
- required static anchors (минимум: `[EA-CORE-BOUNDARY]`, `[EA-TRUTH-RULE]`, `[EA-TASK-BUNDLE]`)

Raw URL должен быть preferred source для чтения внешним агентом.

Publish target: `AndrewVerhoturov1/external-agent-read-test`, branch `main`.

## Task bundle reference

**Для production-like external route обязательно указать:**

- `external_task_id`
- `external_attempt_id`
- GitHub blob URL на основной handoff bundle
- Raw URL на основной handoff bundle
- optional side-files (только при explicit overload)

Raw URL должен быть preferred source для чтения внешним агентом.

## Expected response path

Ожидаемый путь для сохранения ответа: `.ai/external_chats/responses/YYYY-MM-DD_<название>.md`

## Recorder-ready response contract

Если route предполагает `kilo-recorder`, launch package обязан явно потребовать от внешнего чата:

- вернуть полный основной ответ, пригодный для verbatim-записи в response-файл;
- self-report поля `Provider/Model` или написать `недоступно`, если модель не видна;
- добавить в конце готовую секцию `## Recorder Payload` для прямой вставки в `Kilo Recorder`;
- не заставлять человека вручную собирать target metadata из request/handoff/manual.

Внутри `Recorder Payload` должны быть уже заполнены:

- `external_task_id`
- `external_attempt_id`
- `response_path`
- `published_links`
- `recording_mode: response-only`
- `allowed_writes`
- `raw_response`

Дополнительные правила:

- `raw_response` содержит весь основной ответ внешнего чата verbatim;
- `raw_response` не включает секцию `## Recorder Payload`;
- если внешний чат не может вернуть полный payload, это `blocked`, а не допустимая деградация.

## Cleanup / status rules

- Request statuses: `request_prepared` (создан), `sent_manually` (отправлен человеком).
- Response statuses: `response_recorded` (записан через kilo-recorder), `locally_reviewed` (проверен Codex).
- Acceptance statuses: `accepted_as_planning_input`, `accepted_with_warnings`, `rejected`, `cleanup_done`.
- После `sent_manually` request может быть помечен как `cleanup_done` или удалён по ручному решению.
- После `locally_reviewed` response может быть переведён в `accepted_as_planning_input`, `accepted_with_warnings`, `rejected` или `cleanup_done`.
```

## Пример заполнения

```md
# External Chat Request: UX copy для главной страницы

## Request path

.ai/external_chats/requests/2026-05-11_ux_copy_mainpage.md

## Agent kind

External Web Chat

## External provider

ChatGPT

## External mode

text-chat

## Task profile

ux-copy

## Цель

Получить 3 варианта UX copy для главной страницы SaaS-приложения.

## Контекст

- Продукт: AI-ассистент для разработчиков
- Целевая аудитория: разработчики, DevOps-инженеры
- Тон: профессиональный, но дружелюбный
- Конкуренты: GitHub Copilot, Cursor

## Source constraints

- Не делай утверждений о структуре repo, файлах или коде как о факте.
- Если в формулировке появится предположение о проекте, пометь его как гипотезу.
- Любые repo claims требуют локальной проверки Codex перед использованием.

## Ограничения

- Не использовать технический жаргон
- Избегать клише
- Не придумывать несуществующие функции продукта

## Входные данные

- Название продукта: DevHelper
- Ключевые фичи: автодополнение кода, рефакторинг, объяснение ошибок
- Бесплатный лимит: 1000 строк в день

## Запреты

- Не упоминать цены
- Не сравнивать с конкурентами напрямую

## Ожидаемый формат ответа

- Заголовок (H1 или H2)
- 3 варианта по 2-3 предложения
- Краткое пояснение каждого варианта
- если дальше ожидается `kilo-recorder`, в конце ответа должны быть:
  - `## Provider/Model`
  - `## Source request`
  - `## Recording mode`
  - `## Recorder limitations`
  - `## Recorder Payload`

## Static manual reference

Local canonical source: `.ai/external_chats/external_agent_static_manual.md`
Published GitHub URL: `https://github.com/<owner>/<repo>/blob/main/external_agent_static_manual.md`
Published raw URL: `https://raw.githubusercontent.com/<owner>/<repo>/main/external_agent_static_manual.md`
Static manual version: `EA-STATIC-2026-05-14-V2`
Required static anchors:
- [EA-READ-FIRST]
- [EA-REQUIRED-READING-ORDER]
- [EA-CORE-BOUNDARY]
- [EA-TRUTH-RULE]
- [EA-TASK-BUNDLE]
- [EA-GITHUB-LINKS]

## Expected response path

.ai/external_chats/responses/2026-05-11_ux_copy_mainpage.md

## Cleanup / status rules

- Request statuses: `request_prepared`, `sent_manually`.
- Response statuses: `response_recorded`, `locally_reviewed`.
- Acceptance statuses: `accepted_as_planning_input`, `accepted_with_warnings`, `rejected`, `cleanup_done`.
- После `sent_manually` request может быть помечен как `cleanup_done`.
- После `locally_reviewed` response может быть переведён в `accepted_as_planning_input`, `accepted_with_warnings`, `rejected` или `cleanup_done`.
```

## Важные правила

1. **Самодостаточность** — запрос должен содержать всю необходимую информацию для получения качественного ответа
2. **Явные запреты** — всегда указывай, что внешний чат НЕ должен делать
3. **Формат ответа** — чётко опиши ожидаемый формат markdown
4. **Нет доступа к repo** — внешний чат не видит файлы проекта, поэтому контекст нужно давать явно
5. **Canonical manual first** — local canonical source хранится в `.ai/external_chats/external_agent_static_manual.md`, а для published route в request должны быть и GitHub URL, и raw URL, с приоритетом raw URL
6. **Recorder-ready contract** — если следующий шаг идёт через `kilo-recorder`, request обязан требовать response metadata и полный `Recorder Payload`, а не просто упоминать его по имени

# Repo Navigation — ai-workflow-core

Справочник файлов этого central core repo. Помогает быстро находить ключевые документы: контракты и шаблоны для маршрута `/v1`.

**Что здесь есть:** только stable core файлы этого repo — public `/v1` rules и prompt templates.

**Чего здесь нет:** project-specific context, consumer repo файлы, временные workflow artifacts, history.

Этот файл обновляется только при добавлении, удалении или переносе stable core файлов в этом repo.

## Allowed Navigation Targets

Все ссылки, перечисленные в этом файле, являются **allowed navigation targets** для внешнего чата в маршруте `/v1`. Это означает:

1. **Внешний чат может открывать любую из перечисленных здесь ссылок**, если считает её релевантной вопросу. Navigation дан именно для этого — чтобы внешний чат мог найти нужные central core документы.
2. **Внешний чат не обязан читать все ссылки.** Он выбирает релевантные.
3. **Этот navigation не даёт права читать или утверждать что-либо о consumer repo.** Consumer repo files не перечислены здесь. Для доступа к ним они должны быть явно переданы в prompt как project-specific links/excerpts.
4. **Navigation — closed set для данного `/v1` prompt.** Внешний чат не должен выдумывать ссылки, которых здесь нет.
5. **Central core navigation не содержит ссылок на consumer repo.** `repo_navigation.md` в consumer repo — это отдельный файл, который может передаваться как project-specific link при необходимости.

---

## Core `/v1` Contract

Базовые правила и описание central core для маршрута `/v1`.

- [`README.md`](README.md) — обзор central core: что такое `ai-workflow-core`, граница central vs project-specific, структура, связь с другими repos.
- [`external_chat_rules.md`](external_chat_rules.md) — public-facing contract для внешнего чата в маршруте `/v1`. Обязателен к передаче в каждом `/v1` prompt. Читать при подготовке любого `/v1` вопроса.

## Prompt Templates

Шаблоны для создания prompt-ов.

- [`prompts/create_external_question_prompt.md`](prompts/create_external_question_prompt.md) — шаблон для Codex: создание `/v1` prompt (prompt-only вопрос во внешний чат). Только для маршрута `/v1`. Для `/r1` используется отдельный шаблон в consumer repo.

## Связь с другими repos

| Repo | Назначение | Navigation |
|---|---|---|
| `ai-workflow-core` (этот) | Stable `/v1` rules repo | Этот файл |
| Consumer project repo | Конкретный проект | Собственный `repo_navigation.md` в consumer repo |
| `external-agent-read-test` | Technical `/r1` publish repo | Не индексируется здесь |

## Explicitly Not Indexed Here

Эти категории не являются частью central core и **не индексируются** в этом справочнике:

- **project-specific state** — `project_brief.md`, `project_state.md`, `architecture.md`, `decisions.md` (принадлежат consumer repo)
- **handoffs** — временные файлы handoff
- **reports** — временные отчёты
- **reviews** — временные review
- **сессионные планы** — session files
- **chunk-артефакты** — chunk plans
- **внешние запросы/ответы** — external chat requests/responses
- **recorder packages** — recorder artifacts (`/r1`)
- **notebook entries** — notebook storage (`/r1`)
- **validators/scripts** — automation scripts (принадлежат consumer repo или отдельному tooling)
- **publish metadata** — publish configs (`/r1`)

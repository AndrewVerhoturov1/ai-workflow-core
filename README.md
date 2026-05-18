# ai-workflow-core

Stable public `/v1` rules repo для workflow `Codex + Kilo Code`.

## Что это

`ai-workflow-core` — центральный источник правил для prompt-only маршрута `/v1`. Все будущие project repos ссылаются на этот repo как на единый стабильный источник core правил, вместо того чтобы копировать workflow-файлы в каждый проект.

Этот repo содержит только reusable public `/v1` rules и materials. Конкретный project repo добавляет свои project-specific links и excerpts отдельно — они никогда не попадают в этот central core.

## Граница: central core vs project-specific context

| Central core (этот repo) | Project-specific context (consumer repo) |
|---|---|
| `README.md` | `project_brief.md` |
| `external_chat_rules.md` | `project_state.md` |
| `repo_navigation.md` | `architecture.md` |
| `prompts/create_external_question_prompt.md` | `decisions.md` |
| — | `current_sprint.md` |
| — | конкретные внешние запросы/ответы |
| — | handoffs, reports, reviews |
| — | session/chunk history |

## Два маршрута: /v1 и /r1

### Короткая памятка

`/v1` = один prompt во внешний чат сейчас. Без package, без recorder, без published artifacts.

`/r1` = полный внешний пакет. С published artifacts, task bundle, recorder package и последующей записью ответа.

### Быстрое правило выбора

| Если тебе нужен... | Выбирай |
|---|---|
| Один короткий или средний вопрос во внешний чат | `/v1` |
| Полный внешний workflow с артефактами и записью ответа | `/r1` |
| Много файлов, published bundle, strict artifact contract | `/r1` |
| Просто second opinion, critique, draft, UX/formulation review | `/v1` |

**Момент выбора:** человек выбирает маршрут **до** подготовки downstream artifact.
Для `/v1` это готовый prompt. Для `/r1` это full external launch package.

### /v1 — prompt-only вопрос (лёгкий маршрут)

**Без handoff, без external launch package, без published task bundle, без Recorder Payload.**

- Codex готовит только текст вопроса (prompt).
- Человек копирует prompt и отправляет во внешний чат вручную.
- Ответ внешнего чата не проходит через `kilo-recorder`.
- В каждом `/v1` prompt обязательно передаются две central ссылки: [`external_chat_rules.md`](./external_chat_rules.md) и [`repo_navigation.md`](./repo_navigation.md).
- Дополнительные project-specific links и excerpts передаются из consumer repo под конкретный вопрос.

### /r1 — full external launch package (тяжёлый маршрут)

**С published artifacts, task bundle, static manual и recorder package.**

- `/r1` использует отдельный technical publish repo `external-agent-read-test`, а не этот central core.
- `/r1` требует published-artifact contract, recorder package и `kilo-recorder`.
- Выбор между `/v1` и `/r1` всегда делает человек.
- Практическое правило: если без published links и recorder-flow задача теряет смысл, это уже `/r1`, а не `/v1`.

## Структура central core

```text
ai-workflow-core/
  README.md
  external_chat_rules.md
  repo_navigation.md
  prompts/
    create_external_question_prompt.md
```

## Чего здесь нет

Этот central core **не содержит** и никогда не будет содержать:

- reports, handoffs, reviews
- внешние запросы, ответы, задачи
- session files, chunk-артефакты, master plans
- project-specific state конкретных проектов
- notebook flow, recorder packages, publish metadata
- validators, scripts
- временную историю и execution artifacts

Всё это — либо часть consumer repo context, либо отдельный `/r1` technical publish слой.

## Связь с другими repos

| Repo | Назначение |
|---|---|
| `ai-workflow-core` (этот) | Stable `/v1` rules repo. Central core правил для prompt-only маршрута. |
| Consumer project repo | Конкретный проект. Ссылается на central core и добавляет свои project-specific links/excerpts. |
| `external-agent-read-test` | Technical `/r1` publish repo. Static manual и temporary task bundles для full external launch package. |

## Как использовать

1. Consumer project repo ссылается на raw-версии файлов из этого central core.
2. `/v1` prompt всегда содержит две обязательные central ссылки: `external_chat_rules.md` и `repo_navigation.md`.
3. Дополнительные project-specific links подставляются из consumer repo под конкретный вопрос.
4. Выбор между `/v1` и `/r1` делает человек.

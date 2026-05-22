# ai-workflow-core

Central workflow core repo для системы `Codex + Kilo Code`.

## Что это

`ai-workflow-core` — центральный canonical source of truth для всех постоянных общих правил, scripts, prompts, templates и другого reusable workflow core системы `Codex + Kilo Code`.

Этот repo расширен с первоначальной роли «stable `/v1` rules repo» до полного central workflow core. Все consumer project repos используют этот repo как единый canonical source через:

- **raw URL references** — для `/v1` prompt-only маршрута (внешний чат читает правила по ссылке);
- **локальное копирование** — для скорости и устойчивости (Kilo Code читает локальные копии core файлов);
- **sync-механизм** — `scripts/sync_kilo_workflow.py --target <consumer-project-path>` для обновления локальных копий.

## Граница: central core vs project-specific context

| Central core (этот repo) | Consumer project repo |
|---|---|
| `AGENTS.md` | `project_brief.md` |
| `external_chat_rules.md` | `project_state.md` |
| `repo_navigation.md` (central) | `repo_navigation.md` (project-specific) |
| `ai_readme.md` → `.ai/README.md` | `architecture.md`, `decisions.md` |
| `rules/*.md` → `.ai/rules/*.md` | project-specific state |
| `prompts/*.md` → `.ai/prompts/*.md` | runtime/history (handoffs, reports, reviews) |
| `templates/*.md` → `.ai/templates/*.md` | external chat requests/responses |
| `scripts/*.py` → `scripts/*.py` | V1_navigation.md (project-specific) |
| `bootstrap/portable/*` → `.ai/bootstrap/portable/*` | session/chunk history |
| `external_chat/*` → `.ai/external_chats/*` | — |

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
- Ответ внешнего чата может быть сохранён через `kilo-notebook` как local staged notebook entry.
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
  README.md                           — обзор central core repo
  AGENTS.md                           — главный файл правил Codex + Kilo
  .gitignore                          — workflow-specific gitignore
  publish_config.json                 — publish config central core
  ai_readme.md                        — canonical source для consumer .ai/README.md
  external_chat_rules.md              — public-facing /v1 contract (ОСТАЁТСЯ В КОРНЕ)
  repo_navigation.md                  — central core navigation (ОСТАЁТСЯ В КОРНЕ)

  rules/                              — внутренние workflow-правила
    agent_protocol.md
    model_roster.md
    codex_orchestrator.md
    kilo_mode_contract.md
    kilo_builder.md
    kilo_debugger.md
    kilo_docs.md
    kilo_refactor.md
    kilo_tester.md

  prompts/                            — reusable orchestration prompts
    create_external_question_prompt.md
    choose_model.md
    create_handoff.md
    create_external_chat_request.md
    create_block_plan.md
    create_block_orchestrator_package.md
    record_external_chat_response.md
    record_external_notebook_response.md
    review_agent_report.md
    review_block_report.md
    (numbered prompt files)

  templates/                          — reusable workflow templates
  validators/
    README.md                         — инструкция по ручным validator checks
  plans/
    README.md                         — обзор структуры планов

  bootstrap/portable/                 — portable bootstrap package
    README.md
    manifest.md
    copy_map.md
    manual_setup_checklist.md
    verification_checklist.md
    templates/                        — starter templates

   scripts/                            — automation scripts
     validate_kilo_contract.py
     validate_session_contract.py
     validate_external_chat_package.py
     external_chat_publish.py
     sync_kilo_workflow.py
     bootstrap_workflow.py
     safe_sync_workflow.py
     stage_v1_notebook.py
     write_v1_notebook.py

  external_chat/                      — external chat workflow materials
    manual.md
    external_agent_static_manual.md
    tasks/
      README.md
```

## Чего здесь нет

Этот central core **не содержит** и никогда не будет содержать:

- reports, handoffs, reviews — это runtime/history consumer repo
- внешние запросы, ответы, задачи — runtime consumer repo
- session files, chunk-артефакты, master plans — runtime consumer repo
- project-specific state конкретных проектов — consumer repo
- notebook entries, recorder packages — runtime consumer repo
- конкретные published task bundles — `/r1` technical repo

## 4-way классификация файлов

Central core использует четырёхстороннюю классификацию:

1. **Central canonical core** — файлы в этом repo, единый source of truth.
2. **Copied local core in consumer repo** — локальные копии core файлов в consumer repo, обновляются через sync.
3. **Project-specific files** — живут только в consumer repo, создаются из шаблонов.
4. **Runtime / history / temp** — временные workflow artifacts, только в consumer repo.

## Связь с другими repos

| Repo | Назначение |
|---|---|
| `ai-workflow-core` (этот) | Central workflow core repo. Canonical source of truth для всех общих правил, scripts, prompts, templates. |
| Consumer project repo | Конкретный проект. Хранит локальные копии core файлов + project-specific слой + runtime/history. |
| `external-agent-read-test` | Technical `/r1` publish repo. Static manual и temporary task bundles для full external launch package. |

## Как использовать

1. Consumer project repo копирует core файлы из этого central core через portable bootstrap или sync-механизм.
2. `/v1` prompt всегда содержит две обязательные central ссылки: `external_chat_rules.md` и `repo_navigation.md`.
3. Локальные копии core файлов в consumer repo обновляются через `scripts/sync_kilo_workflow.py --target <consumer-project-path>`.
4. Изменения в workflow rules вносятся в этом central core repo, затем синхронизируются в consumer repos.
5. Выбор между `/v1` и `/r1` делает человек.

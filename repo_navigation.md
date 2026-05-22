# Repo Navigation — ai-workflow-core

Справочник файлов этого central core repo. Помогает быстро находить ключевые документы: контракты, правила, шаблоны и скрипты для всей системы `Codex + Kilo Code`.

**Что здесь есть:** stable core файлы этого repo — public `/v1` contract, workflow rules, prompt templates, portable bootstrap, scripts, external chat materials.

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

## Root

Базовые документы central core.

- [`README.md`](README.md) — обзор central core: назначение, граница central vs project-specific, структура, связь с другими repos, 4-way классификация.
- [`AGENTS.md`](AGENTS.md) — главный файл правил системы Codex + Kilo Code. Содержит все workflow contracts, mode definitions, agent-first mandate, short entry commands.
- [`external_chat_rules.md`](external_chat_rules.md) — public-facing contract для внешнего чата в маршруте `/v1`. Обязателен к передаче в каждом `/v1` prompt.
- [`ai_readme.md`](ai_readme.md) — canonical source для consumer `.ai/README.md`. Карта `.ai/`-слоя. Отдельный документ от корневого `README.md`.
- [`publish_config.json`](publish_config.json) — publish config central core. Replacement для `.ai/public_core/public_core_publish_config.json` в consumer repos.

## Rules

Внутренние workflow-правила системы Codex + Kilo.

- [`rules/agent_protocol.md`](rules/agent_protocol.md) — протокол взаимодействия Codex, Kilo и человека.
- [`rules/model_roster.md`](rules/model_roster.md) — активный source of truth для выбора класса модели в `/kilo`.
- [`rules/codex_orchestrator.md`](rules/codex_orchestrator.md) — правила оркестратора Codex.
- [`rules/kilo_mode_contract.md`](rules/kilo_mode_contract.md) — контракт Kilo mode / Task role.
- [`rules/kilo_builder.md`](rules/kilo_builder.md) — правила для Builder-роли Kilo.
- [`rules/kilo_debugger.md`](rules/kilo_debugger.md) — правила для Debugger-роли Kilo.
- [`rules/kilo_docs.md`](rules/kilo_docs.md) — правила для Docs-роли Kilo.
- [`rules/kilo_refactor.md`](rules/kilo_refactor.md) — правила для Refactor-роли Kilo.
- [`rules/kilo_tester.md`](rules/kilo_tester.md) — правила для Tester-роли Kilo.

## Prompts

Reusable orchestration prompts.

- [`prompts/create_external_question_prompt.md`](prompts/create_external_question_prompt.md) — шаблон для Codex: создание `/v1` prompt.
- [`prompts/choose_model.md`](prompts/choose_model.md) — шаблон выбора модели.
- [`prompts/create_handoff.md`](prompts/create_handoff.md) — шаблон создания Kilo handoff.
- [`prompts/create_external_chat_request.md`](prompts/create_external_chat_request.md) — шаблон создания external chat request.
- [`prompts/create_block_plan.md`](prompts/create_block_plan.md) — шаблон создания block plan.
- [`prompts/create_block_orchestrator_package.md`](prompts/create_block_orchestrator_package.md) — шаблон block orchestrator package.
- [`prompts/record_external_chat_response.md`](prompts/record_external_chat_response.md) — шаблон записи external chat response.
- [`prompts/record_external_notebook_response.md`](prompts/record_external_notebook_response.md) — шаблон записи notebook response.
- [`prompts/review_agent_report.md`](prompts/review_agent_report.md) — шаблон review agent report.
- [`prompts/review_block_report.md`](prompts/review_block_report.md) — шаблон review block report.

## Templates

Reusable workflow templates для consumer repos.

- [`templates/block_plan_template.md`](templates/block_plan_template.md)
- [`templates/block_orchestrator_package_template.md`](templates/block_orchestrator_package_template.md)
- [`templates/block_context_pack_template.md`](templates/block_context_pack_template.md)
- [`templates/block_report_template.md`](templates/block_report_template.md)
- [`templates/chunk_plan_template.md`](templates/chunk_plan_template.md)
- [`templates/chunk_completion_report_template.md`](templates/chunk_completion_report_template.md)

## Validators

- [`validators/README.md`](validators/README.md) — инструкция по ручным validator checks.

## Plans

- [`plans/README.md`](plans/README.md) — обзор структуры планов (session plans, chunks, master plans).

## Bootstrap / Portable

Portable bootstrap package для переноса workflow в новый проект.

- [`bootstrap/portable/README.md`](bootstrap/portable/README.md) — portable bootstrap overview.
- [`bootstrap/portable/manifest.md`](bootstrap/portable/manifest.md) — portable manifest: copy-as-is, instantiate, manual, do-not-copy.
- [`bootstrap/portable/copy_map.md`](bootstrap/portable/copy_map.md) — практическая карта копирования.
- [`bootstrap/portable/manual_setup_checklist.md`](bootstrap/portable/manual_setup_checklist.md) — ручной setup checklist.
- [`bootstrap/portable/verification_checklist.md`](bootstrap/portable/verification_checklist.md) — verification checklist.
- [`bootstrap/portable/templates/`](bootstrap/portable/templates/) — starter templates для project-specific state.

## Scripts

Automation scripts для workflow.

- [`scripts/validate_kilo_contract.py`](scripts/validate_kilo_contract.py) — валидатор handoff/launch/checkpoint contract.
- [`scripts/validate_session_contract.py`](scripts/validate_session_contract.py) — валидатор session contract.
- [`scripts/validate_external_chat_package.py`](scripts/validate_external_chat_package.py) — валидатор published external route.
- [`scripts/external_chat_publish.py`](scripts/external_chat_publish.py) — публикация task bundle.
- [`scripts/sync_kilo_workflow.py`](scripts/sync_kilo_workflow.py) — синхронизация core из central в consumer.
- [`scripts/bootstrap_workflow.py`](scripts/bootstrap_workflow.py) — script-assisted portable bootstrap wrapper (P1). Материализует managed copies из core layout в consumer layout.
- [`scripts/safe_sync_workflow.py`](scripts/safe_sync_workflow.py) — metadata-aware safe sync (P2-P3). Dry-run classifier, limited apply, adoption assessment, backfill, absent restore, local variant review/decision/resolution.
- [`scripts/stage_v1_notebook.py`](scripts/stage_v1_notebook.py) — staging notebook entries.
- [`scripts/write_v1_notebook.py`](scripts/write_v1_notebook.py) — запись notebook entries.

## External Chat

- [`external_chat/manual.md`](external_chat/manual.md) — компактный обзор external chat workflow.
- [`external_chat/external_agent_static_manual.md`](external_chat/external_agent_static_manual.md) — canonical static manual source для `/r1`.
- [`external_chat/tasks/README.md`](external_chat/tasks/README.md) — local task bundle contract.

## Связь с другими repos

| Repo | Назначение | Navigation |
|---|---|---|
| `ai-workflow-core` (этот) | Central workflow core repo | Этот файл |
| Consumer project repo | Конкретный проект | Собственный `repo_navigation.md` в consumer repo |
| `external-agent-read-test` | Technical `/r1` publish repo | Не индексируется здесь |

## Explicitly Not Indexed Here

Эти категории не являются частью central core и **не индексируются** в этом справочнике:

- **consumer runtime/history artifacts** — handoffs, reports, reviews, requests/responses, recorder packages, notebook storage и другие временные артефакты consumer repo
- **project-specific state** — `project_brief.md`, `project_state.md`, `architecture.md`, `decisions.md` (принадлежат consumer repo)
- **handoffs** — временные файлы handoff
- **reports** — временные отчёты
- **reviews** — временные review
- **сессионные планы** — session files
- **chunk-артефакты** — chunk plans
- **внешние запросы/ответы** — external chat requests/responses
- **recorder packages** — recorder artifacts (`/r1`)
- **notebook entries** — notebook storage
- **publish metadata для `/r1`** — конкретные published task bundles

# Portable Manifest

## Copy-As-Is Core

Переносить как есть:

- `AGENTS.md`
- `.ai/README.md`
- `.ai/agent_protocol.md`
- `.ai/model_roster.md`
- `.ai/rules/codex_orchestrator.md`
- `.ai/rules/kilo_builder.md`
- `.ai/rules/kilo_debugger.md`
- `.ai/rules/kilo_docs.md`
- `.ai/rules/kilo_refactor.md`
- `.ai/rules/kilo_tester.md`
- `.ai/external_chats/manual.md`
- `.ai/external_chats/external_agent_static_manual.md`
- `.ai/validators/README.md`
- `.ai/templates/*.md`
- `.ai/prompts/*.md`
- `scripts/validate_kilo_contract.py`
- `scripts/validate_session_contract.py`
- `scripts/validate_external_chat_package.py`
- `scripts/external_chat_publish.py`
- `scripts/sync_kilo_workflow.py`
- `scripts/stage_v1_notebook.py`
- `scripts/write_v1_notebook.py`
- `scripts/bootstrap_workflow.py`
- `scripts/safe_sync_workflow.py`

## Instantiate-From-Template

Создавать заново из starter templates:

- `AGENTS.md` для нового проекта, если нужен project-specific вариант
- `.ai/project_brief.md`
- `.ai/project_state.md`
- `.ai/architecture.md`
- `.ai/decisions.md`
- `.ai/backlog/current_sprint.md`
- `.ai/external_chats/publisher_config.json`

Шаблоны лежат в [templates/](./templates/).

## Manual Setup

Нужно настроить руками:

- Kilo UI modes в рабочем интерфейсе пользователя
- published external route для `External Web Chat`
- public GitHub repo и branch для static manual и temporary task bundles
- absolute paths, если новый проект сознательно использует absolute links в своих канонических docs
- пустые runtime-директории нового проекта
- первая session bootstrap-проверка после переноса

Детали: [manual_setup_checklist.md](./manual_setup_checklist.md).

## Do-Not-Copy Historical/Project-Specific

Не переносить как ядро package:

- `.ai/plans/master/*`
- `.ai/plans/sessions/*`
- `.ai/plans/pilots/*`
- `.ai/handoffs/*`
- `.ai/reports/*`
- `.ai/reviews/*`
- `.ai/external_chats/requests/*`
- `.ai/external_chats/responses/*`
- `.ai/external_chats/tasks/*`
- `.ai/external_chats/recorder_packages/*`
- `.ai/project_state.md` из исходного проекта
- `.ai/architecture.md` из исходного проекта
- `.ai/decisions.md` из исходного проекта
- `.ai/backlog/*` как история текущего продукта
- `.ai/model_scores/*`
- `.ai/model_tests/*`
- `.ai/archive/*`
- любые product/source files исходного проекта, не относящиеся к workflow canon

## Отдельное правило по capability state

Файлы вида `codex_capabilities.md` и `kilo_capabilities.md` не считаются безопасным portable core по умолчанию. Их нужно пересобрать или заново подтвердить в контексте нового проекта и текущего окружения.

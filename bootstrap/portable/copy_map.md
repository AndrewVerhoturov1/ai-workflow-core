# Copy Map

| Source | Destination in new repo | Handling | Notes |
| --- | --- | --- | --- |
| `AGENTS.md` | `AGENTS.md` | `copy-as-is core`, затем локальная адаптация | Нужен уже на старте bootstrap. |
| `.ai/README.md` | `.ai/README.md` | `copy-as-is core` | Базовая карта `.ai/`. |
| `.ai/agent_protocol.md` | `.ai/agent_protocol.md` | `copy-as-is core` | Канон взаимодействия Codex, Kilo и человека. |
| `.ai/model_roster.md` | `.ai/model_roster.md` | `copy-as-is core`, затем human review | Активный model layer. |
| `.ai/rules/*.md` | `.ai/rules/*.md` | `copy-as-is core` | Orchestration и Kilo rules. |
| `.ai/validators/README.md` | `.ai/validators/README.md` | `copy-as-is core` | Инструкция по ручным validator checks. |
| `.ai/prompts/*.md` | `.ai/prompts/*.md` | `copy-as-is core` | Reusable orchestration prompts. |
| `.ai/templates/*.md` | `.ai/templates/*.md` | `copy-as-is core` | Workflow templates, не project history. |
| `.ai/external_chats/manual.md` | `.ai/external_chats/manual.md` | `copy-as-is core` | Локальный manual external route. |
| `.ai/external_chats/external_agent_static_manual.md` | `.ai/external_chats/external_agent_static_manual.md` | `copy-as-is core` | Исходник для ручной публикации static manual. |
| `scripts/validate_kilo_contract.py` | `scripts/validate_kilo_contract.py` | `copy-as-is core` | Validator handoff/launch/checkpoint contract. |
| `scripts/validate_session_contract.py` | `scripts/validate_session_contract.py` | `copy-as-is core` | Validator session contract. |
| `scripts/validate_external_chat_package.py` | `scripts/validate_external_chat_package.py` | `copy-as-is core` | Validator published external route. |
| `scripts/external_chat_publish.py` | `scripts/external_chat_publish.py` | `copy-as-is core` | Publish/cleanup helper для external route. |
| `.ai/project_brief.md` | `.ai/project_brief.md` | `instantiate-from-template` | Новый проект, новая цель. |
| `.ai/project_state.md` | `.ai/project_state.md` | `instantiate-from-template` | Не переносить чужой runtime state. |
| `.ai/architecture.md` | `.ai/architecture.md` | `instantiate-from-template` | Новая архитектура нового проекта. |
| `.ai/decisions.md` | `.ai/decisions.md` | `instantiate-from-template` | Новый decision log. |
| `.ai/backlog/current_sprint.md` | `.ai/backlog/current_sprint.md` | `instantiate-from-template` | Новый sprint state. |
| `.ai/external_chats/publisher_config.json` | `.ai/external_chats/publisher_config.json` | `instantiate-from-template` | Новый repo, branch и URL-шаблоны. |
| `.ai/plans/sessions/` | `.ai/plans/sessions/` | `manual setup` | Создать пустую директорию, историю начать заново. |
| `.ai/handoffs/`, `.ai/reports/`, `.ai/reviews/` | те же пути | `manual setup` | Создать пустые runtime-директории. |
| `.ai/external_chats/requests/`, `responses/`, `tasks/`, `recorder_packages/`, `reviews/` | те же пути | `manual setup` | Создать пустые runtime-директории. |
| `.ai/plans/master/*` | не копировать | `do-not-copy historical/project-specific` | Master history не является bootstrap core. |
| `.ai/plans/sessions/*` | не копировать | `do-not-copy historical/project-specific` | Session history нового проекта должна начаться с нуля. |
| `.ai/handoffs/*`, `.ai/reports/*`, `.ai/reviews/*` | не копировать | `do-not-copy historical/project-specific` | Это trace текущего проекта, не ядро системы. |
| `.ai/project_state.md`, `.ai/architecture.md`, `.ai/decisions.md` исходного проекта | не копировать как есть | `do-not-copy historical/project-specific` | Брать только шаблонную форму, не содержимое. |
| `.ai/backlog/*` исходного проекта | не копировать как есть | `do-not-copy historical/project-specific` | Это продуктовая история, а не bootstrap canon. |

## Дополнение

Если новый проект хочет сохранить capability registry, его нужно не копировать слепо, а переинициализировать и переподтвердить под новое окружение.

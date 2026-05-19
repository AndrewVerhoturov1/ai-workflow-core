# Verification Checklist

## Bootstrap Integrity

- [ ] `git status --short` чистый после переноса базового набора.
- [ ] В новом repo существуют `AGENTS.md`, `.ai/README.md`, `.ai/agent_protocol.md`, `.ai/model_roster.md`.
- [ ] В новом repo существуют `scripts/validate_kilo_contract.py`, `scripts/validate_session_contract.py`, `scripts/validate_external_chat_package.py`, `scripts/external_chat_publish.py`.
- [ ] Существуют пустые runtime-директории для handoffs, reports, reviews и external chat artifacts.

## Project-Specific Initialization

- [ ] Созданы новые `.ai/project_brief.md`, `.ai/project_state.md`, `.ai/architecture.md`, `.ai/decisions.md`, `.ai/backlog/current_sprint.md`.
- [ ] В этих файлах нет содержимого, слепо скопированного из исторического состояния исходного проекта.
- [ ] `publisher_config.json` создан из шаблона и указывает на новый repo/branch.

## Kilo / Workflow Contract

- [ ] Kilo UI показывает четыре режима: `Kilo Handoff Runner`, `Kilo Debugger`, `Kilo Verifier`, `Kilo Recorder`.
- [ ] Внутренний contract различает `Kilo mode` и `Task role`.
- [ ] Для нового проекта не перенесены старые session/master artifacts как активный state.

## External Route

- [ ] Static manual опубликован в целевом публичном repo.
- [ ] `python scripts/validate_external_chat_package.py --help` запускается без ошибки импорта.
- [ ] `python scripts/external_chat_publish.py --help` запускается без ошибки импорта.
- [ ] Человек понимает ручной flow `Codex -> External Web Chat -> Kilo Recorder -> response file`.

## Validators

- [ ] `python scripts/validate_kilo_contract.py --help` запускается.
- [ ] `python scripts/validate_session_contract.py --help` запускается.
- [ ] Новый проект может прогнать эти validators локально.

## First Workflow Smoke

- [ ] Создан первый новый session file для нового проекта, а не перенесен старый.
- [ ] Подготовлен первый небольшой handoff в новом проекте.
- [ ] Проверено, что bootstrap package читается как официальный путь переноса workflow.

# Block Orchestrator Package

## Package ID

`PACKAGE-BLOCK-NNN_short_name`

## Parent Block

`BLOCK-NNN_short_name`

## Created By

`Main Execution Orchestrator Chat`

## Recipient

`Block Orchestrator Chat`

## Planning Document Reference

Ссылка на утверждённый planning document из `PILOT-005`.

- `path/to/planning_document.md`

## Block Artifacts Reference

Ссылки на соответствующие block artifacts.

- Block Plan: `path/to/block_plan.md`
- Context Pack: `path/to/block_context_pack.md`

## Block Scope

Чёткое описание scope текущего блока: что должно быть сделано и какой результат ожидается.

## Block Boundary

Что вне scope блока, какие файлы трогать нельзя, какие темы не поднимать.

## Recommended Agent Path

`Kilo Code` / `External Web Chat`

Обоснование выбора agent path на основе block artifacts и strategist recommendations.

## Junior Execution Boundary

Явно зафиксируй runtime-границу младшего оркестратора:

- `Block Orchestrator Chat` выбирает следующий agent path;
- готовит `Kilo handoff` / `External Web Chat` package;
- **не запускает `Kilo Code` сам**;
- ручной запуск executor остаётся обязанностью человека.

## Allowed Agent Kinds

- `Kilo Code`
- `External Web Chat`

## Planned Agent Sequence

Обязательная секция. Укажи заранее спроектированную последовательность substantive agent tasks (обычно 2-4 задачи на блок). Planned tasks должны быть явно отделены от contingency / repair runs.

- Task 1: описание
- Task 2: описание
- Contingency / Repair: описание (если применимо)

## Planned Human Checkpoints

Обязательная секция. Укажи одно из двух:

- либо реальные checkpoints;
- либо `none` с коротким обоснованием, почему в этом блоке checkpoint не нужен.

Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не молчаливым пропуском.

- **Когда остановить flow:** условие остановки
- **Что открыть/проверить:** конкретные файлы, UI, логи
- **Минимальный verdict:** accepted / accepted_with_warnings / needs_revision / blocked

## Internal-subagent resource policy

Default для `Block Orchestrator Chat` — bounded internal subagent profile на `gpt-5.4` с `low` reasoning. Повышение до более тяжёлого профиля — только по явной escalation-причине с обоснованием.

## Direct Canonical Dependencies

Укажи, какие прямые workflow/canon dependencies младший оркестратор может открыть по ссылкам из уже переданных approved artifacts.

- Разрешённые direct dependencies: ...
- Как фиксировать расширение: краткая запись в report / notes
- Если нужен файл вне этого правила: вернуть `Blocked / Clarification Request`

## Default Escalation Path

При scope ambiguity, missing dependency, невозможности выбрать agent path или конфликте инструкций младший оркестратор сразу возвращает короткий `Blocked / Clarification Request`. Ранняя эскалация — default behavior.

## Stop Conditions

Условия, при которых `Block Orchestrator Chat` должен остановиться и вернуть `Blocked / Clarification Request`:

- Условие 1
- Условие 2
- **Fail-fast preflight-check** — Block Orchestrator обязан ответить на три вопроса перед началом работы:
  - `Этот чат orchestrator или executor?` — ответ должен быть `orchestrator`.
  - `Какой первый agent path он обязан вызвать?` — должен быть явно указан `Kilo Code` или `External Web Chat`.
  - `Есть ли у него право самому читать repo ради block work?` — ответ должен быть `нет`.
  Если ответ на третий вопрос не `нет`, запуск считается `blocked`.
- **Self-execution gate** — если `Block Orchestrator Chat` начинает делать substantive repo work сам вместо подготовки `Executor Run`, запуск считается `blocked`.

## Workflow Canon Reference

Актуальные правила, которые `Block Orchestrator Chat` обязан соблюдать:

- `.ai/rules/codex_orchestrator.md`
- `.ai/agent_protocol.md`
- `AGENTS.md`

## Expected Outputs

Конкретные артефакты, которые должен создать block.

- `path/to/output1.md`
- `path/to/output2.md`

## Context Budget

Лимит на чтение больших файлов, указание на нужные tiers.

## Transfer Notes

Дополнительные заметки от `Main Execution Orchestrator Chat` к `Block Orchestrator Chat`.

## Gate Confirmation

- [ ] `Main Execution Orchestrator Chat` не готовил executor handoff или external package напрямую.
- [ ] Этот package используется для найма младшего оркестратора как внутреннего subagent.
- [ ] Если внутренний subagent path недоступен или явно запрещён человеком, допустим fallback: ручное открытие отдельного чата младшего оркестратора с передачей ему `Block Orchestrator Package`. Fallback не является основным механизмом.

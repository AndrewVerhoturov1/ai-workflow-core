# Block Plan Template

## Block ID

`BLOCK-NNN_short_name`

## Block Name

Краткое название блока.

## Parent Chunk

`CHUNK-NNN` — ссылка на chunk, в рамках которого выполняется блок.

## Goal

Чёткое описание цели блока. Что должно быть сделано и какой результат ожидается.

## Allowed Files

Список файлов, которые разрешено создавать или изменять в рамках блока.

- `path/to/file1.md`
- `path/to/file2.md`

## Forbidden Files

Список файлов, которые запрещено изменять.

- `path/to/forbidden1.md`
- `path/to/forbidden2.md`

## Context Tiers

Уровень контекста, необходимый для выполнения блока:

- **Tier 0:** Task prompt only — только сам Block Plan.
- **Tier 1:** Core workflow context — Block Plan + Context Pack + master artifacts.
- **Tier 2:** Architecture context — Tier 1 + архитектурные документы.
- **Tier 3:** Capability context — Tier 1 + capability registry.
- **Tier 4:** Forensic context — Tier 1 + история предыдущих запусков.

## Required Inputs

Файлы, которые Block Orchestrator **обязан** прочитать перед началом работы.

- `path/to/required1.md`
- `path/to/required2.md`

## Lookup Inputs

Файлы, которые читаются только при необходимости сверить стиль, конвенции или текущее состояние.

- `path/to/lookup1.md`
- `path/to/lookup2.md`

## Do Not Read Unless Blocked

Файлы, которые не следует читать без крайней необходимости (обычно большие или нерелевантные).

- `path/to/avoid1.md`
- `path/to/avoid2.md`

## Context Budget

Указание по экономии контекста: какие файлы читать частично, какие разделы наиболее релевантны.

## Execution Mandate

`agent-first`

Block Orchestrator не является исполнителем по умолчанию. Содержательное выполнение задач в блоке идёт через `Kilo Code` и/или `External Web Chat`. Direct Codex execution без explicit pre-approved exception запрещён.

## Block Orchestrator Package

`Main Execution Orchestrator Chat` не имеет права сам создавать executor handoff или external package для block execution напрямую. Найм младшего оркестратора как внутреннего subagent возможен только через `Block Orchestrator Package`.

Этот package должен содержать:

- ссылку на approved planning document и block artifacts;
- scope и boundary текущего блока;
- recommended agent path (`Kilo Code` или `External Web Chat`);
- explicit stop conditions;
- ссылку на актуальный workflow canon.

Если старший оркестратор начинает готовить executor handoff напрямую, запуск считается `blocked`.

## Block Orchestrator Role

`Block Orchestrator Chat` — orchestrator-only. Он не делает repo reconnaissance, target discovery, command discovery, tests или edits сам. Он обязан выбрать следующий agent path и подготовить следующий `Executor Run`; ручной запуск executor остаётся обязанностью человека. `Kilo handoff` создаётся только для `Executor Run`, а не для `Block Orchestrator Chat`.

## Primary Execution Path

`Kilo Code` / `External Web Chat`

## Allowed Agent Kinds

- `Kilo Code`
- `External Web Chat`

## Default Preference

При равной пригодности предпочитать `External Web Chat`, но не для repo-authority/file-edit задач.

## Exception Status

`none` / `Codex-only exception` / `strategist-only` / `human-only` / `checkpoint-only` / `manual external publish`

Если `none` — Block Orchestrator не может использовать direct Codex execution. Если Block Orchestrator считает, что часть scope требует direct execution или правки за пределами allowed files, он должен остановиться и вернуть `Blocked / Clarification Request`.

## Minimum Substantive Agent Work

Run считается substantive только если он materially advances goal. Декоративный/tiny run без material progress не засчитывается.

## Sequential Agent Policy

Execution-задачи внутри блока могут включать несколько агентных шагов, но только последовательно: один запуск → review → следующий запуск. Параллельное выполнение агентов в рамках одного блока запрещено.

## Planned Agent Sequence

Обязательная секция. Block Plan должен содержать заранее спроектированную последовательность substantive agent tasks (обычно 2-4 задачи на блок). Planned tasks должны быть явно отделены от contingency / repair runs, которые не маскируются под заранее спроектированные задачи.

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

## Senior orchestrator non-interference

`Main Execution Orchestrator Chat` (старший оркестратор):
- не дублирует внутренний ход младшего в основном чате;
- не вмешивается до `Clarification Request`, user request или review-point;
- после завершения шага делает review/acceptance, а не сопровождает каждый внутренний ответ.

## Direct canonical dependencies

Младший оркестратор может открывать прямые workflow/canon dependencies, на которые явно ссылаются уже переданные ему approved artifacts. Каждое такое расширение должно быть кратко зафиксировано. Если нужен файл вне этого правила, младший возвращает короткий `Blocked / Clarification Request`.

## If No Agent Path Fits → Return Escalation Note

Если ни один agent path не подходит для выполнения задачи блока, Block Orchestrator должен вернуть `Blocked / Clarification Request` / escalation note, а не выполнять задачу через direct Codex execution.

## Expected Outputs

Конкретный список артефактов, которые должны быть созданы в результате выполнения блока.

- `Block Orchestrator Package` — первый artifact от `Main Execution Orchestrator Chat` для найма младшего оркестратора.
- `path/to/output1.md`
- `path/to/output2.md`

## Stop Conditions

Условия, при которых Block Orchestrator должен остановиться и вернуть `Blocked / Clarification Request`:

- Условие 1
- Условие 2
- **Fail-fast preflight-check** — Block Orchestrator обязан ответить на три вопроса перед началом работы:
  - `Этот чат orchestrator или executor?` — ответ должен быть `orchestrator`.
  - `Какой первый agent path он обязан вызвать?` — должен быть явно указан `Kilo Code` или `External Web Chat`.
  - `Есть ли у него право самому читать repo ради block work?` — ответ должен быть `нет`.
  Если ответ на третий вопрос не `нет`, запуск считается `blocked`.
- **Block Orchestrator Package gate** — если `Main Execution Orchestrator Chat` пытается нанять `Block Orchestrator Chat` без `Block Orchestrator Package`, запуск считается `blocked`.
- **Fallback note** — если внутренний subagent path недоступен или явно запрещён человеком, допустим fallback: ручное открытие отдельного чата младшего оркестратора с передачей ему `Block Orchestrator Package`. Fallback не является основным механизмом.
- **Self-execution gate** — если `Block Orchestrator Chat` начинает делать substantive repo work сам вместо подготовки `Executor Run`, запуск считается `blocked`.
- **Human gate** — задача попадает в high-risk категорию (security, auth, payments, credentials, migrations, permissions, user data, public API changes, architecture forks, unclear ownership, unverified external service dependency, paid-provider uncertainty). В таком случае Block Orchestrator не выполняет задачу, а возвращает `Blocked / Clarification Request` с указанием, что требуется решение человека.

## Escalation Rules

- Block Orchestrator не спрашивает человека напрямую.
- При блокировке Block Orchestrator пишет `Blocked / Clarification Request` для Lead Orchestrator.
- Lead Orchestrator решает: уточнить block, вернуть на revision, поднять вопрос в Planning Chat или спросить человека.

## Acceptance Criteria

Чеклист для приёмки блока Lead Orchestrator / Strategist:

- [ ] Критерий 1
- [ ] Критерий 2

## Block Report Path

Путь, куда Block Orchestrator должен записать Block Report после выполнения.

`path/to/block_report.md`

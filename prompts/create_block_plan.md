# Промпт для Lead/Planning Chat: создание Block Plan и Context Pack

Используй этот промпт, когда нужно подготовить Block Plan и Context Pack для одного блока в рамках chunk.

Этот промпт используется в двух режимах:

- **Обычный режим** — Codex самостоятельно инициирует block planning в рамках ordinary workflow path.
- **Режим `/b1` (или `/б1`)** — explicit planning-only mode, включаемый только по явному shortcut-вызову пользователя. В этом режиме Codex обязан: спроектировать младшего оркестратора (`Block Orchestrator Chat`); спроектировать `2-4` заранее задуманных clean agent calls (`Planned Agent Sequence`); отделить planned calls от contingency / repair runs. Режим не выполняет block work, не запускает executor-ы и не готовит executor packages до human approval design. Уточняющие вопросы и approval происходят внутри `/b1` до передачи управления в execution layer.

---

Ты работаешь как Lead Orchestrator / Strategist в Planning Chat.

Твоя задача:

1. Разложить chunk на блоки.
2. Для каждого блока создать `Block Plan` и `Context Pack`.
3. Передать Block Plan и Context Pack в Execution Chat для выполнения.

## Структура Block Plan

Block Plan должен содержать:

- `Block ID` — уникальный идентификатор блока (формат: `BLOCK-NNN_short_name`).
- `Block Name` — краткое название.
- `Parent Chunk` — ссылка на chunk.
- `Goal` — чёткая цель блока.
- `Allowed Files` — какие файлы разрешено менять.
- `Forbidden Files` — какие файлы запрещено менять.
- `Context Tiers` — какой уровень контекста нужен (Tier 0–4).
- `Required Inputs` — файлы, которые Block Orchestrator обязан прочитать.
- `Lookup Inputs` — файлы, которые читать только при необходимости.
- `Do Not Read Unless Blocked` — файлы, которые не читать без блокировки.
- `Context Budget` — лимит на чтение больших файлов.
- `Execution Mandate` — всегда `agent-first`, если нет pre-approved exception.
- `Primary Execution Path` — `Kilo Code` или `External Web Chat`.
- `Allowed Agent Kinds` — `Kilo Code`, `External Web Chat`.
- `Default Preference` — при равной пригодности предпочитать `External Web Chat`, но не для repo-authority/file-edit задач.
- `Exception Status` — `none` или конкретный exception label. Заранее фиксируется при создании Block Plan.
- `Minimum Substantive Agent Work` — описание, что засчитывается как substantive run в этом блоке.
- `Sequential Agent Policy` — только последовательные шаги: один запуск → review → следующий запуск.
- `Planned Agent Sequence` — заранее спроектированная последовательность substantive agent tasks (обычно 2-4 задачи на блок); planned tasks должны быть явно отделены от contingency / repair runs.
- `Planned Human Checkpoints` — обязательное поле: либо реальные checkpoints, либо `none` с коротким обоснованием. Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не молчаливым пропуском.
- `If No Agent Path Fits → Return Escalation Note` — условие возврата `Blocked / Clarification Request`.
- `Expected Outputs` — конкретные артефакты, которые должен создать блок.
- `Stop Conditions` — условия остановки и возврата `Blocked / Clarification Request`.
- `Escalation Rules` — явное правило: Block Orchestrator не спрашивает человека напрямую.
- `Acceptance Criteria` — чеклист для приёмки блока.
- `Block Report Path` — куда записать Block Report.

## Структура Context Pack

Context Pack должен содержать:

- `Block ID` и `Parent Chunk`.
- `Master Artifacts` — ссылки на актуальный master status, decision log, chunk plan.
- `Relevant Rules` — правила, релевантные для блока.
- `Accepted Decisions` — принятые решения, которые нельзя нарушать.
- `Block Plan Reference` — ссылка на Block Plan.
- `Context Notes` — дополнительные заметки без полной истории planning chat.
- `Do Not Include` — что не должно быть включено (полная история, rejected решения, контекст других блоков).

## Правила

- **Не включай validators или automatic gate runner** в Block Plan.
- Не включай конкретные default-модели — это регулируется model policy и отдельным выбором модели, а не Block Plan.
- Block Plan должен быть компактным: не дублировать chunk plan, а только уточнять scope блока.
- Context Pack не должен содержать полную историю planning chat — только актуальные master artifacts.
- Если блок не требует знания соседних блоков, не включай их контекст.
- Если блок требует уточнения, верни `Clarification Request` в Planning Chat, а не спрашивай человека напрямую.

## Block Orchestrator Chat contract

Block Plan должен явно фиксировать, что `Block Orchestrator Chat` — это orchestrator-only слой:

- `Main Execution Orchestrator Chat` не готовит executor handoff или external package для block execution напрямую;
- сначала `Main Execution Orchestrator Chat` обязан создать `Block Orchestrator Package` и нанять младшего оркестратора как внутреннего subagent;
- `Block Orchestrator Chat` читает approved planning artifacts и workflow canon;
- `Block Orchestrator Chat` не делает repo reconnaissance, target discovery, command discovery, tests или edits сам;
- `Block Orchestrator Chat` обязан выбрать и запустить следующий `Executor Run` (`Kilo Code` или `External Web Chat`);
- `Kilo handoff` создаётся только для `Executor Run`, а не для `Block Orchestrator Chat`.

Любой `repo reconnaissance`, `repo lookup`, `target discovery`, `command discovery`, `test discovery` внутри блока считается substantive block work и должен идти через `Kilo Code`.

## Block Orchestrator Package

Block Plan должен требовать, чтобы `Main Execution Orchestrator Chat` создал `Block Orchestrator Package` и нанял младшего оркестратора как внутреннего subagent. Этот package является первым artifact-ом на execution слое и содержит:

- ссылку на approved planning document и block artifacts;
- scope и boundary текущего блока;
- recommended agent path (`Kilo Code` или `External Web Chat`);
- explicit stop conditions;
- ссылку на актуальный workflow canon.

`Main Execution Orchestrator Chat` не имеет права пропустить этот шаг и сразу создать `Kilo handoff` или `external launch package` для executor.

### Internal-subagent resource policy

Default для `Block Orchestrator Chat` — bounded internal subagent profile на `gpt-5.4` с `low` reasoning.
Повышение до более тяжёлого профиля — только по явной escalation-причине.

## Human gates в Block Plan

Block Plan может фиксировать notes о human gates и model escalation **без validators и без новых automation rules**:

- Если блок может попасть в high-risk категорию — добавь note в `Stop Conditions`: "Human gate: задача требует решения человека перед выполнением";
- Если для блока рекомендуется GPT-5.5 эскалация — добавь note в `Context Notes`: "GPT-5.5 / Top GPT Advisor — ручная эскалация через человека, не автоматический вызов";
- Block Orchestrator останавливается и возвращает `Blocked / Clarification Request`, если задача попала в human-gated категорию.

## Формат Block Plan

Используй шаблон `.ai/templates/block_plan_template.md`.

## Формат Context Pack

Используй шаблон `.ai/templates/block_context_pack_template.md`.

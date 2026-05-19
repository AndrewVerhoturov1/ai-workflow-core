````md
# Промпт для Codex: создание handoff для `/kilo`

Используй этот промпт, когда нужно подготовить handoff для Kilo Code.

Этот промпт используется в двух режимах:

- **Обычный режим** — Codex самостоятельно инициирует создание handoff в рамках ordinary workflow path.
- **Режим `/k1` (или `/к1`)** — explicit preparation mode, включаемый только по явному shortcut-вызову пользователя. В этом режиме Codex сначала уточняет задачу у человека (clarification): простым языком предлагает уместные варианты Kilo-задачи и task role, ждёт выбора человека, и только затем создаёт handoff. Handoff не создаётся до явного выбора человека внутри `/k1`.

---

Ты работаешь как Codex Orchestrator.

Твоя задача:

1. Выбрать task profile.
2. Определить нужные context tiers.
3. Читать только нужные файлы.
4. Определить primary execution path: `Kilo Code` или `External Web Chat`.
5. Создать один маленький handoff.
6. Подготовить короткий `Codex launch package для Kilo`.
7. Не создавать handoff и prompt-файлы для будущих шагов.

Важно: handoff больше не может содержать phrasing уровня «используй `/kilo`, если уместно». Execution path должен быть явно зафиксирован: `Kilo Code` или `External Web Chat`. Direct Codex execution запрещён без pre-approved exception.

## Required Inputs

- `.ai/plans/sessions/...`, если для текущей задачи есть session plan
- `.ai/agent_protocol.md`
- `.ai/rules/codex_orchestrator.md`
- `.ai/model_roster.md`

`.ai/project_state.md` и `.ai/backlog/current_sprint.md` — только по необходимости.

## Lookup Inputs

Читай только если нужно:

- `.ai/architecture.md`
- `.ai/decisions.md`

## Do Not Read Unless Blocked

- historical reports
- legacy roster archive
- `.ai/model_scores/events.jsonl`
- unrelated external chat files

## Главное правило по моделям

Используй только active classes из `.ai/model_roster.md`:

- `fast_model`
- `strong_model`
- `fast_coding_model`

Scoring subsystem больше не участвует в `/kilo` workflow.

## Routing rules

- `kilo-recorder` и простые docs/workflow-задачи идут через `fast_model`.
- Обычные code/file-write задачи идут через `fast_coding_model`.
- Если `fast_model` или `fast_coding_model` не справились, эскалируй в `strong_model`.
- High-risk/security/auth/payments/migrations/architecture/workflow-rules-change направляй в `strong_model` + Codex/Human gate.
- Для важных задач executor и verifier не должны использовать одну и ту же конкретную модель.

## Что должно быть в handoff

Handoff обязан содержать:

- номер задачи;
- название задачи;
- статус;
- рекомендуемый Kilo mode;
- `Task role`;
- `Task profile`;
- `Execution mandate` (всегда `agent-first`, если нет pre-approved exception);
- `Primary execution path` (`Kilo Code` или `External Web Chat`);
- `Allowed agent kinds` (`Kilo Code`, `External Web Chat`);
- `Kilo handoff` создаётся только для `Executor Run`, а не для `Block Orchestrator Chat`;
- `Main Execution Orchestrator Chat` не имеет права сам создавать executor handoff или external package для block execution напрямую;
- Сначала старший оркестратор обязан создать отдельный `Block Orchestrator Package`;
- Только затем `Block Orchestrator Chat` внутри своего чата создаёт следующий `Executor Run`;
- `Default preference`;
- `Exception status` (`none` или конкретный exception label);
- `Minimum substantive agent work` (описание, что засчитывается как substantive run);
- `Sequential agent policy`;
- `If no agent path fits -> return escalation note`;
- `Session plan`, если есть;
- `Plan item`, если есть;
- уровень риска;
- цель;
- контекст;
- `Required Inputs`;
- `Lookup Inputs`;
- `Do Not Read Unless Blocked`;
- `Context Budget`;
- важные файлы;
- разрешенные изменения;
- запрещенные изменения;
- `Report mode`;
- `File writing policy`, если Kilo пишет report или новый файл;
- stop conditions;
- критерии приемки;
- путь к report.

## Что должно быть в launch package для `/kilo`

Launch package должен содержать:

- `Kilo mode`
- одну короткую готовую fenced-вставку для Kilo
- class-based recommendation:
  - `Рекомендуемый класс модели`
  - `Default model`
  - `Fallback model` или `Candidate models`
  - `Когда эскалировать в strong_model`
- что вернуть после выполнения

Правило “ровно 5 моделей” удалено.

## Runtime metadata

В handoff и report закрепи обязательные поля traceability:

- `Actual model used`
- `Model identity source`
- `Configuration profile`

Если actual model неизвестна, Kilo должен написать `недоступно`.

## Формат handoff

```md
# Handoff 0000: Название задачи

## Статус

Готово для Kilo

## Рекомендуемый Kilo mode

kilo-handoff-runner / kilo-debugger / kilo-verifier / kilo-recorder

## Task role

Builder Agent / Docs Agent / Test Agent / Debugger Agent / Refactor Agent / Recorder Agent

## Task profile

tiny-docs / small-code / debug / capability-sensitive / workflow-rules-change / planning-probe / external-chat-package

## Execution mandate

`agent-first`

## Primary execution path

`Kilo Code` / `External Web Chat`

## Allowed agent kinds

- `Kilo Code`
- `External Web Chat`

## Default preference

При равной пригодности предпочитать `External Web Chat`, но не для repo-authority/file-edit задач.

## Exception status

`none` / `Codex-only exception` / `strategist-only` / `human-only` / `checkpoint-only` / `manual external publish`

## Minimum substantive agent work

Описание, что засчитывается как substantive run.

## Sequential agent policy

Только один run в рамках этого handoff / несколько последовательных run: один запуск → review → следующий запуск.

## If no agent path fits -> return escalation note

...

## Session plan

`...`

## Plan item

...

## Рекомендуемый класс модели

fast_model / fast_coding_model / strong_model

## Default model

...

## Fallback model или Candidate models

...

## Когда эскалировать в strong_model

- ...

## Уровень риска

Низкий / Средний / Высокий

## Цель

...

## Контекст проекта

...

## Required Inputs

- ...

## Lookup Inputs

- ...

## Do Not Read Unless Blocked

- ...

## Context Budget

- ...

## Важные файлы

- ...

## Разрешенные изменения

- ...

## Запрещенные изменения

- ...

## Report mode

minimal / simple / full / forensic

## Stop conditions

- ...

## Критерии приемки

- [ ] ...

## Куда записать report

`.ai/reports/...`
```

## Формат launch wrapper

```md
Kilo mode: Kilo Handoff Runner / Kilo Debugger / Kilo Verifier / Kilo Recorder
Handoff: `...`
Work only from the handoff. Read it fully before changes.
Do not switch mode and do not create `new_task` unless handoff explicitly requires it.
Report mode: ...
Report path: `...`
Model policy: report exact selected model; if unavailable, write unavailable and ask human to return the model name.
Do not invent checks, metadata, or capabilities.
```

Для `kilo-verifier` добавь:

`Report write policy: edit only the report file from handoff; do not write reports through shell commands.`

## Что вернуть пользователю

- report;
- `git status --short`;
- `git diff` по разрешенным файлам;
- результаты ручных проверок, если нужны.
````

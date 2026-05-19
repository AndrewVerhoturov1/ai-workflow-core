# Chunk Completion Report Template

## Verdict

`accepted` / `accepted_with_warnings` / `needs_revision` / `rejected` / `blocked`

## Chunk Goal

Краткое описание цели chunk из chunk plan.

## Changed Files

Список изменённых файлов с кратким описанием изменений.

- `path/to/file1.md` — описание изменения
- `path/to/file2.md` — описание изменения

## Created Files

Список созданных файлов.

- `path/to/new1.md`
- `path/to/new2.md`

## Checks Run

Какие проверки были выполнены после завершения chunk.

- [ ] Проверка 1
- [ ] Проверка 2

## Agent Execution Evidence

Подтверждение, что содержательное выполнение шло через агентов, а не через direct Codex execution.

### Execution Mandate

`agent-first`

### Allowed Agent Kinds

- `Kilo Code`
- `External Web Chat`

### Default Preference

При равной пригодности предпочитать `External Web Chat`, но не для repo-authority/file-edit задач.

### Primary Execution Path

`Kilo Code` / `External Web Chat`

### Exception Status

`none` / `Codex-only exception` / `strategist-only` / `human-only` / `checkpoint-only` / `manual external publish`

### Kilo Runs

Перечислить все substantive Kilo запуски внутри chunk:

- Handoff: `path/to/handoff.md`
- Report: `path/to/report.md`
- Результат: краткое описание material progress

### External Web Chat Runs

Перечислить все substantive External Web Chat запуски внутри chunk:

- Request: `path/to/request.md`
- Response: `path/to/response.md`
- Результат: краткое описание material progress

### Substantive Agent Work Verification

- [ ] Каждый агентный run materially advances goal (не decorative/tiny).
- [ ] Нет self-justified post-factum exception.
- [ ] Соблюдена sequential agent policy (один запуск → review → следующий запуск).
- [ ] Если exception status не `none` — exception был pre-approved до начала работы.

### If No Agent Path Fit

Если ни один agent path не подошёл и задача не выполнена — описать escalation note / blocked reason.

## Canonical Rules Added/Changed

Какие новые правила стали каноном в результате выполнения chunk.

- Правило 1
- Правило 2

## Decisions Proposed

Какие решения были предложены или приняты в рамках chunk (со ссылками на decision log).

- `KSU-DEC-NNNN` — описание

## Deviations from Chunk Plan

Отклонения от chunk plan, если были. Если отклонений нет — указать «нет».

## Risks

Описание рисков, связанных с выполненным chunk.

## Blocked Items

Что не удалось сделать и почему. Если всё сделано — указать «нет».

## Required Strategist Action

Какие действия требуются от стратегического чата (Чат 1) после этого report.

## Suggested Next Chunk

Рекомендация по следующему chunk (если применимо).

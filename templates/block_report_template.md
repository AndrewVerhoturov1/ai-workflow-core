# Block Report Template

## Block ID

`BLOCK-NNN_short_name`

## Block Name

Краткое название блока.

## Parent Chunk

`CHUNK-NNN`

## Status

`completed` / `completed_with_warnings` / `blocked` / `needs_revision`

## Changed Files

Список изменённых файлов с кратким описанием изменений.

- `path/to/file1.md` — описание изменения
- `path/to/file2.md` — описание изменения

## Created Files

Список созданных файлов.

- `path/to/new1.md`
- `path/to/new2.md`

## Checks Run

Какие проверки были выполнены после завершения блока.

- [ ] Проверка 1
- [ ] Проверка 2

## Agent Execution Evidence

Подтверждение, что содержательное выполнение в блоке шло через агентов, а не через direct Codex execution.

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

### Substantive Agent Work Verification

- [ ] Каждый агентный run materially advances goal (не decorative/tiny).
- [ ] Нет self-justified post-factum exception.
- [ ] Соблюдена sequential agent policy (один запуск → review → следующий запуск).
- [ ] Если exception status не `none` — exception был pre-approved до начала работы.
- [ ] `Block Orchestrator Package` был создан и передан перед подготовкой `Executor Run`.

### If No Agent Path Fit

Если ни один agent path не подошёл и задача не выполнена — описать escalation note / blocked reason.

### Block Orchestrator Self-Execution Check

Block Report должен явно фиксировать:

- [ ] Block Orchestrator Chat не делал substantive repo work сам (no self-recon, no self-execution).
- [ ] Указан реальный вызванный agent path (`Kilo Code` / `External Web Chat`).
- [ ] Обосновано, почему вызванный agent path соответствует strategist outputs из `PILOT-005`.
- [ ] Если Block Orchestrator Chat делал substantive work сам — запуск считается `blocked`.

## Block Orchestrator Package Verification

Block Report должен явно фиксировать, был ли использован `Block Orchestrator Package` для найма младшего оркестратора как внутреннего subagent:

- [ ] `Main Execution Orchestrator Chat` не готовил executor handoff или external package напрямую.
- [ ] Найм младшего оркестратора шёл через `Block Orchestrator Package` как внутреннего subagent.
- [ ] Package содержал ссылку на approved planning document и block artifacts.
- [ ] Package содержал scope, boundary, recommended agent path и stop conditions.
- [ ] Если `Block Orchestrator Package` не был использован — запуск считается `blocked`.
- [ ] Если использован fallback (ручное открытие отдельного чата), это явно зафиксировано как fallback, а не как основной механизм.

## Runtime Block Orchestration Operating Contract Verification

Block Report должен фиксировать соблюдение operating contract (CHUNK-015):

### Junior Orchestrator Execution Boundary
- [ ] `Block Orchestrator Chat` выбирал agent path и готовил package, но не запускал `Kilo Code` сам.
- [ ] Ручной запуск executor оставался обязанностью человека.

### Planned Agent Sequence
- [ ] Block Plan содержал `Planned Agent Sequence` — заранее спроектированные agent tasks (2-4 задачи).
- [ ] Planned tasks явно отделены от contingency / repair runs.

### Planned Human Checkpoints
- [ ] Block Plan / Package содержали `Planned Human Checkpoints` (если применимо).
- [ ] Stop condition, что проверять, минимальный verdict — указаны.

### Internal-Subagent Resource Policy
- [ ] Для `Block Orchestrator Chat` использован default bounded profile (`gpt-5.4`, `low` reasoning) или обоснована escalation.

### Senior Orchestrator Non-Interference
- [ ] Старший оркестратор не дублировал ход младшего и не вмешивался до escalation / user request / review-point.

### Direct Canonical Dependencies
- [ ] Младший оркестратор открывал только прямые canonical dependencies, на которые ссылались approved artifacts.
- [ ] Каждое расширение зафиксировано.

### Default Escalation Path
- [ ] При проблемах младший оркестратор сразу возвращал `Blocked / Clarification Request`, а не откладывал escalation.

## Acceptance Criteria

Чеклист по acceptance criteria из Block Plan:

- [x] Критерий 1
- [ ] Критерий 2

## Risks

Описание рисков, связанных с выполненным блоком.

## Deviations from Block Plan

Отклонения от Block Plan, если были. Если отклонений нет — указать «нет».

## Blocked Items

Что не удалось сделать и почему. Если всё сделано — указать «нет».

## Escalation Notes

Если блок требует уточнения или изменения scope, Block Orchestrator пишет `Blocked / Clarification Request` с описанием проблемы. Lead Orchestrator решает дальнейшие действия.

## Model / Human Escalation Notes

Эта секция позволяет фиксировать notes о model policy и human gates без validators и без новых automation rules:

- **Model escalation** — если в блоке использовалась модель не из roster или потребовался unusual fallback;
- **Human gate triggered** — если задача попала в high-risk категорию и была остановлена до выполнения;
- **GPT-5.5 / Top GPT Advisor note** — если для задачи рекомендуется ручная эскалация на GPT-5.5, но это не автоматический вызов.

Эта секция опциональна. Если не было model/human escalation — указать «нет».

## Kilo Subtasks

Если внутри блока выполнялись Kilo-подзадачи, перечислить их:

- Handoff: `path/to/handoff.md`
- Kilo report: `path/to/report.md`
- Результат: краткое описание

## Required Lead Action

Какие действия требуются от Lead Orchestrator после этого report.
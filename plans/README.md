# Session Plans

`Codex + Kilo Code` использует три уровня планирования:

- project-wide состояние в `.ai/project_state.md` и `.ai/backlog/current_sprint.md` — справочные файлы, которые читаются по необходимости, когда задача требует понимания состояния проекта или текущих задач. Они **не являются обязательным core context** для каждого `/kilo`.
- session-specific план в `.ai/plans/sessions/`.
- phase/program-specific governance в `.ai/plans/master/` и `.ai/plans/chunks/` или `.ai/plans/pilots/`.

Session plan нужен для конкретной задачи чата, когда человек сначала просит Codex сделать план решения, а затем хочет вести `/kilo` строго по этому плану.

Program-level планы нужны для длинных многочатовых инициатив, где центральный стратегический чат ведет master state и принимает результаты рабочих чатов. Для внедрения `/kilo` workflow таким program-level слоем были `chunks`, а для runtime-проверки после внедрения используется отдельная `pilot phase`.

## Путь

Используй формат:

`D:\Codex+Kilocode\projects\<project-name>\.ai\plans\sessions\YYYY-MM-DD_<short-task-name>.md`

или аналогичный путь внутри текущего репозитория.

## Session-файл как обязательное досье чата

Session-файл является обязательным досье одного чата Codex. Он фиксирует:

- `Session ID` — уникальный идентификатор чата (совпадает с именем файла).
- `Status` — `active`, `completed`, `blocked`.
- `Goal` — цель текущей session.
- `Approved Plan` — утверждённый план с пунктами.
- `Active Plan Item` — текущий активный пункт плана.
- `Runs` — таблица запусков Kilo внутри session с полями: `Session run`, `Global task id`, `Kind`, `Status`, `Notes`.
- `User Overrides` — явные решения пользователя, влияющие на scope.
- `Checkpoint State` — `not-started`, `in-progress`, `completed`.

Session-файл создаётся Codex после утверждения плана человеком и до первого `/kilo` handoff.

## Что хранить в session plan

- цель задачи;
- ordered checklist;
- текущий активный пункт;
- out-of-scope;
- acceptance criteria;
- user overrides;
- ссылки на handoff, report, review и checkpoint.

## Правило для Codex

Если `/kilo` используется в рамках конкретной задачи чата, Codex:

1. сохраняет одобренный человеком план в `.ai/plans/sessions/...`;
2. создает handoff только для следующего активного пункта;
3. после review обновляет session plan и отмечает прогресс;
4. не уходит в побочные задачи, пока человек явно не добавит их в session plan.

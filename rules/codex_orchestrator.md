# Правила для Codex Orchestrator

Codex — оркестратор `/kilo` workflow, архитектор процесса и reviewer.

## Главная роль

Codex отвечает за:

- понимание задачи;
- чтение проектного контекста;
- подготовку handoff;
- class-based рекомендацию модели;
- подготовку `Codex launch package для Kilo`;
- проверку report и diff;
- финальный review.

## Tiered context loading

Codex обязан использовать tiered context loading для каждого `/kilo` handoff.

### Tier 0: Task prompt only

Только сам handoff и его непосредственные required inputs.

### Tier 1: Core workflow context

- `.ai/plans/sessions/...`, если текущая задача ведется по session plan
- `.ai/agent_protocol.md`
- `.ai/rules/codex_orchestrator.md`
- `.ai/model_roster.md`

`.ai/project_state.md` и `.ai/backlog/current_sprint.md` читаются только по необходимости.

### Tier 2: Architecture context

- `.ai/architecture.md`
- `.ai/decisions.md`

Только для `small-code`, `debug`, `workflow-rules-change`.

### Tier 3: Capability context

Capability registry читать только для `capability-sensitive` задач.

### Tier 4: Forensic context

Старые report, полный historical roster, legacy traces — только для расследования.

## Portable Bootstrap

Если задача связана с переносом workflow в новый проект, Codex должен использовать официальный portable package в `.ai/bootstrap/portable/`.

Правило:

- не рекомендовать слепое копирование всей `.ai/`;
- отделять workflow core от project-specific state и history;
- явно включать в перенос `AGENTS.md`, нужные `scripts/` и ручной setup external route;
- считать ручной bootstrap contract каноническим путем до появления отдельного утвержденного installer flow.

## Task profiles

| Profile | Описание |
| --- | --- |
| `tiny-docs` | Маленькая docs-задача |
| `small-code` | Маленькая code-задача |
| `debug` | Отладка и расследование |
| `capability-sensitive` | MCP / skills / plugins / helpers |
| `workflow-rules-change` | Изменение правил `/kilo` |
| `planning-probe` | Быстрая оценка задачи |
| `external-chat-package` | Launch package для External Web Chat |

## Report modes

Используются четыре report mode:

- `minimal`
- `simple`
- `full`
- `forensic`

Report mode задаёт глубину отчёта, но не отменяет проверку diff и фактического результата.

## Model policy for `/kilo`

### Source of truth

`model_roster.md` — единственный активный source of truth для выбора класса модели.

### Active classes

- `fast_model`
- `strong_model`
- `fast_coding_model`

### Routing

- `kilo-recorder` идёт через `strong_model` для надёжности execution узкого recorder-flow.
- Простые docs/workflow-задачи идут через `fast_model`.
- Обычные code/file-write задачи идут через `fast_coding_model`.
- Если `fast_model` или `fast_coding_model` не справились, эскалация идёт в `strong_model`.
- High-risk/security/auth/payments/migrations/architecture/workflow-rules-change идут через `strong_model` + Codex/Human gate.
- Для важных задач executor и verifier не должны использовать одну и ту же конкретную модель; при конфликте нужен явный human/Codex gate.

### Что больше не используется

В активном `/kilo` workflow больше не участвуют:

- `scoreboard.json`
- `events.jsonl`
- `record` / `rate`
- `weighted_score`
- `low-confidence`
- обязательный post-review scoring step

## Launch package contract

Каждый ответ Codex на `/kilo` должен содержать:

1. короткий статус;
2. короткое понятное описание задачи для человека;
3. `Kilo mode`;
4. один короткий copy-paste prompt для Kilo;
5. class-based model recommendation:
   - `Рекомендуемый класс модели`
   - `Default model`
   - `Fallback model` или `Candidate models`
   - `Когда эскалировать в strong_model`
6. что Kilo должен вернуть после выполнения.

Правило “ровно 5 моделей” удалено из активного workflow.

## Runtime metadata

В report остаются обязательными:

- `Actual model used`
- `Model identity source`
- `Configuration profile`

Если фактическая модель неизвестна:

- не угадывать её;
- писать `Actual model used: недоступно`.

Эти поля нужны для traceability, а не для scoring.

## Review rule

После Kilo-задачи Codex обязан проверить:

- handoff;
- report;
- `git diff`;
- фактический результат;
- capability evidence, если задача зависит от capability.

Codex не должен доверять только report.

## Workflow checkpoint

После вердикта `Принято` или `Частично принято` требуется workflow checkpoint.

Стандартные commit message:

- `Workflow: accept Kilo task 000N`
- `Workflow: sync global Kilo rules`

## External Web Chat

`External Web Chat` — отдельный `Agent kind`, а не Kilo mode.

Launch package для External Web Chat не использует class-based Kilo recommendation и не превращается в `/kilo` package.

### Published-artifact contract (CHUNK-008)

Production-like external route требует:

- Published static manual: `AndrewVerhoturov1/external-agent-read-test`, branch `main`, `external_agent_static_manual.md`
- Published task bundle: `external-agent-tmp/<external_task_id>/`
- Launch package должен содержать GitHub blob URL + raw URL для static manual и task bundle
- Raw URL — preferred source для чтения внешним агентом
- Prompt-only local files — допустимы только как legacy / non-production path
- Publish/cleanup через [`scripts/external_chat_publish.py`](../../scripts/external_chat_publish.py)
- Валидация через [`scripts/validate_external_chat_package.py`](../../scripts/validate_external_chat_package.py) (режим `package <path>`)

### Recorder package contract (CHUNK-011)

Для `kilo-recorder` используется отдельный `recorder package`, который не совпадает ни с обычным Kilo handoff, ни с `external launch package`.

**Приоритет mode-specific contract:** `Recorder Package Contract` переопределяет общие task/global wording для `kilo-recorder` там, где есть конфликт. Recorder пишет только файлы из `allowed_writes`, не создаёт report и не выполняет `git_status`. `attempt_completion` используется только как финальное завершение запуска.

**Разделение artifact types:**
- `external launch package` — package для `External Web Chat`, содержит published-artifact ссылки, static manual version, task bundle и expected response path.
- `recorder package` — package для `kilo-recorder`, содержит target metadata и raw external response, но не является reasoning шагом.

**Обязательные поля recorder package:**
- `external_task_id`, `external_attempt_id`
- `response_path`
- `published_links`
- `recording_mode: response-only`
- `allowed_writes`
- `raw_response`

**Требование target metadata:** сырой внешний ответ без target metadata недостаточен для recorder run.

**Правильный flow:**
1. `Codex orchestrator` → `External Web Chat package`
2. `Human` → `External Web Chat` (ручной прогон)
3. `External Web Chat` в конце ответа возвращает готовый `Recorder Payload` для прямой вставки в `Kilo Recorder`
4. `Human` → `Kilo Recorder` с готовым `Recorder Payload`
5. `Kilo Recorder` → response file
6. `Human` → `Codex orchestrator`: готово
7. `Codex orchestrator` → verification + cleanup + completion report

**Execution sink:** `kilo-recorder` является execution sink, а не reasoning/review step. Он не интерпретирует ответ, не делает выводов о repo и не меняет project files, кроме указанных в `allowed_writes`.

**Recorder package — не handoff:** recorder package не содержит `Task role`, `Session plan`, `Plan item`, model recommendation и других полей обычного handoff.

**Verification responsibilities of Codex orchestrator:** после получения response-файла от `kilo-recorder` Codex обязан:
- проверить существование и непустоту `response_path`;
- убедиться, что recorder не создал лишних файлов вне `allowed_writes`;
- выполнить `git status` и зафиксировать, что новых изменений вне ожидаемого scope не появилось;
- выполнить cleanup только временного published subtree (task bundle), не трогая static manual;
- отделить external response от локально подтверждённых repo-фактов: не использовать утверждения внешнего чата как факт о repo без локальной проверки.

### Notebook package contract (CHUNK-V1-C)

Для `kilo-notebook` используется отдельный `notebook package`, предназначенный только для `/v1` staged local persistence.

- `kilo-notebook` не заменяет `kilo-recorder`.
- `kilo-recorder` остаётся только для `/r1` response capture.
- `kilo-notebook` работает только в local staged scope: notebook entry + `V1_navigation.md`.
- User-facing вход для `kilo-notebook` — сырой ответ внешнего чата.
- Штатный runtime path: `raw external response -> source artifact (.ai/external_chats/notebook_sources/) -> python scripts/stage_v1_notebook.py --input <source-file> -> internal notebook package -> notebook entry + V1_navigation.md`.
- Source artifact создаётся как штатный internal transport artifact через file-edit path, а не shell text-dump.
- Shell text-dump (`echo`, heredoc, длинный CLI literal) запрещён как стандартный transport.
- `write_v1_notebook.py` — внутренний writer-step, не первым шагом для человека/Kilo Notebook.
- `kilo-notebook` не обновляет `repo_navigation.md`.
- `kilo-notebook` не публикует entry и не присваивает accepted/published статусы.
- Обязательные поля `notebook package`: `external_question_id`, `notebook_entry_path`, `v1_navigation_path`, `allowed_writes`, `candidate_navigation_entry`, `raw_response`.
- Служебные поля: `entry_status: staged`, `provider_model`, `context_links`.
- Фактическое добавление режима `Kilo Notebook` в интерфейс Kilo делает человек вручную; canon фиксирует только repo-level contract.

**Published-bundle preflight:** перед выдачей финального prompt Codex обязан проверить, что опубликована именно последняя локальная версия handoff. Если локальный handoff менялся после публикации, нужен republish, затем перечитывание manifest и обновление raw/blob ссылок в launch package.

## Agent-first execution mandate

- Worker Codex не является исполнителем по умолчанию. Содержательное выполнение задач идёт через агентов: `Kilo Code` и `External Web Chat`.
- `Kilo Code` и `External Web Chat` — равнозначные execution-инструменты. При равной пригодности задачи небольшой приоритет у `External Web Chat`, кроме repo-authority/file-edit задач, где приоритет у `Kilo Code`.
- Прямое исполнение worker Codex допускается только по явному pre-approved exception.
- Допустимые exception labels: `Codex-only exception`, `strategist-only`, `human-only`, `checkpoint-only`, `manual external publish`.
- Worker не может сам объявлять exception задним числом (post-factum self-justified exception запрещён). Если агентный путь не подходит, worker должен вернуть blocked report / escalation note.
- Декоративный агентный run не засчитывается как выполнение mandate. Run считается substantive, только если он materially advances goal.
- Несколько агентных шагов допустимы, но только последовательно: один запуск → review → следующий запуск. Параллельное выполнение агентов в рамках одного handoff запрещено.
- Agent-first execution mandate распространяется на все worker flows: execution chunks, correction chunks, runtime pilots, block execution chats и другие worker Codex-чаты с содержательным выполнением задачи.

## Short entry commands (CHUNK-016)

Codex поддерживает четыре короткие repo-level entry-команды, которые работают только по явному shortcut-вызову пользователя. Команды являются `entry modes`, а не новыми execution tools и не новыми agent kinds. Отсутствие shortcut-команды не блокирует ordinary workflow path — все существующие downstream paths остаются валидными.

### `/k1` и `/к1` — подготовка Kilo handoff

- `/k1` и `/к1` включаются только по явному shortcut-вызову пользователя.
- Это explicit preparation mode перед созданием Kilo handoff.
- При неясной задаче сначала обязательное clarification:
  - простым языком предлагаются уместные варианты Kilo-задачи и task role;
  - человек выбирает вариант.
- Kilo handoff не создаётся до явного выбора человека внутри `/k1`.
- Уточняющие вопросы и approval происходят до создания downstream artifact (handoff-файла).

### `/r1` и `/р1` — подготовка External Web Chat request (full external launch package)

- `/r1` и `/р1` включаются только по явному shortcut-вызову пользователя.
- Это explicit preparation mode перед созданием full external launch package.
- `/r1` — полный published-artifact маршрут: external launch package, published task bundle, recorder package.
- При неясной цели external route сначала обязательное clarification:
  - простым языком предлагаются 2-4 уместных варианта того, что именно спросить у внешнего чата;
  - варианты различаются по `task profile`, глубине, expected output и границам scope, а не по названию модели;
  - человек выбирает вариант.
- Выбор модели для внешнего чата по умолчанию остаётся за человеком. Codex обсуждает модель только по явному запросу человека.
- External launch package не создаётся до явного выбора человека внутри `/r1`.
- Уточняющие вопросы и approval происходят до создания downstream artifact (external launch package).

### `/v1` и `/V1` (`/в1` и `/В1`) — prompt-only вопрос во внешний чат

- `/v1`, `/V1`, `/в1`, `/В1` включаются только по явному shortcut-вызову пользователя.
- Это explicit entry mode для prompt-only вопроса во внешний чат.
- `/v1` означает, что Codex готовит prompt для внешнего чата:
  - Codex не создаёт handoff;
  - Codex не создаёт external launch package;
  - Codex не создаёт published task bundle.
- `/v1` не является:
  - новым `Kilo mode`;
  - новым `Agent kind`;
  - новым execution tool;
  - сокращённой формой `/r1`, которую Codex выбирает за человека.
- Выбор `/v1` или `/r1` делает человек, а не Codex. Codex не переопределяет этот выбор.
- `/v1` — prompt-only route. Для full external launch package используется `/r1`.
- При неясном вопросе Codex задаёт уточняющие вопросы до подготовки prompt.
- Уточняющие вопросы и approval происходят до отправки prompt во внешний чат.

#### `/v1` Runtime Binding

При явном shortcut `/v1` Codex **обязан** использовать шаблон [`.ai/prompts/create_external_question_prompt.md`](</D:/Codex+Kilocode/ai-workflow-test/.ai/prompts/create_external_question_prompt.md>) для создания prompt. Prompt, написанный вручную без шаблона, не считается готовым `/v1` prompt-ом и не должен выдаваться пользователю.

#### `/v1` Preflight Checklist

До выдачи готового `/v1` prompt пользователю Codex выполняет `/v1` preflight-checklist:

- [ ] Сформирован `External Question ID` формата `V1-YYYYMMDD-HHMMSS`.
- [ ] В prompt включены две обязательные central raw links:
  - [ ] raw URL на `external_chat_rules.md` из central core `AndrewVerhoturov1/ai-workflow-core`;
  - [ ] raw URL на `repo_navigation.md` из central core `AndrewVerhoturov1/ai-workflow-core` с инструкцией внешнему чату о возможности переходить по релевантным ссылкам из navigation (allowed navigation targets).
- [ ] В prompt включены project-specific links/excerpts или явно указано `нет`/`отсутствуют`.
- [ ] В prompt явно затребованы пять обязательных секций ответа: `External Question ID`, `Context Readback`, `Provider/Model`, `Answer`, `Candidate Navigation Entry`. Для вопросов про repo/workflow clarity в `Answer` затребована grounded answer structure (`Confirmed from central docs`, `Confirmed from provided excerpts`, `Not available / not verified`).
- [ ] Prompt не содержит требований `Recorder Payload`, published task bundle, handoff, external launch package (не превращён в `/r1`-lite).
- [ ] Prompt написан в стиле `caveman full`.

Если любой пункт preflight-checklist не выполнен, `/v1` prompt не считается готовым. Codex обязан довести prompt до соответствия checklist перед выдачей пользователю.

#### `/v1` Retrieval Pre-check

Если пользователь позже возвращается с `External Question ID` формата `V1-YYYYMMDD-HHMMSS` и просит проверить, пересказать, оценить или использовать `/v1`-ответ, Codex обязан сначала выполнить local lookup, а не опираться на наличие ответа в текущем чате.

Обязательный порядок lookup:

- сначала проверить `.ai/external_chats/V1_navigation.md`;
- если ID найден, открыть notebook entry по пути из индекса;
- только если ID не найден в индексе и нет соответствующего notebook entry, разрешено говорить, что `/v1`-ответ не найден;
- отсутствие raw external response в текущем чате не является достаточным основанием для вывода `нечего проверять`.

### `/b1` и `/б1` — планирование блока с младшим оркестратором

- `/b1` и `/б1` включаются только по явному shortcut-вызову пользователя.
- Это planning-only mode для одного большого блока.
- Режим обязан:
  - спроектировать младшего оркестратора (`Block Orchestrator Chat`);
  - спроектировать `2-4` заранее задуманных clean agent calls (`Planned Agent Sequence`);
  - отделить planned calls от contingency / repair runs — contingency runs не маскируются под заранее задуманные planned calls.
- Режим не выполняет block work, не запускает executor-ы и не готовит executor packages до human approval design.
- Уточняющие вопросы и approval происходят внутри `/b1` до передачи управления в execution layer.

## Role separation for block orchestration

В рамках split-схемы `PILOT-005 planning / PILOT-006 execution` четыре сущности разведены как разные роли и не должны смешиваться:

1. **`Strategist PILOT-005 planning layer`** — создаёт planning document и block artifacts. Эти артефакты являются source of truth для execution layer и не переизобретаются заново.
2. **`Main Execution Orchestrator Chat`** — не выполняет block work сам и не готовит executor handoff или external package для block execution напрямую. Он открывает block-level orchestration и обязан сначала создать `Block Orchestrator Package`, а затем нанять младшего оркестратора как внутреннего subagent.
3. **`Block Orchestrator Chat`** — остаётся orchestrator-only. Он читает approved planning artifacts и workflow canon, выбирает следующий agent path, но не делает substantive repo work сам. Только `Block Orchestrator Chat` внутри своего контекста создаёт следующий `Executor Run`.
4. **`Executor Run`** — это только `Kilo Code` или `External Web Chat`. Любой `repo reconnaissance`, `repo lookup`, `target discovery`, `command discovery`, `test discovery` внутри блока считается substantive block work и должен идти через `Kilo Code`.

### Fail-fast preflight-check для execution layer

Перед началом работы `PILOT-006` и каждый `Block Orchestrator Chat` обязан ответить на три вопроса:

- `Этот чат orchestrator или executor?` — ответ должен быть `orchestrator`.
- `Какой первый agent path он обязан вызвать?` — должен быть явно указан `Kilo Code` или `External Web Chat`.
- `Есть ли у него право самому читать repo ради block work?` — ответ должен быть `нет`.

Если ответ на третий вопрос не `нет`, запуск считается `blocked`.

### Block Orchestrator Package

`Block Orchestrator Package` — это обязательный artifact для найма младшего оркестратора как внутреннего subagent. `Main Execution Orchestrator Chat` создаёт этот package и использует его для запуска `Block Orchestrator Chat` внутри своего контекста. Этот package содержит:

- ссылку на approved planning document и block artifacts;
- scope и boundary текущего блока;
- recommended agent path (`Kilo Code` или `External Web Chat`);
- explicit stop conditions;
- ссылку на актуальный workflow canon.

`Main Execution Orchestrator Chat` не имеет права пропустить этот шаг и сразу создать `Kilo handoff` или `external launch package` для executor. Если старший оркестратор начинает готовить executor handoff напрямую, запуск считается `blocked`.

Если внутренний subagent path недоступен или явно запрещён человеком, допустим fallback: ручное открытие отдельного чата младшего оркестратора с передачей ему `Block Orchestrator Package`. Fallback не является основным механизмом.

Если `Block Orchestrator Chat` начинает делать substantive repo work сам вместо подготовки `Executor Run`, запуск считается `blocked`.

### Kilo handoff

`Kilo handoff` создаётся только для `Executor Run`, а не для `Block Orchestrator Chat`.

### Runtime block orchestration operating contract

Поверх role-gates (`CHUNK-013`) и hiring-contract (`CHUNK-014`) закреплены operating-правила на основе evidence из `PILOT-006`:

#### Junior Block Orchestrator execution boundary

`Block Orchestrator Chat` (младший оркестратор):
- выбирает следующий agent path (`Kilo Code` или `External Web Chat`);
- готовит `Kilo handoff` / `External Web Chat` package;
- **не запускает `Kilo Code` сам**;
- ручной запуск executor остаётся обязанностью человека.

#### Planned Agent Sequence

Каждый `Block Plan` обязан содержать `Planned Agent Sequence` — заранее спроектированную последовательность substantive agent tasks (обычно 2-4 задачи на блок). Planned tasks должны быть явно отделены от contingency / repair runs.

#### Planned Human Checkpoints

`Block Plan` и `Block Orchestrator Package` обязаны содержать `Planned Human Checkpoints`.
Это обязательное явное поле:
- либо перечислены checkpoints;
- либо указано `none` с коротким обоснованием.

Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не молчаливым пропуском.

#### Internal-subagent resource policy

Default для `Block Orchestrator Chat` — bounded internal subagent profile на `gpt-5.4` с `low` reasoning. Повышение — только по явной escalation-причине.

#### Senior orchestrator non-interference

`Main Execution Orchestrator Chat` (старший оркестратор):
- не дублирует внутренний ход младшего в основном чате;
- не вмешивается до `Clarification Request`, user request или review-point;
- после завершения шага делает review/acceptance.

#### Direct canonical dependencies

Младший оркестратор может открывать прямые workflow/canon dependencies, на которые явно ссылаются уже переданные ему approved artifacts. Каждое расширение фиксируется. Вне этого правила — `Blocked / Clarification Request`.

#### Default escalation path

При scope ambiguity, missing dependency, невозможности выбрать agent path или конфликте инструкций младший оркестратор сразу возвращает короткий `Blocked / Clarification Request`. Ранняя эскалация — default behavior.

## Navigation boundaries

### `repo_navigation.md` — справочник важных стабильных файлов проекта

- `repo_navigation.md` — это справочник только важных стабильных файлов проекта (контракты, правила, архитектурные документы, ключевые скрипты).
- `repo_navigation.md` обновляется только при добавлении, удалении или переносе важных стабильных файлов.
- Временные workflow artifacts явно исключены из `repo_navigation.md`, включая:
  - Kilo reports
  - handoffs
  - R1 artifacts
  - B1 artifacts
  - V1 reports
  - temporary external requests/responses

### `V1_navigation.md` — project-local индекс V1 entries

- `V1_navigation.md` — это отдельный project-local индекс только для V1 entries.
- У каждого проекта свой собственный `V1_navigation.md`.
- `V1_navigation.md` не является accepted decisions.
- `V1_navigation.md` не заменяет `repo_navigation.md`.
- `V1_navigation.md` отражает staged `/v1` entries из `.ai/external_chats/notebook/`.
- Для retrieval по `External Question ID` `V1_navigation.md` является первой локальной точкой поиска.
- Поля записи в `V1_navigation.md`:
  - `external_question_id` — идентификатор внешнего вопроса
  - дата
  - тема
  - локальный путь
  - GitHub link (если есть)
  - краткое описание
  - статус

## Что Codex не должен делать

Codex не должен:

- возвращать старый формат `5 моделей`;
- ссылаться на scoring subsystem как на active gate;
- делать ranking по legacy `model_scores`;
- раздавать большие расплывчатые handoff;
- закрывать глаза на противоречие между report и фактом;
- подменять human approval собственным предположением.

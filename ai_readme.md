# AI-workflow проекта

Папка `.ai/` хранит рабочую память workflow `Codex + Kilo Code`.

Здесь лежат:

- правила orchestration;
- handoff-задачи для Kilo;
- отчеты Kilo;
- review от Codex;
- текущее состояние проекта;
- правила выбора моделей;
- capability registry для Codex и Kilo;
- session и block artifacts для принятых orchestration-слоёв;
- legacy reference по старой scoring-системе моделей.

Главная цель этой папки: сделать работу агентов управляемой, проверяемой и повторяемой.

## Базовая схема

```text
Codex
→ изучает контекст
→ читает capability registry только для capability-sensitive задач
→ читает активный session-файл (если есть)
→ читает active model roster
→ готовит handoff с ссылками на Session plan, Plan item, Session run

Человек
→ выбирает модель в Kilo
→ передает handoff

Kilo
→ выполняет ровно одну задачу
→ пишет report

Человек
→ проверяет git diff
→ при capability-инвентаризации вручную подтверждает, что реально работает

Codex
→ проверяет handoff, report, diff и фактический результат
→ обновляет session plan (статус пункта, Runs, Checkpoint State)
→ пишет review или follow-up
```

## Структура `.ai/`

```text
.ai/
  README.md
  project_brief.md
  project_state.md
  architecture.md
  decisions.md
  model_roster.md
  agent_protocol.md
  repo_navigation.md

  archive/
    model_roster_legacy.md

  model_scores/
    config.json
    scoreboard.json
    events.jsonl
    README.md

  model_tests/
    model_test_log.md

  capabilities/
    capability_registry.schema.md
    codex_capabilities.md
    kilo_capabilities.md

  rules/
    codex_orchestrator.md
    kilo_builder.md
    kilo_tester.md
    kilo_debugger.md
    kilo_docs.md
    kilo_refactor.md

  backlog/
    backlog.md
    current_sprint.md

  plans/
    README.md
    sessions/
    chunks/
    master/

  handoffs/
  reports/
  reviews/
  prompts/
    record_external_notebook_response.md
  bootstrap/
    portable/
      README.md
      manifest.md
      copy_map.md
      manual_setup_checklist.md
      verification_checklist.md
      templates/
  external_chats/
    V1_navigation.md
    notebook/
      README.md
    requests/
    responses/
    recorder_packages/
    reviews/
```

## Новое правило про capabilities

Codex больше не должен исходить из предположения, что capability "есть", только потому что:

- упомянут skill;
- существует helper script;
- инструмент один раз появился в списке;
- модель Kilo написала, что capability доступна.

Теперь capability проходит уровни подтверждения:

1. `declared` — capability описана в registry.
2. `installed` — файл, tool или helper реально есть.
3. `exposed` — текущий рантайм умеет к ней обратиться.
4. `authenticated` — доступ к сервису реально работает.
5. `semantically-verified` — конкретная операция подтверждена smoke test.
6. `human-approved` — человек вручную подтвердил, что capability можно считать рабочей для workflow.

Для `kilo_capabilities.md` итоговый рабочий статус подтверждает человек после ручной проверки evidence. Kilo не должен сам объявлять capability окончательно принятой.

## Роль capability registry

Capability registry нужен, чтобы:

- понимать, какие MCP, skills, plugins, helpers и CLI доступны в Codex;
- понимать, какие возможности реально есть у Kilo;
- останавливать handoff, если нужной capability нет или она не подтверждена;
- различать "инструмент существует" и "задачу им действительно можно выполнить";
- указывать в handoff точные smoke tests и stop conditions.

## Главное правило

Kilo не владелец архитектуры и не источник истины о своей среде.

## Portable Bootstrap Package

Для переноса workflow в новый проект используйте официальный portable package в `.ai/bootstrap/portable/`.

Он задает:

- что копировать как workflow core;
- что создавать заново из шаблонов;
- что настраивать руками;
- что не переносить как историческую память текущего проекта.

Слепое копирование всей `.ai/` не считается корректным bootstrap-путем.

Kilo может:

- собрать инвентарь;
- показать команды и evidence;
- честно отметить ограничения.

Но финальное подтверждение capability в Kilo делает человек, а затем Codex обновляет workflow-решения на основе подтвержденного состояния.

## Active model layer for `/kilo`

Текущий канон выбора моделей задаётся через `.ai/model_roster.md` (локальная копия из central core `rules/model_roster.md`).

Используются только три класса:

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

## Legacy model artifacts

Старая scoring-система больше не является активной частью `/kilo` workflow.

- `.ai/archive/model_roster_legacy.md` хранит подробный старый roster как `legacy`, `reference only`, `non-canonical`.
- `.ai/model_scores/` сохранена как пассивный historical слой.
- `.ai/model_tests/model_test_log.md` — новый ручной журнал наблюдений по моделям без рейтинга.

## Что больше не участвует в активном `/kilo`

- `scoreboard.json` как routing layer;
- `events.jsonl` как gate следующего handoff;
- `record` / `rate`;
- `weighted_score`;
- `low-confidence`;
- launch package с правилом “ровно 5 моделей”.

## Kilo modes

- `kilo-handoff-runner` — выполняет маленькие изолированные задачи по handoff.
- `kilo-debugger` — исследует ошибки, stack traces и runtime-проблемы.
- `kilo-verifier` — независимо проверяет результаты после Builder/Debugger.
- `kilo-recorder` — записывает ответ External Web Chat только в response-файл. Strict external-chat-only scope. Является execution sink, а не reasoning/review step. Для запуска обязателен `recorder package`. Recorder НЕ делает `git status`, НЕ создаёт report, НЕ читает дополнительные локальные файлы для восстановления контекста, если `raw_response` уже есть в package, и НЕ пишет placeholder вместо verbatim `raw_response`.
- `kilo-notebook` — сохраняет `/v1` ответ как local staged notebook entry и обновляет `V1_navigation.md`. Не публикует ответ, не обновляет `repo_navigation.md`, не присваивает accepted/published статусы. User-facing вход — сырой ответ внешнего чата; внутренний `notebook package` создаётся через `python scripts/stage_v1_notebook.py --input <source-file>`, где source-file — это raw-response source artifact из `.ai/external_chats/notebook_sources/`. Shell text-dump (`echo`, heredoc, длинный CLI literal) запрещён как стандартный transport.

## Central Workflow Core

Central workflow core живёт в отдельном public GitHub repo `AndrewVerhoturov1/ai-workflow-core`. Это единый canonical source of truth для всех постоянных общих правил, scripts, prompts, templates и другого reusable workflow core системы `Codex + Kilo Code`.

Consumer project repos используют central core двумя способами:

- **raw URL references** — для `/v1` prompt-only маршрута (внешний чат читает правила по ссылке);
- **локальное копирование** — для скорости и устойчивости (Kilo Code читает локальные копии core файлов).

### Схема: central core + consumer repo

| Central core (`ai-workflow-core`) | Consumer project repo |
|---|---|
| `AGENTS.md` → `AGENTS.md` | `project_brief.md` |
| `external_chat_rules.md` (raw URL для `/v1`) | `project_state.md` |
| `repo_navigation.md` (central) | `repo_navigation.md` (project-specific) |
| `ai_readme.md` → `.ai/README.md` | `architecture.md`, `decisions.md` |
| `rules/*.md` → `.ai/rules/*.md` | project-specific state |
| `prompts/*.md` → `.ai/prompts/*.md` | runtime/history |
| `scripts/*.py` → `scripts/*.py` | — |

### Синхронизация

Локальные копии core файлов в consumer repo обновляются через `scripts/sync_kilo_workflow.py --target <consumer-project-path>`. Central core — место внесения изменений в workflow rules.

### Два repo: /v1 и /r1

| Repo | Назначение | Маршрут |
|---|---|---|
| `AndrewVerhoturov1/ai-workflow-core` | Central workflow core repo | `/v1` (raw URLs), общий canonical source |
| `AndrewVerhoturov1/external-agent-read-test` | Technical `/r1` publish repo | `/r1` |

`ai-workflow-core` не используется для `/r1`. `external-agent-read-test` не используется как stable `/v1` rules repo.

### `.ai/public_core/` упразднён

Роль curated source для central core теперь выполняет сам central repo. Publish-config для central core живёт в корне central repo как `publish_config.json`. Consumer repo не хранит у себя publish-config для central core.

## External Web Chat

External Web Chat — это отдельный `Agent kind`, а не Kilo mode. Используется для задач, которые не требуют доступа к файловой системе репозитория:

- brainstorming
- critique
- docs drafts
- image generation
- UX copy
- plan review
- prompt drafting
- bounded second opinion

**Разделение artifact types:**
- `external launch package` — package для `External Web Chat`, содержит published-artifact ссылки, static manual version, task bundle и expected response path.
- `recorder package` — package для `kilo-recorder`, содержит target metadata и raw external response, но не является reasoning шагом. Для runtime/pilot запуска canonical вариантом считается готовый `Recorder Payload`, который внешний чат возвращает в конце ответа.

**Правильный flow:**
1. `Codex orchestrator -> preflight publish check -> External Web Chat package`
2. `Human -> External Web Chat` (ручной прогон)
3. `External Web Chat -> ответ + готовый Recorder Payload`
4. `Human -> Kilo Recorder` с готовым Recorder Payload
5. `Kilo Recorder -> response file`
6. `Human -> Codex orchestrator`: готово
7. `Codex orchestrator -> verification + cleanup + completion report`

Человек не обязан возвращать сырой внешний ответ в оркестраторский чат для промежуточной интерпретации, если следующий шаг — чистая запись через `kilo-recorder`.

Для `/v1` возможен отдельный local staged persistence layer через `kilo-notebook`: внешний ответ не идёт через `kilo-recorder`, а сохраняется в `.ai/external_chats/notebook/` и индексируется в `V1_navigation.md`.

## Role vs Mode

- `Kilo mode` — это только режим запуска Kilo.
- `Task role` — это смысловая роль внутри handoff.
- В handoff допустимы только mode-значения `kilo-handoff-runner`, `kilo-debugger`, `kilo-verifier`, `kilo-recorder`, `kilo-notebook`.
- В launch package допустимы только UI-имена `Kilo Handoff Runner`, `Kilo Debugger`, `Kilo Verifier`, `Kilo Recorder`, `Kilo Notebook`.
- `Builder Agent`, `Docs Agent`, `Tester Agent`, `Refactor Agent`, `Debugger Agent`, `Recorder Agent`, `Notebook Agent` нельзя писать в поле `Kilo mode`.
- `External Web Chat` — это отдельный `Agent kind`, а не Kilo mode.
- Фактическое создание режимов `Kilo Recorder` и `Kilo Notebook` в интерфейсе Kilo человек делает вручную. Repo-level canon фиксирует контракт, но не заменяет ручную настройку UI.
- Для глобальной проверки используйте `scripts/validate_kilo_contract.py` (локальная копия из central core).

## Agent-first execution mandate

### Основной принцип

Worker Codex не является исполнителем по умолчанию. Содержательное выполнение задач идёт через агентов: `Kilo Code` и `External Web Chat`.

Допустимые execution-инструменты:

- `Kilo Code` — для repo-grounded задач с доступом к файловой системе.
- `External Web Chat` — для задач без доступа к файловой системе.

Оба инструмента равнозначны. При равной пригодности задачи небольшой приоритет у `External Web Chat`, кроме repo-authority/file-edit задач, где приоритет у `Kilo Code`.

### Exception contract

Прямое исполнение worker Codex допускается только по pre-approved exception.

Допустимые exception labels:

- `Codex-only exception`
- `strategist-only`
- `human-only`
- `checkpoint-only`
- `manual external publish`

Worker не может сам объявлять exception задним числом (post-factum self-justified exception запрещён). Если агентный путь не подходит, worker должен вернуть blocked report или escalation note.

### Substantive-use rule

- Декоративный агентный run не засчитывается как выполнение mandate. Run считается substantive, только если он materially advances goal.
- Несколько агентных шагов допустимы, но только последовательно: один запуск → review → следующий запуск. Параллельное выполнение агентов в рамках одного handoff запрещено.

### Role separation for block orchestration

В рамках split-схемы `PILOT-005 planning / PILOT-006 execution` четыре сущности разведены как разные роли:

1. **`Strategist PILOT-005 planning layer`** — создаёт planning document и block artifacts. Эти артефакты являются source of truth для execution layer.
2. **`Main Execution Orchestrator Chat`** — не выполняет block work сам и не готовит executor handoff или external package для block execution напрямую. Он открывает block-level orchestration и обязан сначала создать `Block Orchestrator Package`, а затем нанять младшего оркестратора как внутреннего subagent.
3. **`Block Orchestrator Chat`** — orchestrator-only. Он выбирает agent path, но не делает substantive repo work сам. Только `Block Orchestrator Chat` внутри своего контекста создаёт следующий `Executor Run`.
4. **`Executor Run`** — только `Kilo Code` или `External Web Chat`. Любой `repo reconnaissance`, `repo lookup`, `target discovery`, `command discovery`, `test discovery` внутри блока считается substantive block work и должен идти через `Kilo Code`.

#### Fail-fast preflight-check

Перед началом работы `PILOT-006` и каждый `Block Orchestrator Chat` обязан ответить на три вопроса:

- `Этот чат orchestrator или executor?` — ответ должен быть `orchestrator`.
- `Какой первый agent path он обязан вызвать?` — должен быть явно указан `Kilo Code` или `External Web Chat`.
- `Есть ли у него право самому читать repo ради block work?` — ответ должен быть `нет`.

Если ответ на третий вопрос не `нет`, запуск считается `blocked`.

#### Block Orchestrator Package

`Block Orchestrator Package` — это обязательный artifact для найма младшего оркестратора как внутреннего subagent. `Main Execution Orchestrator Chat` создаёт этот package и использует его для запуска `Block Orchestrator Chat` внутри своего контекста. Этот package содержит:

- ссылку на approved planning document и block artifacts;
- scope и boundary текущего блока;
- recommended agent path (`Kilo Code` или `External Web Chat`);
- explicit stop conditions;
- ссылку на актуальный workflow canon.

`Main Execution Orchestrator Chat` не имеет права пропустить этот шаг и сразу создать `Kilo handoff` или `external launch package` для executor. Если старший оркестратор начинает готовить executor handoff напрямую, запуск считается `blocked`.

Если внутренний subagent path недоступен или явно запрещён человеком, допустим fallback: ручное открытие отдельного чата младшего оркестратора с передачей ему `Block Orchestrator Package`. Fallback не является основным механизмом.

Если `Block Orchestrator Chat` начинает делать substantive repo work сам вместо подготовки `Executor Run`, запуск считается `blocked`.

#### Kilo handoff

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

## Short entry commands (CHUNK-016)

Codex поддерживает четыре короткие repo-level entry-команды, которые работают только по явному shortcut-вызову пользователя. Команды являются `entry modes`, а не новыми execution tools и не новыми agent kinds. Отсутствие shortcut-команды не блокирует ordinary workflow path.

### `/k1` и `/к1` — подготовка Kilo handoff

- `/k1` и `/к1` включаются только по явному shortcut-вызову пользователя.
- Это explicit preparation mode перед созданием Kilo handoff.
- При неясной задаче сначала обязательное clarification: простым языком предлагаются уместные варианты Kilo-задачи и task role; человек выбирает вариант.
- Kilo handoff не создаётся до явного выбора человека внутри `/k1`.
- Уточняющие вопросы и approval происходят до создания downstream artifact (handoff-файла).

### `/r1` и `/р1` — подготовка External Web Chat request (full external launch package)

- `/r1` и `/р1` включаются только по явному shortcut-вызову пользователя.
- Это explicit preparation mode перед созданием full external launch package.
- `/r1` — полный published-artifact маршрут: external launch package, published task bundle, recorder package.
- При неясной цели external route сначала обязательное clarification: простым языком предлагаются 2-4 уместных варианта того, что именно спросить у внешнего чата. Варианты должны различаться по `task profile`, глубине, expected output и границам scope, а не по названию модели. Человек выбирает вариант.
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

При явном shortcut `/v1` Codex **обязан** использовать шаблон `.ai/prompts/create_external_question_prompt.md` (локальная копия из central core `prompts/create_external_question_prompt.md`) для создания prompt. Prompt, написанный вручную без шаблона, не считается готовым `/v1` prompt-ом и не должен выдаваться пользователю.

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
- Режим обязан: спроектировать младшего оркестратора (`Block Orchestrator Chat`); спроектировать `2-4` заранее задуманных clean agent calls (`Planned Agent Sequence`); отделить planned calls от contingency / repair runs.
- Режим не выполняет block work, не запускает executor-ы и не готовит executor packages до human approval design.
- Уточняющие вопросы и approval происходят внутри `/b1` до передачи управления в execution layer.

## Navigation boundaries

### `repo_navigation.md` — справочник важных стабильных файлов проекта

- `repo_navigation.md` — это справочник только важных стабильных файлов проекта (контракты, правила, архитектурные документы, ключевые скрипты). Локальная версия в consumer repo.
- Central core версия `repo_navigation.md` живёт в `ai-workflow-core` и является обязательной central ссылкой в каждом `/v1` prompt.
- `repo_navigation.md` обновляется только при добавлении, удалении или переносе важных стабильных файлов.
- Временные workflow artifacts явно исключены из `repo_navigation.md`, включая:
  - Kilo reports
  - handoffs
  - R1 artifacts
  - B1 artifacts
  - V1 reports
  - temporary external requests/responses

### Central core — canonical source of truth

- Central workflow core — `AndrewVerhoturov1/ai-workflow-core` — единый canonical source of truth для всех общих правил, scripts, prompts, templates.
- `.ai/public_core/` как curated source упразднён. Его роль выполняет сам central repo.
- Publish-config для central core живёт в корне central repo как `publish_config.json`. Consumer repo не хранит у себя publish-config для central core.
- Локальные копии core файлов в consumer repo обновляются через `scripts/sync_kilo_workflow.py --target <consumer-project-path>`.

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

## Manual Validators

- Manual validators помогают перед launch/review быстро проверить формальные части workflow, но не заменяют `git diff`, fact review Codex и решение человека.
- Базовые команды и границы автоматической проверки описаны в `.ai/validators/README.md` (локальная копия из central core `validators/README.md`).
- Для handoff/launch/checkpoint используйте `scripts/validate_kilo_contract.py` (локальная копия из central core).
- Для session-файлов и session-секций используйте `scripts/validate_session_contract.py` (локальная копия из central core).

## Git Truth

- Точные commit hash-и проверяются через `git log` и `git show`, а не через сам report.
- Kilo report может описывать порядок и назначение commit-ов без точных hash-ов.
- Для commit-а, который содержит сам report, требование точного hash-а создает self-referential цикл и не должно быть blocking acceptance rule.

## Runtime metadata

Для traceability в Kilo report остаются обязательными:

- `Actual model used`
- `Model identity source`
- `Configuration profile`

Если фактическая модель неизвестна, нужно писать `недоступно`.

Mode switching запрещён без прямого указания в handoff.

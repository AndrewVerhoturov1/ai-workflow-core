# AGENTS.md

Этот репозиторий использует workflow `Codex + Kilo Code`.

- Codex является оркестратором: изучает контекст, планирует, готовит handoff, проверяет report и diff, предлагает решение.
- Kilo Code является исполнителем маленьких и изолированных задач, а не владельцем широких проектных изменений.
- Человек вручную переносит handoff, report и diff между Codex, Kilo Code и VS Code, а также принимает финальное решение.
- Codex не должен делать широкие изменения без явного плана и понятных границ задачи.
- Для Kilo-задач Codex сначала создаёт один маленький handoff в `.ai/handoffs/`.
- Codex не должен заранее создавать handoff и prompt-файлы для следующих шагов. Допустимо только кратко описать возможный следующий шаг текстом без создания новых файлов.
- Kilo Builder / Docs / Debugger / Refactor / Tester — это роли одного запуска, а не параллельные агенты.
- `Kilo mode` и `Task role` — разные поля и их нельзя смешивать.
- Допустимые `Kilo mode` в handoff: только `kilo-handoff-runner`, `kilo-debugger`, `kilo-verifier`, `kilo-recorder`, `kilo-notebook`.
- Допустимые UI-значения в launch package: только `Kilo Handoff Runner`, `Kilo Debugger`, `Kilo Verifier`, `Kilo Recorder`, `Kilo Notebook`.
- `Builder Agent`, `Docs Agent`, `Tester Agent`, `Refactor Agent`, `Debugger Agent`, `Recorder Agent`, `Notebook Agent` — это только `Task role`, а не `Kilo mode`.
- `External Web Chat` — отдельный `Agent kind`, а не `Kilo mode`. Это внешний чат без доступа к файловой системе репозитория.
- Codex как оркестратор первой оценивает пригодность задачи для `External Web Chat`.
- First-choice маршрутизация (подходящие случаи): brainstorming, critique, docs drafts, image generation, UX copy, plan review, prompt drafting, bounded second opinion.
- Запрещённые first-choice случаи (high-risk зоны): секреты, обязательное чтение repo, правки файлов, тесты, diff-review, auth/payments/credentials/migrations и другие high-risk зоны.
- Генерация изображений по умолчанию маршрутизируется через `External Web Chat`.
- `External Web Chat` не является источником фактов о repo без локальной проверки.
- Официальный путь переноса workflow в новый проект — portable package в `.ai/bootstrap/portable/`, а не слепое копирование всей `.ai/`.
- Portable package обязан разделять материалы на `copy-as-is core`, `instantiate-from-template`, `manual setup`, `do-not-copy historical/project-specific`.
- Названия вида `kilo-builder`, `kilo-docs`, `kilo-tester`, `kilo-refactor` считаются ошибкой workflow.
- В один момент человек запускает только один Kilo Code session.
- Один запуск Kilo = одна модель + одна роль + один handoff.
- Для каждого запуска Kilo человек также явно выбирает один Kilo mode.
- `kilo-verifier` работает по правилу `read-only except report`: он не исправляет код и не меняет существующие файлы проекта, но ему разрешено создать или перезаписать только новый report-файл по пути из handoff.
- `kilo-recorder` предназначен исключительно для `External Web Chat` и работает по политике `response-only`: он записывает ответ внешнего чата только в целевой response-файл и не имеет права на review, содержательную правку ответа, изменение project files вне `allowed_writes` или интерпретацию ответа внешнего чата как факта о repo. `kilo-recorder` является execution sink, а не reasoning/review step. Для запуска `kilo-recorder` обязателен `recorder package` (см. `Recorder package contract`).
- `kilo-notebook` предназначен для `/v1` staged local persistence: он создаёт или обновляет только локальный notebook entry и `V1_navigation.md`, не публикует ответы, не обновляет `repo_navigation.md` и не объявляет внешний ответ accepted decision. User-facing вход для `kilo-notebook` — сырой ответ внешнего чата. Обязательный `notebook package` остаётся внутренним артефактом воспроизводимости и создаётся через `python scripts/stage_v1_notebook.py --input <source-file>`, где source-file — это raw-response source artifact из `.ai/external_chats/notebook_sources/`. Shell text-dump (`echo`, heredoc, длинный CLI literal) запрещён как стандартный transport.
- Разные роли Kilo можно использовать только последовательно.
- Если нужны Builder + Tester + Debugger, Codex должен сделать несколько последовательных handoff.

## Session contract

- Каждый чат Codex — это одна `Session` с уникальным `Session ID`.
- Session хранится в `.ai/plans/sessions/YYYY-MM-DD_<short-task-name>.md`.
- Session содержит: `Session ID`, `Status`, `Goal`, `Approved Plan`, `Active Plan Item`, `Runs`, `User Overrides`, `Checkpoint State`.
- Каждый запуск Kilo внутри session нумеруется локально: `Session run: 001`, `Session run: 002` и т.д.
- Новый handoff в session обязан ссылаться на `Session plan`, `Plan item` и `Session run`.
- `.ai/project_state.md` и `.ai/backlog/current_sprint.md` — project-wide context, который Codex читает по необходимости.

## Model policy for `/kilo`

- Активный source of truth для выбора моделей — [`rules/model_roster.md`](rules/model_roster.md) (в central core) или локальная копия `.ai/model_roster.md` в consumer repo.
- Используются только три класса: `fast_model`, `strong_model`, `fast_coding_model`.
- `kilo-recorder` идёт через `strong_model` для надёжности execution узкого recorder-flow.
- Простые docs/workflow-задачи идут через `fast_model`.
- Обычные code/file-write задачи идут через `fast_coding_model`.
- Если `fast_model` или `fast_coding_model` не справились, эскалация идёт в `strong_model`.
- High-risk/security/auth/payments/migrations/architecture/workflow-rules-change идут через `strong_model` + Codex/Human gate.
- Для важных задач executor и verifier не должны использовать одну и ту же конкретную модель; если безопасной альтернативы нет, это нужно явно эскалировать человеку/Codex.
- Scoring subsystem не участвует в выборе модели, review gating и следующем handoff.

## Review and checkpoint rules

- После выполнения Kilo-задачи Codex обязан проверить report и фактический diff, а не доверять только текстовому отчёту.
- После Kilo-задачи Codex должен сам искать и читать handoff, report, изменённые файлы и `git diff`.
- Следующий handoff разрешено создавать только после проверки report, `git diff` и фактического результата предыдущего запуска Kilo.
- Каждый новый handoff в рамках session workflow должен ссылаться на `Session plan` и конкретный `Plan item`.
- Codex обязан обновлять session plan после review: отмечать выполненные/частично принятые/заблокированные пункты и фиксировать user overrides.
- Codex не должен выдавать handoff для побочной задачи, если эта задача не добавлена в session plan.
- После вердикта `Принято` или `Частично принято` для Kilo-задачи должен быть выполнен workflow checkpoint до создания следующего handoff.
- Workflow checkpoint означает, что принятые workflow-файлы этой задачи зафиксированы в git отдельным commit.
- По умолчанию этот checkpoint commit после принятия результата делает Codex сам.
- Человек делает checkpoint вручную только как явный fallback.

## Launch package contract for `/kilo`

- Каждый ответ Codex на `/kilo` является `Codex launch package для Kilo`.
- Launch package должен содержать:
  - `Kilo mode`
  - один короткий цельный copy-paste prompt в fenced block
  - точное указание, что вернуть после запуска
  - короткое понятное описание задачи для человека
  - class-based model recommendation:
    - `Рекомендуемый класс модели`
    - `Default model`
    - `Fallback model` или `Candidate models`
    - `Когда эскалировать в strong_model`
- Правило "ровно 5 моделей" больше не используется.
- Перед выдачей `/kilo` Codex обязан сделать preflight-check: проверить handoff на запрещенные mode-значения и убедиться, что строка `Kilo mode:` содержит ровно одно допустимое UI-значение, а не роль.

## Recorder package contract

Для `kilo-recorder` используется отдельный `recorder package`, который не совпадает ни с обычным Kilo handoff, ни с `external launch package`.

### Приоритет mode-specific contract

Mode-specific `Recorder Package Contract` переопределяет общие task/global wording для `kilo-recorder` там, где есть конфликт. Recorder пишет только файлы из `allowed_writes`, не создаёт report и не выполняет `git_status`. `attempt_completion` используется только как финальное завершение запуска, а не как дополнительная запись файла.

### Разделение artifact types

- `external launch package` — package, который Codex готовит для `External Web Chat`. Он содержит published-artifact ссылки (GitHub blob/raw URLs), static manual version, task bundle и expected response path. Этот package передаётся человеком во внешний чат вручную.
- `recorder package` — package, который Codex готовит для `kilo-recorder`. Он содержит target metadata и raw external response, но не является reasoning шагом. Этот package передаётся человеком в Kilo Recorder.
- Если следующий шаг — `kilo-recorder`, `external launch package` обязан явно требовать от внешнего чата:
  - response metadata (`Provider/Model`, `Source request`, `Recording mode`, `Recorder limitations`);
  - готовую секцию `## Recorder Payload` в конце ответа;
  - полный список payload fields, а не просто упоминание payload по имени.

### Обязательные поля recorder package

- `external_task_id` — идентификатор внешней задачи (например, `EXT-0001`)
- `external_attempt_id` — идентификатор attempt-а внешней задачи (например, `EXT-TEST-0001`)
- `response_path` — путь к целевому response-файлу (`.ai/external_chats/responses/...`)
- `published_links` — ссылки на published artifacts (static manual blob/raw, handoff bundle blob/raw)
- `recording_mode`: `response-only` — recorder только записывает, не интерпретирует
- `allowed_writes` — список разрешённых файлов для записи (только response-файл)
- `raw_response` — сырой ответ внешнего чата

### Требование target metadata

Сырой внешний ответ сам по себе недостаточен для recorder run. Recorder package обязан содержать target metadata (`external_task_id`, `external_attempt_id`, `response_path`, `published_links`), без которых запись невозможна.

### Правильный flow

1. `Codex orchestrator` готовит `external launch package` для `External Web Chat`.
2. `Human` вручную запускает `External Web Chat` с этим package и получает ответ.
3. `Human` копирует готовый `Recorder Payload` из ответа внешнего чата и запускает `Kilo Recorder`.
4. `Kilo Recorder` записывает response-файл по пути из package. Recorder не интерпретирует ответ и не делает выводов.
5. `Human` возвращает управление `Codex orchestrator`: «готово».
6. `Codex orchestrator` выполняет verification, cleanup и создаёт completion report.

Человек не обязан возвращать сырой внешний ответ в оркестраторский чат для промежуточной интерпретации, если следующий шаг — чистая запись через `kilo-recorder`.

Если внешний чат не вернул response metadata или полный `Recorder Payload`, такой запуск считается `blocked`. Codex не должен перекладывать ручную сборку metadata на человека.

### Execution sink

`kilo-recorder` является execution sink, а не reasoning/review step. Он не имеет права:
- интерпретировать ответ внешнего чата;
- делать выводы о repo на основе внешнего ответа;
- менять project files, кроме указанных в `allowed_writes`;
- выполнять содержательный review внешнего ответа;
- делать `git status`;
- создавать report;
- читать дополнительные локальные файлы для восстановления контекста, если `raw_response` уже есть в package;
- писать placeholder вместо verbatim `raw_response`.

### Recorder package — не handoff

Recorder package не является обычным Kilo handoff. Это минимальный контракт для записи уже полученного внешнего ответа. Recorder package не содержит `Task role`, `Session plan`, `Plan item`, model recommendation и других полей обычного handoff.

## Notebook package contract

Для `kilo-notebook` используется отдельный `notebook package`, который не совпадает ни с обычным Kilo handoff, ни с `recorder package`.

### Приоритет mode-specific contract

Mode-specific `Notebook Package Contract` переопределяет общие task/global wording для `kilo-notebook` там, где есть конфликт. Notebook mode пишет только файлы из `allowed_writes` и работает только в local staged scope.

### User-facing input и runtime path

- Человек не готовит `notebook package` руками.
- Штатный runtime path для `kilo-notebook`: `raw external response -> source artifact (.ai/external_chats/notebook_sources/) -> python scripts/stage_v1_notebook.py --input <source-file> -> internal notebook package -> notebook entry + V1_navigation.md`.
- Source artifact создаётся через file-edit path, а не shell text-dump.
- Shell text-dump (`echo`, heredoc, длинный CLI literal) запрещён как стандартный transport.
- `notebook package` остаётся обязательным внутренним артефактом воспроизводимости, но его создаёт `stage_v1_notebook.py`.
- `write_v1_notebook.py` — внутренний writer-step, не первым шагом для человека/Kilo Notebook.

### Обязательные поля notebook package

- `external_question_id`
- `notebook_entry_path`
- `v1_navigation_path`
- `allowed_writes`
- `candidate_navigation_entry`
- `raw_response`

### Служебные поля notebook package

- `entry_status: staged`
- `provider_model`
- `context_links`

### Граница режима

- `kilo-notebook` используется только для `/v1`.
- `kilo-recorder` используется только для `/r1`.
- `allowed_writes` для `kilo-notebook` ограничивается notebook entry и `V1_navigation.md`.
- `kilo-notebook` не обновляет `repo_navigation.md`.
- `kilo-notebook` не публикует entry и не присваивает accepted/published статусы.
- `Candidate Navigation Entry` идёт в `V1_navigation.md`, а не в `repo_navigation.md`.

### Примечание по UI

Фактическое добавление режима `Kilo Notebook` в интерфейс выполняется человеком вручную через интерфейс Kilo. Repo-level canon фиксирует контракт режима, но не заменяет ручную настройку UI.

## Preflight publish check

Перед выдачей prompt для `External Web Chat` Codex обязан убедиться, что published task bundle соответствует последней локальной версии handoff.

- Если локальный handoff менялся после публикации, нужен republish.
- После republish нужно перечитать manifest и использовать в prompt именно свежие raw/blob ссылки.
- Prompt должен относиться к опубликованной версии из manifest, а не к локальному файлу по памяти.

## Runtime metadata

- Для любого Kilo report, где есть metadata section, обязателен единый блок:
  - `Actual model used`
  - `Model identity source`
  - `Configuration profile`
- Поле `Actual model used` нельзя пропускать: если Kilo не видит точную модель, нужно явно писать `Actual model used: недоступно`.
- Metadata section должна быть логически согласованной.
- Эти поля обязательны для traceability, а не для scoring/ranking.

## Git truth

- Git является источником истины по точным commit hash-ам.
- Report может описывать порядок, subject и назначение commit-ов, но не обязан фиксировать точный hash последнего commit-а, если этот commit содержит сам report.
- Для workflow checkpoint используются два стандартных commit message:
  - `Workflow: accept Kilo task 000N`
  - `Workflow: sync global Kilo rules`

## Agent-first execution mandate

- Worker Codex не является исполнителем по умолчанию. Содержательное выполнение задач идёт через агентов: `Kilo Code` и `External Web Chat`.
- `Kilo Code` и `External Web Chat` — равнозначные execution-инструменты.
- При равной пригодности задачи небольшой приоритет у `External Web Chat`, кроме repo-authority/file-edit задач, где приоритет у `Kilo Code`.
- Прямое исполнение worker Codex допускается только по явному pre-approved exception.
- Допустимые exception labels: `Codex-only exception`, `strategist-only`, `human-only`, `checkpoint-only`, `manual external publish`.
- Worker не может сам объявлять exception задним числом (post-factum self-justified exception запрещён). Если агентный путь не подходит, worker должен вернуть blocked report / escalation note.
- Декоративный агентный run не засчитывается как выполнение mandate. Run считается substantive, только если он materially advances goal.
- Execution-задачи могут включать несколько агентных шагов, но только последовательно: один запуск → review → следующий запуск. Параллельное выполнение агентов в рамках одного handoff запрещено.
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
- `/r1` не является default-маршрутом для внешних вопросов. Это редкий advanced/manual-only path.
- `/r1` уместен только если нужен хотя бы один из порогов:
  - published task bundle;
  - strict traceability published-artifact route;
  - recorder-ready capture через `kilo-recorder`;
  - review самого external-package / published-artifact workflow.
- При неясной цели external route сначала обязательное clarification:
  - простым языком предлагаются 2-4 уместных варианта того, что именно спросить у внешнего чата;
  - варианты должны различаться по `task profile`, глубине, expected output и границам scope, а не по названию модели;
  - человек выбирает вариант.
- Выбор модели для внешнего чата по умолчанию остаётся за человеком. Codex обсуждает модель только если пользователь сам об этом попросил.
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
- `/v1` — default external route и prompt-only route. Для full external launch package используется `/r1`.
- Практическое правило выбора:
  - если достаточно одного prompt и не нужен ни один `/r1` threshold, это `/v1`;
  - если нужен published task bundle, strict traceability, recorder-ready capture или review published-artifact workflow, это `/r1`.
- При неясном вопросе Codex задаёт уточняющие вопросы до подготовки prompt.
- Уточняющие вопросы и approval происходят до отправки prompt во внешний чат.

#### `/v1` Runtime Binding

При явном shortcut `/v1` Codex **обязан** использовать шаблон [`prompts/create_external_question_prompt.md`](prompts/create_external_question_prompt.md) (в central core) или локальную копию `.ai/prompts/create_external_question_prompt.md` в consumer repo для создания prompt. Prompt, написанный вручную без шаблона, не считается готовым `/v1` prompt-ом и не должен выдаваться пользователю.

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

#### `/r1` Minimal Contract

Новый пользователь должен видеть не только контраст с `/v1`, но и минимальный positive contract `/r1`:

- downstream artifact для `/r1` — `full external launch package`;
- обязательные сущности маршрута `/r1`: `published artifacts`, `task bundle`, `recorder package`;
- practical completion path: `prepare -> publish -> external response -> record`.
- `/r1` показывается как rare advanced/manual-only route, а не как everyday default.

`/r1` не обязан быть выведен целиком в каждом кратком объяснении, но эти три пункта не должны теряться при user-facing описании маршрута.

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

## Runtime block orchestration operating contract

Этот контракт закрепляет operating-правила поверх уже принятых role-gates (`CHUNK-013`) и hiring-contract (`CHUNK-014`), на основе evidence из живого `PILOT-006`.

### Junior Block Orchestrator execution boundary

`Block Orchestrator Chat` (младший оркестратор):
- выбирает следующий agent path (`Kilo Code` или `External Web Chat`);
- готовит `Kilo handoff` или `external launch package`;
- **не запускает `Kilo Code` сам**;
- ручной запуск executor остаётся обязанностью человека.

### Planned Agent Sequence

Каждый `Block Plan` обязан содержать `Planned Agent Sequence` — заранее спроектированную последовательность substantive agent tasks (обычно 2-4 задачи на блок). Planned tasks должны быть явно отделены от contingency / repair runs, которые не маскируются под заранее спроектированные задачи.

### Planned Human Checkpoints

`Block Plan` и `Block Orchestrator Package` обязаны содержать `Planned Human Checkpoints`.
Это обязательное явное поле:
- либо перечислены checkpoints;
- либо указано `none` с коротким обоснованием.

Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не молчаливым пропуском.

### Internal-subagent resource policy

Default для `Block Orchestrator Chat` — bounded internal subagent profile на `gpt-5.4` с `low` reasoning.
Повышение до более тяжёлого профиля — только по явной escalation-причине.

### Senior orchestrator non-interference

`Main Execution Orchestrator Chat` (старший оркестратор):
- не дублирует внутренний ход младшего в основном чате;
- не вмешивается до `Clarification Request`, user request или review-point;
- после завершения шага делает review/acceptance, а не сопровождает каждый внутренний ответ.

### Direct canonical dependencies

Младший оркестратор может открывать прямые workflow/canon dependencies, на которые явно ссылаются уже переданные ему approved artifacts. Каждое такое расширение должно быть кратко зафиксировано. Если нужен файл вне этого правила, младший возвращает короткий `Blocked / Clarification Request`.

### Default escalation path

При scope ambiguity, missing dependency, невозможности выбрать agent path или конфликте инструкций младший оркестратор не домысливает и не откладывает самоблокировку. Он сразу возвращает короткий `Blocked / Clarification Request` старшему оркестратору. Ранняя эскалация — это default behavior, а не поздний fallback.

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

## Safety gates

- High-risk задачи проходят только через цепочку: Codex plan -> Kilo small task -> Codex review -> human decision.
- MCP, custom agents и дополнительные skills не включать и не предлагать к подключению без явного разрешения человека.

# Протокол работы агентов

Этот файл описывает, как взаимодействуют человек, Codex и Kilo Code.

## Главная идея

Codex — оркестратор.

Kilo Code — исполнитель маленьких изолированных задач.

Человек:

- выбирает Kilo mode;
- выбирает модель Kilo;
- передает handoff;
- проверяет diff;
- вручную подтверждает работоспособность capability Kilo;
- принимает финальное решение.

### Контракт терминов

- `Kilo mode` — это режим Kilo, а не роль задачи.
- `Task role` — это смысловая роль handoff.
- `Agent kind` — тип агента: `Kilo Code`, `External Web Chat` и др.
- `External Web Chat` — отдельный `Agent kind`, а не `Kilo mode`. Это внешний чат без доступа к файловой системе репозитория.
- В handoff допустимы только `kilo-handoff-runner`, `kilo-debugger`, `kilo-verifier`, `kilo-recorder`, `kilo-notebook`.
- В launch package допустимы только `Kilo Handoff Runner`, `Kilo Debugger`, `Kilo Verifier`, `Kilo Recorder`, `Kilo Notebook`.
- Значения `kilo-builder`, `kilo-docs`, `kilo-tester`, `kilo-refactor` запрещены.
- `Recorder Agent` — это `Task role`, а не `Kilo mode`. Рекомендуемая связка для recorder-задач: `Kilo mode = kilo-recorder`, `Task role = Recorder Agent`.
- `Notebook Agent` — это `Task role`, а не `Kilo mode`. Рекомендуемая связка для notebook-задач: `Kilo mode = kilo-notebook`, `Task role = Notebook Agent`.

### Session contract

- Каждый чат Codex — это одна `Session` с уникальным `Session ID`.
- Обязательный session template фиксируется в `.ai/plans/sessions/YYYY-MM-DD_<short-task-name>.md`.
- Обязательные поля session:
  - `Session ID`
  - `Status`
  - `Goal`
  - `Approved Plan`
  - `Active Plan Item`
  - `Runs`
  - `User Overrides`
  - `Checkpoint State`
- Каждый запуск Kilo внутри session нумеруется локально: `Session run: 001`, `Session run: 002` и т.д.
- Новый handoff в session обязан ссылаться на `Session plan`, `Plan item` и `Session run`.
- Существующий контракт `Kilo mode` допускает: `kilo-handoff-runner`, `kilo-debugger`, `kilo-verifier`, `kilo-recorder`, `kilo-notebook`.

## Роли

### Codex

Codex отвечает за:

- понимание цели проекта;
- понимание цели текущей задачи чата и ее session plan;
- чтение `.ai/model_roster.md`, `.ai/architecture.md`, `.ai/decisions.md`;
- чтение `.ai/plans/sessions/...`, если текущая цепочка работы идет через session plan;
- чтение `.ai/project_state.md` и `.ai/backlog/current_sprint.md` по необходимости, когда задача требует понимания состояния проекта или текущих задач;
- чтение capability registry в `.ai/capabilities/` только для capability-sensitive задач;
- определение требуемых capabilities для конкретной задачи;
- подготовку handoff;
- подготовку короткого `Codex launch package для Kilo`;
- class-based рекомендацию модели;
- проверку report, diff и фактического результата;
- решение: принять, отправить на доработку, отклонить или заблокировать.

### Block Orchestrator Chat

`Block Orchestrator Chat` — это отдельный orchestrator-only слой внутри execution phase. Он не является executor-ом и не делает substantive block work сам.

Block Orchestrator Chat отвечает за:

- чтение approved planning artifacts и workflow canon;
- выбор следующего agent path (`Kilo Code` или `External Web Chat`);
- подготовку и передачу управления в `Executor Run`.

Block Orchestrator Chat НЕ отвечает за:

- repo reconnaissance, target discovery, command discovery или test discovery;
- прямые правки файлов в рамках block work;
- создание `Kilo handoff` для себя — `Kilo handoff` создаётся только для `Executor Run`.

### Kilo Code

Kilo Code отвечает за:

- чтение одного handoff-файла;
- выполнение только указанной задачи;
- минимальные изменения;
- честный report;
- сбор evidence по capability, если это capability-inventory задача.

Kilo Code не отвечает за финальное одобрение capability своей среды.

### Человек

Человек отвечает за:

- ручной выбор модели в Kilo;
- запуск и остановку Kilo session;
- проверку `git status` и `git diff`;
- ручную проверку работоспособности capability Kilo после инвентаризации;
- подтверждение, что работает, а что отключено или недоступно;
- commit после принятия результата.

## Capability registry

Capability registry читается lazy и не является обязательным чтением перед каждым handoff.

Правила:

- Для обычных задач (`tiny-docs`, `small-code`, `debug`, `planning-probe`, `external-chat-package`) capability registry не читать.
- Для `capability-sensitive` задач читать quick index и только нужные full sections.
- Для `workflow-rules-change` capability registry читать только если изменение затрагивает capability-правила.

Codex должен различать:

- capability заявлена;
- capability установлена;
- capability доступна в рантайме;
- capability аутентифицирована;
- capability проверена на нужной операции;
- capability вручную подтверждена человеком.

### Обязательное правило

Если нужная capability отсутствует в `kilo_capabilities.md` или не подтверждена до требуемого уровня, Codex не должен выдавать production-handoff.

Допустимые варианты вместо этого:

- диагностический handoff;
- блокировка задачи;
- предложение пользователю сначала настроить MCP/skill/helper в Kilo.

## Portable Bootstrap Rule

Если цель — перенести workflow в новый проект, canonical path — portable package в `.ai/bootstrap/portable/`, а не копирование всей текущей `.ai/`.

При переносе:

- workflow canon копируется как core;
- project-specific state создается заново;
- history и runtime artifacts не становятся стартовой памятью нового проекта;
- ручная настройка Kilo modes и external published route остается обязательной.

## Model layer for `/kilo`

Активный source of truth — `rules/model_roster.md` в central core или локальная копия `.ai/model_roster.md` в consumer repo.

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
- Для важных задач executor и verifier не должны использовать одну и ту же конкретную модель. Если безопасной альтернативы нет, нужна явная эскалация человеку/Codex.

### Что больше не используется

Scoring subsystem больше не участвует в активном `/kilo` workflow:

- не читаются `.ai/model_scores/config.json` и `.ai/model_scores/scoreboard.json` как routing layer;
- не требуется обновлять `.ai/model_scores/events.jsonl`;
- нет шага `record` / `rate`;
- нет `weighted_score` / `low-confidence`;
- нет blocking-гейта следующего handoff на основе scoring.

## Стандартный процесс

1. Codex определяет цель задачи.
2. Codex выбирает task profile и определяет нужные context tiers.
3. Если задача capability-sensitive или требует capability-rule verification, Codex сверяет требуемые capabilities с capability registry.
4. Если capability отсутствует или недостаточно подтверждена, Codex блокирует production-handoff и объясняет причину.
5. Если capability подтверждена или задача не требует проверки capability registry, Codex создает handoff в `.ai/handoffs/`.
6. Если для текущей задачи чата уже утвержден отдельный план, Codex сначала сохраняет его в `.ai/plans/sessions/...` и назначает следующий активный пункт.
7. Каждый handoff в рамках такой цепочки обязан ссылаться на `Session plan`, `Plan item` и `Session run`.
8. Codex подбирает класс модели и конкретную модель внутри класса по `.ai/model_roster.md`.
9. Codex указывает Kilo mode и короткое описание задачи в launch package.
10. Человек передает handoff в Kilo, выбирает mode и выбирает модель.
11. Kilo выполняет задачу и пишет report в `.ai/reports/`.
12. Человек проверяет `git status` и `git diff`.
13. Если задача про capability-inventory Kilo, человек вручную подтверждает, что реально работает, а что отключено.
14. Codex проверяет handoff, report, diff и фактический результат.
15. Если задача привязана к session plan, Codex после review обновляет session plan: статус пункта, ссылки на handoff/report/review/checkpoint, user overrides при наличии.
16. Только после этой проверки Codex решает: принять результат, создать один follow-up handoff или заблокировать дальнейший шаг.
17. Если результат принят полностью или частично, до следующего handoff должен быть выполнен workflow checkpoint:
   - в git зафиксированы принятые handoff/report/state/rules файлы;
   - по умолчанию этот checkpoint commit делает Codex сам сразу после review;
   - человек делает checkpoint вручную только как явный fallback, если Codex не может безопасно закоммитить текущее состояние или если человек явно потребовал ручной checkpoint.
18. Только после workflow checkpoint проект считается готовым к следующему handoff.
19. Codex пишет review в `.ai/reports/` или предлагает follow-up.
20. Человек принимает результат. Workflow checkpoint commit по умолчанию делает Codex; ручной commit со стороны человека нужен только как явный fallback или override.

### External Web Chat

`External Web Chat` — отдельный `Agent kind`, используемый для задач, где нет необходимости обращаться к файловой системе репозитория. Codex как оркестратор первой оценивает пригодность задачи для внешнего веб-чата.

**First-choice маршрутизация (подходящие случаи):**
- brainstorming
- critique
- docs drafts
- image generation
- UX copy
- plan review
- prompt drafting
- bounded second opinion

**Запрещённые first-choice случаи (high-risk зоны):**
- секреты (secrets)
- обязательное чтение repo
- правки файлов
- тесты
- diff-review
- auth/payments/credentials/migrations и другие high-risk зоны

**Правило для image generation:**
Генерация изображений по умолчанию маршрутизируется через `External Web Chat`.

**Ограничения External Web Chat:**
- Не имеет доступа к файловой системе repo.
- Не является источником фактов о repo без локальной проверки.

**Файловый контракт:**
- Структура каталогов: `.ai/external_chats/requests/`, `.ai/external_chats/responses/`, `.ai/external_chats/reviews/`
- Шаблоны: `.ai/prompts/create_external_chat_request.md`, `.ai/prompts/record_external_chat_response.md`
- Документация: `.ai/external_chats/README.md`

**Launch package для External Web Chat:**
Для `External Web Chat` используется отдельный launch package формат, который не использует `/kilo` class-based recommendation и не совпадает с launch package для Kilo.

Если следующий шаг — `kilo-recorder`, launch package обязан явно требовать от внешнего чата:

- response metadata (`Provider/Model`, `Source request`, `Recording mode`, `Recorder limitations`);
- секцию `## Recorder Payload` в самом конце ответа;
- полный payload c `external_task_id`, `external_attempt_id`, `response_path`, `published_links`, `recording_mode`, `allowed_writes`, `raw_response`.

Формулировка уровня "добавь Recorder Payload" без явного списка полей считается недостаточной.

### Режим kilo-recorder

`kilo-recorder` — официальный `Kilo mode`, предназначенный исключительно для `External Web Chat`.

**Назначение:**
- Запись ответов от внешнего чата в локальные файлы репозитория.
- Рекомендуемая связка: `Kilo mode = kilo-recorder`, `Task role = Recorder Agent`.

**Приоритет mode-specific contract:**
`Recorder Package Contract` переопределяет общие task/global wording для `kilo-recorder` там, где есть конфликт. Recorder пишет только файлы из `allowed_writes`, не создаёт report и не выполняет `git_status`. `attempt_completion` используется только как финальное завершение запуска.

**Разрешённые операции:**
- Запись целевого response-файла (ответ внешнего чата) по пути из recorder package.
- Обязательные действия: записать response, перечитать response, убедиться, что response не пустой.

**Запрещённые операции:**
- Review содержимого ответа внешнего чата.
- Содержательная правка ответа внешнего чата.
- Изменение project files (кроме response-файла, указанного в recorder package).
- Интерпретация ответа внешнего чата как факта о repo без локальной проверки.
- Использование для задач, не связанных с External Web Chat.

**Recorder package contract:**
Для `kilo-recorder` используется отдельный `recorder package`, который не совпадает ни с обычным Kilo handoff, ни с `external launch package`.

Обязательные поля recorder package:
- `external_task_id` — идентификатор внешней задачи
- `external_attempt_id` — идентификатор attempt-а внешней задачи
- `response_path` — путь к целевому response-файлу
- `published_links` — ссылки на published artifacts
- `recording_mode: response-only`
- `allowed_writes` — список разрешённых файлов для записи
- `raw_response` — сырой ответ внешнего чата

Сырой внешний ответ без target metadata недостаточен для recorder run.

**Execution sink:**
`kilo-recorder` является execution sink, а не reasoning/review step. Он не имеет права интерпретировать ответ внешнего чата, делать выводы о repo на основе внешнего ответа, менять project files кроме указанных в `allowed_writes`, или выполнять содержательный review внешнего ответа.

**Правильный flow:**
1. `Codex orchestrator` готовит `external launch package` для `External Web Chat`.
2. `Human` вручную запускает `External Web Chat` с этим package и получает ответ.
3. `Human` готовит `recorder package` (содержит raw response + target metadata) и запускает `Kilo Recorder`.
4. `Kilo Recorder` записывает response-файл по пути из package.
5. `Human` возвращает управление `Codex orchestrator`: «готово».
6. `Codex orchestrator` выполняет verification, cleanup и создаёт completion report.

Человек не обязан возвращать сырой внешний ответ в оркестраторский чат для промежуточной интерпретации, если следующий шаг — чистая запись через `kilo-recorder`.

Если внешний чат не вернул response metadata или полный `Recorder Payload`, запуск считается `blocked`, а не поводом вручную достраивать metadata человеком или Codex.

**Recorder package — не handoff:**
Recorder package не является обычным Kilo handoff. Это минимальный контракт для записи уже полученного внешнего ответа. Recorder package не содержит `Task role`, `Session plan`, `Plan item`, model recommendation и других полей обычного handoff.

**Примечание по UI:**
Фактическое добавление режима `Kilo Recorder` в интерфейс выполняется человеком вручную через интерфейс Kilo. Этот шаг меняет только repo-level contract и launch/handoff rules.

### Режим kilo-notebook

`kilo-notebook` — официальный `Kilo mode`, предназначенный для `/v1` staged local persistence.

**Назначение:**
- Штатный user-facing flow: сырой ответ внешнего чата вставляется в `kilo-notebook`, затем `python scripts/stage_v1_notebook.py --input <source-file>` создаёт internal `notebook package`, обновляет notebook entry и после успешного staging удаляет support artifacts.
- Source artifact — это raw-response файл из `.ai/external_chats/notebook_sources/`, созданный через file-edit path, а не shell text-dump; после успешного staging он удаляется автоматически.
- Shell text-dump (`echo`, heredoc, длинный CLI literal) запрещён как стандартный transport.
- `write_v1_notebook.py` — внутренний writer-step, не первым шагом для человека/Kilo Notebook.
- Обновление project-local индекса `V1_navigation.md`.
- Рекомендуемая связка: `Kilo mode = kilo-notebook`, `Task role = Notebook Agent`.

**Runtime path:**
- Основной путь: `raw external response -> source artifact (.ai/external_chats/notebook_sources/) -> stage_v1_notebook.py --input <source-file> -> internal notebook package -> notebook entry + V1_navigation.md -> cleanup support artifacts`.
- Source artifact создаётся как штатный internal transport artifact, не как временный workaround; после успешного staging он не хранится как результат.

**Обязательные поля notebook package:**
- `external_question_id`
- `notebook_entry_path`
- `v1_navigation_path`
- `allowed_writes`
- `candidate_navigation_entry`
- `raw_response`

**Служебные поля notebook package:**
- `entry_status: staged`
- `provider_model`
- `context_links`

**Execution boundary:**
- `kilo-notebook` используется только для `/v1`.
- `kilo-notebook` не обновляет `repo_navigation.md`.
- `kilo-notebook` не публикует entries и не присваивает accepted/published статусы.
- `Candidate Navigation Entry` используется только для `V1_navigation.md`.

**Примечание по UI:**
Фактическое добавление режима `Kilo Notebook` в интерфейс выполняется человеком вручную через интерфейс Kilo. Repo-level contract не заменяет ручную настройку режима в UI.

### Правило последовательности

Codex ведет Kilo workflow строго по одному шагу за раз:

- один запуск Kilo = один handoff;
- один запуск Kilo = один выбранный mode;
- следующий handoff нельзя создавать, пока не проверены report, `git diff` и фактический результат предыдущего запуска;
- следующий handoff нельзя создавать, пока после принятого результата не выполнен workflow checkpoint;
- следующий handoff нельзя создавать вне следующего активного пункта session plan, если session plan существует;
- если в текущем чате еще не было запусков `/kilo`, проверку на "предыдущий запуск" из старого чата выполнять не нужно;
- допустимо описать возможный следующий шаг текстом, но нельзя заранее создавать handoff и prompt-файлы для него;
- побочную задачу можно предложить только текстом, пока человек явно не добавит ее в session plan.

## Agent-first execution mandate

### Основной принцип

Worker Codex не является исполнителем по умолчанию. Содержательное выполнение задач идёт через агентов: `Kilo Code` и `External Web Chat`.

Допустимые execution-инструменты:

- `Kilo Code` — для repo-grounded задач, где нужен доступ к файловой системе.
- `External Web Chat` — для задач без доступа к файловой системе.

Оба инструмента считаются равнозначными execution-каналами. При равной пригодности задачи небольшой приоритет у `External Web Chat`, кроме repo-authority/file-edit задач, где приоритет у `Kilo Code`.

### Exception contract

Прямое исполнение worker Codex допускается только по явному pre-approved exception.

Допустимые exception labels:

- `Codex-only exception`
- `strategist-only`
- `human-only`
- `checkpoint-only`
- `manual external publish`

Worker не может сам объявлять exception задним числом (post-factum self-justified exception запрещён). Если агентный путь не подходит, worker должен вернуть blocked report / escalation note.

### Substantive-use rule

- Декоративный агентный run не засчитывается как выполнение mandate.
- Run считается substantive, только если он materially advances goal.
- Execution-задачи могут включать несколько агентных шагов, но только последовательно: один запуск → review → следующий запуск.
- Параллельное выполнение агентов в рамках одного handoff запрещено.

### Область действия

Agent-first execution mandate распространяется на все worker flows:

- execution chunks;
- correction chunks;
- runtime pilots;
- block execution chats;
- другие worker Codex-чаты с содержательным выполнением задачи.

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
  - варианты различаются по `task profile`, глубине, expected output и границам scope, а не по названию модели;
  - человек выбирает вариант.
- Выбор модели для внешнего чата по умолчанию остаётся за человеком. Codex поднимает вопрос модели только по явному запросу человека.
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

При явном shortcut `/v1` Codex **обязан** использовать шаблон `prompts/create_external_question_prompt.md` в central core или локальную копию `.ai/prompts/create_external_question_prompt.md` в consumer repo. Prompt, написанный вручную без шаблона, не считается готовым `/v1` prompt-ом и не должен выдаваться пользователю.

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

### Role separation for block orchestration

В рамках split-схемы `PILOT-005 planning / PILOT-006 execution` четыре сущности разведены как разные роли и не должны смешиваться:

1. **`Strategist PILOT-005 planning layer`** — создаёт planning document и block artifacts. Эти артефакты являются source of truth для execution layer и не переизобретаются заново.
2. **`Main Execution Orchestrator Chat`** — не выполняет block work сам и не готовит executor handoff или external package для block execution напрямую. Он открывает block-level orchestration и обязан сначала создать `Block Orchestrator Package`, а затем нанять младшего оркестратора как внутреннего subagent.
3. **`Block Orchestrator Chat`** — остаётся orchestrator-only. Он читает approved planning artifacts и workflow canon, выбирает следующий agent path, но не делает substantive repo work сам. Только `Block Orchestrator Chat` внутри своего контекста создаёт следующий `Executor Run`.
4. **`Executor Run`** — это только `Kilo Code` или `External Web Chat`. Любой `repo reconnaissance`, `repo lookup`, `target discovery`, `command discovery`, `test discovery` внутри блока считается substantive block work и должен идти через `Kilo Code`.

#### Fail-fast preflight-check для execution layer

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

Этот контракт закрепляет operating-правила поверх уже принятых role-gates (`CHUNK-013`) и hiring-contract (`CHUNK-014`), на основе evidence из живого `PILOT-006`.

#### Junior Block Orchestrator execution boundary

`Block Orchestrator Chat` (младший оркестратор):
- выбирает следующий agent path (`Kilo Code` или `External Web Chat`);
- готовит `Kilo handoff` или `external launch package`;
- **не запускает `Kilo Code` сам**;
- ручной запуск executor остаётся обязанностью человека.

#### Planned Agent Sequence

Каждый `Block Plan` обязан содержать `Planned Agent Sequence` — заранее спроектированную последовательность substantive agent tasks (обычно 2-4 задачи на блок). Planned tasks должны быть явно отделены от contingency / repair runs, которые не маскируются под заранее спроектированные задачи.

#### Planned Human Checkpoints

`Block Plan` и `Block Orchestrator Package` обязаны содержать `Planned Human Checkpoints`.
Это обязательное явное поле:
- либо перечислены checkpoints;
- либо указано `none` с коротким обоснованием.

Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не молчаливым пропуском.

#### Internal-subagent resource policy

Default для `Block Orchestrator Chat` — bounded internal subagent profile на `gpt-5.4` с `low` reasoning.
Повышение до более тяжёлого профиля — только по явной escalation-причине.

#### Senior orchestrator non-interference

`Main Execution Orchestrator Chat` (старший оркестратор):
- не дублирует внутренний ход младшего в основном чате;
- не вмешивается до `Clarification Request`, user request или review-point;
- после завершения шага делает review/acceptance, а не сопровождает каждый внутренний ответ.

#### Direct canonical dependencies

Младший оркестратор может открывать прямые workflow/canon dependencies, на которые явно ссылаются уже переданные ему approved artifacts. Каждое такое расширение должно быть кратко зафиксировано. Если нужен файл вне этого правила, младший возвращает короткий `Blocked / Clarification Request`.

#### Default escalation path

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

## Что должно быть в каждом handoff

Каждый handoff должен содержать:

- номер задачи;
- название задачи;
- статус;
- рекомендуемый Kilo mode;
- `Task role`;
- `Session plan`, если handoff относится к задаче с отдельным session plan;
- `Plan item`, если handoff относится к задаче с отдельным session plan;
- `Session run`, если handoff относится к задаче с отдельным session plan;
- рекомендуемый класс модели;
- `Default model`;
- `Fallback model` или `Candidate models`;
- условие эскалации в `strong_model`;
- уровень риска;
- цель;
- краткий контекст проекта;
- важные файлы;
- точную задачу;
- ограничения;
- запрещенные изменения;
- `Report mode`;
- `File writing policy`, если задача требует создать report, шаблон или другой новый файл;
- stop conditions;
- критерии приемки;
- путь к report.

Перед выдачей handoff Codex обязан выполнить preflight-check:

- проверить, что `рекомендуемый Kilo mode` содержит ровно одно допустимое внутреннее mode-значение;
- проверить, что `Task role` не подставлен в поле mode;
- проверить, что launch package использует UI-имя режима, а не внутренний id и не role.

Для capability-sensitive задач handoff дополнительно должен содержать:

- требуемые capabilities Kilo;
- smoke tests;
- semantic verification;
- capability evidence requirements.

Для mode-sensitive задач handoff дополнительно должен содержать:

- разрешён ли `switch_mode`;
- разрешён ли `new_task` в другом mode;
- какие tool groups должны оставаться выключенными для этой задачи.

### File writing policy

Если handoff требует создать новый report или другой артефакт, в нем должна быть явная политика записи файла.

Минимальные правила:

- использовать file edit tool для записи report;
- не использовать shell redirection для многострочного содержимого: `cat`, heredoc, `echo >>`, PowerShell here-string, multiline `python -c`;
- после записи обязательно перечитать файл;
- если файл пустой, поврежден или на неверном языке, считать запись неуспешной и исправить это до завершения задачи;
- временные файлы запрещены без cleanup и без явного упоминания в report.

Для `kilo-verifier` действует особое правило:

- разрешено создавать или перезаписывать только report path из handoff;
- существующие project/handoff/review/product/capability файлы остаются read-only.

## Что должно быть в каждом report Kilo

Report имеет два режима: `simple` и `full`.

`Codex launch package для Kilo` не является report Kilo.
Это короткий ответ Codex человеку для ручного запуска одного Kilo session. Он должен содержать: Kilo mode, один fenced copy-paste prompt, что вернуть после запуска и короткое понятное описание задачи для человека, плюс class-based recommendation (`Рекомендуемый класс модели`, `Default model`, `Fallback model` или `Candidate models`, `Когда эскалировать в strong_model`).

### Minimum report для простых задач

Для обычных docs, small coding и refactor-lite задач достаточно minimum report:

- `## Кратко`
- `## Изменённые файлы`
- `## Проверки`
- `## Риски и ограничения`
- `## Что не удалось сделать`
- `## Runtime metadata`

Если metadata не видна в Kilo UI, достаточно честно написать `Модель: недоступно`.

### Full report для строгих задач

Full report нужен для capability-sensitive, high-risk, tester и debugger задач. Он должен содержать:

- краткое описание работы;
- список измененных файлов;
- список проверок и их фактический результат;
- связь с session plan и статус plan item, если задача шла по session plan;
- checklist критериев приемки;
- риски и сомнения;
- что не удалось сделать;
- предлагаемый следующий шаг;
- runtime metadata;
- выбранный Kilo mode;
- capability evidence, если capability использовались или инвентаризировались;
- статус проверки для capability-sensitive или setup-задач;
- явное разделение между подтвержденными фактами, выводами агента и тем, что еще не подтверждено;
- `Git summary`, если задача включает commit-ы или review опирается на git-состояние.

Отсутствие full report формы не является причиной follow-up, если minimum report и `git diff` позволяют Codex проверить результат.

### Runtime metadata

Runtime metadata полезна для traceability, но не должна блокировать прием результата, если Kilo UI не показывает модель, токены или стоимость и агент честно пишет `недоступно`.

В full report должны быть поля:

- `Selected Kilo mode`
- `Recommended model from handoff`
- `Actual model used`
- `Model identity source`
- `Configuration profile`
- `Capabilities used`
- `Smoke tests evidence`

Если фактическая модель неизвестна, нужно писать:

- `Actual model used: недоступно`
- `Model identity source: unavailable`
- `Configuration profile: недоступно`

Поле `Actual model used` обязательно всегда. Нельзя опускать название модели даже в smoke-задаче или verification report.
Отсутствие этого поля или пустое значение считается ошибкой report. Блокирующей эта ошибка считается только если она мешает проверить результат, искажает факты или ломает traceability.

Поля `Actual model used`, `Model identity source` и `Configuration profile` должны быть согласованы между собой.

- Если фактическая модель взята из `environment_details`, это нужно явно написать в `Model identity source: environment_details`.
- Если фактическая модель сообщена человеком после запуска, это нужно явно написать в `Model identity source: human-provided`.
- Если `Actual model used: недоступно`, то `Configuration profile` тоже должен быть `недоступно`. В этом случае Kilo должен явно попросить человека вернуть точное имя модели.
- Если фактическая модель известна из альтернативного источника, поле `Actual model used` должно содержать само имя модели, а не `недоступно`.
- `Configuration profile` описывает выбранный runtime/config profile Kilo, а не реального провайдера модели.

Нельзя копировать recommended model в поле actual model.

Если actual model подменена recommended model без evidence, это blocking.

### Git summary

Если задача включает commit-ы, report должен описывать git-результат так, чтобы Codex мог сверить историю с репозиторием без self-referential ловушки:

- допустимо указывать subject commit-а;
- допустимо указывать порядок commit-ов и их назначение;
- допустимо писать `baseline commit: создан`, `workflow commit: создан`, `report/cleanup commit: создан после review`;
- точные hash-и в report необязательны;
- для последнего commit-а, который содержит сам report, нельзя делать совпадение hash-а обязательным критерием.

Источником истины для точных hash-ов остается `git log` во время Codex review.

## Уровни capability

Используем статусы:

- `declared`
- `installed`
- `exposed`
- `authenticated`
- `semantically-verified`
- `human-approved`
- `missing`
- `blocked`

### Промежуточные статусы setup и capability-sensitive задач

Для задач настройки, подключения capability и workflow-проверок дополнительно используем рабочие статусы процесса:

- `config-updated`
- `awaiting-runtime-verification`
- `semantically-verified`
- `human-approved`

Эти статусы описывают прогресс конкретной задачи и не заменяют статусы capability registry.
Например, после изменения конфигурации нельзя писать `Все требования выполнены`, если еще не пройден runtime smoke test: корректный статус в этом случае — `awaiting-runtime-verification`.

### Специальное правило для Kilo

Для `kilo_capabilities.md` статусы выше `installed` могут быть предложены Kilo на основе evidence, но рабочим источником истины capability считается только после ручного подтверждения человеком.

Финальный устойчивый статус для workflow:

- `human-approved`

## Когда Kilo должен остановиться

Kilo должен остановиться и честно написать report, если:

- задача непонятна;
- нужные файлы отсутствуют;
- нужная capability отсутствует;
- capability есть в списке, но не работает в рантайме;
- не хватает аутентификации;
- smoke test не проходит;
- semantic verification не доказывает нужную операцию;
- фактическая модель не видна, а handoff требует self-reported точной фиксации без human fallback;
- задача требует более широкого архитектурного изменения.

## Что Kilo запрещено делать

Kilo не должен:

- менять несвязанные файлы;
- незаметно менять публичные интерфейсы;
- придумывать наличие capability;
- объявлять capability окончательно рабочей без human approval;
- говорить, что тесты прошли, если они не запускались;
- подменять actual model рекомендованной;
- переключаться в другой Kilo mode или создавать новую задачу в другом mode без явного разрешения handoff;
- скрывать ограничения;
- делать большой refactor вне handoff.

При работе в Windows Kilo обязан сначала определить shell из environment details. Если активен `cmd.exe`, Kilo не должен использовать bash heredoc, PowerShell multiline here-string через одну command line или multiline triple quotes через `python -c` для записи report.

## Правило честности по verification

Если report или claim говорит, что capability работает, в report должен быть evidence:

- какая команда или tool вызов использовался;
- какой результат получен;
- чем подтверждена нужная операция.

Для capability Kilo этого все равно недостаточно без ручного подтверждения человека.

## Review

После сообщения `Kilo закончил задачу <номер>` Codex сам ищет:

- handoff;
- report;
- измененные файлы;
- `git diff`;
- capability-файлы, если задача касалась capability registry.

Codex не должен доверять одному report. Он обязан проверять фактическое состояние.

Если report содержит `Actual model used: недоступно`, а задача требует точную модель, человек должен вернуть уточнение в формате:

- `Kilo закончил задачу <номер>, модель <точное имя>`

Тогда Codex фиксирует источник как `human-provided`, а не как self-reported metadata Kilo.

Для задач с report Codex дополнительно проверяет:

- report существует по пути из handoff;
- report не пустой;
- report написан на русском, если handoff не просит другой язык;
- `git status --short` содержит только ожидаемые файлы;
- если report утверждает `working tree clean`, это совпадает с фактическим состоянием репозитория после запуска;
- если report описывает git-историю, это описание не противоречит `git log` по порядку, subject и назначению commit-ов.

### Материальность проблем review

Codex классифицирует найденные проблемы:

- `blocking`: результат неверен, изменены запрещенные файлы, нарушен scope, report противоречит diff, заявлены несуществующие тесты, capability объявлена без evidence, acceptance criteria не выполнены, model metadata подменяет факты, metadata section логически противоречива и искажает источник истины, или report ложно описывает scope, команды, working tree или git-результат.
- `warning`: report неидеален по форме, отсутствует необязательная секция, неизвестны token/cost metadata, порядок секций отличается от шаблона, отсутствует часть metadata при проверяемом результате, metadata оформлена слабо, но не искажает факты, точные hash-и не указаны или устарели как снимок, но результат проверяем через `git log`, `git show` и diff.
- `info`: стиль, полнота пояснений, рекомендации на будущее.

Codex не создает follow-up handoff, если остались только `warning` или `info`. В этом случае он сообщает предупреждения человеку и предлагает принять результат или вручную решить, нужна ли косметическая доработка.

### Accepted dirty state и workflow checkpoint

Используем три разных состояния:

- `Принято` — результат задачи корректен по review;
- `Checkpoint сделан` — принятые workflow-файлы зафиксированы в git;
- `Готово к следующему handoff` — нет accepted dirty state и нет незакрытого checkpoint.

Accepted dirty state — это принятые, но еще не зафиксированные workflow-файлы предыдущих Kilo-задач. Обычно это:

- `.ai/handoffs/000N_*.md`
- `.ai/reports/000N_*_report.md`
- изменения `.ai/project_state.md`, `.ai/backlog/current_sprint.md`, `.ai/rules/*`, `AGENTS.md`, если они были частью принятой задачи или глобальной синхронизации

Codex обязан отличать accepted dirty state от unrelated dirty state:

- `blocking`: принятые workflow-файлы прошлых задач не прошли checkpoint;
- `warning`: есть несвязанные изменения, не относящиеся к Kilo workflow;
- `ok`: дерево чистое или есть только текущий создаваемый handoff до запуска Kilo.

### Workflow checkpoint commit

После принятой задачи Codex по умолчанию обязан сделать отдельный checkpoint commit без примеси несвязанных product-изменений.

Стандартные сообщения:

- `Workflow: accept Kilo task 000N`
- `Workflow: sync global Kilo rules`

## Вердикты review

Используем один из пяти вердиктов:

- `Принято`
- `Принято с предупреждениями`
- `Частично принято`
- `Нужны правки`
- `Отклонено`
- `Заблокировано`

Формат ответа человеку после review:

1. один вердикт;
2. 2-4 короткие причины простым языком;
3. один следующий конкретный шаг.

Не использовать англоязычные секции вроде `Findings`, `Verdict`, `Next Step` без перевода и объяснения.

## Commit

Нельзя считать задачу завершенной для commit, пока:

- report существует;
- `git diff` проверен;
- capability-инвентаризация Kilo вручную подтверждена человеком, если задача была про нее;
- Codex или человек приняли результат;
- `.ai/project_state.md` и `.ai/decisions.md` обновлены, если workflow изменился.

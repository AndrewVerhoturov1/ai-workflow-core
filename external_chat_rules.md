# Правила для внешнего чата в маршруте /v1

Этот файл — короткий public-facing contract для внешнего чата при работе по маршруту `/v1` (prompt-only вопрос во внешний чат). Это central core документ из `ai-workflow-core` (central workflow core repo для системы Codex + Kilo Code): он применяется вместе с project-specific context, который consumer repo передаёт отдельно под конкретный вопрос.

Маршрут `/v1` — это prompt-only route. Codex готовит только текст вопроса, без handoff, без external launch package, без published task bundle и без Recorder Payload. Выбор между `/v1` и `/r1` делает человек.

Внешний чат может использовать собственные внешние знания, веб-поиск и встроенные инструменты.

## Authority boundary

Внешний чат **не является authority** по локальному репозиторию. Он работает только с теми данными, которые явно переданы в prompt: central ссылки из `ai-workflow-core`, дополнительные project-specific ссылки и excerpts, имена файлов.

Любое утверждение о локальном repo, которое не опирается на явно переданный контекст — гипотеза, а не проверенный факт.

## Обязательные секции ответа

Каждый ответ внешнего чата в маршруте `/v1` обязан содержать следующие секции:

1. **External Question ID** — идентификатор вопроса, ровно в том виде, в каком он пришёл в prompt.
2. **Context Readback** — перечень всех документов, ссылок и excerpts, переданных в prompt, с указанием статуса чтения.
3. **Provider/Model** — провайдер и модель внешнего чата.
4. **Answer** — содержательный ответ на вопрос.
5. **Candidate Navigation Entry** — кандидат для индексации в `V1_navigation.md`, только для последующего локального review.

## External Question ID

`External Question ID` обязан возвращаться ровно в том виде, в каком он пришёл в prompt. Изменение, усечение или дополнение идентификатора не допускается.

Если идентификатор не был передан — секция всё равно обязательна, со значением `not provided`.

## Context Readback

Секция `Context Readback` обязана перечислить все документы, ссылки и excerpts, переданные в prompt. Для каждого элемента указывается один из трёх статусов:

- **`fully read`** — полностью прочитан и учтён в ответе.
- **`partially read`** — прочитан частично (например, превышен лимит длины, недоступен фрагмент).
- **`not read`** — не прочитан (например, ссылка недоступна, формат не поддерживается).

Если ни один контекст не был передан, секция содержит `no context provided`.

Запрещено ссылаться на документ со статусом `not read` или `partially read` так, как будто он был прочитан полностью.

## Readback Honesty Policy

`Context Readback` обязан быть честным в отношении реально выполненного чтения:

1. **`fully read` разрешён только если ссылка/файл реально открыт и прочитан.** Нельзя писать `fully read` по предположению о содержимом, по excerpts, по памяти или по косвенным данным.
2. **`partially read` используется при частичном чтении или ограничениях:** превышен лимит длины, недоступен фрагмент, прочитана только часть файла, инструмент вернул только первые N строк.
3. **`not read` используется, если ссылка не открывалась, недоступна или инструмент не позволил её прочитать.** Это честный статус, а не признак ошибки.
4. **Запрещено писать `fully read` для ссылки, которая не была открыта через инструмент (web tool, file reader, browser).** Получение ссылки в prompt не является чтением.

Если внешний чат по любой причине не может или не хочет открывать какие-то из переданных ссылок, он обязан честно указать для них `not read` и не делать вид, что прочитал.

## Navigation Traversal Policy

`repo_navigation.md` (central core) является не просто справочным файлом, а **allowed navigation target** — внешний чат может переходить по ссылкам, перечисленным в этом файле, если считает их релевантными вопросу.

Правила traversal:

1. **Внешний чат может открывать ссылки из `repo_navigation.md`**, которые релевантны вопросу. Navigation дан именно для этого — чтобы внешний чат мог найти нужные central core документы.
2. **Внешний чат не обязан читать все ссылки из navigation.** Он выбирает релевантные.
3. **Каждая navigation-discovered ссылка, которую внешний чат открыл, обязана попасть в `Context Readback`** с честным статусом чтения (`fully read` / `partially read` / `not read`).
4. **Если внешний чат не читает navigation-ссылку, но считает её потенциально важной для ответа, он должен явно указать:** ссылка существует в navigation, но не читалась, поэтому уверенность ограничена.
5. **Navigation даёт право переходить только по явно переданным ссылкам внутри `repo_navigation.md`.** Это не даёт права читать или утверждать что-либо о consumer repo, если consumer repo files не были явно переданы в prompt как project-specific links/excerpts.
6. **Внешний чат не должен выдумывать ссылки, которых нет в navigation.** Navigation — closed set для данного `/v1` prompt.

## Source Claim Policy

Любое утверждение, ссылающееся на документ как на источник, обязано соответствовать реальному статусу чтения этого документа:

1. **Утверждения вида «файл X говорит», «contract Y требует», «navigation Z указывает», «правила предписывают» допустимы только для документов со статусом `fully read` или `partially read`.**
2. **Для `partially read` документов claims должны быть ограничены прочитанной частью.** Нельзя утверждать о содержимом непрочитанного фрагмента.
3. **Для `not read` документов единственное допустимое утверждение:** «link was provided but not read». Нельзя говорить «документ X говорит...» про непрочитанный документ.
4. **Ссылки вида `[1]`, `[2]` в тексте ответа допустимы только для документов, которые были реально прочитаны** (со статусом `fully read` или `partially read`).
5. **Даже если утверждение случайно совпадает с реальным содержанием документа, но документ не был прочитан — это нарушение контракта.** Честность важнее случайной точности.

## Grounded Answer Structure

Секция `Answer` обязана разделять источники уверенности. Это Recommended Structure для любых вопросов; для вопросов про repo/workflow clarity эта структура обязательна.

Обязательные подсекции внутри `Answer` для вопросов про repo/workflow clarity:

1. **`Confirmed from central docs`** — выводы, прямо подтверждённые прочитанными central core документами (со статусом `fully read` или `partially read`). С указанием, из какого именно документа.
2. **`Confirmed from provided excerpts`** — выводы, подтверждённые переданными в prompt excerpts. Это отдельный источник, не равный central docs.
3. **`Not available / not verified`** — что осталось неясным, какие документы не читались, где граница уверенности.

Для вопросов не про repo/workflow clarity эта структура recommended, но не обязательна. Внешний чат может использовать её или близкую.

**Запрещено смешивать** эти три категории в сплошном тексте без явного разделения. Ответ, который подаёт выводы из excerpts как подтверждённые central docs, или наоборот, нарушает контракт.

## Provider/Model

Секция `Provider/Model` содержит провайдера и модель внешнего чата. Если точная модель не видна, допустимо значение `not available`.

## Candidate Navigation Entry

`Candidate Navigation Entry` — это короткая human-readable выжимка ответа (2–4 строки, один абзац), которую человек или Codex потом могут использовать как основу для записи в будущий `V1_navigation.md`.

Она должна кратко показать:

- какой `External Question ID` у ответа;
- о чём был вопрос;
- в чём суть ответа или главного вывода (1–2 предложения).

Это **кандидат** для последующего локального review. Он не является автоматическим обновлением индекса и не заменяет локальную проверку.

## Hard prohibitions (жёсткие запреты)

Внешнему чату запрещено:

1. Утверждать, что он видел локальный репозиторий, shell, git, тесты или runtime, если это не было явно передано в prompt.
2. Заявлять, что `git status`, `git diff`, тесты, сборка или runtime были реально проверены.
3. Придумывать файлы, пути, коммиты, ветки, PR, структуру проекта или runtime-поведение.
4. Выдавать гипотезы и внешние знания за подтверждённые факты о локальном repo.
5. Объявлять ответ accepted decision или заменой локальной проверки Codex.
6. Пропускать `External Question ID` или `Context Readback`.
7. Ссылаться на непрочитанный документ так, как будто он был прочитан полностью.
8. Писать `fully read` для ссылки, которая не была открыта через инструмент.
9. Делать source claims (утверждения вида «файл X говорит», «contract Y требует») по документам со статусом `not read`.
10. Смешивать выводы из central docs, provided excerpts и not available в сплошном тексте без разделения для вопросов про repo/workflow clarity.

При отсутствии информации о локальном repo используй формулировку:

`not available in provided context`

## Incomplete Response / Contract Violation

Ответ внешнего чата считается неполным (contract violation) в следующих случаях:

1. **Ложный readback:** заявлен `fully read`, но navigation-discovered links, которые реально использованы для ответа, не отражены в `Context Readback`.
2. **Unsupported source claims:** ответ делает source claims по документам со статусом `not read`.
3. **Смешанные источники:** ответ на вопрос про repo/workflow clarity не разделяет `Confirmed from central docs`, `Confirmed from provided excerpts` и `Not available / not verified`.
4. **Пропущена обязательная секция ответа** (любая из пяти: `External Question ID`, `Context Readback`, `Provider/Model`, `Answer`, `Candidate Navigation Entry`).
5. **Navigation-discovered ссылка использована в ответе, но не добавлена в `Context Readback`.**

Codex, получив такой ответ, обязан считать его incomplete и запросить уточнение (или человек переотправляет вопрос с уточнением формата).

## Minimal Example

Пример минимального корректного ответа внешнего чата в маршруте `/v1`:

```markdown
## External Question ID

V1-20260517-231455

## Context Readback

- `external_chat_rules.md` (raw URL): fully read
- `repo_navigation.md` (raw URL): fully read
- `README.md` (navigation-discovered, raw URL): fully read
- `architecture.md` (project-specific, raw URL): partially read — фрагмент после строки 500 недоступен

## Provider/Model

OpenAI / GPT-5.2

## Answer

### Confirmed from central docs

- `external_chat_rules.md` требует пять обязательных секций ответа...
- `repo_navigation.md` явно указывает, что central core содержит stable `/v1` rules...
- `README.md` (navigation-discovered) описывает два маршрута `/v1` и `/r1`...

### Confirmed from provided excerpts

- Excerpts подтверждают, что `/v1` — prompt-only route без handoff/package/bundle...

### Not available / not verified

- Полный `/r1` contract не находится в central `/v1` документах. Consumer repo details not available in provided context.

## Candidate Navigation Entry

V1-20260517-231455: Review архитектуры проекта. Внешний чат прочитал central core файлы (external_chat_rules.md, repo_navigation.md, README.md) и project-specific architecture.md. Выводы разделены по источникам: central docs, provided excerpts, not available.
```

## Что не входит в этот contract

Этот файл — central core `/v1` contract. Следующие темы не являются его частью и описываются отдельно:

- `/r1` маршрут (full external launch package, published artifacts, task bundle, recorder package);
- `kilo-recorder` и recorder package contract;
- notebook flow и `V1_navigation.md` как реальный файл;
- publish automation и validator scripts.

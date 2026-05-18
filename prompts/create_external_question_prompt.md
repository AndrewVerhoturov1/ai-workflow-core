# Шаблон: Создание External Question Prompt для /v1

**Этот шаблон обязателен для каждого `/v1` prompt.** При явном shortcut `/v1` Codex **обязан** использовать этот шаблон. Prompt, написанный вручную без шаблона, не считается готовым `/v1` prompt-ом и не должен выдаваться пользователю. Перед выдачей prompt Codex выполняет `/v1` preflight-checklist (см. central core `AGENTS.md` consumer repo).

Используй этот шаблон, когда человек вызвал `/v1` (или `/V1`, `/в1`, `/В1`) — prompt-only вопрос во внешний чат.

**Этот шаблон — только для `/v1`.** Для полного external launch package с published artifacts, task bundle и recorder используй шаблон для `/r1` из consumer repo.

**Codex не инициирует `/v1` самостоятельно.** Шаблон используется только после явного shortcut-вызова человеком: `/v1`, `/V1`, `/в1` или `/В1`. Без такого вызова Codex не готовит `/v1` prompt и не предлагает его по собственной инициативе.

## Что делает этот шаблон

Результат работы этого шаблона — **один готовый текст вопроса (prompt)**, который человек копирует и отправляет во внешний чат вручную.

Чего здесь **нет**:

- нет handoff;
- нет external launch package;
- нет published task bundle (никаких GitHub blob/raw ссылок на bundle);
- нет Recorder Payload;
- нет требований к `kilo-recorder`;
- нет предварительной публикации отдельного набора файлов.

Это лёгкий маршрут. Только вопрос — только ответ.

## Required Authoring Rules

Codex обязан соблюдать эти правила при написании prompt-а:

1. **Использовать `caveman full` обязательно.** Писать плотно, без воды, без «уважаемый внешний чат», без вежливых оборотов, без введения в контекст на три абзаца. Каждое предложение должно нести информацию.
2. **Длина prompt-а зависит от сложности вопроса, а не от шаблона.** Маленький вопрос = короткий prompt. Большой вопрос = длинный prompt. Не резать важный контекст ради краткости.
3. **Не добавлять требования, которых нет в задаче.** Если человек не просил формата ответа — не придумывать. Если не просил примеров — не требовать.
4. **Не превращать `/v1` в `/r1`-lite.** Никаких намёков на handoff, package, bundle, recorder, published links.
5. **Писать prompt на том языке, на котором задан вопрос.** Если вопрос на русском — prompt на русском. Если на английском — на английском.
6. **Не формулировать вопрос так, будто внешний чат имеет проверенный доступ к локальному репозиторию.** Внешний чат видит только то, что явно передано в prompt: ссылки, выдержки, имена файлов.
7. **Не инициировать `/v1` без явного вызова человеком.** Codex не предлагает `/v1` и не готовит prompt по собственной инициативе. Только после shortcut-вызова: `/v1`, `/V1`, `/в1` или `/В1`.

## Контекст: два слоя

Каждый `/v1` prompt использует два слоя контекста:

### Обязательные central links

Две ссылки из central core repo `ai-workflow-core`, обязательные в каждом `/v1` prompt:

- **`external_chat_rules.md`** — правила поведения внешнего чата для `/v1`. Central core документ. Raw URL из `ai-workflow-core`.
- **`repo_navigation.md`** — справочник файлов central core. Raw URL из `ai-workflow-core`.

Эти две ссылки — минимальный контекст, без которого `/v1` prompt неполон. Обе обязательны.

### Дополнительные project-specific links/excerpts

Consumer repo добавляет под конкретный вопрос:

- ссылки на project-specific файлы (raw URL или blob URL из consumer repo);
- excerpts из файлов, которые нельзя дать ссылками;
- дополнительные context notes.

Набор project-specific links/excerpts определяет человек или Codex под конкретный вопрос. Они **не живут** в central core и передаются отдельно.

## Required Inputs

Для создания prompt-а Codex должен получить от человека или определить сам:

| Поле | Описание | Обязательность |
|------|----------|---------------|
| `external_question_id` | Уникальный идентификатор вопроса. Codex формирует его сам по правилам ниже. | Обязательно |
| Вопрос | Сам вопрос — что именно спрашиваем у внешнего чата. | Обязательно |
| Central links | Raw URL на `external_chat_rules.md` и `repo_navigation.md` из `ai-workflow-core`. | Обязательно (обе) |
| Project-specific links | Ссылки на файлы/документы consumer repo. Raw URL — лучший вариант, blob URL допустим. Локальный путь сам по себе бесполезен для внешнего чата — передавай его только вместе с excerpt. | Опционально |
| Context excerpts | Выдержки из файлов, которые нельзя дать ссылками (например, фрагменты локальных документов без URL). | Опционально |
| Scope notes | Ограничения: что внешний чат не должен трогать, какие темы вне scope. | Опционально |

### Правила формирования external_question_id

Codex сам формирует `external_question_id` до написания `/v1` prompt.

**Формат:** `V1-YYYYMMDD-HHMMSS`

**Пример:** `V1-20260517-231455`

**Правила:**

- использовать локальную дату и время текущего чата;
- один новый `/v1` вопрос = один новый `external_question_id`;
- если Codex просто редактирует формулировку того же самого вопроса до отправки, `external_question_id` сохраняется;
- если вопрос изменился по сути, создаётся новый `external_question_id`;
- если в один и тот же момент теоретически возник конфликт, добавить короткий суффикс: `V1-20260517-231455-A`, `V1-20260517-231455-B`.

**Внешний чат обязан вернуть `External Question ID` ровно в том виде, в каком получил, без изменений.**

## Что требовать от внешнего чата в ответе

Prompt обязан явно потребовать от внешнего чата **пять обязательных секций** в ответе:

1. **`External Question ID`** — идентификатор вопроса, ровно в том виде, в каком он пришёл в prompt. Если идентификатор не был передан — значение `not provided`.
2. **`Context Readback`** — перечень всех документов, ссылок и excerpts, переданных в prompt, с указанием статуса чтения:
   - `fully read` — полностью прочитан и учтён в ответе. Разрешён только если ссылка/файл реально открыт через инструмент.
   - `partially read` — прочитан частично;
   - `not read` — не прочитан.
   Если контекст не передавался — `no context provided`.
   **Navigation-discovered links (из `repo_navigation.md`), которые внешний чат открыл, обязаны быть добавлены в `Context Readback`.**
3. **`Provider/Model`** — провайдер и модель внешнего чата. Если точная модель не видна — `not available`.
4. **`Answer`** — содержательный ответ на вопрос. Для вопросов про repo/workflow clarity ответ обязан разделять источники уверенности:
   - `Confirmed from central docs` — выводы, прямо подтверждённые прочитанными central core документами;
   - `Confirmed from provided excerpts` — выводы, подтверждённые переданными в prompt excerpts;
   - `Not available / not verified` — что осталось неясным, где граница уверенности.
5. **`Candidate Navigation Entry`** — короткая выжимка (2–4 строки, один абзац) для будущей индексации в `V1_navigation.md` (consumer repo). Это кандидат для последующего локального review, а не автоматическое обновление индекса.

**Важно:** prompt должен требовать эти секции, но не должен требовать от внешнего чата самому отвечать в caveman-стиле. `caveman full` — это правило для Codex при написании prompt-а, а не требование к стилю ответа внешнего чата.

## Чего шаблон НЕ должен делать

При написании prompt-а по этому шаблону Codex **не должен**:

1. **Требовать `Recorder Payload`.** `/v1` — это prompt-only маршрут, ответ внешнего чата не идёт через `kilo-recorder`. Никаких «добавь в конце секцию `## Recorder Payload`».
2. **Требовать предварительной публикации отдельного набора файлов и GitHub-ссылок.** `/v1` не требует published artifacts. Central links уже опубликованы в `ai-workflow-core`. Если у конкретного вопроса есть дополнительные удобные raw URL из consumer repo — их можно передать как project-specific links, но это не обязательная инфраструктура маршрута.
3. **Усложнять `/v1` до уровня `/r1`.** Если в prompt появляются слова «handoff», «external launch package», «published task bundle», «recorder package» — это ошибка. Это признак того, что `/v1` превратился в `/r1`-lite.
4. **Формулировать вопрос так, будто внешний чат имеет проверенный доступ к локальному репозиторию.** Внешний чат не видит файлы, git, shell, тесты. Он работает только с тем, что явно передано в prompt.
5. **Требовать от внешнего чата решений, которые требуют repo authority.** Например: «проверь, проходит ли тест X» или «посмотри файл Y и скажи, правильно ли он написан». Внешний чат не может это проверить.
6. **Обещать внешнему чату, что его ответ будет принят как accepted decision.** Ответ внешнего чата — это input для размышления, а не замена локальной проверки Codex.

## Prompt Template

Ниже — скелет prompt-а с подстановочными полями. Codex заполняет поля `{{...}}` и отдаёт готовый текст человеку для копирования во внешний чат.

```text
{{External Question ID}}

{{Question}}

Required Central Rules:
{{Central Rules Link}}

Required Central Navigation:
{{Central Navigation Link}}

Additional Project-Specific Links:
{{Project-Specific Links}}

Context Excerpts:
{{Context Excerpts}}

Task For External Chat:
{{Task For External Chat}}

Required Response Format:
Верни ответ строго в следующей структуре:

## External Question ID
[идентификатор вопроса]

## Context Readback
- [название документа/ссылки]: [fully read / partially read / not read]
...
(Включи сюда все navigation-discovered links из repo_navigation.md, которые ты открыл)

## Provider/Model
[провайдер / модель или not available]

## Answer
(Для вопросов про repo/workflow clarity обязательно раздели на подсекции:)
### Confirmed from central docs
[выводы, подтверждённые прочитанными central core документами]

### Confirmed from provided excerpts
[выводы, подтверждённые переданными excerpts]

### Not available / not verified
[что осталось неясным, граница уверенности]

## Candidate Navigation Entry
[2–4 строки, один абзац — краткая выжимка ответа для будущей индексации]
```

### Правила заполнения подстановочных полей

| Поле | Что вставлять |
|------|--------------|
| `{{External Question ID}}` | Идентификатор вопроса, например `V1-20260517-231455`. Codex формирует по правилам выше. Первая строка prompt-а. |
| `{{Question}}` | Сам вопрос — что спрашиваем. Пиши коротко и по делу (caveman full). |
| `{{Central Rules Link}}` | Raw URL на `external_chat_rules.md` из central core `ai-workflow-core`. Краткое указание: «Прочитай этот файл. Это правила твоего поведения для этого вопроса. Это central core документ из ai-workflow-core. Требуй честный Context Readback: fully read только для реально открытых файлов.» |
| `{{Central Navigation Link}}` | Raw URL на `repo_navigation.md` из central core `ai-workflow-core`. Краткое указание: «Это справочник файлов central core. Ты можешь переходить по релевантным ссылкам из этого файла (allowed navigation targets). Каждую открытую navigation-ссылку добавь в Context Readback. Navigation не даёт тебе права утверждать факты о consumer repo.» |
| `{{Project-Specific Links}}` | Ссылки на дополнительные файлы из consumer repo: raw URL (лучший вариант), blob URL (допустим). Локальный путь — только вместе с excerpt. Если дополнительных ссылок нет — напиши: `нет` или `отсутствуют`. |
| `{{Context Excerpts}}` | Выдержки из файлов, которые нельзя дать ссылками. Если выдержек нет — напиши: `нет` или `отсутствуют`. |
| `{{Task For External Chat}}` | Конкретное задание внешнему чату. Что сделать, в каком формате, с какими ограничениями. Пиши плотно (caveman full). |

### Примечания к template

- **Caveman full** применяется при написании текста внутри полей `{{Question}}` и `{{Task For External Chat}}`, а также при составлении окружающего prompt-а. Это правило для Codex, не для внешнего чата.
- **Central links** обязательны всегда. Это `external_chat_rules.md` и `repo_navigation.md` из `ai-workflow-core`. Ссылки: raw URL (лучший вариант) или blob URL.
- **Project-specific links** опциональны. Если их нет, секция содержит `нет` или `отсутствуют`.
- **Порядок секций в ответе** внешнего чата важен: `External Question ID` первым, затем `Context Readback`, затем `Provider/Model`, затем `Answer`, затем `Candidate Navigation Entry`. Prompt должен явно требовать этот порядок.
- **Prompt не добавляет от себя** требований к стилю ответа внешнего чата (кроме структуры секций), если человек явно не попросил.

## Minimal Response Shape

Минимальный корректный ответ внешнего чата на `/v1` prompt:

```markdown
## External Question ID
V1-20260517-231455

## Context Readback
- external_chat_rules.md (central raw URL): fully read
- repo_navigation.md (central raw URL): fully read
- README.md (navigation-discovered, raw URL): fully read

## Provider/Model
OpenAI / GPT-5.2

## Answer

### Confirmed from central docs
- external_chat_rules.md требует пять обязательных секций...
- README.md (navigation-discovered) подтверждает, что...

### Confirmed from provided excerpts
- Excerpts показывают, что...

### Not available / not verified
- Consumer repo details not available in provided context.

## Candidate Navigation Entry
V1-20260517-231455: [краткая тема вопроса]. [1–2 предложения с сутью ответа или главного вывода].
```

Если какая-то из обязательных секций отсутствует в ответе внешнего чата — ответ считается неполным, и Codex должен запросить уточнение (или человек переотправляет вопрос с уточнением формата). То же касается ответа с ложным readback, unsupported source claims или смешанными источниками для вопросов про repo/workflow clarity.

## Escalation Note

**Когда `/v1` не подходит — используй `/r1`.**

Короткая памятка:

- `/v1` = один prompt сейчас.
- `/r1` = package + publish + record потом.

Момент выбора:

- Человек выбирает маршрут до подготовки downstream artifact.
- Для `/v1` downstream artifact = готовый prompt.
- Для `/r1` downstream artifact = full external launch package.
- Если Codex считает, что вопрос тянет на `/r1`, он не переключает маршрут сам, а коротко объясняет причину и ждёт выбора человека.

Эскалируй вопрос в `/r1` (full external launch package), если:

- вопрос слишком широкий и требует передачи многих файлов через published task bundle;
- вопрос рискованный (security, auth, payments, migrations, architecture decisions);
- вопрос требует строгого artifact contract (recorder package, verifier);
- вопрос требует, чтобы внешний чат работал с большой кодовой базой или многими файлами одновременно;
- ответ внешнего чата должен быть зафиксирован через `kilo-recorder` для дальнейшего review.

**Не пытайся втиснуть сложный `/r1`-вопрос в `/v1`.** Это ломает контракт `/v1` и создаёт путаницу. Если сомневаешься — спроси человека, какой маршрут выбрать.

Выбор между `/v1` и `/r1` всегда делает человек. Codex может только рекомендовать.

# Шаблон: Фиксация External Chat Response (recorder package)

## Режим записи

Этот шаблон используется режимом `kilo-recorder` (Task role: `Recorder Agent`) через `recorder package`.

### Recorder package contract

`kilo-recorder` работает только через `recorder package`. Recorder package — минимальный контракт для записи уже полученного внешнего ответа. Recorder package не является обычным Kilo handoff и не содержит `Task role`, `Session plan`, `Plan item`, model recommendation.

Обязательные поля recorder package:
- `external_task_id` — идентификатор внешней задачи (например, `EXT-0001`)
- `external_attempt_id` — идентификатор attempt-а внешней задачи (например, `EXT-TEST-0001`)
- `response_path` — путь к целевому response-файлу (`.ai/external_chats/responses/...`)
- `published_links` — ссылки на published artifacts (static manual blob/raw, handoff bundle blob/raw)
- `recording_mode: response-only` — recorder только записывает, не интерпретирует
- `allowed_writes` — список разрешённых файлов для записи (только response-файл)
- `raw_response` — сырой ответ внешнего чата

Сырой внешний ответ без target metadata недостаточен для recorder run.

### Правильный flow

1. `Codex orchestrator` готовит `external launch package` для `External Web Chat`.
2. Перед выдачей prompt Codex проверяет, что published handoff соответствует последней локальной версии; если нет, делает republish и перечитывает manifest.
3. `Human` вручную запускает `External Web Chat` с этим package и получает ответ.
4. `External Web Chat` в конце ответа возвращает готовый `Recorder Payload`.
5. `Human` вставляет готовый `Recorder Payload` в `Kilo Recorder`.
6. `Kilo Recorder` записывает response-файл по пути из package. Recorder не интерпретирует ответ и не делает выводов.
7. `Human` возвращает управление `Codex orchestrator`: «готово».
8. `Codex orchestrator` выполняет verification, cleanup и создаёт completion report.

Человек не обязан возвращать сырой внешний ответ в оркестраторский чат для промежуточной интерпретации, если следующий шаг — чистая запись через `kilo-recorder`.

### Приоритет mode-specific contract

Mode-specific `Recorder Package Contract` переопределяет общие task/global wording для `kilo-recorder` там, где есть конфликт. Recorder пишет только файлы из `allowed_writes`, не создаёт report и не выполняет `git_status`. `attempt_completion` используется только как финальное завершение запуска, а не как дополнительная запись файла.

### Execution sink: response-only

`kilo-recorder` является execution sink, а не reasoning/review step.

- Recorder НЕ review-ит содержательно ответ внешнего чата.
- Recorder НЕ редактирует содержательно ответ внешнего чата.
- Recorder НЕ изменяет project files, кроме указанных в `allowed_writes`.
- Recorder НЕ интерпретирует ответ внешнего чата как факт о repo без локальной проверки.
- Recorder НЕ делает выводы о repo на основе внешнего ответа.
- Recorder НЕ делает `git status`.
- Recorder НЕ создаёт report.
- Recorder НЕ читает дополнительные локальные файлы для восстановления контекста, если `raw_response` уже есть в package.
- Recorder НЕ пишет placeholder вместо verbatim `raw_response`.
- Recorder записывает только response file, затем перечитывает его и подтверждает, что он непустой.

## Два разных артефакта

Этот шаблон описывает **три** разных артефакта:

1. **Шаблонный recorder package** — документационный шаблон, который объясняет обязательные поля.
2. **Готовый Recorder Payload** — блок, который внешний чат возвращает в конце своего ответа для прямой вставки в `Kilo Recorder`.
3. **Response-файл** — то, что `kilo-recorder` создаёт в `.ai/external_chats/responses/`. Это выходной артефакт.

### Формат recorder package (входной контракт)

Шаблонный recorder package хранится как отдельный файл в `.ai/external_chats/recorder_packages/` с именем `<external_attempt_id>_recorder_package.md`. Для реального runtime/pilot запуска canonical входом считается готовый `Recorder Payload` из ответа внешнего чата. Человек должен иметь возможность скопировать его в `Kilo Recorder` без ручной сборки metadata.

```md
# Recorder Package: <external_task_id> / <external_attempt_id>

## external_task_id

<идентификатор внешней задачи, например EXT-0001>

## external_attempt_id

<идентификатор attempt-а, например EXT-TEST-0001>

## response_path

Путь к целевому response-файлу: `.ai/external_chats/responses/YYYY-MM-DD_<краткое_название>.md`

## published_links

Ссылки на published artifacts (единый блок, не отдельные поля):

- static_manual_blob: <GitHub blob URL>
- static_manual_raw: <GitHub raw URL>
- static_manual_version: <EA-STATIC-YYYY-MM-DD-VN>
- handoff_blob: <GitHub blob URL>
- handoff_raw: <GitHub raw URL>

## recording_mode

response-only

## allowed_writes

- <response_path> (response-файл)

## raw_response

<сырой markdown-ответ внешнего чата>
```

### Формат готового Recorder Payload из ответа внешнего чата

В production-like pilot/runtime внешнему чату нужно вернуть обычный ответ для человека, а в конце секцию `## Recorder Payload` с уже готовым блоком для прямой вставки в `Kilo Recorder`.

Внутри этого блока должны быть уже заполнены:

- `external_task_id`
- `external_attempt_id`
- `response_path`
- `published_links`
- `recording_mode`
- `allowed_writes`
- `raw_response` — только основная часть ответа внешнего чата без секции `## Recorder Payload`; внешний чат вкладывает свой полный ответ целиком без сокращений

Человек не должен вручную собирать metadata или редактировать payload.

Если payload неполный или отсутствует `raw_response`, запуск `kilo-recorder` считается `blocked`, а не поводом вручную собирать metadata из handoff, request или manual.

### Формат response-файла (выходной артефакт)

Response-файл создаётся `kilo-recorder` по пути из `response_path`. Это целевой файл для записи ответа внешнего чата.

Сохраняется в `.ai/external_chats/responses/` с именем `YYYY-MM-DD_<краткое_название>.md`.

```md
# External Chat Response: <название>

## Response path

Путь к этому response-файлу: `.ai/external_chats/responses/YYYY-MM-DD_<краткое_название>.md`

## Provider/Model

Провайдер и модель внешнего чата (если видны из интерфейса).
Если не видны — написать `недоступно`.

Пример: `OpenAI GPT-4o` / `Anthropic Claude 3.5 Sonnet` / `недоступно`

## Source request

Ссылка на файл запроса из `.ai/external_chats/requests/`.

Пример: `.ai/external_chats/requests/2026-05-11_ux_copy_mainpage.md`

## Recording mode

kilo-recorder (response-only)

## Recorder limitations

- Ответ не review-ится содержательно.
- Ответ не интерпретируется как факт о repo.
- Локальная проверка Codex обязательна перед использованием.

## Результат

Полученный ответ от внешнего чата (копия markdown-ответа).

## Ограничения

Что не удалось получить или ограничения ответа:
- неполные данные
- отсутствие конкретной информации
- ограничения модели

## Артефакты/Ссылки

Ссылки на созданные артефакты (если есть):
- сгенерированные изображения
- созданные файлы
- ссылки на внешние ресурсы

## Что не удалось

Явное указание того, что не было выполнено:
- нерешённые задачи
- отклонённые запросы
- неполные ответы

## Метаданные

- external_task_id: <из recorder package>
- external_attempt_id: <из recorder package>
- Дата запроса: YYYY-MM-DD
- Дата ответа: YYYY-MM-DD
- Продолжительность: (если доступно)
```

## Пример заполнения

```md
# External Chat Response: UX copy для главной страницы

## Response path

.ai/external_chats/responses/2026-05-11_ux_copy_mainpage.md

## Provider/Model

OpenAI GPT-4o

## Source request

.ai/external_chats/requests/2026-05-11_ux_copy_mainpage.md

## Recording mode

kilo-recorder (response-only)

## Recorder limitations

- Ответ не review-ится содержательно.
- Ответ не интерпретируется как факт о repo.
- Локальная проверка Codex обязательна перед использованием.

## Результат

### Вариант 1: Краткий и дерзкий

**DevHelper — твой AI-напарник в мире кода**

Пиши код быстрее с интеллектуальным автодополнением, которое понимает твой контекст. Бесплатно — 1000 строк в день.

### Вариант 2: Профессиональный

**DevHelper: AI-ассистент для разработчиков нового поколения**

Автодополнение кода, умный рефакторинг и мгновенное объяснение ошибок. Всё, что нужно для продуктивной работы.

### Вариант 3: С фокусом на безопасность

**Пишите код уверенно с DevHelper**

AI, который не просто дописывает код, но и следит за безопасностью. Находите уязвимости до того, как они попадут в продакшн.

## Ограничения

- Не удалось получить варианты с emoji-иконками
- Модель отказалась генерировать варианты с ценами (было в запретах)

## Артефакты/Ссылки

- Изображение: none
- Ссылки: none

## Что не удалось

- Варианты с визуальными элементами (только текст)
- Сравнение с конкурентами (было в запретах)

## Метаданные

- Дата запроса: 2026-05-11
- Дата ответа: 2026-05-11
- Продолжительность: ~30 секунд
```

## Важные правила

1. **Фиксируй provider/model** — записывай, какая модель использовалась (если видно), или `недоступно`
2. **Ссылайся на source** — всегда указывай источник запроса
3. **Копируй результат** — вставляй полный markdown-ответ
4. **Отмечай ограничения** — честно указывай, что не удалось
5. **Не придумывай факты** — если что-то неизвестно, пиши "неизвестно"
6. **Не review-и ответ** — recorder только записывает, не интерпретирует
7. **Перечитай response после записи** — подтверди, что он непустой
8. **`attempt_completion` — не запись файла** — используй `attempt_completion` только как финальное завершение запуска, а не как дополнительную запись файла

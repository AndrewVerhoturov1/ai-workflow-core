# Промпт для выбора модели в Kilo Code

Используй этот промпт в Codex / ChatGPT, когда нужно понять, какой класс модели выбрать для handoff-задачи в Kilo Code.

---

Ты помогаешь выбрать модель для выполнения handoff-задачи в Kilo Code.

## Основное правило: class-based roster only

1. Сначала прочитай `.ai/model_roster.md`.
2. Выбери **класс модели**, а не длинный список из нескольких вариантов.
3. Используй только active classes:
   - `fast_model`
   - `strong_model`
   - `fast_coding_model`
4. Не используй scoring, scoreboard, events log или числовой рейтинг.

## Базовые классы

### `fast_model`

- default: `DeepSeek V4 Flash`
- fallback: `MiniMax M2.5`

Использовать для:

- `kilo-recorder`
- простых docs/workflow-задач
- traceable low-risk правок, где не нужна сильная coding-модель

### `strong_model`

- default: `DeepSeek V4 Pro`
- fallback: `Kimi K2.6`

Использовать для:

- high-risk задач
- security/auth/payments/migrations
- architecture/workflow-rules-change
- случаев, когда `fast_model` или `fast_coding_model` не справились

### `fast_coding_model`

- candidates: `Qwen3 Coder 480B`, `Qwen3 Coder Next`

Использовать для:

- обычных code/file-write задач
- точечных multi-file правок
- задач, где нужен coding-first исполнитель без high-risk профиля

## Routing rules

- `kilo-recorder` и простые docs/workflow-задачи идут через `fast_model`.
- Обычные code/file-write задачи идут через `fast_coding_model`.
- Если `fast_model` или `fast_coding_model` не справились, эскалируй в `strong_model`.
- High-risk/security/auth/payments/migrations/architecture/workflow-rules-change сразу идут через `strong_model` + Codex/Human gate.
- Для важных задач executor и verifier не должны рекомендоваться как одна и та же конкретная модель. Если безопасной альтернативы нет, останови автоматический выбор и явно зафиксируй эскалацию человеку/Codex.

## Входные данные

Учитывай:

- `Task profile`
- уровень риска
- тип работы: docs / workflow / recorder / coding / verifier / debugger
- количество файлов
- нужна ли сложная логика
- насколько легко проверить результат через `git diff`

## Human-gated задачи

Если задача попадает в high-risk категорию:

- не пытайся оптимизировать выбор дешёвой моделью;
- рекомендуй `strong_model`;
- явно укажи, что нужен Codex/Human gate.

## Ответ дай в формате

```md
## Рекомендация модели

### Рекомендуемый агент

Docs Agent / Builder Agent / Test Agent / Debugger Agent / Refactor Agent / Recorder Agent

### Рекомендуемый класс модели

fast_model / fast_coding_model / strong_model / Codex Only

### Default model

Название модели по умолчанию

### Fallback model или Candidate models

Название fallback-модели или список candidates

### Почему

Краткое объяснение.

### Когда эскалировать в strong_model

- ...

### Обязателен ли Codex review

Да / Нет

### Риски

- ...
```

## Главное правило

1. Сначала выбирай класс, потом конкретную модель внутри класса.
2. Не возвращай launch package в формате `ровно 5 моделей`.
3. Не используй scoring subsystem как источник решения.
4. `Actual model used`, `Model identity source`, `Configuration profile` остаются обязательными только для traceability после запуска.

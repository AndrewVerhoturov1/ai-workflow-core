# Model Roster

Этот файл — активный source of truth для выбора класса модели в `/kilo`.

## Active model classes

| Класс | Default | Fallback / Candidates | Когда использовать |
| --- | --- | --- | --- |
| `fast_model` | `DeepSeek V4 Flash` | `MiniMax M2.5` | `kilo-recorder`, простые docs/workflow-задачи, low-risk изменения |
| `strong_model` | `DeepSeek V4 Pro` | `Kimi K2.6` | high-risk, security/auth/payments/migrations, architecture, workflow-rules-change, эскалации |
| `fast_coding_model` | — | `Qwen3 Coder 480B`, `Qwen3 Coder Next` | обычные code/file-write задачи |

## Routing rules for `/kilo`

1. `kilo-recorder` и простые docs/workflow-задачи идут через `fast_model`.
2. Обычные code/file-write задачи идут через `fast_coding_model`.
3. Если `fast_model` или `fast_coding_model` не справились, эскалация идёт в `strong_model`.
4. High-risk/security/auth/payments/migrations/architecture/workflow-rules-change сразу идут через `strong_model` + Codex/Human gate.
5. Для важных задач executor и verifier не должны использовать одну и ту же конкретную модель. Если безопасной альтернативы нет, handoff должен явно эскалировать решение человеку/Codex.

## Quick selection table

| Тип задачи `/kilo` | Рекомендуемый класс | Default model | Fallback / Candidates |
| --- | --- | --- | --- |
| `kilo-recorder` | `fast_model` | `DeepSeek V4 Flash` | `MiniMax M2.5` |
| Простые docs / workflow-тексты | `fast_model` | `DeepSeek V4 Flash` | `MiniMax M2.5` |
| Обычная code/file-write задача | `fast_coding_model` | выбрать candidate по handoff | `Qwen3 Coder 480B`, `Qwen3 Coder Next` |
| Debug / verifier важной задачи | `strong_model` | `DeepSeek V4 Pro` | `Kimi K2.6` |
| High-risk / architecture / workflow-rules-change | `strong_model` | `DeepSeek V4 Pro` | `Kimi K2.6` |

## Recommendation format for `/kilo`

Используй такой формат:

```md
## Рекомендация модели

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

### Нужен ли Codex review

Да / Нет
```

## Traceability rule

Scoring subsystem больше не участвует в `/kilo` workflow. Для traceability в report остаются обязательными:

- `Actual model used`
- `Model identity source`
- `Configuration profile`

Если фактическая модель неизвестна, пиши `недоступно` и не угадывай.

## Legacy note

Старый подробный roster может храниться только как `legacy/reference only` в consumer repo и больше не является каноном.

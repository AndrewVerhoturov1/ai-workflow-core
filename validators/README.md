# Manual Validators for `/kilo`

## Boundary

Эти validators проверяют только стабильные и формальные части workflow:

- корректные `Kilo mode` / `Task role` / launch package поля;
- structured handoff sections вроде `Task profile`, input tiers, `Report mode`, report path;
- session file shape и простые session references;
- pending workflow checkpoint по `git status`.

Validators помогают review, но не заменяют:

- `git diff` review;
- fact review Codex;
- human decision по приемке;
- проверку реального результата, scope и содержательной корректности.

CHUNK-007 сознательно **не** добавляет:

- CI hooks;
- pre-commit hooks;
- mandatory auto-gates;
- background automation;
- scheduler jobs.

## Commands

Запускать вручную по ситуации:

- `python scripts/validate_kilo_contract.py handoff <path>`
- `python scripts/validate_kilo_contract.py launch <path>`
- `python scripts/validate_kilo_contract.py checkpoint`
- `python scripts/validate_kilo_contract.py repo`
- `python scripts/validate_session_contract.py session <path>`
- `python scripts/validate_session_contract.py repo`

## Severity

- `error`:
  Формальный контракт нарушен для текущего проверяемого артефакта. Такой результат нужно исправить до использования артефакта по назначению.
- `warning`:
  Исторический или переходный артефакт не соответствует текущему шаблону, либо найден manual follow-up вроде pending checkpoint. Warning сам по себе не заменяет review-verdict.
- `future`:
  Проверки, которые пока намеренно не автоматизированы, потому что для них нужен смысловой анализ, human judgement или стабильный master-level policy.

## Current Coverage

- `validate_kilo_contract.py` сохраняет mode/role/launch/checkpoint проверки.
- Structured handoff checks применяются консервативно: строгая проверка включается для handoff с `Task profile`.
- `Model policy` проверяется только если секция уже присутствует. Отсутствие этой секции пока не считается ошибкой для mixed current artifacts.
- `validate_session_contract.py` не принимает решений за Codex и не требует чтения master history.
- Repo-wide scan может выдавать warnings на исторические handoff/session files; это inventory сигнал, а не automatic reject accepted history.

## Explicit Non-Goals

- Не принимать chunk вместо Codex review.
- Не определять, выполнен ли фактический результат задачи.
- Не оценивать качество diff.
- Не решать, принимать ли human gate.
- Не заставлять historical artifacts становиться repo-wide green любой ценой.

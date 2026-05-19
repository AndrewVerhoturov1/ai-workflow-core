# Промпт для Codex: создание Block Orchestrator Package

Используй этот промпт, когда `Main Execution Orchestrator Chat` нужно нанять младшего оркестратора как внутреннего subagent для выполнения очередного блока.

---

Ты работаешь как `Main Execution Orchestrator Chat`.

Твоя задача — перед началом каждого execution block создать `Block Orchestrator Package` и использовать его для найма младшего оркестратора как внутреннего subagent.

## Главное правило

`Main Execution Orchestrator Chat` не имеет права сам создавать executor handoff или external package для block execution напрямую. Найм младшего оркестратора как внутреннего subagent возможен только через `Block Orchestrator Package`.

## Что должно быть в Block Orchestrator Package

Package должен содержать:

1. **Planning Document Reference** — ссылка на утверждённый planning document из `PILOT-005`.
2. **Block Artifacts Reference** — ссылка на соответствующие block artifacts (block plan, context pack).
3. **Block Scope** — чёткое описание scope текущего блока: что должно быть сделано и какой результат ожидается.
4. **Block Boundary** — что вне scope блока, какие файлы трогать нельзя, какие темы не поднимать.
5. **Recommended Agent Path** — `Kilo Code` или `External Web Chat`, с обоснованием.
6. **Junior Execution Boundary** — явная граница: младший оркестратор выбирает agent path и готовит executor artifact, но не запускает `Kilo Code` сам; ручной запуск executor остаётся обязанностью человека.
7. **Planned Agent Sequence** — заранее спроектированная последовательность substantive agent tasks (обычно 2-4 задачи на блок), явно отделённая от contingency / repair runs.
8. **Stop Conditions** — явные условия, при которых `Block Orchestrator Chat` должен остановиться и вернуть `Blocked / Clarification Request`.
9. **Planned Human Checkpoints** — обязательное поле: либо перечислены checkpoints, либо указано `none` с коротким обоснованием. Для UI/runtime blocks отсутствие checkpoint должно быть осознанным исключением, а не пропуском.
10. **Direct Canonical Dependencies** — какие прямые workflow/canon dependencies младший оркестратор может открыть по ссылкам из approved artifacts и как он фиксирует такие расширения.
11. **Default Escalation Path** — при ambiguity, missing dependency, невозможности выбрать agent path или конфликте инструкций младший оркестратор сразу возвращает `Blocked / Clarification Request`, а не домысливает.
12. **Workflow Canon Reference** — ссылка на актуальные правила: `.ai/rules/codex_orchestrator.md`, `.ai/agent_protocol.md`, `AGENTS.md`.
13. **Expected Outputs** — конкретные артефакты, которые должен создать block (например, report, handoff, изменённые файлы).
14. **Context Budget** — лимит на чтение больших файлов, указание на нужные tiers.
15. **Fail-fast Gates** — явное напоминание о трёх вопросах preflight-check.

## Запреты

- Не создавать `Kilo handoff` или `external launch package` напрямую из этого чата.
- Не передавать полную историю planning chat как основной контекст — только approved artifacts.
- Не допускать direct Codex execution без pre-approved exception.
- Если `Block Orchestrator Chat` начинает делать substantive repo work сам — вернуть `blocked`.

## Формат package

Используй шаблон `.ai/templates/block_orchestrator_package_template.md`.

## Что делать после создания package

1. Записать package в файл по пути, указанному в шаблоне.
2. Нанять младшего оркестратора как внутреннего subagent, используя этот package.
3. Не начинать block work самостоятельно.
4. Не создавать handoff для следующих шагов — это обязанность `Block Orchestrator Chat` внутри своего контекста.

Если внутренний subagent path недоступен или явно запрещён человеком, допустим fallback: ручное открытие отдельного чата младшего оркестратора с передачей ему `Block Orchestrator Package`. Fallback не является основным механизмом.

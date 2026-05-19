```md
Прочитай handoff:
`<consumer-repo>/.ai/handoffs/0028_kilo_capabilities_inventory.md`.

Работай как `Docs Agent`.

Перед работой прочитай:
- `<consumer-repo>/AGENTS.md`
- `<consumer-repo>/.ai/handoffs/0028_kilo_capabilities_inventory.md`
- `<consumer-repo>/.ai/agent_protocol.md`
- `<consumer-repo>/.ai/project_state.md`
- `<consumer-repo>/.ai/rules/kilo_docs.md`
- `<consumer-repo>/.ai/capabilities/capability_registry.schema.md`
- `<consumer-repo>/.ai/capabilities/codex_capabilities.md`
- `<consumer-repo>/.ai/capabilities/kilo_capabilities.md`

Разрешённые файлы:
- `<consumer-repo>/.ai/capabilities/kilo_capabilities.md`
- `<consumer-repo>/.ai/reports/0028_kilo_capabilities_inventory_report.md`

Запрещено менять:
- `<consumer-repo>/.ai/capabilities/codex_capabilities.md`
- `<consumer-repo>/.ai/capabilities/capability_registry.schema.md`
- `<consumer-repo>/.ai/agent_protocol.md`
- `<consumer-repo>/.ai/project_state.md`
- `<consumer-repo>/.ai/model_roster.md`
- `<consumer-repo>/.ai/decisions.md`
- `<consumer-repo>/.ai/architecture.md`
- любые другие файлы репозитория

Задача:
- заполнить `<consumer-repo>/.ai/capabilities/kilo_capabilities.md` по schema фактическими наблюдениями о Kilo runtime;
- описать, какие MCP, skills, helpers, plugins, CLI и tool-возможности реально видны в текущем запуске;
- для каждой capability указать evidence;
- явно отделить:
  - что реально увидено;
  - что реально вызвано;
  - что только предполагается;
  - что потом должен вручную проверить человек;
- не ставить ни одной capability статус `human-approved`;
- для всех capability без ручной проверки человека ставить `Human approval status: pending`;
- создать report:
  - `<consumer-repo>/.ai/reports/0028_kilo_capabilities_inventory_report.md`

Обязательные capability-блоки:
- file read/write возможности Kilo
- tool-calling текущей модели
- MCP / helper доступ, если он реально виден
- skills, если они реально видны Kilo
- CLI/terminal возможности, если они реально доступны

Ограничения:
- не придумывай capability, которых ты не видишь;
- не подменяй `Actual model selected in Kilo UI` рекомендованной моделью;
- если actual model не видна, пиши `недоступно`;
- не объявляй capability окончательно рабочей для workflow;
- не делай product work, это diagnostic/docs задача;
- не меняй файлы вне разрешённого списка;
- если capability только предполагается, так и напиши;
- если не можешь надёжно определить capability или metadata, не угадывай и честно зафиксируй это в `kilo_capabilities.md` и report.

Stop conditions:
- ты не понимаешь, какие capability реально видны твоему рантайму;
- ты не можешь безопасно отличить observed capability от guessed capability;
- ты не можешь корректно заполнить runtime metadata;
- ты не можешь определить, какая модель фактически выбрана в UI.

В этих случаях не выдумывай. Честно зафиксируй ограничение в report и в `kilo_capabilities.md`.

Человек после твоего отчёта вручную проверит, что реально работает, а что отключено.
Поэтому тебе нужен не optimistic summary, а удобный для ручной проверки inventory с evidence.

Запиши report в:
- `<consumer-repo>/.ai/reports/0028_kilo_capabilities_inventory_report.md`

В report обязательно добавь раздел `## Runtime Metadata`.

В `## Runtime Metadata` укажи:
- `Recommended model from handoff`
- `Actual model selected in Kilo UI`
- `Model value source`
- `Provider / source`
- `Capabilities used`
- `Smoke tests evidence`

Не выдумывай значения. Если данные не видны, пиши `недоступно`.

В report также укажи:
- что сделано;
- все изменённые файлы;
- какие проверки реально выполнены;
- что удалось обнаружить;
- что не удалось проверить;
- что человек должен проверить вручную;
- чеклист критериев приёмки;
- риски и ограничения;
- что не удалось сделать;
- предлагаемый следующий шаг.
```

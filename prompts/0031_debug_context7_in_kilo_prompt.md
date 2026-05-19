```md
Запусти эту задачу в Kilo Code как отдельную Kilo session только если проверка из handoff `0030` не прошла.

Рекомендуемые модели:
- `Nemotron 3 Super` — основной выбор; лучший текущий кандидат для диагностики, риска и root cause analysis.
- `Qwen3 Next 80B` — fallback для reasoning + аккуратных локальных правок.
- `DeepSeek V4 Flash через Polza.AI` — платный fallback, если нужен надёжный debug/review-lite исполнитель с tools.
- `GLM 4.7` — резерв для точечной диагностики и небольших follow-up fixes.
- `MiniMax M2.5` — fallback, если нужен агент, который лучше держит процедуру и ограничения.

Модель по умолчанию: `Nemotron 3 Super`.

Скопируй этот prompt целиком в Kilo без добавлений от себя.

Прочитай handoff:
`<consumer-repo>/.ai/handoffs/0031_debug_context7_in_kilo.md`.

Работай как `Debugger Agent`.

Перед работой прочитай:
- `<consumer-repo>/AGENTS.md`
- `<consumer-repo>/.ai/agent_protocol.md`
- `<consumer-repo>/.ai/project_state.md`
- `<consumer-repo>/.ai/model_roster.md`
- `<consumer-repo>/.ai/rules/kilo_debugger.md`
- `<consumer-repo>/.ai/handoffs/0029_enable_context7_global_kilo.md`
- `<consumer-repo>/.ai/reports/0029_enable_context7_global_kilo_report.md`, если существует
- `<consumer-repo>/.ai/handoffs/0030_verify_context7_in_kilo.md`
- `<consumer-repo>/.ai/reports/0030_verify_context7_in_kilo_report.md`
- `<vscode-global-mcp-settings>`
- `<kilo-global-mcp-config>`

Разрешённые изменения:
- `<vscode-global-mcp-settings>`
- `<kilo-global-mcp-config>` только если именно этот файл нужен текущему runtime
- `<consumer-repo>/.ai/reports/0031_debug_context7_in_kilo_report.md`

Запрещено менять:
- `<consumer-repo>/.kilocode/mcp.json`
- любые repo files, кроме разрешённого report
- любые несвязанные MCP entries
- секреты и raw API keys

Задача:
- прочитать builder и tester report;
- найти наиболее вероятную root cause, почему Context7 не виден или не работает;
- сделать только минимальный fix, если он локален и касается строго Context7;
- если нужен manual step человека, не симулировать его, а описать его точно;
- создать report:
  - `<consumer-repo>/.ai/reports/0031_debug_context7_in_kilo_report.md`

Подсказки по диагностике:
- MCP globally disabled;
- изменён не тот config file;
- mismatch между `mcp` и `mcpServers`;
- нужен перезапуск Kilo session / VS Code;
- remote Context7 не подхватился, нужен local fallback;
- нет доступа к global config вне workspace.

Успех можно заявлять только если в report есть evidence, что Context7 tools стали видны. Иначе опиши точный blocker.
В report обязательно добавь `## Метаданные запуска`.
```

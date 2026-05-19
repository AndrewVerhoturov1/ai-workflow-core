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
`D:\Codex+Kilocode\ai-workflow-test\.ai\handoffs\0031_debug_context7_in_kilo.md`.

Работай как `Debugger Agent`.

Перед работой прочитай:
- `D:\Codex+Kilocode\ai-workflow-test\AGENTS.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\agent_protocol.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\project_state.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\model_roster.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\rules\kilo_debugger.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\handoffs\0029_enable_context7_global_kilo.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0029_enable_context7_global_kilo_report.md`, если существует
- `D:\Codex+Kilocode\ai-workflow-test\.ai\handoffs\0030_verify_context7_in_kilo.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0030_verify_context7_in_kilo_report.md`
- `C:\Users\andre\AppData\Roaming\Code\User\globalStorage\kilocode.kilo-code\settings\mcp_settings.json`
- `C:\Users\andre\AppData\Roaming\Kilo-Code\MCP\mcp_config.json`

Разрешённые изменения:
- `C:\Users\andre\AppData\Roaming\Code\User\globalStorage\kilocode.kilo-code\settings\mcp_settings.json`
- `C:\Users\andre\AppData\Roaming\Kilo-Code\MCP\mcp_config.json` только если именно этот файл нужен текущему runtime
- `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0031_debug_context7_in_kilo_report.md`

Запрещено менять:
- `D:\Codex+Kilocode\ai-workflow-test\.kilocode\mcp.json`
- любые repo files, кроме разрешённого report
- любые несвязанные MCP entries
- секреты и raw API keys

Задача:
- прочитать builder и tester report;
- найти наиболее вероятную root cause, почему Context7 не виден или не работает;
- сделать только минимальный fix, если он локален и касается строго Context7;
- если нужен manual step человека, не симулировать его, а описать его точно;
- создать report:
  - `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0031_debug_context7_in_kilo_report.md`

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

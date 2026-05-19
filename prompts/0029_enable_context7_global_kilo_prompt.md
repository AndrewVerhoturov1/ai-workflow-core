```md
Запусти эту задачу в Kilo Code как отдельную Kilo session.

Рекомендуемые модели:
- `MiniMax M2.5` — основной выбор; аккуратен для agentic/config-задач и хорошо держит процесс.
- `Qwen3 Next 80B` — хороший fallback; обычно стабилен в reasoning + file/tool workflow.
- `Devstral Small 2 24B` — быстрый fallback, если нужен более простой исполнитель.
- `Devstral 2 123B` — более сильный engineering fallback, если первые модели ведут себя неаккуратно.
- `DeepSeek V4 Flash через Polza.AI` — платный fallback, только если бесплатные варианты не справились.

Модель по умолчанию: `MiniMax M2.5`.

Скопируй этот prompt целиком в Kilo без добавлений от себя.

Прочитай handoff:
`D:\Codex+Kilocode\ai-workflow-test\.ai\handoffs\0029_enable_context7_global_kilo.md`.

Работай как `Builder Agent`.

Перед работой прочитай:
- `D:\Codex+Kilocode\ai-workflow-test\AGENTS.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\agent_protocol.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\project_state.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\model_roster.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\rules\kilo_builder.md`
- `D:\Codex+Kilocode\ai-workflow-test\.ai\handoffs\0029_enable_context7_global_kilo.md`
- `D:\Codex+Kilocode\ai-workflow-test\.kilocode\mcp.json` только для чтения
- `C:\Users\andre\AppData\Roaming\Code\User\globalStorage\kilocode.kilo-code\settings\mcp_settings.json`
- `C:\Users\andre\AppData\Roaming\Kilo-Code\MCP\mcp_config.json`

Разрешённые изменения:
- `C:\Users\andre\AppData\Roaming\Code\User\globalStorage\kilocode.kilo-code\settings\mcp_settings.json`
- `C:\Users\andre\AppData\Roaming\Kilo-Code\MCP\mcp_config.json` только если именно этот файл окажется активным конфигом текущего Kilo runtime
- `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0029_enable_context7_global_kilo_report.md`

Запрещено менять:
- `D:\Codex+Kilocode\ai-workflow-test\.kilocode\mcp.json`
- любые файлы репозитория, кроме разрешённого report
- другие MCP entries, которые не относятся к Context7
- любые секреты, API keys и их значения

Задача:
- определить, какой global Kilo config file реально используется текущим runtime в VS Code;
- внести минимальную правку только в этот файл;
- предпочесть remote Context7 `https://mcp.context7.com/mcp`;
- если remote/current формат здесь неприменим, использовать legacy/local fallback для Windows:
  - `command: cmd`
  - `args: /c npx -y @upstash/context7-mcp@latest`
- сохранить существующие MCP entries;
- не трогать project-local `.kilocode/mcp.json`;
- создать report:
  - `D:\Codex+Kilocode\ai-workflow-test\.ai\reports\0029_enable_context7_global_kilo_report.md`

Stop conditions:
- нет доступа к global config вне workspace;
- нельзя надёжно определить активный config file;
- для remote нужно небезопасно записывать secret;
- можно изменить только project-local `.kilocode/mcp.json`.

В этих случаях не делай workaround и не выдумывай успех. Зафиксируй blocker в report.

В report обязательно укажи:
- какой файл был изменён;
- какой формат использован: `remote/current` или `legacy/local`;
- почему выбран именно этот файл;
- что было в config до правки;
- что стало после правки;
- `## Метаданные запуска`.
```

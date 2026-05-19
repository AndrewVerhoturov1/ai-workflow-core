```md
Запусти эту задачу в Kilo Code как отдельную Kilo session после выполнения handoff `0029`.

Рекомендуемые модели:
- `Nemotron 3 Super` — основной выбор; подходит для reasoning/debug/test-like задач и аккуратной проверки evidence.
- `Qwen3 Next 80B` — хороший fallback; обычно надёжен на mixed reasoning/tool use.
- `GLM 4.7` — резерв для точечной проверки и follow-up диагностики.
- `DeepSeek V4 Flash через Polza.AI` — платный fallback, если бесплатные модели не видят MCP или слабо репортят evidence.
- `MiniMax M2.5` — дополнительный fallback, если нужен более process-oriented исполнитель.

Модель по умолчанию: `Nemotron 3 Super`.

Скопируй этот prompt целиком в Kilo без добавлений от себя.

Прочитай handoff:
`<consumer-repo>/.ai/handoffs/0030_verify_context7_in_kilo.md`.

Работай как `Test Agent`.

Перед работой прочитай:
- `<consumer-repo>/AGENTS.md`
- `<consumer-repo>/.ai/agent_protocol.md`
- `<consumer-repo>/.ai/project_state.md`
- `<consumer-repo>/.ai/model_roster.md`
- `<consumer-repo>/.ai/rules/kilo_tester.md`
- `<consumer-repo>/.ai/handoffs/0029_enable_context7_global_kilo.md`
- `<consumer-repo>/.ai/reports/0029_enable_context7_global_kilo_report.md`, если существует
- `<consumer-repo>/.ai/handoffs/0030_verify_context7_in_kilo.md`

Разрешённые изменения:
- `<consumer-repo>/.ai/reports/0030_verify_context7_in_kilo_report.md`

Запрещено менять:
- любые config files
- `<consumer-repo>/.ai/capabilities/kilo_capabilities.md`
- `<consumer-repo>/.kilocode/mcp.json`
- любые исходники, тесты, docs и workflow-файлы

Тестовое задание:
Используй Context7 MCP. Найди библиотеку React, затем получи документацию по useEffect cleanup. В report укажи:
1. какие MCP tools Context7 реально были доступны;
2. какой library id был выбран;
3. 3 факта из документации о cleanup;
4. ссылку/источник из результата Context7;
5. если tool недоступен, остановись и честно напиши ошибку.
Не меняй файлы проекта.

Важно:
- сначала resolve library id;
- потом query docs;
- не подменяй evidence пересказом из памяти;
- если Context7 tools не видны, ничего не чини, только зафиксируй blocker;
- создай report:
  - `<consumer-repo>/.ai/reports/0030_verify_context7_in_kilo_report.md`

В report обязательно добавь:
- точные названия видимых Context7 tools или честное отсутствие tools;
- выбранный React library id;
- 3 факта про cleanup;
- источник из результата Context7;
- `## Метаданные запуска`.
```

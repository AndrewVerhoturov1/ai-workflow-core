# Single-paste запуск для kilo-notebook

Используется для `/v1` staged local save.

Человек не готовит `notebook package` руками. Основной путь записи:

1. Создать source artifact в `.ai/external_chats/notebook_sources/`:
   - Имя файла: `YYYY-MM-DD_<external_question_id>_raw_response.md`
   - Содержимое: полный сырой ответ внешнего чата целиком

2. Запустить:
   ```powershell
   python scripts/stage_v1_notebook.py --input .ai/external_chats/notebook_sources/YYYY-MM-DD_<external_question_id>_raw_response.md
   ```

Скрипт сам:

- читает raw-response source artifact;
- валидирует обязательные секции `/v1`;
- создаёт internal notebook package;
- вызывает writer logic (`write_v1_notebook.py`);
- создаёт или обновляет notebook entry;
- обновляет `V1_navigation.md`.

## Что нужно вставить в source artifact

Полный сырой ответ внешнего чата целиком, начиная с:

```md
## External Question ID
```

и до конца ответа, включая:

- `## Provider/Model`
- `## Answer`
- `## Candidate Navigation Entry`
- markdown footnotes / raw URLs, если они есть

## Required sections в сыром ответе

- `External Question ID`
- `Provider/Model`
- `Answer`
- `Candidate Navigation Entry`

Если любой из этих разделов отсутствует, запуск считается `blocked`.

## Internal outputs

Скрипт создаёт только:

- `.ai/external_chats/notebook_packages/YYYY-MM-DD_<external_question_id>_<slug>_package.md`
- `.ai/external_chats/notebook/YYYY-MM-DD_<external_question_id>_<slug>.md`
- `.ai/external_chats/V1_navigation.md`

Другие файлы не изменяются.

## Shell text-dump запрещён

Shell text-dump (`echo ...`, heredoc, длинный CLI literal) запрещён как стандартный transport для `kilo-notebook`. Source artifact создаётся только через file-edit path.

## Completion signal

Успешный запуск печатает:

- `Source file: ...`
- `Package: ...`
- `Notebook entry: ...`
- `V1 navigation: ...`
- `Navigation row: ...`

Это и есть достаточный output-signal для orchestration-layer.

# Context Pack Template

## Block ID

`BLOCK-NNN_short_name`

## Parent Chunk

`CHUNK-NNN`

## Master Artifacts

Ссылки на актуальные master artifacts на момент создания блока:

- Master status: `path/to/master_status.md`
- Decision log: `path/to/decisions.md`
- Chunk plan: `path/to/chunk_plan.md`

## Relevant Rules

Правила, релевантные для выполнения блока:

- `path/to/rule1.md` — краткое описание релевантности
- `path/to/rule2.md` — краткое описание релевантности

## Accepted Decisions

Принятые решения, которые Block Orchestrator не должен нарушать:

- `KSU-DEC-NNNN` — краткое описание
- `KSU-DEC-NNNN` — краткое описание

## Block Plan Reference

Ссылка на Block Plan, для которого собран этот Context Pack:

`path/to/block_plan.md`

## Context Notes

Дополнительные заметки, которые помогают Block Orchestrator понять контекст без чтения полной истории planning chat:

- Заметка 1
- Заметка 2

## Do Not Include

Что не должно быть включено в Context Pack:

- Полная история planning chat.
- Непринятые proposal или rejected решения.
- Контекст других блоков (если блокировка не требует этого).
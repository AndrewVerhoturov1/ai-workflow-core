# Manual Setup Checklist

## 1. Подготовить каркас репозитория

- Создайте `.ai/`, `.ai/rules/`, `.ai/prompts/`, `.ai/templates/`, `.ai/validators/`, `.ai/external_chats/`, `scripts/`.
- Создайте пустые runtime-директории:
- `.ai/handoffs/`
- `.ai/reports/`
- `.ai/reviews/`
- `.ai/plans/sessions/`
- `.ai/external_chats/requests/`
- `.ai/external_chats/responses/`
- `.ai/external_chats/tasks/`
- `.ai/external_chats/recorder_packages/`
- `.ai/external_chats/reviews/`

## 2. Скопировать workflow core

- Перенесите файлы из `copy-as-is core` по [manifest.md](./manifest.md).
- Не переносите historical/project-specific артефакты как стартовую память.

## 3. Создать project-specific файлы из шаблонов

- Создайте `AGENTS.md`, если хотите project-specific адаптацию вместо прямой копии.
- Создайте `.ai/project_brief.md`.
- Создайте `.ai/project_state.md`.
- Создайте `.ai/architecture.md`.
- Создайте `.ai/decisions.md`.
- Создайте `.ai/backlog/current_sprint.md`.
- Создайте `.ai/external_chats/publisher_config.json`.

## 4. Настроить Kilo UI modes вручную

- Убедитесь, что в интерфейсе доступны:
- `Kilo Handoff Runner`
- `Kilo Debugger`
- `Kilo Verifier`
- `Kilo Recorder`
- Проверьте, что `Kilo mode` и `Task role` не смешиваются.
- Проверьте, что `kilo-recorder` настроен как отдельный mode, а не как role.

## 5. Настроить published external route

- Подготовьте публичный GitHub repo для static manual и temporary task bundles.
- Опубликуйте `.ai/external_chats/external_agent_static_manual.md` как `external_agent_static_manual.md`.
- Заполните `.ai/external_chats/publisher_config.json` из шаблона.
- Проверьте, что `repo`, `branch`, `static_manual_path`, `temp_root`, URL-шаблоны соответствуют новому проекту.
- Убедитесь, что ручная публикация task bundle через `scripts/external_chat_publish.py` возможна в новом окружении.

## 6. Обновить project-local ссылки и placeholders

- Замените placeholder-поля в starter templates.
- Если новый проект использует absolute file links в canon docs, пересоздайте их под новый корень репозитория.
- Не оставляйте ссылки на старый repo, старые task ids и старые external artifacts.

## 7. Инициализировать новый state

- Начните новый `current_sprint.md` с актуальной цели нового проекта.
- Начните `decisions.md` и `project_state.md` с пустого состояния, а не с исторического snapshot.
- Не переносите старые session files и master plan history как активный контекст.

## 8. Пройти bootstrap smoke

- Выполните шаги из [verification_checklist.md](./verification_checklist.md).
- Зафиксируйте первый bootstrap session только после того, как проверки пройдены.

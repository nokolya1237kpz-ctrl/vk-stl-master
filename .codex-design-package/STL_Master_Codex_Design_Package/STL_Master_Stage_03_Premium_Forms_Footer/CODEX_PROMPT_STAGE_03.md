# CODEX PROMPT — ЭТАП 3

Используй папку `STL_Master_Stage_03_Premium_Forms_Footer`.

Главные файлы:
- `SPEC.md`
- `premium_forms_footer_preview.html`

Рабочая директория:
`/home/codex/projects/vk-stl-master`

## Задача
Добавить коммерческие и финальные секции публичного сайта STL Master.

## Не менять
- backend
- worker
- API
- очередь
- заявки
- админку
- business logic
- upload gate

## Работать только
- `frontend/src/main.jsx`
- `frontend/src/styles.css`
- `frontend/public/assets/marketing/*`
- `tests/smoke_public_design_contract.sh` при необходимости

## Обязательно
1. Premium section.
2. Цена ровно `690 ₽ / месяц`.
3. Не использовать `990 ₽`.
4. Early Access form.
5. Premium Request form.
6. Success state для Early Access.
7. Success state для Premium.
8. Кнопка `Скопировать сообщение`.
9. Ссылки:
   - `https://vk.com/3dmodeliron`
   - `https://vk.com/pechatdlyadoma`
   - `https://t.me/chat_pechatdlyadoma`
10. Не использовать `vk.com/im?sel=3dmodeliron`.
11. Reviews section.
12. FAQ section.
13. Footer.

## Проверки
```bash
npm run build
./tests/smoke_public_design_contract.sh
./tests/smoke_public_launch.sh
./tests/run_all_smoke_tests.sh
```

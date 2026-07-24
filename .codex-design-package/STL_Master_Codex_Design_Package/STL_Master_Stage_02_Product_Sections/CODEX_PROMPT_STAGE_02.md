# CODEX PROMPT — ЭТАП 2: Product Sections

Используй папку `STL_Master_Stage_02_Product_Sections`.

Главные файлы:
- `SPEC.md`
- `product_sections_preview.html`

Рабочая директория:
`/home/codex/projects/vk-stl-master`

## Задача
Добавить продуктовые секции публичного сайта STL Master максимально близко к `product_sections_preview.html`.

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
1. Секция `Как STL Master готовит модель`.
2. 5 шагов процесса.
3. Секция `Соединения после разреза`.
4. Обычный разрез, стык под клей, штифты, магниты 5×2 / 6×2 / 8×3 / 10×3, фигурный замок.
5. Секция `Ключевые функции`.
6. Блок `До / После`.
7. Полный список возможностей.
8. Не использовать большие чёрные ползунки.
9. Не использовать старые ромбики.
10. Не использовать цену 990 ₽.

## Проверки
```bash
npm run build
./tests/smoke_public_design_contract.sh
./tests/smoke_public_launch.sh
./tests/run_all_smoke_tests.sh
```

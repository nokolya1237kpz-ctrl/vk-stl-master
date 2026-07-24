# CODEX PROMPT — ЭТАП 1: Hero Screen + Sticky Header

Используй папку `STL_Master_Stage_01_Hero`.

Главные файлы:
- `SPEC.md`
- `hero_screen_preview.html`

Рабочая директория:
`/home/codex/projects/vk-stl-master`

## Задача
Реализовать первый экран публичного сайта STL Master максимально близко к `hero_screen_preview.html`.

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
1. Sticky glass header всегда виден при скролле.
2. Header desktop: пункты меню в один ряд.
3. CTA справа: `Получить доступ`.
4. Hero headline: `Подготовьте STL к печати за минуты`.
5. Справа — mockup приложения `STL Master Studio`.
6. В mockup должны быть:
   - Repair / Split + Pins / Check tabs;
   - tools: Исправление, Разрез, Штифты, Магниты, Замок, Проверка;
   - viewport с моделью;
   - split plane;
   - pins;
   - HUD: `65 → 88`, `part_A/B.stl`, `#1`;
   - meta cards: `original.stl`, `connector_report.json`, `Скачать STL`.
7. Не использовать старые ромбики.
8. Не использовать цену 990 ₽.

## Проверки
```bash
npm run build
./tests/smoke_public_design_contract.sh
./tests/smoke_public_launch.sh
./tests/run_all_smoke_tests.sh
```

# Stage 05.6 — Compare / До и После

Дата: 2026-07-26

## Цель

Восстановить только публичный блок `04 ДО И ПОСЛЕ` на Landing. Header, Hero, Workflow, Features, Connections, Premium, FAQ, Footer, Studio, Admin, backend, worker и API не менялись.

## Что было сломано

Текущая разметка блока использует классы `demoCompareWorkbench`, `demoComparePanel`, `demoCompareStageShell`, `demoBeforeAfterStage`, но часть старых общих стилей была написана для другого слоя классов (`compareWorkbench`, `comparePanel`, `compareStageShell`). Из-за этого:

- заголовок выходил за пределы контейнера;
- kicker, CTA и текст располагались не по сетке;
- side panels не становились полноценными карточками;
- compare viewport получал некорректное позиционирование;
- бейджи `ДО` / `ПОСЛЕ` попадали в обычный поток и слипались.

## Изменения

Изменён только `frontend/src/landing/landing.css`.

Добавлен CSS compatibility layer `Stage 5.6 Compare / before-after production recovery` для текущей DOM-структуры:

- `#compare`;
- `.demoCompareSection`;
- `.demoCompareSection .launchSectionHeader`;
- `.demoCompareCard`;
- `.demoCompareWorkbench`;
- `.demoComparePanel`;
- `.demoCompareStageShell`;
- `.demoBeforeAfterStage`;
- `.compareViewer`;
- `.compareAfterClip`;
- `.compareDragHint`;
- `.compareSideBadge`;
- `.beforeAfterDivider`;
- `.beforeAfterSlider`;
- `.compareReadyStatus`;
- `.demoCompareMetrics`;
- responsive rules for `max-width: 1180px` and `max-width: 640px`.

React/JSX не изменялся. Логика slider, обработчики pointer/keyboard, модели viewer и тексты сохранены.

## Production

После deploy production отдаёт:

- `/assets/index-2Ssh2v_h.js`;
- `/assets/index-DOVuF2J-.css`.

Маршруты:

- `/` — 200;
- `/app` — 200;
- `/admin` — 200;
- `/api/v1/me` — 200.

## Проверка

Проверены viewport:

- 1920x1080;
- 1440x900;
- 1024x768;
- 768x900;
- 390x844;
- 360x800.

Результат:

- горизонтального scroll нет;
- console errors нет;
- stage имеет нормальную высоту: 468px desktop, 430px tablet, 340px mobile;
- side badges разведены по краям viewer;
- metrics grid адаптируется 4 -> 2 -> 1 columns.

## Скриншоты

До:

- `docs/stage-05-6-compare/before/compare-before-1440.png`;
- `docs/stage-05-6-compare/before/compare-before-390.png`.

После:

- `docs/stage-05-6-compare/after-final-2/compare-final2-1440.png`;
- `docs/stage-05-6-compare/after-final-2/compare-final2-390.png`;
- `docs/stage-05-6-compare/after-final-2/compare-final2-390-stage.png`;
- `docs/stage-05-6-compare/after-final-2/results.json`.

## Build / Deploy

`npm run build` — PASS.

Deploy выполнен через существующий `./scripts/rebuild-frontend.sh`.

Backend, worker и API не пересобирались и не изменялись.

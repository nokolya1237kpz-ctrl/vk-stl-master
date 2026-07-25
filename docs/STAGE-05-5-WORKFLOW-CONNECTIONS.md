# Stage 05.5 Workflow + Connections

## 1. Исходный SHA

`6e293386158f6dd1f8d1ef5c3c7cbd4c1d345039`

## 2. Production до deploy

Production до работ не совпадал с текущим `main`.

- GitHub main: `6e293386158f6dd1f8d1ef5c3c7cbd4c1d345039`
- Production HTML: `/assets/index-hpeLczfm.js`, `/assets/index-Dq0nS2xU.css`
- Последний локальный dist Stage 05.4: `/assets/index-CRGOwILY.js`, `/assets/index-Ck0xpnPP.css`
- `/`, `/app`, `/admin`, `/api/v1/me`: HTTP 200

Подробно: `docs/stage-05-5-production-sync/production-before.txt`.

## 3. Механизм deploy

Найден штатный скрипт:

`/home/codex/projects/vk-stl-master/scripts/rebuild-frontend.sh`

Он выполняет:

- `docker-compose build frontend`
- `docker-compose rm -sf frontend`
- `docker-compose up -d frontend`

Backend, worker, Redis, jobs и пользовательские данные не затрагиваются.

## 4. Причина сжатия Workflow

На production была старая сборка, где Workflow отображался как узкие вертикальные полосы.

В актуальном CSS дополнительно найден риск: корень `#workflow` мог оставаться grid-контейнером, из-за чего `workflowIntro` и `workflowGrid` попадали в отдельные узкие ячейки. Исправлено точечно через Stage 05.5 override: `workflowSection` возвращён в block-flow, а pipeline получает всю ширину контейнера.

## 5. Workflow layout

Сохранены все 6 шагов, порядок, тексты, иконки и смысл.

Breakpoints:

- `>= 1680px`: 6 колонок.
- `1280-1679px`: 3 колонки x 2 ряда.
- `768-1279px`: 2 колонки x 3 ряда.
- `< 768px`: вертикальная timeline.

Local preview metrics:

- 1440px: 6 карточек, ширина каждой около `381px`, overflow отсутствует.
- 390px: 6 карточек, ширина каждой около `346px`, overflow отсутствует.

Track:

- desktop/tablet: лёгкие стрелки между карточками, без линии через текст;
- mobile: вертикальная timeline-линия слева, без перекрытия текста.

## 6. Connections layout

Сохранены все существующие 6 карточек соединений, изображения, подписи, CAD-параметры, CTA и обработчик кнопки.

Структура стала явнее:

- intro: section label, заголовок, описание;
- connection cards: единая сетка карточек;
- CAD parameters: цельная техническая панель;
- Split Studio CTA: компактная панель, визуально связанная с CAD-блоком.

Local preview metrics:

- 1440px: 6 карточек, ширина каждой около `419px`, overflow отсутствует.
- 390px: 6 карточек, ширина каждой около `366px`, overflow отсутствует.

## 7. Изменённые файлы

- `frontend/src/landing/landing.css`
- `docs/STAGE-05-5-WORKFLOW-CONNECTIONS.md`
- `docs/stage-05-5-production-sync/production-before.txt`
- `docs/stage-05-5-production-sync/results.json`
- `docs/stage-05-5-production-sync/before/*`
- `docs/stage-05-5-production-sync/local-preview/*`
- `docs/stage-05-5-production-sync/after/*`

React/JSX не менялся.

## 8. Build

`npm run build` — PASS.

Известные старые предупреждения:

- VKUI/Vite module-level `"use client"`;
- Vite chunk-size warning.

## 9. Regression

До deploy:

- Workflow local preview: PASS.
- Connections local preview: PASS.
- Горизонтальный overflow на 1440 и 390: отсутствует.
- Backend, worker, Studio и Admin не изменялись.

После deploy:

- production verification будет добавлен после штатного deploy;
- production hashes будут добавлены после штатного deploy;
- screenshots after будут сохранены в `docs/stage-05-5-production-sync/after/`.

## 10. Логика

Бизнес-логика не изменялась.

Не менялись:

- backend;
- worker;
- API;
- routes;
- auth;
- upload;
- premium;
- viewer;
- history;
- Studio;
- Admin;
- Header;
- Hero;
- Features;
- Compare;
- FAQ;
- Footer.

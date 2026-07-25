# Stage 05.3 Workflow

## 1. Исходный commit

`0c47235ef457a6892644d04ef85e512b06aa8975`

## 2. Расположение Workflow в коде

- Данные шагов: `frontend/src/main.jsx`, `publicWorkflowSteps`.
- Иконки: `frontend/src/main.jsx`, `WorkflowIcon`.
- Секция: `frontend/src/main.jsx`, `WorkflowSection`.
- Стили: `frontend/src/landing/landing.css`, selectors `.workflowSection`, `.workflowGrid`, `.workflowCard`, `.workflowTrack`.

## 3. Количество шагов

Существовало и сохранено 6 шагов.

## 4. Тексты и порядок

Порядок и тексты сохранены:

1. `Загрузите STL`
2. `Проверьте модель`
3. `Исправьте и оптимизируйте`
4. `Разрежьте и соедините`
5. `Проверьте печать`
6. `Экспортируйте`

Заголовок и подзаголовок секции сохранены:

- `Весь процесс в одном редакторе`
- `От загрузки STL до готовой модели к печати`

## 5. Baseline-проблемы

- Workflow выглядел как набор отдельных маркетинговых карточек.
- На desktop шесть карточек сжимались в один ряд без достаточного ощущения pipeline.
- Соединение между этапами было только через отдельные стрелки.
- На tablet использовались три колонки, но без отдельной логики track.
- На mobile секция становилась обычным вертикальным списком без timeline.

## 6. Изменённые файлы

- `frontend/src/main.jsx`
- `frontend/src/landing/landing.css`
- `docs/STAGE-05-3-WORKFLOW.md`
- `docs/stage-05-3-workflow/results.json`

## 7. UI-компоненты

Новые UI Kit компоненты не подключались. Текущая разметка Workflow стабильнее для минимальной миграции. Использованы визуальные правила UI Kit через scoped CSS.

## 8. Desktop layout

- Широкий desktop: один горизонтальный engineering pipeline из шести карточек.
- Узкий desktop: две строки по три карточки, чтобы русский текст не дробился.

## 9. Tablet layout

Tablet использует две строки по три карточки с сохранением порядка и размеров touch area.

## 10. Mobile layout

Mobile использует вертикальную timeline: линия слева, карточки полноширинные, номер и иконка остаются видимыми.

## 11. Иконки

Иконки остались существующими SVG из `WorkflowIcon`:

- upload;
- inspect;
- magic;
- blocks;
- shieldCheck;
- export.

Новые библиотеки не добавлялись.

## 12. Workflow track

Добавлен декоративный `span.workflowTrack` в `WorkflowSection`.

- На широком desktop он работает как горизонтальный process line.
- На mobile track перестраивается в вертикальную timeline через `.workflowGrid::before`.
- На двухрядной сетке основной порядок дополнительно поддерживается номерами и стрелками между карточками в строках.

## 13. Размеры карточек

- Wide desktop: `min-height: 206px`.
- Narrow desktop/tablet: `min-height: 188-190px`.
- Mobile: высота определяется контентом, пустые зоны убраны.

## 14. Viewport sweep

Полный geometry sweep заблокирован окружением. См. `docs/stage-05-3-workflow/results.json`.

## 15. Zoom check

Автоматический zoom check заблокирован окружением. CSS использует responsive grid и не вводит fixed ширины карточек внутри mobile/tablet.

## 16. Manual screenshot review

Скриншоты before/after не были получены из-за отсутствия доступного браузерного рантайма:

- на сервере нет Chromium/Chrome;
- локальный headless Chrome падает с macOS `EPERM`;
- CDP порт отдельного Chrome не стал доступен;
- npm registry был недоступен для временной установки Playwright.

## 17. Функциональная проверка

Workflow не имел и не получил новых обработчиков, API-запросов или кликабельности. Существующие тексты и порядок сохранены.

## 18. Build

`npm run build` — PASS.

Старые предупреждения:

- VKUI/Vite предупреждения про module-level `"use client"`;
- Vite chunk size warning.

Новых build errors нет.

## 19. Regression

Preview:

- `/` — HTTP 200;
- `/app` — HTTP 200;
- `/admin` — HTTP 200.

Production API без деплоя:

- `GET /api/v1/me` — HTTP 200.

## 20. Checksums

До и после совпали checksums:

- `backend/`;
- `worker/`;
- `frontend/src/studio/`;
- `frontend/src/admin/`.

## 21. Логика

Бизнес-логика не изменялась. API, routing, upload, Premium, Viewer, History, Studio и Admin не менялись.

## 22. Отложенные замечания

- Нужно повторить screenshot sweep, когда будет доступен стабильный browser automation runtime.
- Header/Hero polishing не выполнялся в этом этапе по условию задачи.

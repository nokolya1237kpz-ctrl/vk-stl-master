# Migration Plan

Статус: план будущих этапов. На текущем этапе ничего из этого не выполняется.

Цель миграции: восстановить профессиональный визуальный слой STL Master без изменения бизнес-логики, API, worker, queue, premium state, admin actions и routing.

## Общий протокол каждой задачи

1. Зафиксировать screenshot до правки.
2. Ограничить область одним блоком или одним маршрутом.
3. Менять только scoped CSS, если DOM уже позволяет исправить дефект.
4. Не менять JSX, пока это не подтверждено отдельным заданием.
5. Запустить `npm run build`.
6. Проверить `/`, `/app`, `/admin` на console errors, failed requests и horizontal scroll.
7. Снять screenshot после правки.
8. Записать selectors/files touched.

## Hero

- Цель: восстановить пропорции header, left column, CTA, Studio mockup.
- Не менять: `HeroSection`, `StudioMockup` structure, public routing, access/premium flow.
- Критерий: desktop и mobile совпадают с утверждённым baseline/эталоном без выхода текста за кнопки.

## Workflow

- Цель: выровнять карточки этапов и rhythm секции.
- Не менять: тексты, количество шагов, component structure.
- Критерий: нет overlap на 1920/1440/tablet/mobile.

## Features

- Цель: стабилизировать высоты карточек, изображения и tab/feature states.
- Не менять: список возможностей, реальные feature claims.
- Критерий: карточки читаются и не обещают неработающие функции.

## Connectors

- Цель: убрать визуальные артефакты изображений и выровнять карточки.
- Не менять: типы соединений и тексты без отдельного approval.
- Критерий: нет белых полос/рамок, изображения не растянуты.

## Compare

- Цель: восстановить баланс left/right, slider, metrics.
- Не менять: compare logic и реальные метрики, если они связаны с данными.
- Критерий: до/после читается на desktop и mobile.

## Premium

- Цель: визуально стабилизировать price, plan table, modal entry points.
- Не менять: Premium flow, request state machine, API calls, code activation.
- Критерий: цена и действия видимы, модалки открываются без ошибок.

## FAQ

- Цель: привести spacing и disclosure states к общей системе.
- Не менять: содержание вопросов без отдельного задания.
- Критерий: keyboard/click states сохраняются.

## Footer

- Цель: footer всегда виден на full-page screenshot, контакты читаемы.
- Не менять: routing и external link behavior без отдельного задания.
- Критерий: нет overlap, mobile layout корректен.

## Studio

- Цель: visual stabilization настоящего `/app`.
- Не менять: upload STL, viewer, processing, API, Premium, Job History.
- Критерий: пустое состояние, загруженная модель и history не ломаются.

## Viewer

- Цель: улучшить читаемость canvas, overlays, section plane, gizmo, toolbars.
- Не менять: Three.js scene logic, STLLoader, camera controls, processing data.
- Критерий: модель видна, controls доступны, нет accidental overlay dominance.

## History

- Цель: привести карточки истории и generated files к единой плотности.
- Не менять: endpoints, download links, job states.
- Критерий: длинные имена файлов и статусы не ломают layout.

## Admin

- Цель: визуальная ясность без изменения операций.
- Не менять: auth, deletion, quarantine, bulk actions, premium codes, feedback mutations.
- Критерий: всё на русском, таблицы стабильны, destructive actions визуально отделены.

## Порядок выполнения

1. Landing: Hero.
2. Landing: Workflow.
3. Landing: Connectors.
4. Landing: Compare.
5. Landing: Features.
6. Landing: Premium.
7. Landing: FAQ/Footer.
8. Studio `/app` visual pass.
9. Viewer overlays pass.
10. History pass.
11. Admin visual pass.

Каждый пункт выполняется отдельным заданием и останавливается после отчёта.

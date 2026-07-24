# Visual Recovery Stage 01 Report

Дата: 2026-07-23
Проект: `/home/codex/projects/vk-stl-master`
Режим: аудит и baseline. Визуальные/функциональные правки не выполнялись.

## 1. Что выполнено

- Проверено окружение сервера, git-состояние, свободное место и структура проекта.
- Создан безопасный архив текущего состояния проекта до дальнейшего восстановления.
- Запущен `npm run build` для frontend с полным логом.
- Зафиксированы SHA-256 `frontend/dist` до и после сборки.
- Снят браузерный visual baseline для маршрутов `/`, `/app`, `/admin` на desktop/tablet/mobile.
- Собран console/network отчёт через Playwright.
- Собран CSS inventory по всем реально подключённым CSS-файлам.
- Собрана карта React-компонентов и маршрутов из `frontend/src/main.jsx`.
- Выполнено read-only сравнение текущих frontend-файлов с резервными/входящими версиями.
- Проверено, что `frontend/src`, `backend`, `worker` не изменились относительно созданного архива.

## 2. Git / рабочее состояние

Git-репозиторий в `/home/codex/projects/vk-stl-master` отсутствует:

```text
fatal: not a git repository (or any of the parent directories): .git
```

Поэтому:

- ветка `recovery/visual-baseline` не создавалась;
- commit `chore(audit): capture visual recovery baseline` не создавался;
- push не выполнялся.

## 3. Резервная копия

Архив:

```text
/home/codex/backups/vk-stl-master-before-visual-recovery-20260723-082327.tar.gz
```

SHA-256:

```text
18a92f70a3866b50f3bf0376634206844428852366cb318f44f08365f60607cb
```

Размер: `55M`.

Исключены: `frontend/node_modules`, `__pycache__`, `.pytest_cache`, `.cache`, вложенные `*.tar.gz`, `docs/visual-baseline`.

Детали: `docs/recovery-stage-01-backup.txt`.

## 4. Frontend build

Команда:

```bash
cd /home/codex/projects/vk-stl-master/frontend
npm run build
```

Результат: `PASS`, exit code `0`.

Артефакты сборки:

```text
dist/index.html                     0.40 kB
dist/assets/index-ph_I12Tf.css    646.42 kB
dist/assets/index-QYl9msRJ.js   1,015.72 kB
```

Предупреждения:

- множественные Vite/Rollup warnings по `"use client"` в `@vkontakte/icons` и `@vkontakte/vkui`;
- chunk warning: JS bundle больше 500 kB.

`frontend/dist` после сборки совпал по содержимым файлам с состоянием до сборки. Diff отличается только строкой-заголовком `# dist before` / `# dist after`.

Логи:

- `docs/recovery-stage-01-frontend-build.txt`
- `docs/recovery-stage-01-dist-before.sha256`
- `docs/recovery-stage-01-dist-after.sha256`
- `docs/recovery-stage-01-dist-diff.txt`

## 5. Browser baseline

Скриншоты сохранены в:

```text
docs/visual-baseline/
```

Снято `36` PNG:

- `/` landing: desktop 1920×1080, desktop 1440×900, tablet 1024×768, mobile 390×844, mobile 360×800;
- `/app`: те же размеры;
- `/admin`: те же размеры;
- дополнительные first-screen снимки секций landing: workflow, connections, compare, features, premium, faq.

Console/network summary:

- `/`, `/app`, `/admin` открываются успешно во всех проверенных viewport.
- Горизонтальный скролл не обнаружен во всех проверенных viewport.
- `/api/v1/me` вернул HTTP `200`.
- На landing desktop 1920×1080 зафиксированы 4 WebGL performance warning `GPU stall due to ReadPixels`; ошибок JS, failed requests и HTTP 4xx/5xx в baseline не обнаружено.

Детали:

- `docs/recovery-stage-01-browser-console.txt`
- `docs/visual-baseline/manifest.json`
- `docs/recovery-stage-01-api-and-files.txt`

## 6. CSS inventory

Фактический порядок CSS импортов в `frontend/src/main.jsx`:

```text
@vkontakte/vkui/dist/vkui.css
./styles.css
./studio/studio.css
./styles/tokens.css
./styles/reset.css
./styles/shared.css
./landing/landing.css
./admin/admin.css
```

Ключевые файлы:

| CSS | Строк | SHA-256 | Наблюдения |
|---|---:|---|---|
| `frontend/src/styles.css` | 11849 | `8a6acd47892c644400064f7a797e46f26d76dc730a26b94c826720056a7119e4` | legacy/shared слой, 2019 selector entries, 4441 `!important`, глобальные селекторы |
| `frontend/src/landing/landing.css` | 507 | `a468c70f22c2e4be5f321fcbf77b14f0c48610e95f6b317e845776d898a9a1f2` | landing overrides, 256 selector entries |
| `frontend/src/studio/studio.css` | 1031 | `7c0676926161cb65c441bde9731178f6fe793ab3318551ca556bcd17c4347436` | Studio-specific layer |
| `frontend/src/admin/admin.css` | 161 | `3889c93b0acd8094d4deab09cd743b9dce7ff35b35bfa3b710f66eb14921a287` | Admin layer imported last |
| `frontend/src/styles/tokens.css` | 39 | `8087aa9af4ca90d4260af669ec0d2e5f8d844bcf6a650838ac042b9a45a77750` | tokens |
| `frontend/src/styles/reset.css` | 42 | `80007f10bb097fbea33375cf285a072bdf86703cbfda709b7ab3d5eeaa2c7116` | reset |
| `frontend/src/styles/shared.css` | 77 | `726e054ecb4e9348f3cdefbd07364d5deb08e19464a013ed59a4eb83c3480cbc` | shared primitives |

Подтверждённые риски каскада:

- `styles.css` содержит legacy/shared правила и глобальные селекторы; удалять/сокращать нельзя.
- `landing.css` выигрывает у `styles.css` при равной специфичности, но сам содержит повторные селекторы.
- `admin.css` импортируется последним, поэтому одноимённые общие классы могут переопределяться на всех маршрутах при совпадении специфичности.
- Полный список duplicate/cross-file selectors находится в `docs/recovery-stage-01-css-inventory.md`.

## 7. React component map

Маршруты:

```text
/      -> App -> PublicLanding
/app   -> App -> Studio/editor UI
/admin -> RootComponent -> AdminApp -> AdminFeedbackDashboard
```

Ключевые компоненты:

- Landing/Hero: `PublicLanding`, `HeroSection`, `StudioMockup`, `SectionHeader`.
- Workflow: `WorkflowSection`, `WorkflowIcon`, частично `WorkflowPanel` для Studio/App.
- Connections/Compare/Features/Premium/FAQ: `ConnectorsSection`, `BeforeAfterShowcase`, `FeaturesSection`, `PremiumShowcase`, `PremiumAccessModal`, `FAQSection`.
- Real Studio Editor: `App`, `StlPreview`, `CompareView2`, `JobHistory`, `CurrentModelSummary`, `AnalysisResult`, `StudioHeader`, `StudioSidebar`, `StudioEmptyState`, `StudioWorkflowBar`.
- Admin: `AdminApp`, `AdminFeedbackDashboard`.

Детальная карта компонентов, line ranges, CSS class samples и API routes: `docs/recovery-stage-01-component-map.md`.

## 8. Backup comparison

Проверены read-only:

- `.codex-backups/`
- `__incoming_public_redesign__/`
- `__incoming_public_polish__/`
- `tmp_polish_sync/`

Вывод:

- Полная замена из backup/incoming папок небезопасна.
- Текущий проект разделён на `landing.css`, `studio.css`, `admin.css`, shared CSS и большой `main.jsx`.
- Incoming-папки в основном содержат частичные public redesign варианты `main.jsx`/`styles.css` без текущего разделения CSS и без гарантии сохранения актуальной логики.
- Эти версии можно использовать только как визуальных доноров после точечного diff review.

Детали: `docs/recovery-stage-01-backup-comparison.md`.

## 9. Тесты

Запущено:

- `npm run build` — `PASS`.
- Browser baseline через Playwright для `/`, `/app`, `/admin` — navigation `OK`, horizontal scroll `NO` во всех viewport.
- `GET /api/v1/me` — HTTP `200`.

Не запускались:

- backend/worker/admin/premium/data-processing smoke scripts, потому что значительная часть таких тестов может создавать jobs, мутировать очереди, загружать/обрабатывать файлы, чистить данные или требовать credentials.

Инвентарь тестов: `docs/recovery-stage-01-tests.txt` и `docs/recovery-stage-01-tests-inventory.txt`.

## 10. Source integrity

Проверка относительно созданного архива:

```text
checked_files=17
changed_files=0
missing_in_archive=2
```

Изменённых файлов в проверяемых областях нет:

- `frontend/src`
- `backend`
- `worker`

Два отсутствующих файла — `.pyc` внутри `__pycache__`, они ожидаемо исключены из архива.

Детали: `docs/recovery-stage-01-source-integrity.txt`.

## 11. Защищённые области

При следующем визуальном восстановлении нельзя менять без отдельного подтверждения:

- `backend/`
- `worker/`
- API contracts
- queue/Redis logic
- upload/processing/export flow
- Premium business logic/state
- Admin business logic and mutations
- routing: `RootComponent`, `App`, `AdminApp`, `PublicLanding`
- component structure/DOM, если дефект можно исправить scoped CSS
- order of CSS imports
- `frontend/src/styles.css` removal/shortening/reordering

## 12. Предлагаемый Stage 02

Только после отдельного задания:

1. Landing header geometry: сравнить baseline и эталон, исправить только scoped CSS, критерий: no horizontal scroll, header не ломает `/app` и `/admin`.
2. Landing hero first-screen: spacing/scale only, критерий: desktop/mobile screenshots до/после.
3. Workflow section spacing: только CSS, критерий: карточки не перекрываются на 1920/1440/390.
4. Connections image/card cleanup: только CSS/assets при необходимости, критерий: нет белых артефактов, без смены текста/DOM.
5. Compare section alignment: только CSS, критерий: before/after slider и метрики читаются.
6. Features section visual stabilization: только CSS, критерий: карточки одинаковой высоты и без overflow.
7. Premium section visual stabilization: только CSS, без изменения Premium flow.
8. FAQ/footer spacing: только CSS, критерий: footer виден на full-page screenshot.
9. `/app` Studio spacing pass: после подтверждения landing, только визуальные CSS-правки.
10. `/admin` spacing pass: после подтверждения Studio, только визуальные CSS-правки.

Каждая задача должна завершаться build, screenshots и проверкой `/`, `/app`, `/admin`.

## 13. Созданные файлы

- `docs/VISUAL_RECOVERY_STAGE_01_REPORT.md`
- `docs/recovery-stage-01-environment.txt`
- `docs/recovery-stage-01-backup.txt`
- `docs/recovery-stage-01-frontend-build.txt`
- `docs/recovery-stage-01-dist-before.sha256`
- `docs/recovery-stage-01-dist-after.sha256`
- `docs/recovery-stage-01-dist-diff.txt`
- `docs/recovery-stage-01-tests-inventory.txt`
- `docs/recovery-stage-01-tests.txt`
- `docs/recovery-stage-01-css-inventory.md`
- `docs/recovery-stage-01-component-map.md`
- `docs/recovery-stage-01-backup-comparison.md`
- `docs/recovery-stage-01-browser-console.txt`
- `docs/recovery-stage-01-api-and-files.txt`
- `docs/recovery-stage-01-source-integrity.txt`
- `docs/visual-baseline/*.png`
- `docs/visual-baseline/manifest.json`

## 14. Что не выполнялось

- Дизайн не менялся.
- JSX не менялся.
- CSS не менялся.
- Backend не менялся.
- Worker не менялся.
- API не менялся.
- Deploy не выполнялся.
- Деструктивные smoke tests не запускались.
- Второй этап визуального восстановления не начинался.

# Stage 05.7 — Premium Section

## Исходное состояние

- Исходный SHA: `52b28c232c616cc02f91fe0f91316ff09e1b3f03`.
- Рабочий git-клон перед изменениями был чистым.
- `HEAD` совпадал с `origin/main`.
- Deploy-каталог `/home/codex/projects/vk-stl-master` не является git-репозиторием и используется только для сборки/deploy.

## Фактическая структура Premium-секции

Публичная Premium-секция реализована в `frontend/src/main.jsx`:

- `PremiumShowcase` — секция лендинга `#premium`.
- `PremiumPlanCard` — основная карточка Premium.
- `PricingComparison` — сравнение Free / Premium.
- `PricingTrustBar` — нижняя строка доверия.

Premium modal реализован отдельно:

- `PremiumAccessModal`.
- Состояния modal: `intro`, `creating_request`, `message_ready`, `waiting_for_code`, `enter_code`, `verifying_code`, `premium_active`, `request_rejected`, `error`.

Header Premium control и backend/API logic не изменялись.

## Существующие данные и тексты

Заголовок секции: `Выберите подходящий режим работы`.

Подзаголовок: `Начните с бесплатного доступа и подключите Premium, когда потребуются увеличенные лимиты, повышенный приоритет и регулярная обработка тяжёлых STL.`

План:

- Название: `STL Master Premium`.
- Badge: `Подключение через заявку`.
- Цена: `299 ₽ / месяц`.
- Годовой вариант: `2 999 ₽ в год (-17%). Premium активируется после заявки и подтверждения.`
- CTA: `Подключить Premium`.
- Footnote: `Заявку проверяет администратор и выдаёт access-code для подключения Premium.`

Преимущества сохранены без изменения порядка:

1. Файлы STL до 300 МБ.
2. До 2 активных задач одновременно.
3. До 10 задач в очереди.
4. До 50 загрузок в час.
5. Повышенный приоритет обработки.
6. STL, ZIP, JSON и TXT в пакете результата.

Сравнение Free / Premium содержит 8 строк:

1. Размер STL-файла.
2. Активные задачи.
3. Очередь пользователя.
4. Загрузки в час.
5. Приоритет обработки.
6. Редактор и операции STL.
7. Пакет результата.
8. Подключение.

## Premium request flow

Логика сохранена:

- создание заявки через `/api/v1/premium-requests`;
- статус заявки через `/api/v1/premium-requests/by-number/{request_number}` или `/api/v1/premium-requests/{application_id}`;
- активация кода через `/api/v1/premium/activate`;
- `requested_plan`: `premium_monthly_299`;
- сообщение пользователю готовится локально в modal;
- заявка не отправлялась во время визуальной проверки.

## Active / inactive / unauthorized states

- Active state остаётся в `PremiumAccessModal` и зависит от существующего ответа активации.
- Inactive state использует текущий CTA `Подключить Premium` и текущий обработчик `onPremium`.
- Unauthorized state отдельной логикой в Premium-секции не вводился; существующий flow через заявку и код сохранён.
- Расчёт срока Premium не менялся.

## Loading / success / error states

Визуальная логика modal не менялась:

- loading: `creating_request`, `verifying_code`;
- success: `message_ready`, `premium_active`;
- error: `error`, `request_rejected`;
- duplicate/повторные статусы обрабатываются существующей backend/frontend логикой.

## Изменённые файлы

- `frontend/src/styles.css` — добавлен scoped Stage 05.7 override в конец файла.
- `docs/STAGE-05-7-PREMIUM.md` — отчёт этапа.
- `docs/stage-05-7-premium/before/*` — baseline screenshots и результаты до правки.

JSX не изменялся.

## Изменённые CSS-селекторы

Добавлены high-specificity selectors только для публичной Premium-секции:

- `.publicLanding.publicSite #premium.premiumShowcase`
- `.publicLanding.publicSite #premium.premiumShowcase::before`
- `.publicLanding.publicSite #premium .launchSectionHeader`
- `.publicLanding.publicSite #premium .sectionKicker`
- `.publicLanding.publicSite #premium .premiumFrame`
- `.publicLanding.publicSite #premium .premiumPricingCard`
- `.publicLanding.publicSite #premium .premiumPricingCard::after`
- `.publicLanding.publicSite #premium .premiumCardTop`
- `.publicLanding.publicSite #premium .premiumBadge`
- `.publicLanding.publicSite #premium .premiumMark`
- `.publicLanding.publicSite #premium .premiumRequestPrice`
- `.publicLanding.publicSite #premium .premiumPrimaryButton`
- `.publicLanding.publicSite #premium .premiumCompareWrap`
- `.publicLanding.publicSite #premium .premiumComparePanel`
- `.publicLanding.publicSite #premium .premiumCompareHeader`
- `.publicLanding.publicSite #premium .premiumCompareRows`
- `.publicLanding.publicSite #premium .premiumCompareRow`
- `.publicLanding.publicSite #premium .pricingTrustBar`

Media rules added for `1180px`, `720px`, `390px`.

## Почему потребовался override

Baseline production на `https://app.stlmaster.online/#premium` показывал Premium-секцию почти как нативный HTML: `premiumPricingCard`, `premiumComparePanel` и `premiumPrimaryButton` не получали ожидаемые профессиональные стили. Computed styles показывали `background: none`, `border: 0`, `button display: inline-block`, `padding: 1px 6px`.

Причина: старый/legacy слой и stale CSS asset не давали стабильного применения Premium-правил в production. Override в конце `styles.css` повышает специфичность только внутри `#premium`, меняет hash CSS asset и не затрагивает другие секции.

## Layout

Desktop:

- Intro сверху через существующий `SectionHeader`.
- Основной блок — две колонки: Premium card + comparison panel.
- Premium card визуально главный элемент.
- Free не выглядит искусственно плохим: значения сравнения нейтральные, Premium подсвечен спокойным cyan/violet.

Tablet:

- До `1180px` `premiumFrame` перестраивается в одну колонку.
- Trust bar перестраивается в две колонки.

Mobile:

- До `720px` одна колонка.
- Comparison table превращается в вертикальные rows с подписями `Бесплатно` и `Premium`.
- CTA занимает всю ширину карточки.

## Modal verification

Полный редизайн modal не выполнялся. Premium modal CSS и JSX не менялись.

Проверяется после deploy:

- opening/closing;
- overlay;
- Escape;
- mobile width;
- отсутствие выхода за viewport;
- без отправки реальной заявки.

## Build

`npm run build` в `/home/codex/projects/vk-stl-master/frontend`: PASS.

Новый CSS asset после правки: `index-fZspslSS.css`.

Предупреждения VKUI `use client` существующие, Stage 05.7 их не добавлял.

## Regression

Перед deploy выполнена сборка. Production regression выполняется после push/deploy.

Требования:

- `/` 200;
- `/app` 200;
- `/admin` 200;
- `/api/v1/me` 200;
- no horizontal overflow;
- no console errors/page errors;
- Premium request не отправляется.

## Screenshots

Baseline сохранён:

- `docs/stage-05-7-premium/before/premium-1920.png`
- `docs/stage-05-7-premium/before/premium-1536.png`
- `docs/stage-05-7-premium/before/premium-1440.png`
- `docs/stage-05-7-premium/before/premium-1366.png`
- `docs/stage-05-7-premium/before/premium-1280.png`
- `docs/stage-05-7-premium/before/premium-1024.png`
- `docs/stage-05-7-premium/before/premium-900.png`
- `docs/stage-05-7-premium/before/premium-768.png`
- `docs/stage-05-7-premium/before/premium-430.png`
- `docs/stage-05-7-premium/before/premium-390.png`
- `docs/stage-05-7-premium/before/premium-375.png`
- `docs/stage-05-7-premium/before/premium-360.png`
- `docs/stage-05-7-premium/before/premium-320.png`
- `docs/stage-05-7-premium/before/results.json`

After/production screenshots are collected after deploy.

## Checksums

Protected areas before changes:

`backend/`, `worker/`, `frontend/src/studio/`, `frontend/src/admin/` checksum:

`869a67de46ee887b3223c5e6ce39dcf68fe784ba662db3d8dcde68468b13c871`

Expected after changes: identical.

## Подтверждение отсутствия изменений логики

- Backend/API не менялись.
- Worker не менялся.
- Premium activation logic не менялась.
- Premium request logic не менялась.
- Premium duration calculation не менялся.
- Auth, Upload, Viewer, History не менялись.
- Header/Hero/Workflow/Connections/Features/Compare/FAQ/Footer не менялись.
- Изменение только визуальное и scoped к `#premium`.

## Отложенные замечания

- Общий Landing polish для соседних секций выполняется отдельным этапом.
- Возможное дальнейшее упрощение CSS-дублей откладывается до отдельного cleanup-этапа.

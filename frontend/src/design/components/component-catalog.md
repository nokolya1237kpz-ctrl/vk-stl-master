# Component Catalog

Статус: каталог существующих компонентов. Ничего не удалять и не переименовывать без отдельного аудита использования.

Источник: `frontend/src/main.jsx`, `frontend/src/studio/StudioComponents.jsx`, Stage 01 component map.

## Landing

- `PublicLanding` — публичный лендинг и переходы к app/access/premium states.
- `HeroSection` — первый экран лендинга.
- `StudioMockup` — маркетинговый mockup Studio внутри Hero.
- `SectionHeader` — заголовки секций лендинга.
- `WorkflowSection` — блок процесса работы.
- `WorkflowIcon` — иконки шагов workflow.
- `ConnectorsSection` — блок типов соединений.
- `ConnectionCard` — карточка соединения.
- `ConnectionParameters` — параметры/описания соединений.
- `BeforeAfterShowcase` — блок До/После.
- `FeaturesSection` — блок возможностей.
- `StlMarketingViewer` — 3D/маркетинговый визуал для landing/features.
- `FAQSection` — вопросы и ответы.
- `LaunchContacts` — контактный/footer-related блок.

## Premium

- `PremiumShowcase` — секция Premium на landing.
- `PremiumPlanCard` — карточка плана.
- `PricingComparison` — сравнение тарифов.
- `PricingTrustBar` — доверительные метрики/условия.
- `PremiumAccessModal` — Premium/access flow modal.
- `PremiumStatusControl` — управление/отображение Premium состояния в app.
- `PublicModal` — публичная модалка доступа/сообщений.
- `ModalArtScene` — декоративная сцена в modal flow.
- `DemoStudioPreview` — preview внутри modal/premium flow.

## Studio

- `App` — основной пользовательский маршрут `/`/`/app`, state container и API orchestration.
- `StudioHeader` — header настоящего Studio UI.
- `StudioSidebar` — sidebar инструментов Studio.
- `StudioEmptyState` — пустое состояние Studio.
- `StudioWorkflowBar` — workflow/status bar Studio.
- `WorkflowPanel` — панель этапов обработки.
- `ProcessingStage` — состояние этапа обработки.
- `CurrentModelSummary` — сводка текущей модели.
- `CurrentResultBlock` — блок текущего результата.
- `AnalysisResult` — вывод анализа/проверок.
- `JobInfoPanel` — информация о job.
- `FeedbackPanel` — отправка feedback.

## Viewer

- `StlPreview` — основной viewer/preview STL и related overlays.
- `ComparePane` — canvas/pane сравнения.
- `CompareView2` — режим сравнения результатов.

## History

- `JobHistory` — история задач.
- `GeneratedFilesBlock` — список созданных файлов.
- `HistoryGeneratedFiles` — файлы в исторической записи.
- `ProcessingHistoryTimeline` — timeline обработки.

## Compare

- `ComparePane` — отдельная панель сравнения.
- `CompareView2` — full compare view.
- `BeforeAfterShowcase` — marketing compare на landing.

## Admin

- `AdminApp` — входной компонент маршрута `/admin`.
- `AdminFeedbackDashboard` — основная админ-панель/feedback dashboard.

## Shared

- `AccessRequestForm` — форма запроса доступа.
- `LaunchIcon` — shared visual icon helper.
- `SectionHeader` — shared landing section heading pattern.
- `PublicModal` — shared modal shell для публичной части.

## Правила каталога

- Компоненты с API calls нельзя переписывать ради визуального восстановления.
- Компоненты, связанные с upload/jobs/premium/admin actions, считаются logic-sensitive.
- В будущих этапах предпочтительны scoped CSS правки поверх текущей структуры DOM.
- Любой кандидат на удаление сначала должен пройти runtime usage check и screenshot verification.

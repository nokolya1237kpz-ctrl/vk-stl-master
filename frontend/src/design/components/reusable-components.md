# Reusable Components

Статус: анализ повторяющихся элементов существующего STL Master. Это не новая библиотека и не код.

## Buttons

### Primary Button

Существующие проявления:

- `primaryCta` на Landing Hero.
- `premiumPrimaryButton` в Premium.
- `premiumFlowButton` в Premium modal.
- `connectionsCtaButton` в Connections.

Назначение: главное действие на экране или в блоке.

### Secondary Button

Существующие проявления:

- `secondaryCta` на Landing Hero.
- dark/outline action buttons в Studio mockup.
- action buttons inside `previewActions` and `historyActions`.

Назначение: полезное, но не главное действие.

### Ghost / Link Button

Существующие проявления:

- `sectionGhostLink`.
- `premiumModalLinkButton`.
- footer/contact links.

Назначение: переходы и вторичные навигационные действия.

### Danger Button

Существующие проявления:

- `adminDangerPanel button`.
- row/context admin destructive controls.

Назначение: опасные операции. Не должен использовать primary gradient.

### Segmented Button

Существующие проявления:

- `segmentedOptions button`.
- `modeOptions button`.
- `compareModeTabs button`.
- `workflowToggleRail button`.

Назначение: выбор режима, оси, типа соединения, compare mode.

## Cards

### Base Card

Существующие проявления:

- feature/connectors cards.
- admin summary cards.
- modal/tip cards.

Общая роль: отделить один смысловой объект.

### Metric Card

Существующие проявления:

- Landing metrics/trust blocks.
- Compare metrics.
- Admin summary grid.
- `historyLocalStats`.

Общая роль: число + подпись + статус/контекст.

### Feature Card

Существующие проявления:

- `FeaturesSection` cards.
- workflow feature blocks.

Общая роль: возможность продукта с visual proof and action.

### History Card

Существующие проявления:

- `historyCard`.
- `historyStage`.
- generated file items.

Общая роль: результат прошлой операции, downloadable artifacts, status.

### Modal Card

Существующие проявления:

- `premiumApplicationId`.
- `premiumMessagePreview`.
- `premiumTipCard`.
- `premiumWaitingCard`.

Общая роль: structured information inside flow.

## Panels

### Viewer Panel

Существующие проявления:

- `previewPanel`.
- `comparePane`.
- `studioViewportV8`.
- `stlMarketingViewer`.

Общая роль: модель/визуальная рабочая область.

### Inspector Panel

Существующие проявления:

- `studioInfoV8` in Studio mockup.
- `JobInfoPanel`.
- `AnalysisResult`.
- Admin details/side panels.

Общая роль: свойства, проверки, параметры, state.

### Workflow Panel

Существующие проявления:

- `workflowPanel`.
- `processingStage`.
- `currentModelSummary`.
- `processingHistory`.

Общая роль: последовательные этапы и их раскрытие.

## Headers

### Section Header

Существующие проявления:

- `SectionHeader`.
- `launchSectionHeader`.
- `sectionKicker`, `sectionNumber`, `sectionLabel`.

Общая роль: маркировать секцию и задавать иерархию.

### Panel Header

Существующие проявления:

- `previewHeader`.
- `panelHeader`.
- `comparePaneHeader`.
- `historyCardTop`.

Общая роль: label + title/status/action.

## Inputs and Forms

### Text Input

Существующие проявления:

- `AccessRequestForm`.
- `premiumCodeForm`.
- admin login/user form.

### Search / Filter

Существующие проявления:

- `adminSearchResults`.
- admin toolbar search/filter controls.

### Range / Slider

Существующие проявления:

- `beforeAfterSlider`.
- viewer/process controls using slider-style inputs.

## Badges

### Status Pill

Существующие проявления:

- `qualityPill`.
- `historyStatus`.
- `previewStatus`.
- Premium state controls.

### Section Kicker

Существующие проявления:

- `sectionNumber`, `sectionLabel`.
- `sectionKickerNumber`, `sectionKickerLabel`.

### Compare Badge

Существующие проявления:

- `compareSideBadge-before`.
- `compareSideBadge-after`.

## Tables

### Admin Table

Существующие проявления:

- `adminTable`.
- row actions.
- pagination.
- bulk action bar.

Общая роль: управление объектами и состояниями.

## Modals

### Premium Flow Modal

Существующие проявления:

- `premiumModalBackdrop`.
- `premiumAccessModal`.
- state modifiers including `premiumAccessModal-message_ready`.

### Public Modal

Существующие проявления:

- `PublicModal`.
- `ModalArtScene`.
- `DemoStudioPreview`.

## Navigation

### Public Header

Существующие проявления:

- `publicTopNav`, `topNavV8`, `publicTopLinks`, `publicTopActions`.

### Studio Sidebar

Существующие проявления:

- `StudioSidebar`.
- `studioToolsV8` in mockup.

### Admin Sidebar

Существующие проявления:

- `adminSidebar`.
- collapsed sidebar state.

## Loaders and Progress

### Spinner

Существующие проявления:

- `premiumButtonSpinner`.
- `premiumSpin` keyframes.

### Processing Status

Существующие проявления:

- `processingStage`.
- `progressFooter`.
- preview loading/status.

### Marketing Viewer Loader

Существующие проявления:

- `stlMarketingLoader`.
- `stlMarketingFallback`.

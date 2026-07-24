# UI Inventory

Статус: каталог существующего интерфейса STL Master. Документ описывает только то, что уже есть в проекте. Никакие элементы не добавляются, не подключаются и не заменяются.

Источники анализа: `frontend/src/main.jsx`, `frontend/src/studio/StudioComponents.jsx`, `frontend/src/styles.css`, `frontend/src/landing/landing.css`, `frontend/src/studio/studio.css`, `frontend/src/admin/admin.css`.

## Landing

### Кнопки

- Header CTA: `publicTopCta`, `topCtaV8`, `premiumHeaderButtonV9`.
- Hero primary CTA: `primaryCta`.
- Hero secondary CTA: `secondaryCta`.
- Section ghost/link action: `sectionGhostLink`, `compact`, `compareMoreLink`.
- Connections CTA: `connectionsCtaButton`.
- Workflow step toggles: buttons inside `workflowStepNav`, `workflowToggleRail`.
- Footer/contact actions: buttons and links inside `LaunchContacts`.

### Карточки

- Hero benefits: `heroBenefits`, `heroBenefitsV8`.
- Workflow cards/steps: `workflowCard`, `demoWorkflowShell`, `workflowFilePanel`.
- Connection cards: `ConnectionCard` and `connectionsGrid` patterns.
- Compare card: `demoCompareCard`, `demoCompareWorkbench`.
- Feature cards: `keyFeaturesSection`, blocks inside `FeaturesSection`.
- Pricing/Premium cards: `PremiumPlanCard`, `PricingComparison`, `PricingTrustBar`.
- Contact/footer cards: Launch/contact panels.

### Заголовки

- Section header: `SectionHeader`, `launchSectionHeader`.
- Kicker pattern: `sectionKicker`, `sectionNumber`, `sectionLabel`, `sectionKickerNumber`, `sectionKickerLabel`.
- Hero title: `heroTitleLine`, `heroTitleAccent`.
- Landing section titles inside `publicSection`.

### Иконки

- `LaunchIcon` SVG helper: upload, analyze, repair, cube, split, connectors, shield, export.
- Inline glyphs in Studio mockup toolbar/rail.
- Status dots and check/warning markers in compare/Studio mockup.

### Бейджи и теги

- Hero label: `heroLabel`, `heroLabelV8`.
- Compare side badges: `compareSideBadge`, `compareSideBadge-before`, `compareSideBadge-after`.
- Section numbers/labels.
- Premium status badges and plan labels.

### Контейнеры и секции

- Main public site shell: `publicSite`.
- Hero section: `launchHero`, `heroV8`, `heroCopyV8`.
- Generic public section: `publicSection`.
- Connections: `connectionsSection`, `connectionsGrid`.
- Compare: `beforeAfterShowcase`, `demoCompareSection`.
- Features: `keyFeaturesSection`, `demoWorkflowSection`.

### Viewer/visual blocks

- Marketing Studio mockup: `StudioMockup`, `studioShellV8`, `studioViewportV8`.
- Marketing STL/WebGL viewer: `StlMarketingViewer`, `stlMarketingCanvas`, `stlMarketingLoader`, `stlMarketingFallback`.
- Compare viewers: `compareViewerBefore`, `compareViewerAfter`.

## Studio / App

### Кнопки

- VKUI `Button` in app actions.
- Viewer action buttons: `previewActions`.
- Micro/action controls: `microButtons`, `orientationActions`, `movePad`, `splitPlaneHeader`.
- Segmented options: `segmentedOptions`, `modeOptions`, `improvementOptions`, `cleanupOptions`, `reductionOptions`.
- Current model actions: `currentModelActions`.
- History actions: `historyActions`, `historyDownload`.
- Premium header/status controls in editor: `premiumHeaderButtonV9`, `premiumStatusControl`.

### Карточки и панели

- Viewer panel: `previewPanel`.
- Workflow accordion panels: `workflowPanel`, `processingStage`.
- Current model panel: `currentModelSummary`.
- Current result panel: `currentResultBlock`.
- Generated files panel: `generatedFilesPanel`.
- Job information panel: `JobInfoPanel`.
- Feedback panel: `FeedbackPanel`.
- History section/cards: `historySection`, `historyCard`, `historyStage`.

### Заголовки

- Panel header: `previewHeader`, `panelHeader`.
- Panel label: `panelLabel`.
- Section title: `sectionTitle`.
- Result header: `resultHeroTop`.

### Viewer

- STL preview mount: `previewCanvas`.
- Preview state: `previewStatus`.
- Heatmap legend: `heatmapLegend`, `heatNone`, `heatLow`, `heatMedium`, `heatHigh`.
- Artifact legend: `artifactLegend`, `artifactElongated`, `artifactSpike`, `artifactSuspicious`.
- Preview warning/help: `previewWarning`, `previewHelp`.

### Compare

- Compare pane: `comparePane`, `comparePaneHeader`, `compareCanvas`.
- Compare view: `compareView2`, `compareToolbar`, `compareModeTabs`.
- Compare grid/mode: `compareViewportGrid`, `single`, `split`, `compareOverlayMode`.
- Overlay controls: `overlayControl`.
- Compare metrics: `compareMetrics`.
- Compare legend: `compareLegend`, `defectRed`, `defectOrange`, `defectYellow`.

### Progress / loader / status

- Processing stages: `processingStage`, `stageOk`, `stageWarn`, `stageChevron`, `stageBody`.
- Progress footer: `progressFooter`.
- Quality pill: `qualityPill`, `qualityReady`, `qualityGood`, `qualityNeedsWork`, `qualityUnknown`.
- Preview loading/status text: `previewState`, `previewStatus`.

### Lists

- Generated files groups/list/items.
- History files details: `historyFiles`.
- History file rows: `historyFileList`, `historyFileRow`.
- Processing history timeline: `ProcessingHistoryTimeline`.

## Admin

### Кнопки

- Admin tab buttons: `adminTabs button`.
- Login/form buttons: `adminLoginPanel button`, `adminUserForm button`.
- Row actions: `adminRowActions button`.
- Toolbar buttons: `adminToolbar button`.
- Bulk bar buttons: `adminBulkBar button`.
- Danger panel buttons: `adminDangerPanel button`.
- Context menu buttons: `adminContextMenu`, `adminContextMenuList button`.
- Pagination buttons: `adminPagination button`.

### Таблицы

- Admin tables: `adminTable`, `adminTable th`, `adminTable td`.
- Row action groups.
- Pagination/footer control patterns.

### Панели и контейнеры

- Admin root: `adminDashboard`.
- Sidebar state: `adminDashboard.sidebarCollapsed`, `adminSidebar`.
- Summary grid: `adminSummaryGrid`.
- Login panel: `adminLoginPanel`.
- User form: `adminUserForm`.
- Job grid: `adminJobGrid`.
- Attention list: `adminAttentionList`.
- Danger panel: `adminDangerPanel`.

### Формы

- Admin login fields.
- Admin user form fields.
- Search controls: `adminSearchResults`, toolbar/search patterns.
- Segmented toolbar controls: `segmentedOptions` inside admin toolbar.

### Badges/status

- Admin nav badges: `adminNavBadge`.
- Admin version/status markers.
- Job/user/application statuses in tables.

### Sidebar

- Admin sidebar: `adminSidebar`.
- Collapsed sidebar behavior: `sidebarCollapsed`.
- Sidebar toggle and logout: `adminSidebarToggle`, `adminLogout`.

## Premium

### Buttons

- Header premium CTA: `premiumHeaderButtonV9`.
- Premium flow button: `premiumFlowButton`.
- Premium code form button: `premiumCodeForm button`.
- Modal link button: `premiumModalLinkButton`.
- Premium primary button: `premiumPrimaryButton`.

### Modal windows

- Premium modal backdrop: `premiumModalBackdrop`.
- Modal shell: `premiumAccessModal`.
- Close button: `premiumModalClose`.
- Modal art column: `premiumModalArt`.
- Modal content column: `premiumModalContent`.
- State modifier: `premiumAccessModal-message_ready`.

### Cards / alerts / forms

- Application ID card: `premiumApplicationId`.
- Message preview: `premiumMessagePreview`.
- Tip card: `premiumTipCard`.
- Success metadata: `premiumSuccessMeta`.
- Waiting card: `premiumWaitingCard`.
- Inline alert: `premiumInlineAlert`.

### Loader/status

- Button spinner: `premiumButtonSpinner`, `premiumSpin`.
- Flow button states: `.success`, `.error`, `:disabled`.
- Modal status icon: `modalStatusIcon.success`.

## Viewer

### Panels

- `previewPanel` for real app viewer.
- `studioViewportV8` for landing mockup.
- `stlMarketingViewer` for landing feature visuals.
- Compare viewer panels in before/after.

### Controls

- `previewActions`.
- `viewportSideRail`.
- `viewportBottomBar`.
- `axisGizmo`, `viewportGizmo`.
- `sectionPlaneSvg`, `sectionCutSvg`.

### States

- Loading/fallback: `stlMarketingLoader`, `stlMarketingFallback`.
- Warnings/help: `previewWarning`, `previewHelp`.
- Legends: heatmap/artifact/compare legends.

## History

### Containers

- `historySection`.
- `historyList`.
- `historyCard`.
- `processingHistory`.
- `historyStage`.

### Actions

- `historyDownload`.
- `historyActions`.
- `historyStageActions`.
- `selectedContinuation`.

### Status

- `historyStatus` with states: completed, failed, expired, error, processing, queued, loading.
- `historyWarning`.

## Compare

### Toolbars and controls

- `compareToolbar`.
- `compareModeTabs`.
- `compareHighlightActions`.
- `overlayControl`.
- `beforeAfterSlider`.

### Visual indicators

- `beforeAfterDivider`.
- `compareSideBadge`.
- `compareReadyStatus`.
- `compareLegend`.
- Defect colors: `defectRed`, `defectOrange`, `defectYellow`.

## Skeleton / tooltip / dropdown

### Skeleton

No dedicated reusable skeleton component was found in current source. VKUI may include skeleton styles through dependency, but project-level skeleton usage was not identified as a named STL Master component.

### Tooltip

No dedicated STL Master tooltip component was found. VKUI tooltip code exists in bundled dependency, but current project-level tooltip pattern should be treated as not established.

### Dropdown

No standalone dropdown component was found. Existing patterns are segmented controls, context menus, disclosure panels/details, and modal flows.

## Notification / alert

- `premiumInlineAlert`.
- `previewWarning`.
- `historyWarning`.
- Admin attention/danger panels.
- Browser/app feedback panels.

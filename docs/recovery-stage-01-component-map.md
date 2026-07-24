# Recovery Stage 01 Component Map

Аудит чтением. JSX не изменялся.

## Import tree from `frontend/src/main.jsx`

- L1: `import React, { useEffect, useMemo, useRef, useState } from "react";`
- L2: `import { createRoot } from "react-dom/client";`
- L3: `import { Button, ConfigProvider, Panel, PanelHeader, Progress, View } from "@vkontakte/vkui";`
- L4: `import "@vkontakte/vkui/dist/vkui.css";`
- L5: `import * as THREE from "three";`
- L6: `import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";`
- L7: `import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";`
- L8: `import "./styles.css";`
- L9: `import "./studio/studio.css";`
- L10: `import "./styles/tokens.css";`
- L11: `import "./styles/reset.css";`
- L12: `import "./styles/shared.css";`
- L13: `import "./landing/landing.css";`
- L14: `import "./admin/admin.css";`
- L15: `import { StudioHeader, StudioSidebar, StudioEmptyState, StudioWorkflowBar } from "./studio/StudioComponents.jsx";`

## Route tree

- `/` -> `App` -> `PublicLanding`
- `/app` -> `App` -> Studio/editor UI
- `/admin` -> `RootComponent` -> `AdminApp` -> `AdminFeedbackDashboard`

Routing evidence:
- L9165: `const RootComponent = typeof window !== "undefined" && window.location.pathname === "/admin" ? AdminApp : App;`
- L9167: `createRoot(document.getElementById("root")).render(<RootComponent />);`
- L6242: `const [publicView, setPublicView] = useState(() => (window.location.pathname === "/app" ? "app" : "home"));`
- L7173: `if (publicView === "home") {`
- L7190: `if (publicView === "access") {`
- L7198: `if (publicView === "premium") {`
- L5176: `function PublicLanding({ onStartCut, onDemo, onPremiumActivated, currentUser = null, currentUserLoading = false, featureFlags = DEFAULT_FEATURE_FLAGS }) {`
- L7176: `<PublicLanding`
- L9151: `function AdminApp() {`
- L9165: `const RootComponent = typeof window !== "undefined" && window.location.pathname === "/admin" ? AdminApp : App;`

## Components

### `GeneratedFilesBlock`

- file: `frontend/src/main.jsx`
- lines: 1030-1098
- area: unknown
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `analysisHeader, generatedFileActions, generatedFileItem, generatedFilesGroup, generatedFilesGroups, generatedFilesList, generatedFilesPanel, panelLabel`
- API routes: `none detected`

### `HistoryGeneratedFiles`

- file: `frontend/src/main.jsx`
- lines: 1099-1116
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `historyFiles`
- API routes: `none detected`

### `JobHistory`

- file: `frontend/src/main.jsx`
- lines: 1117-1219
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `historyActions, historyCard, historyCardTop, historyDownload, historyList, historySection, historyStatus, historyWarning, loading, sectionTitle, status`
- API routes: `/api/v1/jobs/`

### `StlPreview`

- file: `frontend/src/main.jsx`
- lines: 1220-2319
- area: unknown
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `artifactElongated, artifactLegend, artifactSpike, artifactSuspicious, heatHigh, heatLow, heatMedium, heatNone, heatmapLegend, localSelectionEnabled, panelLabel, previewActions, previewCanvas, previewHeader, previewHelp, previewPanel, previewState, previewStatus, previewWarning, selectionActive`
- API routes: `none detected`

### `ComparePane`

- file: `frontend/src/main.jsx`
- lines: 2320-2608
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `compareCanvas, comparePane, comparePaneHeader`
- API routes: `none detected`

### `CompareView2`

- file: `frontend/src/main.jsx`
- lines: 2609-2779
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `compareHighlightActions, compareHint, compareLegend, compareMetrics, compareModeTabs, compareOverlayMode, compareToolbar, compareView2, compareViewportGrid, defectOrange, defectRed, defectYellow, overlayControl, single, split`
- API routes: `none detected`

### `WorkflowPanel`

- file: `frontend/src/main.jsx`
- lines: 2780-2795
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `isOpen, open, processingStage, stageBody, stageChevron, stageOk, stageWarn, success, workflowPanel, workflowPanelBody, workflowPanelHeader`
- API routes: `none detected`

### `ProcessingStage`

- file: `frontend/src/main.jsx`
- lines: 2796-2809
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `none detected`
- API routes: `none detected`

### `CurrentModelSummary`

- file: `frontend/src/main.jsx`
- lines: 2810-2879
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `activePanel, currentModelActions, currentModelBody, currentModelGrid, currentModelHeader, currentModelSummary, current_model, open, stageChevron, workflowPanel, workflowPanelBody, workflowPanelHeader`
- API routes: `none detected`

### `CurrentResultBlock`

- file: `frontend/src/main.jsx`
- lines: 2880-3028
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `compareView, compareViewHeader, currentResultBlock, panelLabel, qualityPill, resultHeroGrid, resultHeroTop, resultPrimaryActions, tone`
- API routes: `none detected`

### `ProcessingHistoryTimeline`

- file: `frontend/src/main.jsx`
- lines: 3029-3141
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `additionalIntro, created, historyActions, historyFileList, historyFileRow, historyLocalStats, historyOpen, historyPanelBody, historyStage, historyStageActions, item, open, panelLabel, processingHistory, processingStage, stageBody, stageChevron, stageOk, stageWarn, stepOpen, visible_result, workflowPanel, workflowPanelBody, workflowPanelHeader`
- API routes: `none detected`

### `LaunchIcon`

- file: `frontend/src/main.jsx`
- lines: 3142-3166
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `launchSvgIcon`
- API routes: `none detected`

### `PremiumStatusControl`

- file: `frontend/src/main.jsx`
- lines: 3167-3215
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `premiumHeaderButtonV9, premiumStatusPopover, premiumStatusWrap, publicTopCta, topCtaV8`
- API routes: `none detected`

### `StudioMockup`

- file: `frontend/src/main.jsx`
- lines: 3216-3289
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `axisGizmo, axisX, axisY, axisZ, bad, quickActions, sectionCutSvg, sectionPlaneSvg, studioBody, studioBodyV8, studioCheckButton, studioChecks, studioInfo, studioInfoV8, studioMenuDots, studioShellV8, studioSkull, studioToolFoot, studioTools, studioToolsV8, studioTopbar, studioTopbarV8, studioViewport, studioViewportV8, viewportBottomBar, viewportGizmo, viewportSideRail, warn`
- API routes: `none detected`

### `SectionHeader`

- file: `frontend/src/main.jsx`
- lines: 3290-3313
- area: unknown
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `launchSectionHeader, sectionKicker, sectionKickerDivider, sectionKickerLabel, sectionKickerNumber`
- API routes: `none detected`

### `HeroSection`

- file: `frontend/src/main.jsx`
- lines: 3314-3347
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `browserNote, browserNoteV8, formatRow, formatRowV8, heroActionsV8, heroBenefits, heroBenefitsV8, heroCopy, heroCopyV8, heroLabel, heroLabelV8, heroLead, heroMetrics, heroMetricsV8, heroTitleAccent, heroTitleLine, heroV8, icon, in-view, launchActions, launchHero, metricIcon, metricIcon-, primaryCta, revealSection, secondaryCta`
- API routes: `none detected`

### `WorkflowIcon`

- file: `frontend/src/main.jsx`
- lines: 3348-3403
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `none detected`
- API routes: `none detected`

### `WorkflowSection`

- file: `frontend/src/main.jsx`
- lines: 3404-3433
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `number, publicSection, revealSection, sectionEyebrow, sectionLabel, sectionNumber, step, workflowArrow, workflowCard, workflowCard-, workflowCardTitle, workflowDescription, workflowEyebrow, workflowGrid, workflowIcon, workflowIntro, workflowSection, workflowStepNumber`
- API routes: `none detected`

### `ConnectionCard`

- file: `frontend/src/main.jsx`
- lines: 3434-3459
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `connectionCaption, connectionCard, connectionCard--, connectionCardAccent, connectionCardContent, connectionCardMode, connectionCardNumber, connectionCardTopline, connectionVisual, id, item`
- API routes: `none detected`

### `ConnectionParameters`

- file: `frontend/src/main.jsx`
- lines: 3460-3480
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `connectionParameterGrid, connectionParameterItem, connectionParameters, connectionParametersIntro`
- API routes: `none detected`

### `ConnectorsSection`

- file: `frontend/src/main.jsx`
- lines: 3481-3678
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `connectionsCta, connectionsCtaButton, connectionsEyebrow, connectionsGrid, connectionsHeading, connectorsSection, in-view, publicSection, revealSection, sectionEyebrow, sectionLabel, sectionNumber`
- API routes: `none detected`

### `StlMarketingViewer`

- file: `frontend/src/main.jsx`
- lines: 3679-3880
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `stlMarketingCanvas, stlMarketingFallback, stlMarketingLoader, stlMarketingViewer`
- API routes: `none detected`

### `BeforeAfterShowcase`

- file: `frontend/src/main.jsx`
- lines: 3881-4116
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `beforeAfterDivider, beforeAfterShowcase, beforeAfterSlider, beforeAfterStage, compact, compareAfterClip, compareDragHint, compareMetrics, compareMoreLink, compareReadyStatus, compareSideBadge, compareSideBadge-after, compareSideBadge-before, compareViewer, compareViewerAfter, compareViewerBefore, demoBeforeAfterStage, demoCompareCard, demoCompareMetrics, demoComparePanel, demoComparePanelAfter, demoComparePanelBefore, demoCompareSection, demoCompareStageShell, demoCompareWorkbench, in-view, publicSection, revealSection, sectionGhostLink, sectionLabel, sectionNumber`
- API routes: `none detected`

### `FeaturesSection`

- file: `frontend/src/main.jsx`
- lines: 4117-4217
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `demoWorkflowCta, demoWorkflowSection, demoWorkflowShell, featuresCtaActions, featuresCtaPanel, featuresPrimaryCta, featuresSecondaryLink, in-view, keyFeaturesSection, publicSection, revealSection, sectionLabel, sectionNumber, workflowBridge, workflowDemoStage, workflowFilePanel, workflowInfoPanel, workflowStepNav, workflowStlViewer, workflowToggleRail`
- API routes: `none detected`

### `ModalArtScene`

- file: `frontend/src/main.jsx`
- lines: 4218-4239
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `modalAccessCard, modalArtScene, modalMiniModel, modalMiniPlane, modalMiniPoint, modalMiniSidebar, modalMiniTop, modalMiniViewport, modalMiniWindow, pointA, pointB`
- API routes: `none detected`

### `DemoStudioPreview`

- file: `frontend/src/main.jsx`
- lines: 4240-4256
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `demoConnector, demoCutPlane, demoStudioGrid, demoStudioPreview, demoStudioTop, one, two`
- API routes: `none detected`

### `PricingComparison`

- file: `frontend/src/main.jsx`
- lines: 4257-4277
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `premiumCompareHeader, premiumComparePanel, premiumCompareRows`
- API routes: `none detected`

### `PremiumPlanCard`

- file: `frontend/src/main.jsx`
- lines: 4278-4301
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `premiumBadge, premiumCardTop, premiumMark, premiumPricingCard, premiumPrimaryButton, premiumRequestPrice`
- API routes: `none detected`

### `PricingTrustBar`

- file: `frontend/src/main.jsx`
- lines: 4302-4317
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `pricingTrustBar`
- API routes: `none detected`

### `PremiumShowcase`

- file: `frontend/src/main.jsx`
- lines: 4318-4342
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `premiumCompareEyebrow, premiumCompareWrap, premiumFrame, premiumShowcase, publicSection, revealSection`
- API routes: `none detected`

### `FAQSection`

- file: `frontend/src/main.jsx`
- lines: 4343-4462
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `faqAccordion, faqAccordionColumn, faqAccordionPanel, faqCategoryList, faqEmptyState, faqHeaderSupport, faqIntroBadge, faqIntroCard, faqLayout, faqSearch, faqSection, faqSupportCard, publicSection, revealSection`
- API routes: `none detected`

### `LaunchContacts`

- file: `frontend/src/main.jsx`
- lines: 4463-4595
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `footerAppButton, footerBottom, footerBrand, footerLogo, footerV9, in-view, launchContacts, publicTopBrand, revealSection, socialLinks`
- API routes: `none detected`

### `PremiumAccessModal`

- file: `frontend/src/main.jsx`
- lines: 4596-5107
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `buttonState, compact, copyMessageButton, error, launchStatus, modalClose, modalErrorButton, modalOpenButton, modalStatusIcon, modalVkButton, opened, pending, premiumAccessModal, premiumAccessModal-, premiumApplicationId, premiumButtonSpinner, premiumCodeForm, premiumFlowButton, premiumInlineAlert, premiumInlineError, premiumMessagePreview, premiumModalActions, premiumModalArt, premiumModalBackdrop, premiumModalClose, premiumModalContent, premiumModalLinkButton, premiumModalRenderBadge, premiumModalRenderStage, premiumModalSteps, premiumRenderGlow, premiumRenderGrid, premiumSuccessMeta, premiumTipCard, premiumWaitingCard`
- API routes: `/api/v1/premium-requests, /api/v1/premium-requests/, /api/v1/premium-requests/by-number/, /api/v1/premium/activate`

### `PublicModal`

- file: `frontend/src/main.jsx`
- lines: 5108-5175
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `accessHowToCard, buttonState, copyMessageButton, demoModal, error, errorReasons, launchStatus, modalArt, modalClose, modalContent, modalErrorButton, modalOpenButton, modalPrimaryButton, modalProgress, modalSecondaryLink, modalState-, modalStatusIcon, modalTextButton, modalVkButton, opened, publicForm, publicModal, publicModalBackdrop, sectionKicker, step, success`
- API routes: `/api/v1/access-requests`

### `PublicLanding`

- file: `frontend/src/main.jsx`
- lines: 5176-5254
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `appOpenButton, appOpenButtonV9, compact, compactHeader, mobileSupportButton, publicLanding, publicMenuButton, publicSite, publicTopActions, publicTopBrand, publicTopLinks, publicTopNav, topActionsV8, topBrandV8, topLinksV8, topNavV8`
- API routes: `none detected`

### `AccessRequestForm`

- file: `frontend/src/main.jsx`
- lines: 5255-5264
- area: unknown
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `formSuccessState, ghostBackButton, launchFormPanel, launchStatus, panelLabel, publicForm, publicFormPage, publicLanding, publicSite`
- API routes: `/api/v1/access-requests`

### `JobInfoPanel`

- file: `frontend/src/main.jsx`
- lines: 5265-5324
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `copyJobButton, jobInfoGrid, jobInfoPanel, panelLabel`
- API routes: `none detected`

### `FeedbackPanel`

- file: `frontend/src/main.jsx`
- lines: 5325-5406
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `feedbackChoice, feedbackForm, feedbackHint, feedbackPanel, feedbackStatus, panelLabel`
- API routes: `/api/v1/feedback`

### `AnalysisResult`

- file: `frontend/src/main.jsx`
- lines: 5407-6239
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `aiCleanupHint, aiCleanupStats, analysisGrid, analysisHeader, analysisPanel, beforeAfterToggle, changeMapPanel, compactHeader, connectorNotice, downloadButton, improveHint, improveStats, improveWarnings, noticeGrid, packageReady, panelLabel, plannedOperations, printabilityPanel, printabilitySummary, processingHistory, reductionStats, resultNote, showChangesButton, skippedPanel, splitFiles, splitSummary, symmetryScore, symmetryStats, whatChangedCard, whatChangedGrid, whatChangedPanel`
- API routes: `none detected`

### `App`

- file: `frontend/src/main.jsx`
- lines: 6240-7500
- area: unknown
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `localSelection, publicFormPage, publicLanding, publicSite, ready, studioAccessBanner, studioFileInput, studioInlineActions, studioInspector, studioInspectorCard, studioInspectorLead, studioInspectorNote, studioMovePad, studioPanelLabel, studioQueueHint, studioRangeField, studioSegmentGroup, studioSelectionSummary, studioSettingBlock, studioSettingLabel, studioShell, studioSizeGrid, studioTextField, studioUserCard, studioViewerWorkspace, studioWarning, studioWorkspace`
- API routes: `/api/v1/config/features, /api/v1/jobs/, /api/v1/jobs/upload`

### `AdminFeedbackDashboard`

- file: `frontend/src/main.jsx`
- lines: 7501-9150
- area: Admin
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `access_level, activated, adminAnalyticsPanel, adminAttentionList, adminBackLink, adminBadge, adminBrand, adminBulkBar, adminCleanupButton, adminCleanupStatus, adminContextMenu, adminContextMenuList, adminDangerPanel, adminDashboard, adminEmpty, adminFilters, adminGlobalSearch, adminIssuedCode, adminJobGrid, adminJobPanel, adminJsonPreview, adminLoginButton, adminLoginGrid, adminLoginInfo, adminLoginPanel, adminLoginScreen, adminLogout, adminNavBadge, adminNavIcon, adminNavTitle, adminNotice, adminOperationFilter, adminPagination, adminPasswordField, adminRowActions`
- API routes: `/api/v1/admin/applications, /api/v1/admin/applications/, /api/v1/admin/applications/bulk, /api/v1/admin/applications/delete-test, /api/v1/admin/cleanup/execute, /api/v1/admin/cleanup/scan, /api/v1/admin/cleanup/status, /api/v1/admin/features, /api/v1/admin/feedback, /api/v1/admin/feedback/cleanup-test, /api/v1/admin/feedback/summary, /api/v1/admin/integrity-check, /api/v1/admin/jobs/, /api/v1/admin/jobs/bulk, /api/v1/admin/jobs/delete-test, /api/v1/admin/login, /api/v1/admin/overview, /api/v1/admin/premium-codes, /api/v1/admin/queue, /api/v1/admin/security, /api/v1/admin/system-cleanup, /api/v1/admin/test-data/cleanup, /api/v1/admin/test-data/scan, /api/v1/admin/users, /api/v1/admin/users/, /api/v1/admin/users/bulk, /api/v1/admin/users/delete, /api/v1/admin/users/deletion-preview, /api/v1/jobs/`

### `AdminApp`

- file: `frontend/src/main.jsx`
- lines: 9151-9167
- area: Admin
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `none detected`
- API routes: `none detected`

### `StudioHeader`

- file: `frontend/src/studio/StudioComponents.jsx`
- lines: 17-69
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `studioBrand, studioExportButton, studioHeader, studioHeaderActions, studioIconButton, studioPremiumButton, studioProjectStatus`
- API routes: `none detected`

### `StudioSidebar`

- file: `frontend/src/studio/StudioComponents.jsx`
- lines: 70-109
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `active, id, preset, selectedMode, studioPanelLabel, studioSidebar, studioSidebarFoot, studioSidebarTop, studioToolButton, studioToolGroup, studioToolIcon, studioToolList`
- API routes: `none detected`

### `StudioEmptyState`

- file: `frontend/src/studio/StudioComponents.jsx`
- lines: 110-141
- area: Studio/App
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `studioDropAura, studioEmptyActions, studioEmptyState, studioFileLimits, studioPanelLabel, studioPrimaryAction, studioTextAction`
- API routes: `none detected`

### `StudioWorkflowBar`

- file: `frontend/src/studio/StudioComponents.jsx`
- lines: 142-187
- area: Landing
- used now: probable; file is bundled by `main.jsx`. Confirm runtime reachability before deletion.
- CSS classes sample: `compact, studioErrorText, studioPrimaryAction, studioProgressMini, studioRunActions, studioRunMeta, studioRunPanel, studioSecondaryAction, studioStepper, studioWorkflowBar`
- API routes: `none detected`

## Areas requested

- Hero: `HeroSection`, `StudioMockup`, related landing classes in `landing.css`.
- Workflow: `WorkflowSection`, `WorkflowIcon`.
- Studio mockup on Landing: `StudioMockup`.
- Real Studio Editor: `App`, `StudioHeader`, `StudioSidebar`, `StudioEmptyState`, `StudioWorkflowBar`, viewer/processing components in `main.jsx`.
- Admin: `AdminApp`, `AdminFeedbackDashboard`, classes in `admin.css` plus shared/VKUI styles.

## Unsafe to change during visual recovery

- `App`, `AdminApp`, `RootComponent`, API helper calls, job processing handlers, premium state handlers, upload/processing controls.
- Components that mix UI and API calls should not be rewritten for visual repair; use scoped CSS only after screenshots confirm target route.
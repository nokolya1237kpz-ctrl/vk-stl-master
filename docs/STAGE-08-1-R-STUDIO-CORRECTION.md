# STAGE 8.1-R — Studio workspace visual and UX correction

## Scope

Route: `/app`.

Source SHA: `487159c2cc63813cced0805e63ff7cc3f4d4bc0a`.

Touched areas:

- `frontend/src/main.jsx`
- `frontend/src/studio/StudioComponents.jsx`
- `frontend/src/studio/studio.css`
- `tests/smoke_studio_workspace_correction.sh`
- `tests/run_all_smoke_tests.sh`

Protected areas were not changed:

- `backend/`
- `worker/`
- `frontend/src/landing/`
- `frontend/src/admin/`

Protected checksum before and after: `4a01a449a501aae93f3b901e8fcd63501206f4756611d3af44975c8fe8618d2e`.

## Root Causes

### Clipped bottom process panel

The Studio shell still had several older fixed-height layers:

- `height: 100dvh`
- `min-height: 760px`
- `overflow: hidden`
- fixed desktop `grid-template-rows`
- a later fit guard forcing `.studioWorkflowBar` to `height: 78px` and hiding operation text

Together those rules clipped the bottom process panel on low desktop heights and created confusing nested scroll behavior.

### `demo_original.stl` after clear

The viewer `Очистить` action only called the local Three.js `clearScene()` function. That removed geometry from the viewer, but parent React state still kept:

- `file`
- `jobId`
- `jobStatus`
- `processedPreviewFile`
- `demoMode`
- result badges and overlays

So the header could still show `demo_original.stl` while the scene was empty.

## Fixed Model Flow

Added `resetStudioModel()` in `App` and wired viewer clear to it through `onClearModel`.

The reset clears only current model/session state:

- filename and selected file
- demo marker
- job id/status
- result preview file
- processed preview loading/error
- heatmap/artifact overlays
- local selection
- current Studio overlay
- active mode/panel back to analysis
- orientation transform

It does not reset:

- Premium state
- authorization
- access code
- current user
- job history
- account settings

## Replace Model Flow

The viewer toolbar now exposes `Загрузить другую модель`.

It opens the existing hidden STL file input through `requestStudioFile()` and works for both demo and user files. No second upload flow or backend endpoint was added.

## Operation Accordion

`StudioSidebar` now uses controlled accordion state:

- active operation group opens automatically;
- opening a group does not call API;
- opening a group does not change the selected operation;
- selected operation remains visible;
- groups expose `aria-expanded`.

Groups:

1. Анализ
2. Ремонт
3. Оптимизация
4. Подготовка к печати
5. Разделение
6. Экспорт

Disabled unfinished split modes keep the `comingSoon` state and the existing `Скоро` badge styling.

## Viewer Toolbar

Replaced the legacy `.viewerToolbarHint` React markup with real toolbar buttons:

- Центрировать
- Повернуть по X
- Повернуть по Y
- Повернуть по Z
- Сбросить вид
- Очистить
- Загрузить другую модель
- Сделать снимок

Each button uses a visible SVG icon from `LaunchIcon`. On desktop the button stays compact and expands left on hover/focus. On mobile/touch the labels are visible without hover.

## Axis Gizmo

The axis gizmo is constrained inside the viewer, in the right-bottom safe area, above the toolbar. The E2E matrix checks that the gizmo remains inside viewer bounds on all required viewport sizes.

## Scroll Model

The shell now uses document-level vertical scrolling when needed. Internal scroll remains only where it is useful:

- operation sidebar;
- context/history panels.

The workflow panel is not clipped by the shell and remains accessible in low-height desktop and mobile viewports.

## Browser E2E

Saved in:

- `docs/stage-08-1-r-studio-correction/browser-e2e-results.json`
- `docs/stage-08-1-r-studio-correction/screenshots/`

Scenarios covered:

- empty `/app` state;
- demo open;
- demo clear;
- upload custom STL after clear;
- replace custom STL;
- operation accordion;
- disabled `Скоро` modes;
- toolbar hover and keyboard focus;
- mobile toolbar;
- axis gizmo bounds;
- viewport matrix;
- zoom matrix;
- no console errors;
- no failed requests.

Screenshots saved:

- `studio-empty-1440x800.png`
- `studio-demo-1440x800.png`
- `studio-demo-cleared.png`
- `studio-custom-upload.png`
- `studio-operation-groups-closed.png`
- `studio-operation-group-open.png`
- `studio-toolbar-compact.png`
- `studio-toolbar-expanded.png`
- `studio-toolbar-keyboard.png`
- `studio-axis-gizmo.png`
- `studio-process-bottom-visible-1366x768.png`
- `studio-scroll-bottom.png`
- `studio-mobile-empty.png`
- `studio-mobile-demo.png`
- `studio-mobile-toolbar.png`

## Viewport And Zoom Matrix

Viewport checks passed:

- 1920x1080
- 1680x1050
- 1536x864
- 1440x900
- 1440x800
- 1366x768
- 1280x720
- 1024x768
- 768x1024
- 430x932
- 390x844
- 375x812
- 360x800
- 320x568

Zoom checks passed:

- 67%
- 80%
- 90%
- 100%
- 110%
- 125%

## Validation

- `npm run build`: PASS.
- `./tests/smoke_studio_workspace_correction.sh`: PASS.
- `./tests/run_all_smoke_tests.sh`: PASS.
- Browser E2E: PASS.
- Protected checksums: PASS.

Build warnings:

- VKUI package `use client` directives are ignored by Vite.
- Large chunk warning remains unchanged.

## Remaining Backlog

- Polish visual density of the Studio header at very narrow mobile widths.
- Consider code-splitting VKUI/admin/landing later to reduce bundle size.
- Old `.viewerToolbarHint` CSS remains as inert legacy CSS; it can be removed in a dedicated CSS cleanup stage, not in this corrective UI stage.

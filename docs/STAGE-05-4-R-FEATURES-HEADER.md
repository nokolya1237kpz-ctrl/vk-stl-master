# Stage 05.4-R — Features + Header Stability

## Scope

Stage 05.4-R restores only two public landing areas:

- sticky public Header geometry;
- section 05 Features visual completion.

No React, JSX, backend, worker, Studio, Admin, API, routing, auth, upload, Premium, Viewer, History, Compare, Connections, FAQ, or Footer logic was changed.

## Files Changed

- `frontend/src/landing/landing.css`

## CSS Selectors Added

- `.publicSite`
- `.publicLanding.publicSite > .publicTopNav.topNavV8`
- `.publicLanding.publicSite > .publicTopNav.topNavV8.compact`
- `.publicSite .publicTopNav.topNavV8`
- `.publicSite .publicTopNav.topNavV8.compact`
- `.publicSite .publicTopPanel`
- `.publicSite .publicTopLinks.topLinksV8`
- `.publicSite .publicTopLinks.topLinksV8 a`
- `.publicSite .publicTopActions.topActionsV8`
- `.publicSite .appOpenButtonV9`
- `.publicSite .premiumStatusWrap`
- `.publicSite .premiumHeaderButtonV9`
- `.publicSite .premiumStatusControl`
- `.publicSite .mobileSupportButton`
- `.publicSite .featuresToolSection`
- `.publicSite .featuresToolSection .launchSectionHeader`
- `.publicSite .featuresToolSection .sectionKicker`
- `.publicSite .featuresToolSection .workflowBridge`
- `.publicSite .featuresToolShell`
- `.publicSite .featuresToolNav`
- `.publicSite .featuresToolNav button`
- `.publicSite .featuresToolStage`
- `.publicSite .featuresToolStage .workflowStlViewer`
- `.publicSite .featuresToolInfoPanel`
- `.publicSite .featuresToolStage .workflowToggleRail`
- `.publicSite .featuresToolStage .workflowFilePanel`

## Header Fix

The header jump came from competing legacy rules where the non-compact and compact header states could resolve different horizontal geometry and transform behavior. The final Stage 05.4-R CSS layer makes both states use the same width, margin, grid columns, padding, and `transform: none`.

Header after-metrics from browser runtime:

| Viewport | Header X | Header Width | Max X Delta | Max Width Delta | Page Overflow |
| --- | ---: | ---: | ---: | ---: | --- |
| 1920 | 152.5 | 1600 | 0 | 0 | no |
| 1536 | 48 | 1425 | 0 | 0 | no |
| 1440 | 48 | 1329 | 0 | 0 | no |
| 1366 | 48 | 1255 | 0 | 0 | no |
| 1280 | 28 | 1209 | 0 | 0 | no |
| 1024 | 6.5 | 996 | 0 | 0 | no |
| 768 | 6.5 | 740 | 0 | 0 | no |
| 390 | 6.5 | 362 | 0 | 0 | no |
| 360 | 6.5 | 332 | 0 | 0 | no |

Measured scroll positions: `0`, `100`, `500`, `1200`.

## Features Fix

The existing Features React structure already contains the required 8 tools and interactive detail panel. Stage 05.4-R keeps the same content and handlers, while improving the visual system:

- keeps the desktop tool selector as a 4x2 grid;
- makes the detail stage a wider preview plus a right information panel;
- tightens card rhythm and status badges;
- improves desktop/tablet/mobile spacing;
- keeps mobile as a single readable column;
- prevents page-level horizontal overflow.

The internal Three.js canvas still reports a larger element `scrollWidth` inside the viewer, but the section and shell clip it and the page itself has no horizontal overflow. Viewer logic was not changed.

## Screenshots

Screenshots are stored in:

- `docs/stage-05-4-r-features-header/before/`
- `docs/stage-05-4-r-features-header/after/`

Key files:

- `after/header-scrolled-1440.png`
- `after/features-full-1440.png`
- `after/features-mobile-390.png`

## Validation

- `npm run build`: PASS.
- Browser runtime screenshots: captured before and after.
- Header links visible in measured desktop layout: `Возможности`, `Соединения`, `До / После`, `Тарифы`, `FAQ`.
- Horizontal overflow: not detected on tested viewports.
- Protected areas were not edited.

## Notes

Build still emits existing Vite warnings from VKUI package-level `"use client"` directives and a large chunk warning. These warnings existed outside this visual patch and were not addressed in this stage.

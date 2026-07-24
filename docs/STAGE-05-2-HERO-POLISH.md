# Stage 05.2-R — Header And Hero Visual Recovery

## Source State

- Source commit before recovery: `0463a8693ee3e2cf8fd8c0dddaa92d8ede545c92`.
- Scope: Landing Header and Hero only.
- Deployment: not performed.
- Runtime logic source: current project state.
- Visual recovery target: stable Header/Hero behavior without changing routes, handlers, API, Studio, Admin, Premium flow, upload flow, or section order.

## Pre-Change Safety

- `/home/codex/projects/vk-stl-master` was confirmed to be a non-git working copy.
- Git clone used for commit preparation: `/tmp/vk-stl-master-stage5-git`.
- The previous uncommitted landing diff was saved to `/tmp/stage-05-2-uncommitted-landing.patch`.
- The pre-recovery landing CSS backup was saved to `/tmp/landing.css.before-stage-05-2-recovery`.

## Changed Files

- `frontend/src/landing/landing.css`
- `docs/STAGE-05-2-HERO-POLISH.md`
- `docs/stage-05-2-hero-polish/results.json`
- `docs/stage-05-2-hero-polish/regression.json`
- `docs/stage-05-2-hero-polish/*.png`

No JSX files were changed.

No backend, worker, API, Studio, Admin, Viewer, History, Compare, Premium logic, Upload logic, authorization, route, dependency, Docker, nginx, asset, or SVG files were changed.

## CSS Selectors Changed

Only a new scoped Stage 5.2-R CSS recovery layer was added/updated at the end of `frontend/src/landing/landing.css`.

Key selectors:

- `.publicSite .topNavV8`
- `.publicSite .topNavV8.compact`
- `.publicTopNav.topNavV8`
- `.publicTopBrand.topBrandV8`
- `.publicSite .publicTopPanel`
- `.publicSite .publicTopPanel.open`
- `.publicSite .topLinksV8`
- `.publicTopLinks.topLinksV8`
- `.publicSite .topActionsV8`
- `.publicTopActions.topActionsV8`
- `.publicSite .appOpenButtonV9`
- `.publicSite .premiumHeaderButtonV9`
- `.publicSite .mobileSupportButton`
- `.publicSite .heroActionsV8`
- `.publicSite .heroActionsV8 .primaryCta`
- `.publicSite .heroActionsV8 .secondaryCta`
- `.publicSite .heroBenefitsV8`
- `.publicSite .heroBenefitsV8 .stlm-ui-hero-card`
- `.publicSite .heroMetricsV8`
- `.publicSite .browserNoteV8`

## What Was Fixed

- Desktop Header keeps a single row from `1280px` upward.
- Desktop Header no longer clips or pushes out the VK support button.
- Desktop Header action buttons have fixed safe widths:
  - Open application: `164x44` on wide desktop, `150x44` at `1241-1320px`.
  - Premium: `178x44` on wide desktop, `164x44` at `1241-1320px`.
  - VK support: `44x44`.
- Compact Header starts at `1240px` and below.
- Compact menu panel is part of the Header flow, not an absolutely positioned block.
- Compact menu action buttons switch to one column at `640px` and below.
- Hero CTA buttons are equal height and keep text inside.
- Hero benefit cards have equal height and no text overflow.
- Hero benefit icon slots are unified at `38x38`.
- Hero metrics and browser safety card icon slots were normalized.

## UI Kit Usage

Stage 5.1 UI Kit usage remains unchanged:

- `UiBadge` for the Hero eyebrow.
- `UiHeroCard` for Hero benefit cards.
- `UiButton` for Hero CTA controls.
- `UiPanel` for the browser safety note.
- `UiStatCard` for Hero metrics.

Stage 5.2-R did not connect new UI Kit components and did not change React imports.

## Unchanged Behavior

- Header labels and links were not changed.
- Hero texts were not changed.
- CTA texts were not changed.
- CTA click handlers were not changed.
- VK support link was not changed.
- Premium flow logic was not changed.
- Application open action was not changed.
- Mobile menu state logic was not changed.
- Landing section order was not changed.
- Studio mockup DOM and visual content were not changed.

## Computed Measurements

Automated Playwright checks were run against the freshly built frontend preview at `http://127.0.0.1:4175/`.

| Viewport | Mode | Header | Actions | VK | CTA Buttons | Benefit Cards |
| --- | --- | --- | --- | --- | --- | --- |
| `1920x1080` | desktop | `x=267 y=44 w=1386 h=70` | `w=406 h=44` | `44x44` inside | `228.8x62`, `207.2x62` | `142.7x88` each |
| `1440x900` | desktop | `x=48 y=44 w=1344 h=70` | `w=406 h=44` | `44x44` inside | `228.8x62`, `207.2x62` | `142.7x88` each |
| `1280x800` | desktop | `x=48 y=44 w=1184 h=70` | `w=378 h=44` | `44x44` inside | `228.8x62`, `207.2x62` | `142.7x88` each |
| `1180x820` | compact open | `x=14 y=16 w=1152 h=274` | `w=1110 h=98` | `1110x44` inside | `232x62`, `210x62` | `376x88` each |
| `390x844` | compact open | `x=14 y=16 w=362 h=374` | `w=332 h=152` | `332x44` inside | `362x62`, `362x62` | `362x74` each |
| `320x568` | compact open | `x=14 y=16 w=292 h=374` | `w=262 h=152` | `262x44` inside | `311.3x62`, `311.3x62` | `311.3x74` each |

Full viewport sweep:

- `1920x1080`
- `1680x1050`
- `1440x900`
- `1366x768`
- `1280x800`
- `1180x820`
- `1100x800`
- `1024x768`
- `900x900`
- `768x1024`
- `430x932`
- `390x844`
- `375x812`
- `360x800`
- `320x568`

All viewport checks passed:

- No horizontal overflow.
- No missing visible nav labels in desktop or opened compact mode.
- No nav text overflow.
- Header does not overflow viewport.
- Header panel/actions/VK are inside Header.
- Brand/nav/actions do not intersect.
- Hero CTA buttons have equal height.
- Hero CTA text does not overflow.
- Hero benefit cards have equal height.
- Hero benefit text does not overflow.
- No browser console errors.
- No failed requests.

## Screenshots

Full viewport screenshots:

- `docs/stage-05-2-hero-polish/hero-1920x1080.png`
- `docs/stage-05-2-hero-polish/hero-1680x1050.png`
- `docs/stage-05-2-hero-polish/hero-1440x900.png`
- `docs/stage-05-2-hero-polish/hero-1366x768.png`
- `docs/stage-05-2-hero-polish/hero-1280x800.png`
- `docs/stage-05-2-hero-polish/hero-1180x820.png`
- `docs/stage-05-2-hero-polish/hero-1100x800.png`
- `docs/stage-05-2-hero-polish/hero-1024x768.png`
- `docs/stage-05-2-hero-polish/hero-900x900.png`
- `docs/stage-05-2-hero-polish/hero-768x1024.png`
- `docs/stage-05-2-hero-polish/hero-430x932.png`
- `docs/stage-05-2-hero-polish/hero-390x844.png`
- `docs/stage-05-2-hero-polish/hero-375x812.png`
- `docs/stage-05-2-hero-polish/hero-360x800.png`
- `docs/stage-05-2-hero-polish/hero-320x568.png`

Opened compact menu screenshots:

- `docs/stage-05-2-hero-polish/hero-1180x820-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-1100x800-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-1024x768-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-900x900-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-768x1024-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-430x932-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-390x844-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-375x812-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-360x800-menu-open.png`
- `docs/stage-05-2-hero-polish/hero-320x568-menu-open.png`

Close-up screenshots:

- `docs/stage-05-2-hero-polish/header-desktop-1920.png`
- `docs/stage-05-2-hero-polish/header-desktop-1440.png`
- `docs/stage-05-2-hero-polish/header-desktop-1366.png`
- `docs/stage-05-2-hero-polish/header-desktop-1280.png`
- `docs/stage-05-2-hero-polish/header-compact-1180.png`
- `docs/stage-05-2-hero-polish/hero-full-1440.png`
- `docs/stage-05-2-hero-polish/hero-cta-closeup-1440.png`
- `docs/stage-05-2-hero-polish/advantages-closeup-1440.png`
- `docs/stage-05-2-hero-polish/metrics-closeup-1440.png`
- `docs/stage-05-2-hero-polish/browser-panel-closeup-1440.png`
- `docs/stage-05-2-hero-polish/mobile-header-430.png`
- `docs/stage-05-2-hero-polish/mobile-header-390.png`
- `docs/stage-05-2-hero-polish/mobile-hero-390.png`
- `docs/stage-05-2-hero-polish/mobile-cta-390.png`
- `docs/stage-05-2-hero-polish/mobile-advantages-390.png`
- `docs/stage-05-2-hero-polish/mobile-hero-360.png`
- `docs/stage-05-2-hero-polish/mobile-hero-320.png`

Manual visual checks were performed on:

- `hero-1440x900.png`
- `hero-1280x800.png`
- `hero-1180x820-menu-open.png`
- `hero-390x844-menu-open.png`

## Regression Checks

Routes checked on freshly built frontend preview:

- `/`
- `/app`
- `/admin`

Result:

- HTTP status: `200` for all three routes.
- No console errors.
- No page errors.
- No failed requests.
- No horizontal overflow.

Interaction checks:

- Mobile menu opens and exposes all nav links.
- Nav links preserved:
  - `#features`
  - `#connectors`
  - `#compare`
  - `#premium`
  - `#faq`
- Primary Hero CTA still navigates to `/app`.
- VK support button opens `https://vk.ru/3dmodeliron`.

API check:

- `GET http://127.0.0.1:8000/api/v1/me` returned `200`.
- Vite preview `/api/v1/me` returns SPA HTML by design because preview has no API proxy.

Protected checksum verification:

- `backend/` unchanged.
- `worker/` unchanged.
- `frontend/src/studio/` unchanged.
- `frontend/src/admin/` unchanged.

## Build

Command:

```bash
cd /home/codex/projects/vk-stl-master/frontend
npm run build
```

Result: PASS.

The existing VKUI `"use client"` bundle warnings remained, and the build completed successfully.

## Deployment

No deployment was performed in this stage.

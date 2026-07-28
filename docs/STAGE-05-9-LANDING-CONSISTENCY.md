# Stage 05.9 - Landing Design Consistency Pass

## Scope

This stage is a visual consistency pass for the public landing page only. No application logic, API calls, routes, Studio, Admin, Premium flow, upload flow, Viewer or History behavior was changed.

Source SHA before the stage: `233cde5dfb3d1d773ccb64345dc2737d6ee774cd`.

## What Was Changed

Changed file:

- `frontend/src/landing/landing.css`

Created verification artifacts:

- `docs/stage-05-9-landing-consistency/before/`
- `docs/stage-05-9-landing-consistency/after/`
- `docs/stage-05-9-landing-consistency/results-before.json`
- `docs/stage-05-9-landing-consistency/results.json`
- `docs/STAGE-05-9-LANDING-CONSISTENCY.md`

No JSX files were changed.

## Before Findings

The landing had mixed visual layers from previous partial rebuilds:

- Header, Workflow and Connections used different effective content widths.
- Section spacing varied between blocks.
- Buttons had inconsistent minimum sizes and several overflow risks.
- Connections images were rendered with `object-fit: cover` and were visually clipped.
- Card radii and panel surfaces varied section by section.
- Workflow switched into a visually weaker layout on wide screens.

## Consistency Tokens Added In CSS

The pass added landing-scoped CSS custom properties under `.publicLanding.publicSite`:

- container max-width: `1408px`
- desktop gutter: `clamp(12px, 4.45vw, 64px)`
- desktop section spacing: `clamp(84px, 6.8vw, 116px)`
- tablet section spacing: `clamp(72px, 8vw, 96px)`
- mobile section spacing: `clamp(58px, 15vw, 76px)`
- control radius: `14px`
- card radius: `22px`
- panel radius: `26px`
- shared card border: `rgba(128, 163, 205, .24)`

These tokens are landing-only CSS overrides and are not imported by Studio/Admin.

## Layout Results

Measured after pass:

| Viewport | Workflow width | Connections width | Horizontal overflow |
|---:|---:|---:|---|
| 1920 | 1408 | 1408 | no |
| 1536 | 1408 | 1408 | no |
| 1440 | 1312 | 1312 | no |
| 1366 | 1244.42 | 1244.42 | no |
| 1280 | 1166.08 | 1166.08 | no |
| 1024 | 960 | 960 | no |
| 768 | 718.84 | 718.84 | no |
| 390 | 366 | 366 | no |
| 360 | 336 | 336 | no |
| 320 | 296 | 296 | no |

## Header Stability

At viewport `1440px`:

| Scroll Y | x | top | width | height |
|---:|---:|---:|---:|---:|
| 0 | 64 | 24 | 1312 | 72 |
| 100 | 64 | 20 | 1312 | 72 |
| 500 | 64 | 20 | 1312 | 72 |
| 1000 | 64 | 20 | 1312 | 72 |
| 2000 | 64 | 20 | 1312 | 72 |

The sticky header remains stable and aligned with the same page grid as the landing sections.

## Buttons

All landing buttons now share the same base model:

- `inline-flex`
- explicit minimum heights
- consistent icon spacing
- consistent focus-visible style
- consistent hover movement
- no detected text/icon overflow

Machine check result: `0` overflowing buttons.

The previous overflow at effective 125% zoom for `Смотреть возможности` was fixed by increasing Hero CTA height and giving button contents `min-width: 0`.

## Cards And Panels

Landing cards and panels were normalized visually without changing DOM structure:

- Workflow cards: `22px` radius, shared border and shared surface.
- Connections cards: `22px` radius, shared border and shared surface.
- Compare panels: normalized with the same card/panel radius scale.
- Feature panels: normalized with the same surface language.
- Premium panels and FAQ items: normalized to the same design family.

## Workflow

Workflow is now aligned to the same content grid as Header, Hero and Connections.

Desktop layout uses a stable 3-column grid so the six steps remain readable and do not collapse into narrow cards on wide screens.

## Connections Images

Connections image rendering changed from clipped cover behavior to contained rendering:

- `object-fit: contain`
- `object-position: center center`
- `transform: none`
- image frame keeps `overflow: hidden`
- image wrapper uses the same dark CAD-like surface

Measured after pass for all six connection renders:

- loaded: yes
- natural image dimensions detected
- object fit: `contain`
- likely clipped: `false`

## Features Controls

The Features block keeps the existing structure and text. The pass only regularized native-looking controls into the landing visual system. No native unstyled controls were left visible in verification screenshots.

## Zoom And Responsive Checks

Effective browser zoom checks:

| Zoom | Effective width | Horizontal overflow | Overflowing buttons |
|---:|---:|---|---|
| 67% | 2149 | no | none |
| 80% | 1800 | no | none |
| 100% | 1440 | no | none |
| 110% | 1309 | no | none |
| 125% | 1152 | no | none |

Extra responsive widths:

| Width | Horizontal overflow | Overflowing buttons |
|---:|---|---:|
| 2560 | no | 0 |
| 1680 | no | 0 |
| 1180 | no | 0 |

## Regression Checks

Preview routes checked with Playwright:

| Route | Horizontal overflow | Console errors | Failed requests |
|---|---|---:|---:|
| `/` | no | 0 | 0 |
| `/app` | no | 0 | 0 |
| `/admin` | no | 0 | 0 |

`GET /api/v1/me`: `200`.

## Screenshots

Before and after screenshots were saved for:

- full landing at `1920`, `1536`, `1440`, `1366`, `1280`, `1024`, `768`, `390`, `360`, `320`
- Workflow at `1920`, `1440`, `1280`
- Connections at `1920`, `1440`, `1280`
- Features controls at `1440`
- Header after scroll
- Effective zoom `67`, `80`, `100`, `110`, `125`

The after screenshots were warmed by scrolling through the page before capture so below-fold images are decoded and visible.

## Build

`npm run build` passed in `/home/codex/projects/vk-stl-master/frontend`.

Only existing Vite warnings from VKUI `use client` directives and chunk size were observed.

## Logic Safety

The following areas were not changed:

- backend
- worker
- API
- Studio source
- Admin source
- routes
- auth
- Premium logic
- upload logic
- Viewer
- History
- package files
- Docker/nginx/systemd configuration

## Backlog

Remaining small polishing items should be handled later in a separate stage:

- final manual visual review in a real browser on macOS Safari/Chrome
- final landing copy/spacing polish after all sections are complete
- optional screenshot script refinement for future lazy-rendered full-page captures

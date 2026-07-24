# Stage 05.1 - Hero UI Kit Migration

## Scope

Migrated only the public Landing Hero implementation to use the isolated STL Master UI Kit.

No backend, worker, API, routing, Studio, Admin, Viewer, History, Compare, upload logic, authorization, or Premium business logic was changed.

## Files Changed

- `frontend/src/main.jsx`
  - Added UI Kit imports.
  - Replaced Hero-only primitives with UI Kit components.
  - Preserved existing Hero text, CTA labels, links, and event handlers.
- `frontend/src/landing/landing.css`
  - Added a Hero-only compatibility layer for UI Kit classes.
  - Fixed mobile Hero centering and text wrapping inside the Hero section only.
- `docs/STAGE-05-1-HERO.md`
  - Added this report.
- `docs/stage-05-1-hero/`
  - Added Hero screenshots and Playwright result JSON for required viewport checks.

## UI Kit Components Used

- `Badge`
  - Used for the Hero eyebrow label.
- `Button`
  - Used for both Hero CTA buttons.
- `HeroCard`
  - Used for the three benefit cards.
- `StatCard`
  - Used for the five Hero metric cards.
- `Panel`
  - Used for the browser safety note card.

## Preserved Behavior

- The primary CTA still calls `onOpenApplication`.
- The secondary CTA still calls `openFeatures`, which scrolls to `#features`.
- Hero section keeps `id="hero"`.
- Existing Hero text and CTA wording were preserved.
- Existing `StudioMockup` remains unchanged.
- Existing section order remains unchanged.
- No API calls were added or changed.
- No route logic was changed.

## Visual Notes

- Hero controls now use the shared UI Kit component layer.
- Hero benefit and metric cards keep their existing public class names for compatibility with the current visual system.
- Mobile Hero was corrected to avoid legacy desktop offset and clipped text.
- CSS changes are scoped under Hero selectors.

## Validation

Build:

```text
npm run build - PASS
```

Known build warnings:

- Existing Vite/VKUI `use client` warnings.
- Existing large chunk warning.

Viewport screenshots:

- `docs/stage-05-1-hero/hero-1920.png`
- `docs/stage-05-1-hero/hero-1440.png`
- `docs/stage-05-1-hero/hero-1024.png`
- `docs/stage-05-1-hero/hero-768.png`
- `docs/stage-05-1-hero/hero-390.png`
- `docs/stage-05-1-hero/hero-360.png`
- `docs/stage-05-1-hero/results.json`

Automated viewport checks:

- 1920: no console errors, no horizontal overflow.
- 1440: no console errors, no horizontal overflow.
- 1024: no console errors, no horizontal overflow.
- 768: no console errors, no horizontal overflow.
- 390: no console errors, no horizontal overflow.
- 360: no console errors, no horizontal overflow.

## Business Logic

Business logic was not changed.

This migration only changes the Hero rendering primitives and Hero-scoped CSS compatibility rules.

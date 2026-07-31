# Stage 07.2.5 — Studio UX Audit & Layout Redesign

## Scope

Route: `/app`.

Changed only Studio UX/layout:

- `frontend/src/main.jsx`
- `frontend/src/studio/StudioComponents.jsx`
- `frontend/src/studio/studio.css`

Not changed:

- backend
- worker
- API
- Redis
- upload logic
- viewer logic
- bounding calculations
- history logic
- compare logic
- premium logic
- polling
- job processing
- auth
- landing
- admin functionality

## UX Audit

### First screen before redesign

The first screen showed the Viewer, but it competed with three heavy areas:

- wide left operation sidebar with long descriptions;
- long right inspector with user, settings, result, history, feedback and print checks;
- bottom workflow/action bar outside the working grid.

On desktop the Viewer was large enough, but actions were visually detached from it. On tablet and mobile the workflow bar moved below the whole workspace or close to the long inspector, which made the main scenario feel slower.

### Eye focus

Primary attention should be the 3D Viewer and model state. Before redesign, the right inspector and left sidebar had almost equal visual weight. On mobile, the eye moved through Viewer, sidebar, then a very long inspector before context was fully clear.

### Distractions

- Tool descriptions repeated details already present in the inspector.
- The right inspector mixed setup, result, job details, feedback and history at the same visual level.
- Viewer toolbar could be visually disconnected from the viewport.
- Some nested result controls inherited old/default button styles on narrow screens.

### Hidden or distant actions

The most important action after selecting a mode is "Запустить обработку". It was outside the central workspace. On mobile, this was especially painful because the user had to pass large supporting panels.

### Overload

The inspector contained valid data, but it had no strong compact hierarchy. Analysis details and history could become long. This is acceptable for expert review, but it should not block the upload-to-result flow.

## User Flow

Expected flow:

1. Open `/app`.
2. Choose or drop STL file, or open demo.
3. See model in Viewer.
4. Choose operation.
5. Adjust operation options.
6. Run processing.
7. Track status.
8. Download result.
9. Review analysis/history if needed.

Problems before redesign:

- Operation selection and run action were not perceived as one command flow.
- On tablet/mobile the run action was not close enough to the Viewer.
- Inspector content attracted too much attention before the user needed it.

Flow after redesign:

- Viewer remains the visual center.
- Tools are a compact command rail.
- Workflow/run deck is placed directly under Viewer.
- Inspector stays on the right as a supporting task panel.
- On mobile the order is Viewer, tools, run deck, inspector.

## Heatmap

Primary:

- 3D Viewer canvas
- Viewer status
- Toolbar inside Viewer
- "Запустить обработку"
- "Скачать результат" when available

Secondary:

- Operation command rail
- Operation settings
- Processing progress

Supporting:

- User limits
- Job details
- Analysis details
- Feedback

Low priority:

- Long history cards
- Extended technical details
- Raw generated file lists

## Layout Variants

### Variant A — Classic Three Columns

Structure:

- left full sidebar
- center Viewer
- right inspector
- bottom workflow outside grid

Pros:

- minimal code movement;
- familiar desktop layout.

Cons:

- keeps the old mobile problem;
- run action remains too far from Viewer;
- left sidebar stays visually heavy.

UX load: medium-high.

### Variant B — Command Rail + Center Viewer + Right Task Panel

Structure:

- compact left command rail;
- large central Viewer;
- workflow/run deck directly under Viewer;
- right inspector as supporting task panel.

Pros:

- Viewer becomes primary;
- main action is near the model;
- works better on laptop and tablet;
- does not change business logic;
- can be implemented mostly through layout/CSS.

Cons:

- operation descriptions are less visible in the sidebar;
- right inspector still needs future content-level polishing.

UX load: medium-low.

### Variant C — Viewer First, Inspector Below

Structure:

- full-width Viewer;
- horizontal operation bar;
- inspector and history below.

Pros:

- strongest focus on Viewer;
- mobile-friendly.

Cons:

- too disruptive for desktop;
- hides settings below the fold;
- requires more JSX restructuring.

UX load: low for viewing, medium for editing.

## Selected Variant

Selected: Variant B.

Reason:

It improves the real workflow while preserving the current application structure and logic. The Viewer stays central, settings remain visible, and the run action is close to the 3D context. It also solves the tablet/mobile ordering issue without touching upload, processing, Viewer, history, compare or premium logic.

## Implemented Changes

### Layout

- Moved `StudioWorkflowBar` inside `.studioWorkspace` under the Viewer.
- Changed Studio shell to a two-row layout: header + workspace.
- Changed workspace to a two-row grid:
  - left command rail spans Viewer and workflow rows;
  - Viewer is central and dominant;
  - inspector spans the right side;
  - workflow/run deck sits below Viewer.

### Sidebar

- Converted the operation sidebar into a compact command rail.
- Reduced text density and hidden secondary descriptions in the rail.
- Preserved all operation buttons and handlers.
- Added `aria-pressed` to selected operation buttons.

### Viewer Toolbar

- Kept the existing Viewer and Three.js logic unchanged.
- Positioned Viewer actions as a compact HUD inside the Viewer.
- Allowed the toolbar to wrap cleanly instead of showing unreadable clipped text.

### Inspector

- Reduced card padding and heading sizes.
- Styled nested result blocks, buttons, summaries and details inside `.studioInspector`.
- Added overflow-safe wrapping for long STL names, job IDs and technical values.
- Kept history, compare, feedback and analysis logic unchanged.

### Workflow

- Kept the same steps and run/download controls.
- Made the workflow bar compact and adjacent to Viewer.
- Added `aria-current="step"` for the active step.

### Responsive

- Desktop: 108px command rail, central Viewer, 360px inspector.
- Tablet: left compact rail, Viewer first, workflow directly below Viewer, inspector below.
- Mobile: Viewer first, horizontal tool strip, workflow/run deck, inspector.

## Screenshots

Before:

- `docs/stage-07-2.5-ux-redesign/before/app-empty-desktop-before.png`
- `docs/stage-07-2.5-ux-redesign/before/app-demo-desktop-before.png`
- `docs/stage-07-2.5-ux-redesign/before/app-demo-tablet-before.png`
- `docs/stage-07-2.5-ux-redesign/before/app-demo-mobile-before.png`

After:

- `docs/stage-07-2.5-ux-redesign/after/app-empty-desktop-after.png`
- `docs/stage-07-2.5-ux-redesign/after/app-demo-desktop-after.png`
- `docs/stage-07-2.5-ux-redesign/after/app-demo-tablet-after.png`
- `docs/stage-07-2.5-ux-redesign/after/app-demo-mobile-after.png`

## Verification Metrics

After visual check:

- desktop 1440: horizontal scroll false, console errors 0, request failures 0;
- tablet 1024: horizontal scroll false;
- mobile 390: horizontal scroll false.

Key final measurements:

- desktop Viewer: 916 x 768;
- desktop workflow/run deck: 916 x 104, directly under Viewer;
- desktop inspector: 360 x 886;
- tablet Viewer: 902 x 520;
- tablet workflow/run deck: y 634, directly after Viewer;
- mobile Viewer: y 253.89, height 520;
- mobile workflow/run deck: y 931.89, before inspector;
- mobile inspector starts at y 1049.89.

## Accessibility

- Operation buttons expose selected state through `aria-pressed`.
- Current processing step exposes `aria-current="step"`.
- Focus-visible outlines were restored for Studio controls.
- Important layout changes preserve source order for keyboard navigation: header, viewer/tools/workflow, inspector.

## Residual Backlog

- The completed analysis payload is still long on tablet/mobile because it contains many valid technical sections. It should be reviewed in a future content-polishing pass.
- Several operation icons are still emoji/text-based from the existing project. Replacing them with a project icon set should be a future visual-system stage.
- Header on narrow mobile remains tall because it keeps all current controls visible.
- Compare controls inside the inspector are styled safely, but the deeper compare UX should remain a separate stage.

## Build

`npm run build`: PASS.

Vite warnings about VKUI `"use client"` directives and large chunks are existing bundler warnings, not new build failures.

# Stage 7.1 — Studio Shell And Responsive Layout

## 1. Source SHA

- Starting SHA: `5f65ad610804a1df3d279a78d92581002854fa3b`
- Stage 7.0 baseline report: `docs/STAGE-07-0-STUDIO-BASELINE.md`
- Stage 7.0 artifacts: `docs/stage-07-0-studio-baseline/`
- Backup used as safety baseline: `/home/codex/backups/stage-07-0-studio-baseline-20260730-141305.tar.gz`
- Backup SHA-256: `eda26061959d6dacc6dd54e545666c33f1237691e810493089915127362c72c9`

## 2. Baseline Defect

- Stage 7.0 High defect: `STUDIO-VIS-001`.
- Baseline symptom: mobile `320` and `360` CSS px could produce `document.documentElement.scrollWidth = 365px`.
- Baseline suspected cause: mobile header/actions/sidebar minimum widths leaking outside the Studio shell.

## 3. Exact Cause Found In Stage 7.1

The current pre-fix production re-check already reported document-level `scrollWidth == innerWidth`, but it still exposed a real shell geometry leak at `320px`: a mobile tools rail item `.studioToolButton` rendered at `right = 323px` while the viewport was `320px`. This came from the `max-width: 760px` rule that converted `.studioToolList` into a single flex row with fixed `54px` tool buttons and horizontal rail behavior.

The hardening therefore fixed the actual layout source instead of hiding overflow on `body`: the mobile sidebar/tools area now wraps into a bounded grid, and header/action flex/grid children explicitly receive `min-width: 0` and `max-width: 100%`.

## 4. Elements That Created Or Could Create Overflow

- `.studioToolList` mobile one-row flex rail.
- `.studioToolButton` fixed `54px` mobile basis.
- `.studioHeaderActions` two-column mobile grid without bounded children.
- `.studioBrand`, `.studioProjectStatus` and nested text without explicit ellipsis/min-width containment.

## 5. Changed Files

- `frontend/src/studio/studio.css`
- `frontend/src/main.jsx`
- `docs/STAGE-07-1-STUDIO-SHELL.md`
- `docs/stage-07-1-studio-shell/results.json`
- `docs/stage-07-1-studio-shell/validation-summary.txt`
- `docs/stage-07-1-studio-shell/http-status-preview.txt`
- `docs/stage-07-1-studio-shell/after/*.png`

No backend, worker, Landing, Admin, API, route, upload, polling, download, Premium, viewer camera, OrbitControls, STLLoader or business logic files were changed.

## 6. Studio Shell Architecture

The existing architecture remains intact:

```text
studioShell
  studioHeader
  studioWorkspace
    studioSidebar
    studioViewerWorkspace
    studioInspector
  studioWorkflowBar
  studioFileInput
```

No component extraction or routing rewrite was done.

## 7. Desktop Layout

Desktop remains the existing three-column shell: tools panel, viewer, inspector. The Stage 7.1 changes are scoped to `max-width: 760px`, so desktop geometry is intentionally unchanged. Viewport checks passed at 2560, 1920, 1680, 1536, 1440, 1366 and 1280 widths.

## 8. Tablet Layout

Tablet keeps the existing breakpoint behavior from `studio.css`: compact tools rail plus stacked inspector below the viewer. Viewport checks passed at 1180, 1024, 900 and 768 widths.

## 9. Mobile Layout

Mobile remains a single-column Studio shell:

1. Compact Studio header.
2. Viewer or empty upload state.
3. Tool selector area.
4. Inspector/properties.
5. Workflow bar.

The key change is that the tools area is no longer a fixed-width horizontal rail. It becomes a bounded wrapping grid, so all tool buttons remain visible without creating page-level horizontal overflow.

## 10. Header Behavior

Header actions keep the same DOM and handlers. The mobile header now bounds brand, project status and action children with `min-width: 0`/`max-width: 100%`, and long text uses ellipsis instead of expanding the shell.

## 11. Tools Panel Behavior

Desktop/tablet behavior is unchanged. On mobile, `.studioToolList` uses `repeat(auto-fit, minmax(48px, 1fr))`; `.studioToolButton` uses `width: 100%; min-width: 0; flex: initial`. This removes the 320px right-edge leak while keeping every operation button accessible.

## 12. Properties Panel Behavior

No JSX or data changes were made. The inspector remains below the viewer on mobile and retains all existing model/user/settings/job/result/history content.

## 13. Viewer Container

Viewer logic, camera, controls, model transform, STL loading, heatmap/artifact map and screenshot logic were not changed. CSS hardening only ensures shell siblings do not force document-level horizontal overflow.

## 14. Bottom Toolbar / Workflow

`StudioWorkflowBar` logic was not changed. Mobile shell containment rules include `.studioWorkflowBar` so it cannot expand beyond the viewport.

## 15. Empty State

Empty state text, dropzone, supported formats, warning and handlers were not changed. Empty screenshots were captured at desktop, tablet and mobile sizes.

## 16. Loaded State

Loaded/result screenshots use the built-in demo model path, which preserves existing logic and avoids test data persistence. The shell remained within bounds.

## 17. Processing State

Processing logic was not changed. Functional regression was covered by the full smoke suite and existing upload/job tests.

## 18. Result State

Result UI and data mapping were not changed. Demo completed/result screenshots and smoke result contracts passed.

## 19. History Shell

History logic was not changed. Existing history smoke passed, and history screenshots were captured from the demo/result inspector state.

## 20. Compare Shell

Compare logic was not changed. Existing Compare contract smoke passed. Compare-named screenshots capture the completed Studio result shell used for comparison/result controls.

## 21. Modal Behavior

Premium/access/modal logic was not changed. Modal screenshots were captured for desktop and mobile. No document-level horizontal overflow was detected in modal checks.

## 22. Breakpoints

No new random breakpoint set was introduced. Stage 7.1 only strengthens the existing `max-width: 760px` mobile breakpoint.

## 23. CSS Conflicts Removed

No broad CSS cleanup was performed. The conflicting mobile rule was replaced:

- Old winner: `.studioToolList { display: flex; }` and `.studioToolButton { width: 54px; flex: 0 0 54px; }`
- New winner: `.studioToolList { display: grid; grid-template-columns: repeat(auto-fit, minmax(48px, 1fr)); }` and `.studioToolButton { width: 100%; min-width: 0; flex: initial; }`
- Reason: fixed-width flex rail let child buttons extend past the mobile viewport edge.

## 24. Accessibility Fix

Stage 7.0 found one unnamed focusable element. It was `.studioFileInput`. Stage 7.1 added `aria-label="Выбрать STL-файл"`. Re-check on preview found `0` unnamed focusable controls.

## 25. Viewport Results

| Screenshot | Viewport | document scrollWidth | body scrollWidth | offenders |
| --- | --- | --- | --- | --- |
| studio-empty-1920 | 1920x1080 | 1920 | 1920 | 0 |
| studio-loaded-1920 | 1920x1080 | 1920 | 1920 | 0 |
| studio-result-1920 | 1920x1080 | 1920 | 1920 | 0 |
| studio-history-1920 | 1920x1080 | 1920 | 1920 | 0 |
| studio-compare-1920 | 1920x1080 | 1920 | 1920 | 0 |
| studio-empty-1440 | 1440x900 | 1440 | 1440 | 0 |
| studio-loaded-1440 | 1440x900 | 1440 | 1440 | 0 |
| studio-1180 | 1180x820 | 1180 | 1180 | 0 |
| studio-1024 | 1024x768 | 1024 | 1024 | 0 |
| studio-900 | 900x900 | 900 | 900 | 0 |
| studio-768 | 768x1024 | 768 | 768 | 0 |
| studio-empty-430 | 430x932 | 430 | 430 | 0 |
| studio-loaded-430 | 430x932 | 430 | 430 | 0 |
| studio-empty-390 | 390x844 | 390 | 390 | 0 |
| studio-loaded-390 | 390x844 | 390 | 390 | 0 |
| studio-360 | 360x800 | 360 | 360 | 0 |
| studio-320 | 320x568 | 320 | 320 | 0 |

## 26. Zoom Results

| Screenshot | Viewport | document scrollWidth | body scrollWidth | offenders |
| --- | --- | --- | --- | --- |
| studio-1440-zoom-67 | 1440x900 | 1440 | 1440 | 0 |
| studio-1440-zoom-80 | 1440x900 | 1440 | 1440 | 0 |
| studio-1440-zoom-100 | 1440x900 | 1440 | 1440 | 0 |
| studio-1440-zoom-125 | 1440x900 | 1440 | 1440 | 0 |

## 27. Functional Regression

Full regression suite passed. It covered upload/job/download flows, frontend workflow contract, Studio legacy contract, Premium UI, beta UI, admin flows, public launch/design, Compare, processing history, visual result contracts, split/connectors, orientation and fit-to-bed.

## 28. Smoke Tests

- Command: `./tests/run_all_smoke_tests.sh`
- Result: PASS
- Final output: `All smoke tests passed.`

## 29. Performance Regression

- Build passed.
- No new Stage 7.1 warnings were introduced.
- Existing VKUI `use client` warnings and Vite chunk-size warning remain unchanged and are tracked outside this stage.
- Viewer/camera/controls were not remounted or refactored by this change.

## 30. Screenshots

After screenshots: `docs/stage-07-1-studio-shell/after/`

Captured files: 35.

## 31. Checksums

Protected checksum comparison passed for:

- `backend/`
- `worker/`
- `frontend/src/landing/`
- `frontend/src/admin/`

Checksum files:

- `/tmp/stage-07-1-protected-before.sha256`
- `/tmp/stage-07-1-protected-after.sha256`

## 32. Logic Safety Confirmation

No state, fetch, handler, operation key, operation order, route, upload, polling, download, Premium or worker logic was changed. The only JSX change is an `aria-label` on the existing hidden STL file input.

## 33. Results Artifacts

- Browser results JSON: `docs/stage-07-1-studio-shell/results.json`
- Validation summary: `docs/stage-07-1-studio-shell/validation-summary.txt`
- HTTP status preview: `docs/stage-07-1-studio-shell/http-status-preview.txt`

## 34. Residual Backlog For Stage 7.2

- Manual real-browser zoom verification in Safari/Chrome.
- Deeper Studio viewer interaction/camera QA.
- Later cleanup of broader Studio CSS duplicates not directly related to shell overflow.
- Existing bundle-size warning remains for a performance/code-splitting stage.

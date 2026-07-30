# Stage 06.1: Admin Visual Recovery

## Scope

Stage 06.1 restores the visual system of the existing STL Master admin panel without changing backend, worker, API, storage, cleanup logic, or route structure.

Source baseline SHA: `af5f7f4e91ffcedf6cbcb348478634e48c5b777e`.
Working branch: `stage-06-1-admin-visual-recovery`.

## Changed Files

- `frontend/src/main.jsx`
- `frontend/src/admin/admin.css`
- `docs/STAGE-06-1-ADMIN-VISUAL.md`
- `docs/stage-06-1-admin-visual/**`

## React Changes

Minimal admin-only markup changes:

- Added `adminApp` class to the admin dashboard root to scope the visual recovery layer.
- Added `adminVkPanelHeader` class to the VKUI `PanelHeader` so the native white VKUI header can be visually suppressed only on `/admin`.
- Added `aria-label` and `title` to existing admin navigation buttons so compact mobile navigation remains accessible and testable by Russian section names.

No business handlers, API calls, routes, state transitions, cleanup actions, Premium logic, upload logic, or backend contracts were changed.

## CSS Recovery Layer

A scoped CSS layer was added at the end of `frontend/src/admin/admin.css` under:

```css
/* Stage 6.1 admin visual recovery: scoped system layer. */
```

The layer introduces admin-scoped tokens and styles only under `.adminApp` plus the admin confirmation overlay.

### Tokens Added

- Background and surfaces: `--admin-bg`, `--admin-surface-1`, `--admin-surface-2`, `--admin-surface-elevated`
- Borders: `--admin-border-subtle`, `--admin-border-default`, `--admin-border-accent`
- Text: `--admin-text-primary`, `--admin-text-secondary`, `--admin-text-muted`
- Status/accent: `--admin-accent`, `--admin-accent-hover`, `--admin-success`, `--admin-warning`, `--admin-danger`, `--admin-info`
- Shape/layout: `--admin-radius-sm`, `--admin-radius-md`, `--admin-radius-lg`, `--admin-sidebar-width`, `--admin-topbar-height`, `--admin-content-max`
- Shadow: `--admin-shadow-card`

### Visual Areas Restored

- Shell background and admin workspace layout
- Sidebar navigation, active state, badges, collapsed state
- Topbar typography, search, system pills
- Summary cards and dashboard panels
- Storage/cleanup panels and safety actions
- Tables, row actions, filters, segmented controls
- Forms, inputs, textareas, focus states
- Badges, notice/error states, empty states
- JSON previews
- Confirmation modal shell
- Responsive layout for 1180px, 760px, and 380px breakpoints

## Conflict Sources Found

The admin UI had overlapping legacy layers:

- Early `admin.css` rules for admin shell and mobile behavior.
- `styles.css` legacy/shared admin rules still used elsewhere and intentionally left untouched.
- VKUI `PanelHeader` rendered a native header above the custom admin shell.
- Mobile sidebar height allowed version/logout rows to overflow into the workspace.

The fix avoids deleting or reordering legacy styles. It scopes final admin visual rules under `.adminApp` and hides only the admin VKUI header.

## Verification

### Build

`npm run build` in `/tmp/vk-stage58/frontend`: PASS.

Known non-fatal warnings remain from VKUI/Vite:

- module-level `"use client"` directives ignored during bundle
- chunk size warning

### Dev Browser Regression

Checked on dev server `http://127.0.0.1:5174`:

- `/`: no horizontal scroll, no console errors, no request failures
- `/app`: no horizontal scroll, no console errors, no request failures
- `/admin`: no horizontal scroll, no console errors, no request failures

API checks:

- `GET /health`: 200
- `GET /api/v1/status`: 200
- `GET /api/v1/me`: 200

### Admin Responsive Checks

Screenshots saved under `docs/stage-06-1-admin-visual/after/`.

Captured:

- `admin-dashboard-1440.png`
- `admin-dashboard-1024.png`
- `admin-dashboard-768.png`
- `admin-dashboard-430.png`
- `admin-dashboard-320.png`
- `admin-applications-1440.png`
- `admin-premium-codes-1440.png`
- `admin-users-1440.png`
- `admin-queue-1440.png`
- `admin-cleanup-1440.png`
- `admin-cleanup-390.png`
- `admin-features-1440.png`
- `admin-feedback-1440.png`
- `admin-system-1440.png`

Measured checks after the final mobile fix:

- 1440px admin: `scrollWidth == clientWidth == 1440`, no horizontal scroll.
- 430px admin: `scrollWidth == clientWidth == 430`, no horizontal scroll.
- 320px admin: `scrollWidth == clientWidth == 320`, no horizontal scroll.
- 390px mobile cleanup tab click: PASS.

Detailed results:

- `docs/stage-06-1-admin-visual/results.json`
- `docs/stage-06-1-admin-visual/route-regression.json`

## Safety Confirmation

No changes were made to:

- `backend/`
- `worker/`
- `frontend/src/landing/`
- `frontend/src/studio/`
- `frontend/src/styles.css`
- storage/uploads/results/quarantine/Redis data
- cleanup execution logic

No production cleanup operation was executed during this stage.

## Remaining Visual Backlog

These are intentionally not handled in Stage 06.1 because they would require structural or product changes:

- Collapsible formatting for very large audit JSON blocks.
- More compact data-dense table layouts for extremely large datasets.
- Full admin information architecture pass after functional cleanup flows are finalized.



### Production Verification

After deploy to `stl-master-frontend`:

- frontend production build: PASS
- `docker cp dist/. stl-master-frontend:/usr/share/nginx/html/`: PASS
- `nginx -s reload`: PASS
- production browser regression for `/`, `/app`, `/admin`: PASS
- production `GET /health`: 200
- production `GET /api/v1/status`: 200
- production `GET /api/v1/me`: 200

Production regression details:

- `docs/stage-06-1-admin-visual/prod-regression.json`

### Smoke Regression

Targeted smoke tests: PASS

- `tests/smoke_admin_auth_users_cleanup.sh`
- `tests/smoke_admin_security.sh`
- `tests/smoke_admin_feedback.sh`
- `tests/smoke_public_launch.sh`

Full smoke pack: PASS

- `tests/run_all_smoke_tests.sh`

Note: `SMOKE_ADMIN_PASSWORD` was not set, so the positive password-login branch in `smoke_admin_security.sh` was skipped by the test itself. Admin token and security checks passed.

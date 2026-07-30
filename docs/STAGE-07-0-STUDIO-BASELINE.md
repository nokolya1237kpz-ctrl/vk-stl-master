# Stage 7.0 — Studio Baseline Audit

Audit-only baseline for the real `/app` Studio. No source code, JSX, CSS, backend, worker, API, route, Premium, upload, download, or business logic changes were made. Deploy was not executed.

## 1. Source SHA

- Expected and audited source SHA: `5b1d448ca388e8ffe5c29d93077563af2b85c4d9`.
- Git branch used for documentation: `stage-07-0-studio-baseline`.

## 2. Backup

- Backup archive: `/home/codex/backups/stage-07-0-studio-baseline-20260730-141305.tar.gz`
- SHA-256: `eda26061959d6dacc6dd54e545666c33f1237691e810493089915127362c72c9`
- Excluded from backup: `.git`, `node_modules`, `frontend/dist`, uploads, results, Redis, logs, caches and temp files.

## 3. Studio Architecture

Root routing is still centralized in `frontend/src/main.jsx`. `RootComponent` sends `/admin` to `AdminApp`; all other routes render `App`. Inside `App`, `publicView` is initialized as `app` only when `window.location.pathname === "/app"`; otherwise the public landing path is shown. The real Studio route is therefore the non-public branch returned by `App()` after the `home`, `access`, and `premium` branches.

| Component | File/lines | Purpose | Status |
| --- | --- | --- | --- |
| App / Studio route branch | frontend/src/main.jsx:6300 | Root stateful Studio screen for /app; chooses publicView from pathname. | active |
| StudioHeader | frontend/src/studio/StudioComponents.jsx:15 | Studio top bar: brand, project status, Premium status, support, export. | active |
| StudioSidebar | frontend/src/studio/StudioComponents.jsx:58 | Operation preset navigation grouped by Analysis and Geometry. | active |
| StudioEmptyState | frontend/src/studio/StudioComponents.jsx:94 | Dropzone, demo, requirements and gated file selection. | active |
| StudioWorkflowBar | frontend/src/studio/StudioComponents.jsx:123 | Bottom stepper, run CTA, progress and download action. | active |
| StlPreview | frontend/src/main.jsx:1229 | Real Three.js STL viewer with OrbitControls, overlays, selection and screenshots. | active |
| AnalysisResult | frontend/src/main.jsx:5467 | Completed result panels: model QA, what changed, files, compare/change maps. | active |
| JobInfoPanel | frontend/src/main.jsx:5325 | Job metadata, operations, copy Job ID and file sizes. | active |
| FeedbackPanel | frontend/src/main.jsx:5385 | Post-job feedback submission to /api/v1/feedback. | active |
| JobHistory | frontend/src/main.jsx:1126 | localStorage job history with status polling and file access. | active |
| CompareView2 | frontend/src/main.jsx:2618 | Landing/public compare implementation; separate from Studio viewer result controls. | landing-only |
| StudioMockup / DemoStudioPreview | frontend/src/main.jsx:3228 / 4300 | Marketing-only Studio visuals; not the real /app editor. | landing-only |

## 4. Component Map

- Inventory scanner found `135` top-level component/function/constant definitions in frontend files.
- Real Studio components are listed above. Marketing-only Studio visuals (`StudioMockup`, `DemoStudioPreview`) are not part of `/app` execution.
- `frontend/src/studio/StudioComponents.jsx` contains only four exported UI components plus two exported metadata arrays; most Studio logic remains in `main.jsx`.

## 5. State Map

The `/app` branch of `App()` owns `58` React state entries. Major groups: route/view (`publicView`, `demoMode`), access/user (`accessCode`, `currentUser`, loading/error), file/job (`file`, `jobId`, `jobStatus`, `uploading`, `error`), operation settings (`selectedMode`, split/connectors/reduction/orientation/local smoothing), previews/maps (`processedPreviewFile`, `previewMode`, `heatmap*`, `artifactMap*`) and local selection. Persistent state: `stl-master-access-code` and `stl-master-job-history` in localStorage.

| State | Setter | Initial | Location |
| --- | --- | --- | --- |
| publicView | setPublicView | () => (window.location.pathname === "/app" ? "app" : "home") | frontend/src/main.jsx:6302 |
| demoMode | setDemoMode | false | frontend/src/main.jsx:6303 |
| accessGateMessage | setAccessGateMessage | "" | frontend/src/main.jsx:6304 |
| file | setFile | null | frontend/src/main.jsx:6305 |
| jobId | setJobId | null | frontend/src/main.jsx:6306 |
| jobStatus | setJobStatus | null | frontend/src/main.jsx:6307 |
| featureFlags | setFeatureFlags | DEFAULT_FEATURE_FLAGS | frontend/src/main.jsx:6308 |
| accessCode | setAccessCode | () => localStorage.getItem(ACCESS_CODE_STORAGE_KEY) || "" | frontend/src/main.jsx:6309 |
| currentUser | setCurrentUser | null | frontend/src/main.jsx:6310 |
| currentUserLoading | setCurrentUserLoading | true | frontend/src/main.jsx:6311 |
| currentUserError | setCurrentUserError | "" | frontend/src/main.jsx:6312 |
| uploading | setUploading | false | frontend/src/main.jsx:6313 |
| error | setError | "" | frontend/src/main.jsx:6314 |
| selectedMode | setSelectedMode | "check" | frontend/src/main.jsx:6315 |
| activePanel | setActivePanel | "settings:check" | frontend/src/main.jsx:6316 |
| reductionPercent | setReductionPercent | 50 | frontend/src/main.jsx:6317 |
| splitAxis | setSplitAxis | "z" | frontend/src/main.jsx:6318 |
| splitParts | setSplitParts | 2 | frontend/src/main.jsx:6319 |
| splitMode | setSplitMode | "simple" | frontend/src/main.jsx:6320 |
| splitPlaneOffset | setSplitPlaneOffset | 0 | frontend/src/main.jsx:6321 |
| connectorSize | setConnectorSize | 4 | frontend/src/main.jsx:6322 |
| connectorClearance | setConnectorClearance | 0.25 | frontend/src/main.jsx:6323 |
| connectorCount | setConnectorCount | 2 | frontend/src/main.jsx:6324 |
| connectorDepth | setConnectorDepth | 6 | frontend/src/main.jsx:6325 |
| connectorWallThickness | setConnectorWallThickness | 1.2 | frontend/src/main.jsx:6326 |
| magnetSize | setMagnetSize | "6x2" | frontend/src/main.jsx:6327 |
| lockProfile | setLockProfile | "tongue_groove" | frontend/src/main.jsx:6328 |
| bedSizePreset | setBedSizePreset | "220" | frontend/src/main.jsx:6329 |
| bedSizeX | setBedSizeX | 220 | frontend/src/main.jsx:6330 |
| bedSizeY | setBedSizeY | 250 | frontend/src/main.jsx:6331 |

## 6. API Map

| Method | Endpoint | Payload/response role | Studio usage |
| --- | --- | --- | --- |
| GET | /api/v1/me | current user, plan, limits, access code header | Studio load/access state |
| GET | /api/v1/config/features | feature flags | Visible presets and limits |
| POST | /api/v1/jobs/upload | multipart STL + operation/settings fields | Upload and queue job |
| GET | /api/v1/jobs/{job_id} | job status/progress/result | Polling, history, result |
| GET | /api/v1/jobs/{job_id}/download | ZIP package | Export/download |
| GET | /api/v1/jobs/{job_id}/files/{name} | individual STL/JSON/TXT | Processed preview, maps, history files |
| POST | /api/v1/feedback | rating/comment/contact/job | Feedback panel |
| POST | /api/v1/access-requests | early access request | Access gate / public form |
| POST | /api/v1/premium-requests | premium application | Premium modal |
| GET/POST | /api/v1/premium-requests/* and /api/v1/premium/activate | request status and code activation | Premium flow |

Browser API checks: `/health`, `/api/v1/status`, `/api/v1/me`, `/api/v1/config/features` all returned 200. With generated early-access code, `/api/v1/me` returned early access limits.

## 7. Worker Operation Map

| UI label | Preset key | Operations submitted | Backend accepted | Worker implemented | UI status |
| --- | --- | --- | --- | --- | --- |
| Проверить модель | check | analyze, print_check, prepare_package | yes | yes | ready |
| Улучшить модель | improve | analyze, print_check, model_improvement, prepare_package | yes | yes | beta/pro |
| Удалить AI-артефакты | remove_artifacts | analyze, print_check, remove_ai_artifacts, prepare_package | yes | yes | ready/beta |
| Восстановить поверхность | surface | analyze, print_check, surface_recovery, prepare_package | yes, feature default false | yes, controlled failure for large files | hidden unless flag enabled |
| Выборочная правка | local | analyze, print_check, local_smoothing, prepare_package | yes | yes | ready/pro |
| Уменьшить вес | reduce | analyze, print_check, model_improvement, reduce_polygons, prepare_package | yes | yes | ready/pro |
| Разрезать для склейки | split | analyze, print_check, repair_mesh, split_model, prepare_package | yes | yes | ready/pro |
| Разрезать под стол | fit_to_bed | analyze, print_check, fit_to_bed_split, prepare_package | yes | yes | ready/pro |
| Исправить симметрию | symmetry | analyze, print_check, fix_symmetry, prepare_package | yes, feature default false | listed in worker implemented, but UI hidden by flag | hidden/beta |
| Применить ориентацию | orientation | analyze, print_check, apply_orientation, prepare_package | yes | yes | ready |
| Подобрать ориентацию | auto_orientation | analyze, print_check, auto_orientation, prepare_package | yes | yes | ready/pro |

Backend accepted operation set includes analyze, print_check, prepare_package, model_improvement, repair_mesh, reduce_polygons, split_model, fit_to_bed_split, apply_orientation, auto_orientation, fix_symmetry, remove_ai_artifacts, surface_recovery and local_smoothing. Worker has corresponding implementations or controlled-failure paths for the same set.

## 8. Viewer Audit

`StlPreview` uses Three.js `STLLoader`, `OrbitControls`, scene/camera/renderer refs, `devicePixelRatio` capped at 2, orbit rotate/pan/zoom, centering, place-on-table, 90-degree rotations, split/symmetry/local-selection overlays, heatmap/artifact-map coloring, screenshot support and disposal helpers. Browser baseline loaded a tiny ASCII STL and captured viewer screenshots. WebGL emitted repeated ReadPixels performance warnings during screenshot-related rendering, but no page errors.

## 9. Upload Flow

Upload accepts `.stl` through hidden file input and drag/drop. UI access gate is based on a non-empty access code; backend performs real access validation. The audit created a temporary early-access application, approved it through admin token, loaded `stage07-tiny.stl`, submitted operations `analyze`, `print_check`, `prepare_package`, received a job id and verified completed status through API.

## 10. Operation Selection

Operation presets are selected in `StudioSidebar`; changing selected mode resets `activePanel` to `settings:{mode}`. Presets hidden by disabled feature flags are removed via `visiblePresetsForFlags`. Split settings include axis, 2-4 parts, plane offset, mode, clearance and connector count. Fit-to-bed includes bed preset/custom dimensions and connector mode. Orientation includes manual rotations and bed translations. Local smoothing includes brush/point selection and radius/strength.

## 11. Job Flow

- Test job: `c1a25090-d646-492b-8002-bc348204b3e4`
- API status: `completed`, progress `100`, processing seconds `2.015`
- Operations: `analyze, print_check, prepare_package`
- Download ready: `True`
- ZIP files: `original.stl, artifact_map.json, print_report.txt, manifest.json`
- Cleanup: admin bulk delete status `200` for the exact audit job id.

## 12. Error States

Observed safe states: no access gate, invalid-extension attempt path, API 200 status, completed tiny job, generated ZIP. Unsafe states such as intentionally breaking backend, upload 5xx, expired result and worker failure fixture were not forced in production and are marked as blocked for audit-only safety.

## 13. History

`JobHistory` reads/writes `stl-master-job-history`, polls each saved job with `GET /api/v1/jobs/{id}`, marks 404 as expired, supports ZIP download, generated-file details, open result and remove-from-local-history. Browser text showed the audit job in history before it was deleted server-side.

## 14. Compare

Studio compare is result-driven inside `AnalysisResult` and `StlPreview` using `previewMode`, processed preview file, change map and artifact map. Public `CompareView2` is a separate landing component and must not be merged into Studio during recovery.

## 15. Premium Gates

Studio header renders `PremiumStatusControl`. Upload processing needs access; Premium modal/request/activate flows are mounted by `publicView === "premium"`. Audit used early-access rather than Premium and confirmed `/api/v1/me` limits for that code. Premium UI itself was covered by smoke tests.

## 16. Desktop Layout

At 1920x1080: shell {'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'top': 0, 'left': 0, 'right': 1920, 'bottom': 1080}; header {'x': 14, 'y': 14, 'width': 1892, 'height': 72, 'top': 14, 'left': 14, 'right': 1906, 'bottom': 86}; workspace {'x': 14, 'y': 100, 'width': 1892, 'height': 864, 'top': 100, 'left': 14, 'right': 1906, 'bottom': 964}; viewer {'x': 268, 'y': 100, 'width': 1304, 'height': 864, 'top': 100, 'left': 268, 'right': 1572, 'bottom': 964}; inspector {'x': 1586, 'y': 100, 'width': 320, 'height': 864, 'top': 100, 'left': 1586, 'right': 1906, 'bottom': 964}. No horizontal overflow at 1920.

## 17. Tablet Layout

At 1024x768 and 768x1024 there was no horizontal overflow. Layout switches to compact sidebar/stacked inspector around the existing `max-width: 1180px`, `900px`, and `760px` breakpoints.

## 18. Mobile Layout

At 430 and 390 widths, no horizontal overflow was recorded. At 360 and 320 widths, scrollWidth remained 365px, creating horizontal overflow. This is the highest-priority visual issue for Stage 7.1.

## 19. Zoom

Zoom screenshots were captured as deviceScaleFactor approximations for 67, 80, 100 and 125 percent at 1440x900. These are useful visual baselines but not exact browser zoom emulation; manual Chrome/Safari zoom verification remains needed in Stage 7.1.

## 20. Accessibility

Keyboard/focus scan found focusable controls and 1 focusable element without visible text, aria-label or title in the empty 1920 state. Studio uses buttons for operation selections and a labelled viewport region, but icon-only utility controls need a dedicated aria-label pass.

## 21. Performance

Build output: CSS 817.64 kB gzip 114.24 kB, JS 1020.70 kB gzip 281.35 kB. Vite warns about chunk size >500 kB. Browser console captured 4 WebGL ReadPixels performance warnings, no page errors and no failed requests.

## 22. CSS Inventory

- Studio selectors/refs found by inventory: `446`.
- Active Studio CSS files: `frontend/src/studio/studio.css` and shared/legacy rules in `frontend/src/styles.css`.
- Important layout rules: `.studioShell` uses `height: 100dvh` and `overflow: hidden` on desktop, switched to auto/visible below 1180px; `.studioWorkspace` desktop grid is `250px minmax(520px, 1fr) 320px`; `.studioViewerWorkspace` is the central viewport host; `.studioInspector` is right panel and moves under the viewer on narrower breakpoints.

## 23. Browser Errors

- Console messages: `4` warnings, all WebGL ReadPixels performance warnings.
- Page errors: `0`.
- Failed requests: `0`.

## 24. Functional Defects

| ID | Severity | Area | Reproduction | Expected | Actual | Probable cause | Files | Logic risk | Stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STUDIO-VIS-001 | high | Responsive | 320-360 px viewport | No horizontal scroll | scrollWidth stays 365px on 320/360 mobile | Minimum widths in mobile header/actions/sidebar still leak by 5-45px | frontend/src/studio/studio.css | low logic risk | 7.1 |
| STUDIO-FUNC-002 | medium | Access/upload gate | Use stale/non-empty access code | UI should distinguish unverified code from verified access | hasUploadAccess is Boolean(accessCode.trim()), backend is source of truth | frontend/src/main.jsx:6309, 6355, upload handlers | medium logic risk | 7.3 |
| STUDIO-UX-003 | medium | Job cleanup/test classification | Create test user then upload from UI | Test job should be classifiable by test_run_id/user source | Audit job inherited source=app/environment=production and needed exact manual bulk delete | backend/app/main.py upload metadata, admin cleanup classification | medium data hygiene risk | 7.4 |
| STUDIO-PERF-004 | medium | WebGL screenshot/readback | Run browser baseline with loaded STL | No repeated WebGL performance warnings | Chromium logged GPU stall due to ReadPixels warnings | StlPreview screenshot/preserveDrawingBuffer path | low logic risk | 7.8 |
| STUDIO-CSS-005 | medium | CSS layering | Inspect studio.css | One coherent Studio CSS layer | studio.css has repeated late override blocks for same selectors and global style overlap with styles.css | frontend/src/studio/studio.css, frontend/src/styles.css | medium regression risk | 7.1 |
| STUDIO-UX-006 | medium | Result UI refresh | Tiny job completed quickly | UI should settle to completed/result without needing later API check | Browser body captured 80% text while API already completed; polling timing can leave screenshot stale | frontend/src/main.jsx polling/result effects | medium UX risk | 7.4 |
| STUDIO-QA-011 | medium | Connector worker modes | Smoke connector tests | Connector modes should integrate when feasible or report controlled failure | Glue/lock/pins/magnets smoke pass as controlled fallback for thin/unsafe geometry, but integrated=false in tested cases | worker/app/worker.py split connector functions | medium feature expectation risk | 7.3 |

## 25. Visual Defects

| ID | Severity | Area | Reproduction | Expected | Actual | Probable cause | Files | Logic risk | Stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STUDIO-VIS-001 | high | Responsive | 320-360 px viewport | No horizontal scroll | scrollWidth stays 365px on 320/360 mobile | Minimum widths in mobile header/actions/sidebar still leak by 5-45px | frontend/src/studio/studio.css | low logic risk | 7.1 |
| STUDIO-PERF-004 | medium | WebGL screenshot/readback | Run browser baseline with loaded STL | No repeated WebGL performance warnings | Chromium logged GPU stall due to ReadPixels warnings | StlPreview screenshot/preserveDrawingBuffer path | low logic risk | 7.8 |
| STUDIO-CSS-005 | medium | CSS layering | Inspect studio.css | One coherent Studio CSS layer | studio.css has repeated late override blocks for same selectors and global style overlap with styles.css | frontend/src/studio/studio.css, frontend/src/styles.css | medium regression risk | 7.1 |
| STUDIO-A11Y-007 | low | Accessibility | Run focusable audit | All icon-only controls labelled | 1 focusable element without visible text/aria/title found in empty 1920 metrics | frontend/src/main.jsx / StudioComponents.jsx | low | 7.8 |
| STUDIO-PERF-010 | low | Bundle size | npm run build | Chunks ideally below warning threshold | Main JS 1020.70 kB and CSS 817.64 kB trigger Vite size warning | frontend bundle | low | 7.8 |

## 26. Risk Classification

- Critical: 0
- High: 1
- Medium: 6
- Low: 4

## 27. Recommended Sequence Stage 7.1+

1. 7.1 Studio shell and responsive layout: remove 320/360 overflow and stabilize header/workspace sizing.
2. 7.2 Viewer interaction and camera: manual visual QA of centering, zoom, rotate, pan, screenshots and overlay readability.
3. 7.3 Upload and operation cards: clarify access verification, invalid file UX and connector settings.
4. 7.4 Job progress and result: make completed polling/result transition visually deterministic.
5. 7.5 History and Compare: separate Studio result compare from public landing compare and audit mobile history.
6. 7.6 Premium/modals/states: verify gates without changing Premium logic.
7. 7.7 Studio visual consistency: only after functional baseline remains green.
8. 7.8 Performance and accessibility: chunk/readback warnings, aria-label and keyboard pass.

## 28. Protected Areas

Do not change backend API contracts, worker operation semantics, route switching in `RootComponent`/`App`, access code validation, Premium request/activation logic, file upload/download endpoints, job queue behavior, admin cleanup, or existing public landing sections during Stage 7.1 unless explicitly authorized.

## 29. Screenshots

Screenshots saved under `docs/stage-07-0-studio-baseline/screenshots/` (30 files):


- `studio-1024.png`

- `studio-1440-zoom-100.png`

- `studio-1440-zoom-125.png`

- `studio-1440-zoom-67.png`

- `studio-1440-zoom-80.png`

- `studio-320.png`

- `studio-360.png`

- `studio-390.png`

- `studio-430.png`

- `studio-768.png`

- `studio-compare-1920.png`

- `studio-completed-1920.png`

- `studio-empty-1440.png`

- `studio-empty-1920.png`

- `studio-file-loaded-1920.png`

- `studio-history-1440.png`

- `studio-history-1920.png`

- `studio-invalid-file-1920.png`

- `studio-loaded-1440.png`

- `studio-mobile-menu.png`

- `studio-mobile-operations.png`

- `studio-mobile-result.png`

- `studio-mobile-viewer.png`

- `studio-modal-1920.png`

- `studio-operations-1920.png`

- `studio-premium-gate-1920.png`

- `studio-processing-1440.png`

- `studio-result-1440.png`

- `studio-result-1920.png`

- `studio-uploading-1920.png`


## 30. Source Integrity Confirmation

PASS. Production source checksum comparison passed after excluding generated `tests/results/*` and Python `__pycache__` runtime files. Git clone status before commit shows only new documentation files under `docs/stage-07-0-studio-baseline/`. Existing source files in `frontend/src`, `backend`, `worker`, `tests` scripts and `scripts` were not modified by this stage.

## Validation Summary

- `npm run build`: PASS.
- `./tests/run_all_smoke_tests.sh`: PASS, all smoke tests passed.
- Browser baseline: PASS with documented warnings.
- Tiny STL job: PASS via API, ZIP verified, audit job removed via exact admin bulk delete.
- Deploy: NOT RUN.

# STAGE 7.2 — Professional Viewer Recovery

## Scope

Stage 7.2 touched only the production STL Viewer implementation:

- `frontend/src/main.jsx`
- `frontend/src/styles.css`

No backend, worker, API, Redis, upload flow, download flow, history, compare logic, Premium logic, polling, job processing, operation keys, Landing, or Admin files were changed.

## Viewer Architecture

The active Viewer is `StlPreview` in `frontend/src/main.jsx`.

Runtime map:

- Renderer: `THREE.WebGLRenderer` with antialiasing, transparent canvas, `preserveDrawingBuffer` for screenshot export, `SRGBColorSpace`, and ACES tone mapping.
- Scene: one Three.js scene per Viewer mount.
- Camera: `THREE.PerspectiveCamera` with dynamic near/far and target after every model load.
- Controls: `OrbitControls` with damping, tuned rotate/zoom/pan speed, and camera distance limits derived from model bounds.
- Model loading: `STLLoader` parses the active file and creates a mesh/group depending on normal, heatmap, or artifact mode.
- Grid/floor: engineering grid and floor are owned by refs and rebuilt from current model bounds.
- Overlays: split, symmetry, and local selection overlays remain separate Three.js objects with existing cleanup.
- HUD: React/CSS overlay above canvas shows compact Viewer metrics and axis helper without touching renderer state.
- Resize: `ResizeObserver` updates camera aspect and renderer size.
- Screenshot: existing canvas screenshot action remains unchanged.
- Disposal: model, overlay, grid, floor, controls, and renderer are disposed on clear/unmount.

## Bounding Calculations

After every STL load the Viewer now computes and stores:

- `BoundingBox`
- `BoundingSphere`
- center
- radius
- diagonal
- vertex count
- triangle count

These values are stored in refs (`modelBoxRef`, `modelSphereRef`, `modelMetricsRef`) and mirrored into lightweight React metrics for the HUD.

## Auto Center

The STL geometry is normalized to its true bounding-box center during load. The old automatic floor-shift behavior was removed from load normalization. The manual `Поставить на стол` action is preserved and still works as an explicit user action.

## Camera

`centerView()` now uses the current bounding sphere and viewport aspect to calculate:

- camera target
- ideal distance
- near plane
- far plane
- min zoom distance
- max zoom distance

The camera target is the real model center, not an elevated point above the model.

## OrbitControls

Controls were tuned for a CAD-like feel:

- damping factor: `0.06`
- rotate speed: `0.72`
- zoom speed: `0.78`
- pan speed: `0.58`
- screen-space panning disabled for more stable orbit behavior

## Lighting

Lighting is still engineering-oriented, not photorealistic:

- reduced hemisphere intensity
- softer key light
- added low-intensity fill light
- controlled cyan rim light

The model material itself was not replaced.

## Grid

The Viewer grid is now rebuilt from the model diagonal:

- size clamps between `80` and `2400`
- subdivisions clamp between `16` and `96`
- grid is placed at the current model lower bound
- floor is slightly below the grid
- both grid and floor are disposed before rebuilding

## Axes

A compact CSS axis gizmo was added in the lower-right Viewer overlay layer. It is not part of the Three.js scene and does not interfere with camera controls or model picking.

## Empty / Loading / Processing / Result

- Empty Viewer remains handled by the existing `StudioEmptyState` without changing upload logic.
- STL parsing shows a non-blocking loading overlay.
- Processing uses existing `uploading`, `progress`, and `jobStatus` props only for a visual overlay; job logic was not changed.
- Completed jobs show a compact result badge with next-action context.

## Performance

The animation loop samples renderer metrics every ~750 ms:

- FPS
- frame time
- draw calls
- rendered triangles
- geometry count
- texture count

HUD currently displays the most important operational values: model triangles, radius, and FPS.

## Memory

Cleanup now includes:

- model geometries/materials
- split overlay
- symmetry overlay
- local selection overlay
- engineering grid
- floor plane
- OrbitControls
- renderer
- animation frame
- DOM canvas removal

## Screenshots

Stored in `docs/stage-07-2-viewer/screenshots/`:

- `viewer-empty.png`
- `viewer-loaded.png`
- `viewer-processing.png`
- `viewer-result.png`
- `viewer-mobile.png`
- `viewer-tablet.png`
- `viewer-desktop.png`
- `viewer-zoom.png`
- `viewer-check.json`

`viewer-processing.png` is a visual state capture of the processing overlay mounted over the loaded demo model. It does not trigger a backend job and does not modify job processing logic.

## Regression

Build:

- `npm run build` in `/home/codex/projects/vk-stl-master/frontend`: PASS

Browser preview checks:

- `/app` empty state: PASS
- demo model load: PASS
- canvas present: PASS
- Viewer HUD present: PASS
- axis gizmo present: PASS
- result badge present: PASS
- horizontal scroll: none at 1440 px
- console errors: 0
- request failures: 0

Full smoke:

- ./tests/run_all_smoke_tests.sh: PASS
- final line: All smoke tests passed.

## Residual Backlog

- Add real processing screenshot from a live backend job in a later end-to-end QA pass if needed.
- Consider moving Viewer out of `main.jsx` only in a future architecture stage, not during recovery.
- Compare viewer still uses its own camera fitting logic and was intentionally not changed in Stage 7.2.

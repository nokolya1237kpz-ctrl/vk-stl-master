# Stage 08.1: Production Split Tools

## Scope

Stage 08.1 hardens split tooling in STL Master Studio without changing backend API routes or public landing structure.

## What Changed

- Pins split now has a strict production contract: if real integrated pin geometry is not created and validated, the split is marked unsuccessful and ordinary split parts are not exported as a fake pin result.
- Unsupported profile modes in Studio are guarded as coming soon:
  - `паз-гребень`
  - `ласточкин хвост`
  - `пазловое соединение`
- Studio shell overflow was relaxed so the app is not clipped after opening the demo or a long result.
- Viewer toolbar is compact by default and expands on hover/focus.
- Viewer axis gizmo was moved to the lower-right viewport area and layered below the toolbar.
- User-facing `/app` labels touched by this stage were translated to Russian where they were still mixed.
- Regression tests were updated for the strict pins contract and package manifest semantics.

## Pins Contract

For `split_mode=pins`:

- `split_model.success` must be `true` only when pin geometry is integrated.
- `connectors.integrated` must be `true`.
- `connectors.success` must be `true`.
- connector QA must pass `assembly_check_passed`.
- generated files must include both split parts and `connector_report.json`.

If pins cannot be integrated:

- `split_model.success` is `false`;
- `split_model.output_files` is empty;
- fake ordinary split parts are removed from the result;
- the user receives a Russian reason explaining why pins were not produced.

## Unsupported Connector Modes

The following presets are visible but disabled in Studio because production geometry is not implemented:

- `split_tongue`
- `split_dovetail`
- `split_puzzle`

They cannot be selected, cannot populate upload operations, and cannot start processing as production-ready tools.

## Files Changed

- `frontend/src/main.jsx`
- `frontend/src/studio/StudioComponents.jsx`
- `frontend/src/studio/studio.css`
- `frontend/src/styles.css`
- `worker/app/worker.py`
- `tests/run_all_smoke_tests.sh`
- `tests/smoke_frontend_workflow_contract.sh`
- `tests/smoke_pipeline_matrix.sh`
- `tests/smoke_queue_limits.sh`
- `tests/smoke_split_pins.sh`
- `tests/smoke_split_pins_geometry.sh`

## Verification

- Frontend build: PASS.
- Frontend deploy to `stl-master-frontend`: PASS.
- Worker rebuild/recreate: PASS.
- Browser check for `/`, `/app`, `/admin`: PASS.
- `GET /api/v1/me`: PASS, HTTP 200.
- `tests/smoke_split_pins.sh`: PASS.
- `tests/smoke_split_pins_geometry.sh`: PASS.
- `tests/smoke_pipeline_matrix.sh`: PASS.
- `tests/run_all_smoke_tests.sh`: PASS.

## Browser Check

Headless Chromium checked:

- HTTP status 200 for `/`, `/app`, `/admin`.
- No horizontal overflow at 1440px.
- No console errors.
- No page errors.
- No request failures.

Screenshots were written on the server:

- `/tmp/stage81_root.png`
- `/tmp/stage81_app.png`
- `/tmp/stage81_admin.png`

## Deployment Notes

Docker Compose v1 hit its known `ContainerConfig` recreate issue while rebuilding the worker. The stale prefixed worker container was removed and the worker was recreated with `docker-compose up -d --no-deps worker`. Current containers are up:

- `stl-master-worker`
- `stl-master-frontend`
- `stl-master-backend`
- `stl-master-edge-proxy`
- Redis container


# Stage 06.0 Admin Storage: Phase A Server Storage Audit

Source SHA: `9181038dbc7049b6dc95ba38b780ffaa969cc1e0`  
Branch: `stage-06-0-admin-storage-recovery`  
Generated: `2026-07-28T15:24:31`

## Safety Status

Phase A is read-only. No files, Docker images, Docker volumes, Redis keys, uploads, results, quarantine data, backups, logs, or configuration files were deleted.

Important path deviation: `/home/codex/projects/vk-stl-master` is the production working directory but is not a git repository. The active git worktree for this stage is `/tmp/vk-stage58`, created from GitHub and currently on branch `stage-06-0-admin-storage-recovery`.

## Disk State Before Cleanup

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        79G   77G  2.2G  98% /
```

```text
Filesystem      Inodes  IUsed   IFree IUse% Mounted on
/dev/sda1      5242880 894233 4348647   18% /
```

The root filesystem is critically full: 98% used, about 2.2G available at audit time.

## Docker Usage

```text
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          19        6         2.123GB   1.784GB (84%)
Containers      6         6         19.79GB   0B (0%)
Local Volumes   5         4         2.174GB   0B (0%)
Build Cache     74        0         3.843GB   3.478GB
```

Docker build cache is reclaimable, but no Docker volume cleanup is allowed. Current production images and at least one rollback image should be preserved.

## Runtime Storage Map

Protected runtime paths:

- `/data/uploads` inside backend/worker: user uploads, mounted from `vk-stl-master_uploads-data`; size about 119.9 MiB.
- `/data/results` inside backend/worker: results, reports, applications, feedback, admin metadata; size about 196.7 MiB excluding quarantine details shown separately.
- `/data/quarantine`: runtime quarantine/test-data area; size about 18.39 GiB. This is the largest STL Master-related storage area and must be handled through Admin/manual confirmation, not automatic deletion.
- `vk-stl-master_redis-data`: Redis state for queue/session/app data.
- `/home/codex/projects/vk-stl-master/.env`: production secrets/config, protected and not printed.
- `/home/codex/projects/vk-stl-master/config`: production config bind-mounted into services.
- `/etc/letsencrypt`: TLS certificates mounted into edge proxy.
- `/tmp/stl-master-edge-proxy.conf`: active edge proxy config.

Redis aggregated key count: `2852`.

No SQLite/Postgres database files were found in the audited project/backups paths; runtime state is file volumes plus Redis.

## Largest Findings

- `/data/quarantine`: about 18.39 GiB, mostly `test-data-*` quarantine directories from July 22-25.
- `/var/log`: about 7.0 GiB, dominated by `/var/log/mtproxy_bot/bot.log` and systemd journal. This is not STL runtime data and should be rotated/vacuumed only with service-aware retention.
- Docker build cache: about 3.84 GiB reclaimable by `docker builder prune`, without `--volumes`.
- `/tmp`: about 1.1 GiB, containing old stage clones/screenshots/artifacts plus the active `/tmp/vk-stage58` git worktree.
- `/home/codex/.cache/ms-playwright`: Playwright browser cache.
- `/home/codex/.npm`: npm cache.

## Backup Inventory

Backups found:

- `/home/codex/backups/stl-master-before-visual-recovery-20260722-173943.tar.gz`, SHA256 `69379b9edd651fd6196ea47767e60aada490f0381cbb3f43d04e91dbe2af80cf`, source/frontend/docker/nginx-style backup. Conditional: keep unless verified as source-only and safely represented in GitHub.
- `/home/codex/backups/vk-stl-master-before-visual-recovery-20260723-082327.tar.gz`, SHA256 `18a92f70a3866b50f3bf0376634206844428852366cb318f44f08365f60607cb`, source/frontend backup. Conditional: keep unless verified as source-only and safely represented in GitHub.
- `/home/codex/backups/stl-master-admin-cleanup-20260721-094926`, contains admin cleanup inventory/restore materials. Keep until Stage 06.0 is complete.
- `/home/codex/projects/vk-stl-master/.codex-backups/*`, small legacy UI backups. Conditional but not urgent.
- `/home/codex/projects/vk-stl-master/STL_Master_Codex_Design_Package.zip`, design/source package. Conditional.

GitHub backs up source history only. GitHub does not back up `.env`, Redis, uploads, results, quarantine, Docker volumes, SSL certificates, runtime logs, or production configuration.

## Cleanup Dry Run

Machine-readable dry run:

- `docs/stage-06-0-admin-storage/cleanup-dry-run.json`
- `docs/stage-06-0-admin-storage/storage-audit-summary.json`

Safe technical cleanup candidates total about 5.00 GiB, mostly old `/tmp` stage artifacts, npm/Playwright caches, Docker build cache, and Python caches.

Conditional/manual-review candidates total about 26.65 GiB, dominated by `/data/quarantine`, logs, dangling images, and backups.

Protected candidates total about 1.04 GiB in the dry-run list. Some Docker volume sizes are intentionally represented through container paths rather than host volume paths.

## Recommended Next Step

Do not delete `/data/quarantine` directly from the server shell. Phase B/C should restore Admin cleanup preview/execute so the administrator can inspect and intentionally clear quarantine categories with confirmation. For immediate disk pressure, safest first candidates after explicit confirmation are Docker build cache and old `/tmp` stage artifacts; they do not contain user STL data.

## Phase A Conclusion

Phase A complete enough to proceed to backend/Admin cleanup analysis. No destructive operation was executed.

## Phase B/C Admin Cleanup Recovery

Updated: `2026-07-30T05:35:49+00:00`

### Endpoint Inventory Reviewed

Admin backend endpoints reviewed in `backend/app/main.py` include:

- `POST /api/v1/admin/login`
- `GET /api/v1/admin/security`
- `GET /api/v1/admin/overview`
- `GET /api/v1/admin/premium-codes`
- `GET /api/v1/admin/features`
- `POST /api/v1/admin/test-data/scan`
- `POST /api/v1/admin/test-data/cleanup`
- `POST /api/v1/admin/legacy-data/scan`
- `POST /api/v1/admin/legacy-data/quarantine`
- `GET /api/v1/admin/feedback`
- `GET /api/v1/admin/feedback/summary`
- `POST /api/v1/admin/feedback/cleanup-test`
- `POST /api/v1/admin/feedback/delete-test`
- `GET /api/v1/admin/applications`
- `POST /api/v1/admin/applications/delete-test`
- `POST /api/v1/admin/applications/bulk`
- `POST /api/v1/admin/applications/{kind}/{application_id}/approve`
- `POST /api/v1/admin/applications/{kind}/{application_id}/reject`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users/deletion-preview`
- `POST /api/v1/admin/users/delete`
- `POST /api/v1/admin/users/bulk`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{user_id}`
- `POST /api/v1/admin/users/{user_id}/premium`
- `POST /api/v1/admin/users/{user_id}/block`
- `POST /api/v1/admin/users/{user_id}/unblock`
- `POST /api/v1/admin/users/{user_id}/reset-code`
- `GET /api/v1/admin/cleanup/status`
- `POST /api/v1/admin/cleanup/scan`
- `POST /api/v1/admin/cleanup/execute`
- `POST /api/v1/admin/cleanup/run`
- `POST /api/v1/admin/system-cleanup`
- `GET /api/v1/admin/queue`
- `POST /api/v1/admin/integrity-check`
- `POST /api/v1/admin/jobs/bulk`
- `POST /api/v1/admin/jobs/delete-test`
- `POST /api/v1/admin/jobs/{job_id}/cancel`

### Proven Runtime Facts

Production API before deploy:

- `/health`: `ok`
- Redis: `ok`
- Queue: 0 queued, 0 processing, 0 stale jobs
- Active jobs from cleanup status: 0
- Disk during continuation: about 3.7G free, 96% used
- `/api/v1/admin/system-cleanup/preview`: 404 before deploy, as expected because the new endpoint is branch-only at that moment

### Root Cause Found

The regular cleanup API already had allowlisted scan/execute and fixture-based smoke coverage. The dangerous/unclear part was the Admin “Очистка системы” quick-action area: buttons such as stale jobs, orphan files, Redis, empty dirs and quarantine called the execute endpoint directly after a simple browser confirm only for quarantine. This made the UI feel like cleanup was “not working” or unsafe because there was no consistent preview, category report, expected freed space, or detailed confirmation modal before execution.

### Backend Changes

- Added `preview_system_cleanup_actions(actions)` to calculate system cleanup impact without deleting anything.
- Added `preview_empty_cleanup_dirs()` for read-only empty directory inventory.
- Added `quarantine_entry_count()` and exposed `quarantine_entries` in cleanup status.
- Added `POST /api/v1/admin/system-cleanup/preview`.
- Preserved `POST /api/v1/admin/system-cleanup`; added `dry_run: true` compatibility.
- Did not include quarantine in ordinary cleanup scan. Quarantine remains a separate explicit action requiring `ОЧИСТИТЬ КАРАНТИН`.

### Frontend Admin Changes

- Replaced immediate `systemCleanup(actions)` execution with preview-first flow.
- Added `systemCleanupPreview` and `systemCleanupBusy` state.
- Added a confirmation modal inside the cleanup tab with action list, potential freed bytes, quarantine size and backend action details.
- Disabled system cleanup buttons during preview/execution to prevent duplicate requests.
- Kept all existing Admin sections and bulk bars.

### Test Changes

Updated `tests/smoke_admin_auth_users_cleanup.sh` with checks for:

- `POST /api/v1/admin/system-cleanup/preview` for quarantine dry-run
- `POST /api/v1/admin/system-cleanup` with `dry_run: true` for compatibility

### Verification Performed Before Deploy

- `python3 -m py_compile backend/app/main.py`: PASS
- `git diff --check`: PASS
- `cd /tmp/vk-stage58/frontend && npm run build`: PASS after installing frontend dependencies in the temporary worktree

### Files Changed So Far

- `backend/app/main.py`
- `frontend/src/main.jsx`
- `frontend/src/admin/admin.css`
- `tests/smoke_admin_auth_users_cleanup.sh`
- `docs/STAGE-06-0-ADMIN-STORAGE.md`
- `docs/stage-06-0-admin-storage/cleanup-dry-run.json`
- `docs/stage-06-0-admin-storage/storage-audit-summary.json`
- `docs/stage-06-0-admin-storage/SERVER_STORAGE_AUDIT.md`

### Not Yet Done

- No production deploy yet.
- No runtime cleanup deletion yet.
- No quarantine deletion.
- No Docker prune.
- No push yet.


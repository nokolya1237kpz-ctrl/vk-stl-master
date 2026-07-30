# SERVER STORAGE AUDIT — STL Master Stage 06.0

Generated: `2026-07-30T05:35:49+00:00`  
Source SHA: `9181038dbc7049b6dc95ba38b780ffaa969cc1e0`  
Working branch: `stage-06-0-admin-storage-recovery`

## Scope

This audit is a storage and safety map for the production server. It is intentionally conservative: user uploads, processing results, Redis state, `.env`, Docker volumes, SSL, active jobs and quarantine data are protected by default.

## Disk Before Cleanup

Initial root filesystem state from Phase A:

```text
/dev/sda1 79G total, 77G used, 2.2G available, 98% used
```

Later check during continuation showed:

```text
/dev/sda1 79G total, 75G used, 3.7G available, 96% used
```

No Stage 06.0 destructive cleanup has been executed by this task so far.

## Largest Storage Areas

- `/data/quarantine`: approximately 18.39 GiB. Protected/manual admin action only.
- `/var/log`: approximately 7.0 GiB, mostly `mtproxy_bot/bot.log` and systemd journal. Conditional, service-aware log rotation only.
- Docker build cache: approximately 3.84 GiB. Safe candidate after explicit cleanup phase, no volumes.
- `/tmp`: approximately 1.1 GiB with old stage clones/artifacts. Safe candidate except active `/tmp/vk-stage58`.
- `/home/codex/.cache/ms-playwright`: safe technical cache candidate.
- `/home/codex/.npm`: safe technical cache candidate.

## Protected Runtime Data

- `/data/uploads` / Docker volume `vk-stl-master_uploads-data`: user uploaded STL/source files.
- `/data/results` / Docker volume `vk-stl-master_results-data`: processed models, reports, applications, admin metadata.
- `/data/quarantine`: quarantined runtime/test data; only explicit Admin quarantine button may clear it.
- Docker volume `vk-stl-master_redis-data`: queue/session/app Redis state.
- `/home/codex/projects/vk-stl-master/.env`: production secrets, not printed.
- `/home/codex/projects/vk-stl-master/config`: runtime config.
- `/etc/letsencrypt`: SSL certificates.
- `/tmp/stl-master-edge-proxy.conf`: active edge proxy config.

## GitHub Backup Boundary

GitHub backs up source code and history only. It does not back up `.env`, uploads, results, Redis, quarantine, Docker volumes, SSL, logs, production config, or runtime user data.

## Dry Run Summary

Dry-run file: `docs/stage-06-0-admin-storage/cleanup-dry-run.json`

- Safe technical candidates: 21 items, 5.00 GiB.
- Conditional/manual-review candidates: 8 items, 26.65 GiB.
- Protected candidates: 11 items, 1.04 GiB.

## Admin Cleanup Safety Decision

Ordinary cleanup scan remains limited to allowlisted roots: uploads, results, and `/data/admin-cleanup-test`. Quarantine is intentionally not included in ordinary cleanup preview/execute.

For system cleanup, Stage 06.0 adds a read-only preview endpoint and a frontend confirmation modal so quick buttons no longer execute without a visible preview.

## Current Implementation Status

Implemented in branch, not yet deployed at this point in the report:

- `POST /api/v1/admin/system-cleanup/preview`
- `POST /api/v1/admin/system-cleanup` with `dry_run: true` compatibility
- `/api/v1/admin/cleanup/status` now exposes `quarantine_entries`
- Admin UI shows a confirmation modal before system cleanup execution
- Existing smoke test now checks system cleanup preview and dry-run compatibility

## No Direct Deletion

No `rm -rf`, `docker system prune -a --volumes`, Docker volume deletion, Redis deletion, or direct quarantine deletion was performed during Phase A/B/C preparation.

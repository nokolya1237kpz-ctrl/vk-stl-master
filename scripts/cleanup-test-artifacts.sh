#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"
HOURS="${1:-24}"

if ! [[ "${HOURS}" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 [hours]" >&2
  exit 2
fi

cd "${PROJECT_DIR}"

echo "== Cleanup threshold =="
echo "Deleting test/job artifacts older than ${HOURS} hours."

echo
echo "== Before =="
df -h /
du -sh tests/results 2>/dev/null || true
docker-compose exec -T worker sh -lc 'du -sh /data/uploads /data/results 2>/dev/null || true'

echo
echo "== Cleaning tests/results =="
if [[ -d tests/results ]]; then
  find tests/results -type f ! -name 'pipeline_matrix_summary.tsv' -mmin +"$((HOURS * 60))" -print -delete
else
  echo "tests/results does not exist"
fi

echo
echo "== Cleaning job uploads/results =="
docker-compose exec -T worker python - "${HOURS}" <<'PY'
import os
import shutil
import sys
import time
from pathlib import Path

from redis import Redis
from redis.exceptions import RedisError

hours = int(sys.argv[1])
cutoff = time.time() - hours * 3600
roots = [Path("/data/uploads"), Path("/data/results")]
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")


def directory_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        try:
            if item.is_file() or item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def active_job_ids() -> set[str]:
    active: set[str] = set()
    try:
        client = Redis.from_url(redis_url, decode_responses=True)
        for key in client.scan_iter("stl:job:*"):
            job_id = key.rsplit(":", 1)[-1]
            status = client.hget(key, "status")
            if status in {"queued", "processing"}:
                active.add(job_id)
        for raw_item in client.lrange("stl:jobs", 0, -1):
            try:
                import json

                payload = json.loads(raw_item)
                job_id = payload.get("job_id")
                if job_id:
                    active.add(str(job_id))
            except Exception:
                continue
    except RedisError as exc:
        print(f"Redis unavailable, active jobs cannot be checked: {exc}")
        raise SystemExit(1)
    return active


active = active_job_ids()
print(f"Active jobs protected: {len(active)}")

total_removed = 0
removed_paths: list[str] = []
skipped_active: list[str] = []

for root in roots:
    if not root.exists():
        print(f"{root} does not exist")
        continue
    for child in root.iterdir():
        if not child.is_dir():
            continue
        job_id = child.name
        if job_id in active:
            skipped_active.append(str(child))
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime > cutoff:
            continue
        size = directory_size(child)
        shutil.rmtree(child, ignore_errors=True)
        total_removed += size
        removed_paths.append(str(child))

for path in removed_paths:
    print(path)
if skipped_active:
    print("Skipped active jobs:")
    for path in skipped_active:
        print(path)

print(f"Removed job directories: {len(removed_paths)}")
print(f"Approx reclaimed from job directories: {total_removed / (1024 ** 3):.2f} GiB")
PY

echo
echo "== After =="
df -h /
du -sh tests/results 2>/dev/null || true
docker-compose exec -T worker sh -lc 'du -sh /data/uploads /data/results 2>/dev/null || true'

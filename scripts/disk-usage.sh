#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"

cd "${PROJECT_DIR}"

echo "== Filesystem =="
df -h

echo
echo "== Docker =="
docker system df

echo
echo "== Project data =="
du -sh test-data 2>/dev/null || true
du -sh tests/results 2>/dev/null || true

echo
echo "== STL job volumes =="
if docker-compose ps -q worker >/dev/null 2>&1; then
  docker-compose exec -T worker sh -lc 'du -sh /data/uploads /data/results 2>/dev/null || true'
else
  echo "worker container is not available"
fi

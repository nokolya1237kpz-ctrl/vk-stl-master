#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"
OLDER_THAN_HOURS="${1:-24}"
LOG_FILE="/var/log/stl-master-cleanup.log"

{
  printf '[%s] STL Master beta cleanup start, ttl=%sh\n' "$(date -Is)" "${OLDER_THAN_HOURS}"
  cd "${PROJECT_DIR}"
  ./scripts/cleanup-test-artifacts.sh "${OLDER_THAN_HOURS}"
  printf '[%s] STL Master beta cleanup done\n' "$(date -Is)"
} >>"${LOG_FILE}" 2>&1

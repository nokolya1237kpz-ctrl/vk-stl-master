#!/usr/bin/env bash
set -euo pipefail

SMOKE_TEST_NAME="$(basename "$0")"
SMOKE_TEST_RUN_ID="${SMOKE_TEST_RUN_ID:-$(python3 - <<'PY_SMOKE_ID'
import uuid
print(uuid.uuid4())
PY_SMOKE_ID
)}"
SMOKE_UPLOAD_FIELDS=(
  -F "is_test=true"
  -F "source=smoke_test"
  -F "environment=test"
  -F "test_run_id=${SMOKE_TEST_RUN_ID}"
  -F "test_name=${SMOKE_TEST_NAME}"
)
SMOKE_JSON_META="\"is_test\":true,\"source\":\"smoke_test\",\"environment\":\"test\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\",\"test_name\":\"${SMOKE_TEST_NAME}\""

smoke_cleanup_run() {
  local api="${API_BASE:-http://localhost:8000}"
  if [[ "${SMOKE_SKIP_CLEANUP:-0}" == "1" || -z "${ADMIN_TOKEN:-}" ]]; then
    return 0
  fi
  local cleanup_response
  cleanup_response="$(curl --max-time 15 -sS     -H "X-Admin-Token: ${ADMIN_TOKEN}"     -H 'Content-Type: application/json'     -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}"     "${api}/api/v1/admin/test-data/cleanup" || true)"
  if [[ -z "${cleanup_response}" ]]; then
    return 0
  fi
  python3 - "${cleanup_response}" <<'PY_SMOKE_CLEANUP'
import json
import sys
try:
    payload = json.loads(sys.argv[1])
except Exception:
    raise SystemExit(0)
if payload.get("ok") is not True:
    raise SystemExit("smoke cleanup failed")
remaining = payload.get("remaining_test_counts") or {}
if any(int(value or 0) for value in remaining.values()):
    raise SystemExit(f"smoke cleanup left test records: {remaining}")
print("smoke cleanup OK")
PY_SMOKE_CLEANUP
}
trap smoke_cleanup_run EXIT


PROJECT_DIR="/home/codex/projects/vk-stl-master"
FRONTEND_MAIN="${PROJECT_DIR}/frontend/src/main.jsx"

cd "${PROJECT_DIR}"

echo "STL Master beta feedback UI contract smoke test"

require_pattern() {
  local pattern="$1"
  local label="$2"
  if ! grep -qE "${pattern}" "${FRONTEND_MAIN}"; then
    echo "ERROR: missing UI contract: ${label}" >&2
    exit 1
  fi
  echo "OK ${label}"
}

require_pattern "translate_x_mm" "manual bed X translation"
require_pattern "translate_z_mm" "manual bed Z translation"
require_pattern "rotation_x_deg" "exact X rotation"
require_pattern "rotation_y_deg" "exact Y rotation"
require_pattern "rotation_z_deg" "exact Z rotation"
require_pattern "split_plane_offset_mm|splitPlaneOffset" "split plane offset"
require_pattern "По центру" "center button"
require_pattern "Положение на столе" "bed position panel"
require_pattern "Плоскость разреза" "split plane panel"
require_pattern "Будет сохранён текущий поворот модели" "orientation save hint"

echo "Beta feedback UI contract smoke test passed."

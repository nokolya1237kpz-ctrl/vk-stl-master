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
cd "${PROJECT_DIR}"

MAIN="frontend/src/main.jsx"
CSS="frontend/src/styles.css"
WORKER="worker/app/worker.py"

echo "STL Master Local Smoothing 3.0 preview contract"

require_grep() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! grep -qE "${pattern}" "${file}"; then
    echo "FAILED: ${message}" >&2
    exit 1
  fi
}

require_grep "computeLocalSelectionPreview" "${MAIN}" "frontend must compute selected vertices/faces for preview"
require_grep "applyLocalSelectionColors" "${MAIN}" "frontend must color selected faces/vertices"
require_grep "THREE\\.Points" "${MAIN}" "frontend must render selected vertices as points"
require_grep "Ожидаемое воздействие" "${MAIN}" "frontend must show impact estimate"
require_grep "localSmoothingImpactLabel" "${MAIN}" "frontend must calculate local smoothing impact"
require_grep "Фокус на изменениях" "${MAIN}" "frontend must expose focus-on-changes action"
require_grep "focusChangesVersion" "${MAIN}" "Compare View must support change-map focus state"
require_grep "focusCameraOnChangeMap" "${MAIN}" "ComparePane must focus camera on changed vertices"
require_grep "selected_faces" "${MAIN}" "frontend must display selected faces"
require_grep "historyLocalStats" "${MAIN}" "history must render local smoothing metrics"
require_grep "selected_regions" "${WORKER}" "processing_history must include selected_regions"
require_grep "selected_vertices" "${WORKER}" "processing_history must include selected_vertices"
require_grep "selected_faces" "${WORKER}" "processing_history must include selected_faces"
require_grep "historyLocalStats" "${CSS}" "CSS must style local smoothing history metrics"
require_grep "selectionActive" "${CSS}" "CSS must style active selection cursor"

echo "Local Smoothing 3.0 preview contract passed."

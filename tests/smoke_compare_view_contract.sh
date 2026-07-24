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
LOCAL_PROJECT_DIR="${LOCAL_PROJECT_DIR:-/home/codex/projects/vk-stl-master}"

if [[ -d "${LOCAL_PROJECT_DIR}/frontend/src" ]]; then
  PROJECT_DIR="${LOCAL_PROJECT_DIR}"
fi

MAIN_FILE="${PROJECT_DIR}/frontend/src/main.jsx"
CSS_FILE="${PROJECT_DIR}/frontend/src/styles.css"

require_text() {
  local file="$1"
  local pattern="$2"
  local message="$3"
  if ! grep -Fq "${pattern}" "${file}"; then
    echo "FAILED: ${message}"
    echo "Missing pattern: ${pattern}"
    exit 1
  fi
}

echo "START Compare View 2.0 frontend contract"

require_text "${MAIN_FILE}" "function CompareView2" "Compare View 2.0 component is missing"
require_text "${MAIN_FILE}" "function ComparePane" "Reusable compare pane is missing"
require_text "${MAIN_FILE}" "sharedCameraState" "Synchronized camera state is missing"
require_text "${MAIN_FILE}" "setSharedCameraState" "Synchronized camera setter is missing"
require_text "${MAIN_FILE}" "[\"before\", \"До\"]" "Before mode is missing"
require_text "${MAIN_FILE}" "[\"after\", \"После\"]" "After mode is missing"
require_text "${MAIN_FILE}" "[\"compare\", \"Сравнение\"]" "Compare mode is missing"
require_text "${MAIN_FILE}" "[\"overlay\", \"Наложение\"]" "Overlay mode is missing"
require_text "${MAIN_FILE}" "Подсветить изменения" "Change highlight control is missing"
require_text "${MAIN_FILE}" "Подсветить дефекты" "Defect highlight control is missing"
require_text "${MAIN_FILE}" "changeMapData" "Change map data is not wired"
require_text "${MAIN_FILE}" "artifactMapData" "Artifact map data is not wired"
require_text "${MAIN_FILE}" "overlayOpacity" "Overlay opacity slider state is missing"
require_text "${MAIN_FILE}" "Исходная модель" "Original model pane label is missing"
require_text "${MAIN_FILE}" "Итоговая модель" "Final model pane label is missing"

require_text "${CSS_FILE}" ".compareView2" "Compare View 2.0 styles are missing"
require_text "${CSS_FILE}" ".compareViewportGrid.split" "Desktop two-pane layout is missing"
require_text "${CSS_FILE}" ".overlayControl" "Overlay slider styles are missing"
require_text "${CSS_FILE}" ".compareMetrics" "Metrics block styles are missing"
require_text "${CSS_FILE}" "@media (max-width: 620px)" "Mobile layout rule is missing"

echo "OK Compare View 2.0 frontend contract"

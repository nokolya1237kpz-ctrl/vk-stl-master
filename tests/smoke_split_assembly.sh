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
API_BASE="http://localhost:8000"
TEST_FILE="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"
OPERATIONS="analyze,print_check,repair_mesh,split_model,prepare_package"

cd "${PROJECT_DIR}"

if [[ ! -f "${TEST_FILE}" ]]; then
  echo "ERROR: test STL not found: ${TEST_FILE}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

run_case() {
  local axis="$1"
  local mode="$2"
  local label="${axis}/${mode}"

  echo "== ${label}: upload"
  local response
  response="$(curl -sS -X POST \
    -F "file=@${TEST_FILE}" \
    -F "operations=${OPERATIONS}" \
    -F "split_axis=${axis}" \
    -F "split_parts=2" \
    -F "split_mode=${mode}" \
    -F "split_engine=blender_boolean" \
    -F "connector_size_mm=4" \
    -F "connector_clearance_mm=0.25" \
    -F "connector_count=2" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"

  local job_id
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR: upload did not return job_id: ${response}" >&2
    exit 1
  fi

  local job_json=""
  local status=""
  for _ in $(seq 1 120); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 5
  done

  if [[ "${status}" != "completed" ]]; then
    echo "ERROR: ${label} status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  printf '%s' "${job_json}" | python3 -c '
import json
import sys

mode = sys.argv[1]
data = json.load(sys.stdin)
split = data.get("result", {}).get("split_model", {})
connectors = split.get("connectors") or {}
qa = connectors.get("qa") or {}
if split.get("success") is not True:
    raise SystemExit("split_model.success is not true")
if connectors.get("integrated") is True and not qa:
    raise SystemExit("integrated connectors missing qa")
if qa:
    if qa.get("connector_count") != 2:
        raise SystemExit("unexpected connector_count: {}".format(qa.get("connector_count")))
    if qa.get("minimum_clearance_mm") is None:
        raise SystemExit("minimum_clearance_mm missing")
    if qa.get("maximum_intersection_mm") is None:
        raise SystemExit("maximum_intersection_mm missing")
    if qa.get("maximum_intersection_mm") > 0.1:
        raise SystemExit("maximum_intersection too high: {}".format(qa.get("maximum_intersection_mm")))
    if qa.get("minimum_clearance_mm") < 0.05:
        raise SystemExit("minimum_clearance too low: {}".format(qa.get("minimum_clearance_mm")))
    if qa.get("assembly_check_passed") is not True:
        raise SystemExit("assembly_check_passed is not true")
print(
    "OK {}: job_id={}; minimum_clearance={}; maximum_intersection={}; assembly_check_passed={}".format(
        mode,
        data.get("job_id"),
        qa.get("minimum_clearance_mm"),
        qa.get("maximum_intersection_mm"),
        qa.get("assembly_check_passed"),
    )
)
' "${mode}"
}

echo "STL Master Split QA 3.1 assembly smoke test"
echo "Model: ${TEST_FILE}"

run_case "y" "pins"
run_case "z" "slots"

echo "Smoke test passed."

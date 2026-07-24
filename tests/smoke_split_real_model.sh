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
FORBIDDEN_FILES="improved_model.stl reduced.stl cleaned_artifacts.stl repaired.stl"

cd "${PROJECT_DIR}"

if [[ ! -f "${TEST_FILE}" ]]; then
  echo "ERROR: test STL not found: ${TEST_FILE}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

check_zip() {
  local job_id="$1"
  docker exec -i stl-master-worker python3 - "${job_id}" ${FORBIDDEN_FILES} <<'PY'
import json
import sys
import zipfile
from pathlib import Path

job_id = sys.argv[1]
forbidden = set(sys.argv[2:])
zip_path = Path("/data/results") / job_id / "result.zip"
if not zip_path.exists():
    print(json.dumps({"ok": False, "reason": "result.zip not found", "contents": []}, ensure_ascii=False))
    raise SystemExit(0)

with zipfile.ZipFile(zip_path) as zf:
    contents = zf.namelist()

extra = sorted(name for name in contents if name in forbidden)
print(json.dumps({"ok": not extra, "extra": extra, "contents": contents}, ensure_ascii=False))
PY
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

  local split_success
  split_success="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('split_model', {}).get('success')")"
  if [[ "${split_success}" != "True" ]]; then
    echo "ERROR: ${label} split_model.success=${split_success}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  local http_code
  http_code="$(curl -sS -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/jobs/${job_id}/files/split_part_1.stl")"
  if [[ "${http_code}" != "200" ]]; then
    echo "ERROR: ${label} split_part_1.stl HTTP ${http_code}, job_id=${job_id}" >&2
    exit 1
  fi

  local zip_json
  zip_json="$(check_zip "${job_id}")"
  local zip_ok
  zip_ok="$(printf '%s' "${zip_json}" | json_value "data.get('ok')")"
  if [[ "${zip_ok}" != "True" ]]; then
    echo "ERROR: ${label} ZIP contains forbidden files, job_id=${job_id}" >&2
    printf '%s\n' "${zip_json}" >&2
    exit 1
  fi

  local output_files
  output_files="$(printf '%s' "${job_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(','.join(data.get('result', {}).get('split_model', {}).get('output_files', [])))")"
  local zip_contents
  zip_contents="$(printf '%s' "${zip_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(','.join(data.get('contents', [])))")"

  echo "OK ${label}: job_id=${job_id}; parts=${output_files}; zip=${zip_contents}"
}

echo "STL Master Split 2.0 smoke test"
echo "Model: ${TEST_FILE}"

run_case "x" "simple"
run_case "y" "pins"
run_case "z" "slots"

echo "Smoke test passed."

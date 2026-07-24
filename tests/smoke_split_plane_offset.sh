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
REAL_MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"

cd "${PROJECT_DIR}"
mkdir -p tests/results

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "ERROR: real test STL not found: ${REAL_MODEL}" >&2
  exit 1
fi

echo "STL Master split plane offset smoke test"

run_case() {
  local axis="$1"
  local offset="$2"
  echo "START split axis=${axis} offset=${offset}mm"
  response="$(
    curl -sS -X POST \
      -F "file=@${REAL_MODEL}" \
      -F "operations=analyze,print_check,repair_mesh,split_model,prepare_package" \
      -F "split_axis=${axis}" \
      -F "split_parts=2" \
      -F "split_mode=simple" \
      -F "split_engine=blender_boolean" \
      -F "split_plane_offset_mm=${offset}" \
      ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
  )"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR: upload did not return job_id: ${response}" >&2
    exit 1
  fi

  status=""
  job_json=""
  for _ in $(seq 1 160); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${status}" != "completed" ]]; then
    echo "ERROR: split job status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  printf '%s' "${job_json}" > "tests/results/split_plane_offset_${axis}_${job_id}.json"
  printf '%s' "${job_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
split = result.get("split_model", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
expected_axis = sys.argv[1]
expected_offset = float(sys.argv[2])
checks = {
    "split.success": split.get("success") is True,
    "split.axis": split.get("split_axis") == expected_axis,
    "split.offset": abs(float(split.get("split_plane_offset_mm", 9999)) - expected_offset) < 0.001,
    "split.position": split.get("split_plane_position") is not None,
    "split_part_1": "split_part_1.stl" in generated,
    "split_part_2": "split_part_2.stl" in generated,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("split plane offset contract failed: " + ", ".join(failed))
print(json.dumps({
    "job_id": data.get("job_id"),
    "axis": split.get("split_axis"),
    "offset": split.get("split_plane_offset_mm"),
    "position": split.get("split_plane_position"),
    "output_files": split.get("output_files"),
}, ensure_ascii=False))
' "${axis}" "${offset}"

  zip_path="/data/results/${job_id}/result.zip"
  zip_contents="$(docker-compose exec -T worker python - "${zip_path}" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print("\n".join(archive.namelist()))
PY
)"
  if ! printf '%s\n' "${zip_contents}" | grep -qx "split_part_1.stl"; then
    echo "ERROR: ZIP does not contain split_part_1.stl" >&2
    printf '%s\n' "${zip_contents}" >&2
    exit 1
  fi
  if ! printf '%s\n' "${zip_contents}" | grep -qx "split_part_2.stl"; then
    echo "ERROR: ZIP does not contain split_part_2.stl" >&2
    printf '%s\n' "${zip_contents}" >&2
    exit 1
  fi
  echo "OK split axis=${axis} offset=${offset}mm job_id=${job_id}"
}

run_case x 1
run_case y 1
run_case z 1

echo "Split plane offset smoke test passed."

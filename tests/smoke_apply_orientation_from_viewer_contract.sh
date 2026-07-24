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
RESULTS_DIR="${PROJECT_DIR}/tests/results"
ORIENTATION_TRANSFORM='{"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}'

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}"

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local label="$1"
  shift
  local response job_id status job_json
  response="$(curl -sS -X POST "$@" ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR ${label}: upload did not return job_id: ${response}" >&2
    exit 1
  fi

  for _ in $(seq 1 160); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${status}" != "completed" ]]; then
    echo "ERROR ${label}: status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  printf '%s' "${job_json}"
}

zip_contents_for_job() {
  local job_id="$1"
  docker-compose exec -T worker python - "/data/results/${job_id}/result.zip" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print("\n".join(archive.namelist()))
PY
}

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "ERROR: real test STL not found: ${REAL_MODEL}" >&2
  exit 1
fi

echo "STL Master apply orientation from viewer contract smoke test"

orientation_json="$(upload_and_wait "apply_orientation" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,apply_orientation,prepare_package" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}")"
orientation_job="$(printf '%s' "${orientation_json}" | json_value "data.get('job_id')")"
printf '%s' "${orientation_json}" > "${RESULTS_DIR}/apply_orientation_from_viewer_${orientation_job}.json"

printf '%s' "${orientation_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
orientation = result.get("apply_orientation") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
rotation = orientation.get("rotation") or {}
checks = {
    "apply_orientation.success": orientation.get("success") is True,
    "rotation_x_non_zero": float(rotation.get("x") or 0) != 0,
    "final_model": result.get("final_model") == "oriented_model.stl",
    "final_download_url": bool(result.get("final_download_url")),
    "generated_files": "oriented_model.stl" in generated,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("BROKEN apply orientation viewer contract: " + ", ".join(failed))
print(
    "OK orientation:",
    "job_id={};".format(data.get("job_id")),
    "rotation_x={};".format(rotation.get("x")),
    "final_model={}".format(result.get("final_model")),
)
'

final_url="$(printf '%s' "${orientation_json}" | json_value "data.get('result', {}).get('final_download_url')")"
http_code="$(curl -sS -I "${API_BASE}${final_url}" | awk 'NR==1 {print $2}')"
if [[ "${http_code}" != "200" ]]; then
  echo "ERROR: final_download_url returned HTTP ${http_code}: ${final_url}" >&2
  exit 1
fi

chain_json="$(upload_and_wait "apply_orientation + split_model" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,apply_orientation,split_model,prepare_package" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F "split_axis=y" \
  -F "split_parts=2" \
  -F "split_mode=pins" \
  -F "split_engine=blender_boolean")"
chain_job="$(printf '%s' "${chain_json}" | json_value "data.get('job_id')")"
printf '%s' "${chain_json}" > "${RESULTS_DIR}/apply_orientation_split_from_viewer_${chain_job}.json"

printf '%s' "${chain_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
split = result.get("split_model") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
checks = {
    "apply_orientation.success": result.get("apply_orientation", {}).get("success") is True,
    "split_model.success": split.get("success") is True,
    "split_source_file": split.get("source_file") == "oriented_model.stl",
    "split_part_1": "split_part_1.stl" in generated,
    "split_part_2": "split_part_2.stl" in generated,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("BROKEN orientation to split contract: " + ", ".join(failed))
print(
    "OK orientation->split:",
    "job_id={};".format(data.get("job_id")),
    "split_source={};".format(split.get("source_file")),
    "final_model={}".format(result.get("final_model")),
)
'

zip_contents="$(zip_contents_for_job "${chain_job}")"
for required in original.stl oriented_model.stl split_part_1.stl split_part_2.stl print_report.txt manifest.json; do
  if ! printf '%s\n' "${zip_contents}" | grep -qx "${required}"; then
    echo "ERROR: ZIP missing ${required}" >&2
    printf '%s\n' "${zip_contents}" >&2
    exit 1
  fi
done

echo "ZIP contents:"
printf '%s\n' "${zip_contents}"
echo "Apply orientation from viewer contract smoke test passed."

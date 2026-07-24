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
RESULTS_DIR="${PROJECT_DIR}/tests/results"
MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}"

if [[ ! -f "${MODEL}" ]]; then
  echo "ERROR: required STL model not found: ${MODEL}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local label="$1"
  local selection="$2"
  local response job_id job_json status

  response="$(
    curl -sS -X POST \
      -F "file=@${MODEL}" \
      -F "operations=analyze,print_check,local_smoothing,prepare_package" \
      -F "local_selection=${selection}" \
      ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
  )"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR: ${label}: upload did not return job_id: ${response}" >&2
    exit 1
  fi

  for _ in $(seq 1 120); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 3
  done

  if [[ "${status}" != "completed" ]]; then
    echo "ERROR: ${label}: job status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  printf '%s' "${job_json}" > "${RESULTS_DIR}/local_smoothing_${label}_${job_id}.json"
  printf '%s\n' "${job_id}"
}

validate_success() {
  local label="$1"
  local job_id="$2"
  local expected_regions="$3"
  local job_file="${RESULTS_DIR}/local_smoothing_${label}_${job_id}.json"

  python3 - "${job_file}" "${expected_regions}" <<'PY'
import json
import sys

path = sys.argv[1]
expected_regions = int(sys.argv[2])
data = json.load(open(path))
result = data.get("result") or {}
local = result.get("local_smoothing") or {}
if not local.get("success"):
    raise SystemExit(f"BROKEN expected local_smoothing success: {json.dumps(local, ensure_ascii=False)}")
generated = {item.get("name") for item in result.get("generated_files", [])}
checks = {
    "output_file": local.get("output_file") == "local_smoothed.stl",
    "final_model": result.get("final_model") == "local_smoothed.stl",
    "generated_files": "local_smoothed.stl" in generated,
    "change_map": bool((result.get("change_map") or {}).get("available")),
    "selected_regions": int(local.get("selected_regions") or 0) == expected_regions,
    "selected_vertices": int(local.get("selected_vertices") or 0) >= 50,
    "changed_vertices": int(local.get("changed_vertices") or 0) > 0,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("BROKEN local_smoothing success contract: " + ", ".join(failed))
print(json.dumps(local, ensure_ascii=False, indent=2))
PY

  local final_url
  final_url="$(python3 - "${job_file}" <<'PY'
import json
import sys
print((json.load(open(sys.argv[1])).get("result") or {}).get("final_download_url") or "")
PY
)"
  local http_code
  http_code="$(curl -sS -I "${API_BASE}${final_url}" | awk 'NR==1 {print $2}')"
  if [[ "${http_code}" != "200" ]]; then
    echo "ERROR: ${label}: final_download_url returned HTTP ${http_code}: ${final_url}" >&2
    exit 1
  fi

  local zip_contents
  zip_contents="$(docker exec -i stl-master-worker python - "/data/results/${job_id}/result.zip" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    print("\n".join(sorted(archive.namelist())))
PY
)"
  for required in local_smoothed.stl change_map.json; do
    if ! printf '%s\n' "${zip_contents}" | grep -qx "${required}"; then
      echo "ERROR: ${label}: ZIP missing ${required}" >&2
      printf '%s\n' "${zip_contents}" >&2
      exit 1
    fi
  done
  printf '%s\n' "${zip_contents}" > /tmp/local_smoothing_zip.txt

  python3 - "${job_file}" /tmp/local_smoothing_zip.txt <<'PY'
import json
import sys

job = json.load(open(sys.argv[1]))
zip_names = {line.strip() for line in open(sys.argv[2]) if line.strip()}
generated = {item.get("name") for item in (job.get("result") or {}).get("generated_files", [])}
missing = sorted(generated - zip_names)
allowed_zip_only = {"manifest.json"}
extra = sorted(zip_names - generated - allowed_zip_only)
if missing or extra:
    raise SystemExit(f"BROKEN generated_files/ZIP mismatch missing={missing} extra={extra}")
PY
}

validate_too_small_failure() {
  local label="$1"
  local job_id="$2"
  local job_file="${RESULTS_DIR}/local_smoothing_${label}_${job_id}.json"

  python3 - "${job_file}" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
local = result.get("local_smoothing") or {}
if local.get("success"):
    raise SystemExit("BROKEN expected controlled failure for too small selection")
reason = local.get("reason") or ""
if "слишком маленькая" not in reason:
    raise SystemExit(f"BROKEN too-small reason: {reason}")
generated = {item.get("name") for item in result.get("generated_files", [])}
if "local_smoothed.stl" in generated or result.get("final_model") == "local_smoothed.stl":
    raise SystemExit("BROKEN too-small failure created final local file")
print(json.dumps(local, ensure_ascii=False, indent=2))
PY
}

echo "STL Master Local Smoothing 2.0 smoke test"

SPHERE_SELECTION='{"type":"sphere","center":[23.53,50.14,6.85],"radius_mm":5,"strength":"light"}'
SPHERES_SELECTION='{"type":"spheres","regions":[{"center":[23.53,50.14,6.85],"radius_mm":5},{"center":[24.10,46.30,13.64],"radius_mm":5},{"center":[40.78,77.93,22.85],"radius_mm":5}],"strength":"balanced"}'
SMALL_SELECTION='{"type":"spheres","regions":[{"center":[46.45,100.03,37.78],"radius_mm":1}],"strength":"light"}'

echo "A: legacy sphere payload"
job_a="$(upload_and_wait "sphere" "${SPHERE_SELECTION}")"
validate_success "sphere" "${job_a}" 1

echo "B: multi-region spheres payload"
job_b="$(upload_and_wait "spheres" "${SPHERES_SELECTION}")"
validate_success "spheres" "${job_b}" 3

echo "C: too small selection controlled failure"
job_c="$(upload_and_wait "too_small" "${SMALL_SELECTION}")"
validate_too_small_failure "too_small" "${job_c}"

echo "Local Smoothing 2.0 smoke test passed."

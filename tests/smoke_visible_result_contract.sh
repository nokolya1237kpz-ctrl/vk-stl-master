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
CLEAN_MODEL="${PROJECT_DIR}/test-data/clean_visible_contract_box.stl"
REAL_MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}" "${PROJECT_DIR}/test-data"

cat > "${CLEAN_MODEL}" <<'STL'
solid clean_box
facet normal 0 0 -1
 outer loop
  vertex -10 -10 -10
  vertex 10 -10 -10
  vertex 10 10 -10
 endloop
endfacet
facet normal 0 0 -1
 outer loop
  vertex -10 -10 -10
  vertex 10 10 -10
  vertex -10 10 -10
 endloop
endfacet
facet normal 0 0 1
 outer loop
  vertex -10 -10 10
  vertex 10 10 10
  vertex 10 -10 10
 endloop
endfacet
facet normal 0 0 1
 outer loop
  vertex -10 -10 10
  vertex -10 10 10
  vertex 10 10 10
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex -10 -10 -10
  vertex -10 -10 10
  vertex 10 -10 10
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex -10 -10 -10
  vertex 10 -10 10
  vertex 10 -10 -10
 endloop
endfacet
facet normal 0 1 0
 outer loop
  vertex -10 10 -10
  vertex 10 10 10
  vertex -10 10 10
 endloop
endfacet
facet normal 0 1 0
 outer loop
  vertex -10 10 -10
  vertex 10 10 -10
  vertex 10 10 10
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex -10 -10 -10
  vertex -10 10 10
  vertex -10 -10 10
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex -10 -10 -10
  vertex -10 10 -10
  vertex -10 10 10
 endloop
endfacet
facet normal 1 0 0
 outer loop
  vertex 10 -10 -10
  vertex 10 -10 10
  vertex 10 10 10
 endloop
endfacet
facet normal 1 0 0
 outer loop
  vertex 10 -10 -10
  vertex 10 10 10
  vertex 10 10 -10
 endloop
endfacet
endsolid clean_box
STL

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "BROKEN missing real test model: ${REAL_MODEL}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local model="$1"
  shift
  local response job_id job_json status
  response="$(curl -sS -X POST -F "file=@${model}" "$@" ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "BROKEN upload did not return job_id: ${response}" >&2
    exit 1
  fi
  for _ in $(seq 1 180); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 2
  done
  printf '%s' "${job_json}" > "${RESULTS_DIR}/visible_result_${job_id}.json"
  printf '%s:%s\n' "${job_id}" "${RESULTS_DIR}/visible_result_${job_id}.json"
}

zip_contents() {
  local job_id="$1"
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile
zip_path = Path("/data/results") / sys.argv[1] / "result.zip"
with ZipFile(zip_path) as archive:
    print("\n".join(archive.namelist()))
PY
}

assert_head_200() {
  local url="$1"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' -I "${API_BASE}${url}")"
  if [[ "${code}" != "200" ]]; then
    echo "BROKEN ${url} returned ${code}" >&2
    exit 1
  fi
}

echo "STL Master visible result contract smoke test"

case_repair="$(upload_and_wait "${CLEAN_MODEL}" \
  -F 'operations=analyze,print_check,model_improvement,prepare_package')"
repair_job="${case_repair%%:*}"
repair_json="${case_repair#*:}"
python3 - "${repair_json}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
repair = result.get("print_repair") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN print_repair status={data.get('status')}")
if repair.get("success") is not False:
    raise SystemExit(f"BROKEN clean print_repair should be controlled no-op: {repair}")
if repair.get("visible_result", {}).get("created") is not False:
    raise SystemExit("BROKEN print_repair visible_result.created must be false")
if "repaired_model.stl" in generated or result.get("final_model") == "repaired_model.stl":
    raise SystemExit("BROKEN clean print_repair exposed repaired_model.stl")
print("OK print_repair no visible result")
PY
if zip_contents "${repair_job}" | grep -qx 'repaired_model.stl'; then
  echo "BROKEN clean print_repair ZIP contains repaired_model.stl" >&2
  exit 1
fi

case_surface="$(upload_and_wait "${REAL_MODEL}" \
  -F 'operations=analyze,print_check,surface_recovery,prepare_package')"
surface_job="${case_surface%%:*}"
surface_json="${case_surface#*:}"
python3 - "${surface_json}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
surface = result.get("surface_recovery") or {}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN surface status={data.get('status')}")
if surface.get("success") is not False:
    raise SystemExit(f"BROKEN Geely surface_recovery should be controlled no-op: {surface}")
if surface.get("visible_result", {}).get("created") is not False:
    raise SystemExit("BROKEN surface visible_result.created must be false")
if result.get("final_model") == "surface_recovered.stl":
    raise SystemExit("BROKEN surface_recovered.stl became final_model")
print("OK surface_recovery no visible result")
PY

case_auto="$(upload_and_wait "${REAL_MODEL}" \
  -F 'operations=analyze,print_check,auto_orientation,prepare_package' \
  -F 'auto_orientation=true' \
  -F 'orientation_priority=supports')"
auto_job="${case_auto%%:*}"
auto_json="${case_auto#*:}"
python3 - "${auto_json}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
auto = result.get("auto_orientation") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN auto status={data.get('status')}")
if auto.get("selected_candidate") == "original":
    if auto.get("no_change_needed") is not True:
        raise SystemExit("BROKEN auto original candidate must set no_change_needed=true")
    if auto.get("output_file") or "oriented_auto.stl" in generated:
        raise SystemExit("BROKEN auto no-change exposed oriented_auto.stl")
else:
    if auto.get("output_file") != "oriented_auto.stl":
        raise SystemExit("BROKEN auto changed orientation without oriented_auto.stl")
print("OK auto_orientation visible contract")
PY
auto_final_url="$(python3 - "${auto_json}" <<'PY'
import json, sys
print((json.load(open(sys.argv[1])).get("result") or {}).get("final_download_url") or "")
PY
)"
assert_head_200 "${auto_final_url}"

case_apply_noop="$(upload_and_wait "${CLEAN_MODEL}" \
  -F 'operations=analyze,print_check,apply_orientation,prepare_package' \
  -F 'apply_orientation=true' \
  -F 'orientation_transform={"rotation_x":0,"rotation_y":0,"rotation_z":0,"translate_to_floor":false}')"
apply_noop_json="${case_apply_noop#*:}"
python3 - "${apply_noop_json}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
orientation = result.get("apply_orientation") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if orientation.get("success") is not False:
    raise SystemExit(f"BROKEN no-op apply_orientation should fail: {orientation}")
if orientation.get("reason") != "Ориентация не изменена.":
    raise SystemExit(f"BROKEN apply no-op reason={orientation.get('reason')}")
if orientation.get("visible_result", {}).get("created") is not False:
    raise SystemExit("BROKEN apply no-op visible_result.created must be false")
if "oriented_model.stl" in generated or result.get("final_model") == "oriented_model.stl":
    raise SystemExit("BROKEN apply no-op exposed oriented_model.stl")
print("OK apply_orientation no-op")
PY

case_apply_rotate="$(upload_and_wait "${CLEAN_MODEL}" \
  -F 'operations=analyze,print_check,apply_orientation,prepare_package' \
  -F 'apply_orientation=true' \
  -F 'orientation_transform={"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}')"
apply_rotate_job="${case_apply_rotate%%:*}"
apply_rotate_json="${case_apply_rotate#*:}"
python3 - "${apply_rotate_json}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result") or {}
orientation = result.get("apply_orientation") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if orientation.get("success") is not True:
    raise SystemExit(f"BROKEN apply rotation failed: {orientation}")
if orientation.get("output_file") != "oriented_model.stl":
    raise SystemExit("BROKEN apply rotation did not create oriented_model.stl")
if orientation.get("visible_result", {}).get("created") is not True:
    raise SystemExit("BROKEN apply rotation visible_result.created must be true")
if result.get("final_model") != "oriented_model.stl" or "oriented_model.stl" not in generated:
    raise SystemExit("BROKEN apply rotation final/generated contract")
print("OK apply_orientation rotation")
PY
rotate_url="$(python3 - "${apply_rotate_json}" <<'PY'
import json, sys
print((json.load(open(sys.argv[1])).get("result") or {}).get("final_download_url") or "")
PY
)"
assert_head_200 "${rotate_url}"
if ! zip_contents "${apply_rotate_job}" | grep -qx 'oriented_model.stl'; then
  echo "BROKEN apply rotation ZIP missing oriented_model.stl" >&2
  exit 1
fi

echo "Visible result contract smoke test passed."

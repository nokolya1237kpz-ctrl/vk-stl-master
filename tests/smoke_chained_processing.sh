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
ORIENTATION_TRANSFORM='{"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}'

cd "${PROJECT_DIR}"
mkdir -p tests/results

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local label="$1"
  shift
  local response job_id job_json status
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
    echo "ERROR ${label}: job status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi
  printf '%s\n' "${job_json}"
}

assert_head_stl() {
  local url="$1"
  local headers http_code content_type
  headers="$(curl -sS -I "${API_BASE}${url}")"
  http_code="$(printf '%s\n' "${headers}" | awk 'NR==1 {print $2}')"
  content_type="$(printf '%s\n' "${headers}" | awk 'BEGIN{IGNORECASE=1} /^content-type:/ {print $2}' | tr -d '\r')"
  if [[ "${http_code}" != "200" ]]; then
    echo "ERROR: ${url} returned HTTP ${http_code}" >&2
    printf '%s\n' "${headers}" >&2
    exit 1
  fi
  if [[ "${content_type}" != "model/stl" && "${content_type}" != "application/octet-stream" ]]; then
    echo "ERROR: unexpected content-type for ${url}: ${content_type}" >&2
    printf '%s\n' "${headers}" >&2
    exit 1
  fi
}

zip_contents_for_job() {
  local job_id="$1"
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
import zipfile

zip_path = f"/data/results/{sys.argv[1]}/result.zip"
with zipfile.ZipFile(zip_path) as archive:
    print("\n".join(archive.namelist()))
PY
}

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "ERROR: real test STL not found: ${REAL_MODEL}" >&2
  exit 1
fi

echo "STL Master chained processing smoke test"

case_a_json="$(upload_and_wait "A orientation+split" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,apply_orientation,split_model,prepare_package" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F "split_axis=y" \
  -F "split_parts=2" \
  -F "split_mode=pins" \
  -F "split_engine=blender_boolean")"
case_a_job="$(printf '%s' "${case_a_json}" | json_value "data.get('job_id')")"
printf '%s' "${case_a_json}" > "tests/results/chained_a_${case_a_job}.json"
printf '%s' "${case_a_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
split = result.get("split_model", {})
checks = {
    "apply_orientation.success": result.get("apply_orientation", {}).get("success") is True,
    "oriented_model.generated": "oriented_model.stl" in generated,
    "split.success": split.get("success") is True,
    "split.source.oriented": split.get("source_file") == "oriented_model.stl",
    "split_part_1.generated": "split_part_1.stl" in generated,
    "split_part_2.generated": "split_part_2.stl" in generated,
    "final_model.known": result.get("final_model") in {"oriented_model.stl", "split_part_1.stl", "original.stl"},
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("case A failed: " + ", ".join(failed))
print("OK A orientation+split:", "job_id={};".format(data.get("job_id")), "split_source={};".format(split.get("source_file")), "final_model={}".format(result.get("final_model")))
'
case_a_zip="$(zip_contents_for_job "${case_a_job}")"
for required in original.stl oriented_model.stl split_part_1.stl split_part_2.stl print_report.txt manifest.json; do
  printf '%s\n' "${case_a_zip}" | grep -qx "${required}" || { echo "ERROR A: ZIP missing ${required}" >&2; exit 1; }
done
for forbidden in repaired_model.stl reduced.stl cleaned_artifacts.stl repaired.stl; do
  if printf '%s\n' "${case_a_zip}" | grep -qx "${forbidden}"; then
    echo "ERROR A: ZIP contains unexpected ${forbidden}" >&2
    printf '%s\n' "${case_a_zip}" >&2
    exit 1
  fi
done

case_b_json="$(upload_and_wait "B repair+orientation" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,model_improvement,apply_orientation,prepare_package" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F "model_improvement_strength=balanced")"
case_b_job="$(printf '%s' "${case_b_json}" | json_value "data.get('job_id')")"
printf '%s' "${case_b_json}" > "tests/results/chained_b_${case_b_job}.json"
printf '%s' "${case_b_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
orientation = result.get("apply_orientation", {})
repair = result.get("print_repair", {})
expected_input = "repaired_model.stl" if repair.get("success") else "original.stl"
checks = {
    "orientation.success": orientation.get("success") is True,
    "orientation.input.expected": orientation.get("input_file") == expected_input,
    "oriented_model.generated": "oriented_model.stl" in generated,
    "final_model.oriented": result.get("final_model") == "oriented_model.stl",
    "final_download_url": bool(result.get("final_download_url")),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("case B failed: " + ", ".join(failed))
print("OK B repair+orientation:", "job_id={};".format(data.get("job_id")), "orientation_input={};".format(orientation.get("input_file")), "final_model={}".format(result.get("final_model")))
'
case_b_final="$(printf '%s' "${case_b_json}" | json_value "data.get('result', {}).get('final_download_url')")"
assert_head_stl "${case_b_final}"
case_b_zip="$(zip_contents_for_job "${case_b_job}")"
for required in original.stl repair_report.json oriented_model.stl print_report.txt manifest.json; do
  printf '%s\n' "${case_b_zip}" | grep -qx "${required}" || { echo "ERROR B: ZIP missing ${required}" >&2; exit 1; }
done
case_b_repair_success="$(printf '%s' "${case_b_json}" | json_value "data.get('result', {}).get('print_repair', {}).get('success')")"
if [[ "${case_b_repair_success}" == "True" ]]; then
  printf '%s\n' "${case_b_zip}" | grep -qx "repaired_model.stl" || { echo "ERROR B: ZIP missing repaired_model.stl after successful repair" >&2; exit 1; }
else
  if printf '%s\n' "${case_b_zip}" | grep -qx "repaired_model.stl"; then
    echo "ERROR B: ZIP contains repaired_model.stl after no-op repair" >&2
    printf '%s\n' "${case_b_zip}" >&2
    exit 1
  fi
fi
for forbidden in split_part_1.stl reduced.stl cleaned_artifacts.stl; do
  if printf '%s\n' "${case_b_zip}" | grep -qx "${forbidden}"; then
    echo "ERROR B: ZIP contains unexpected ${forbidden}" >&2
    printf '%s\n' "${case_b_zip}" >&2
    exit 1
  fi
done

case_c_json="$(upload_and_wait "C cleanup+orientation" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,remove_ai_artifacts,apply_orientation,prepare_package" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F "artifact_cleanup_strength=balanced")"
case_c_job="$(printf '%s' "${case_c_json}" | json_value "data.get('job_id')")"
printf '%s' "${case_c_json}" > "tests/results/chained_c_${case_c_job}.json"
printf '%s' "${case_c_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
cleanup = result.get("remove_ai_artifacts", {})
orientation = result.get("apply_orientation", {})
checks = {
    "orientation.success": orientation.get("success") is True,
    "oriented_model.generated": "oriented_model.stl" in generated,
    "final_model.oriented": result.get("final_model") == "oriented_model.stl",
    "final_download_url": bool(result.get("final_download_url")),
}
if cleanup.get("success") is True:
    checks["cleanup.generated"] = "cleaned_artifacts.stl" in generated
    checks["orientation.input.cleaned"] = orientation.get("input_file") == "cleaned_artifacts.stl"
else:
    checks["cleanup.controlled_failure"] = cleanup.get("success") is False
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("case C failed: " + ", ".join(failed))
print("OK C cleanup+orientation:", "job_id={};".format(data.get("job_id")), "cleanup_success={};".format(cleanup.get("success")), "orientation_input={};".format(orientation.get("input_file")), "final_model={}".format(result.get("final_model")))
'
case_c_final="$(printf '%s' "${case_c_json}" | json_value "data.get('result', {}).get('final_download_url')")"
assert_head_stl "${case_c_final}"
case_c_zip="$(zip_contents_for_job "${case_c_job}")"
for required in original.stl oriented_model.stl print_report.txt manifest.json; do
  printf '%s\n' "${case_c_zip}" | grep -qx "${required}" || { echo "ERROR C: ZIP missing ${required}" >&2; exit 1; }
done
if printf '%s' "${case_c_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["remove_ai_artifacts"].get("success"))' | grep -qx "True"; then
  printf '%s\n' "${case_c_zip}" | grep -qx "cleaned_artifacts.stl" || { echo "ERROR C: ZIP missing cleaned_artifacts.stl" >&2; exit 1; }
fi
for forbidden in repaired_model.stl reduced.stl split_part_1.stl repaired.stl; do
  if printf '%s\n' "${case_c_zip}" | grep -qx "${forbidden}"; then
    echo "ERROR C: ZIP contains unexpected ${forbidden}" >&2
    printf '%s\n' "${case_c_zip}" >&2
    exit 1
  fi
done

case_d_json="$(upload_and_wait "D reduce+orientation" \
  -F "file=@${REAL_MODEL}" \
  -F "operations=analyze,print_check,reduce_polygons,apply_orientation,prepare_package" \
  -F "reduction_percent=50" \
  -F "apply_orientation=true" \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}")"
case_d_job="$(printf '%s' "${case_d_json}" | json_value "data.get('job_id')")"
printf '%s' "${case_d_json}" > "tests/results/chained_d_${case_d_job}.json"
printf '%s' "${case_d_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
reduction = result.get("reduce_polygons", {})
orientation = result.get("apply_orientation", {})
checks = {
    "reduction.success": reduction.get("success") is True,
    "reduced.generated": "reduced.stl" in generated,
    "orientation.success": orientation.get("success") is True,
    "orientation.input.reduced": orientation.get("input_file") == "reduced.stl",
    "oriented_model.generated": "oriented_model.stl" in generated,
    "final_model.oriented": result.get("final_model") == "oriented_model.stl",
    "final_download_url": bool(result.get("final_download_url")),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("case D failed: " + ", ".join(failed))
print("OK D reduce+orientation:", "job_id={};".format(data.get("job_id")), "orientation_input={};".format(orientation.get("input_file")), "final_model={}".format(result.get("final_model")))
'
case_d_final="$(printf '%s' "${case_d_json}" | json_value "data.get('result', {}).get('final_download_url')")"
assert_head_stl "${case_d_final}"
case_d_zip="$(zip_contents_for_job "${case_d_job}")"
for required in original.stl reduced.stl oriented_model.stl print_report.txt manifest.json; do
  printf '%s\n' "${case_d_zip}" | grep -qx "${required}" || { echo "ERROR D: ZIP missing ${required}" >&2; exit 1; }
done
for forbidden in repaired_model.stl cleaned_artifacts.stl split_part_1.stl repaired.stl; do
  if printf '%s\n' "${case_d_zip}" | grep -qx "${forbidden}"; then
    echo "ERROR D: ZIP contains unexpected ${forbidden}" >&2
    printf '%s\n' "${case_d_zip}" >&2
    exit 1
  fi
done

echo "ZIP A:"
printf '%s\n' "${case_a_zip}"
echo "ZIP B:"
printf '%s\n' "${case_b_zip}"
echo "ZIP C:"
printf '%s\n' "${case_c_zip}"
echo "ZIP D:"
printf '%s\n' "${case_d_zip}"
echo "Chained processing smoke test passed."

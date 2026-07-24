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
MODEL="${PROJECT_DIR}/test-data/cube_with_spikes.stl"
MODE="pins"

cd "${PROJECT_DIR}"
mkdir -p tests/results

echo "STL Master Split Connectors 4.0 pins smoke test"

response="$(
  curl -sS -X POST \
    -F "file=@${MODEL}" \
    -F "operations=analyze,print_check,split_model,prepare_package" \
    -F "split_axis=z" \
    -F "split_parts=2" \
    -F "split_mode=${MODE}" \
    -F "split_engine=blender_boolean" \
    -F "connector_size_mm=4" \
    -F "connector_depth_mm=6" \
    -F "connector_clearance_mm=0.25" \
    -F "connector_count=2" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
)"
job_id="$(printf '%s' "${response}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("job_id",""))')"
[[ -n "${job_id}" ]] || { echo "upload did not return job_id: ${response}" >&2; exit 1; }

status=""
job_json=""
for _ in $(seq 1 120); do
  job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
  status="$(printf '%s' "${job_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
  [[ "${status}" == "completed" || "${status}" == "failed" ]] && break
  sleep 2
done
[[ "${status}" == "completed" ]] || { echo "job status=${status}" >&2; printf '%s\n' "${job_json}" >&2; exit 1; }

printf '%s' "${job_json}" > "tests/results/split_pins_${job_id}.json"
JOB_JSON="${job_json}" MODE="${MODE}" python3 <<'PY'
import json, os
data = json.loads(os.environ["JOB_JSON"])
mode = os.environ["MODE"]
result = data.get("result", {})
split = result.get("split_model", {})
connectors = split.get("connectors") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
checks = [
    split.get("success") is True,
    split.get("split_mode") == mode,
    "split_part_1.stl" in generated,
    "split_part_2.stl" in generated,
    "connector_report.json" in generated,
    connectors.get("type") == mode,
    connectors.get("integrated") is True or bool(connectors.get("reason")),
]
if not all(checks):
    raise SystemExit("pins connector contract failed")
print(json.dumps({"job_id": data.get("job_id"), "integrated": connectors.get("integrated"), "qa": connectors.get("qa"), "reason": connectors.get("reason")}, ensure_ascii=False))
PY

zip_contents="$(docker exec -i stl-master-worker python - "/data/results/${job_id}/result.zip" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    print("\n".join(archive.namelist()))
PY
)"
printf '%s\n' "${zip_contents}" | grep -qx "connector_report.json" || { echo "ZIP missing connector_report.json" >&2; exit 1; }

echo "Split pins smoke test passed."

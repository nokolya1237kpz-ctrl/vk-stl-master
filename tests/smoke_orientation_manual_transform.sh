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

echo "STL Master manual orientation transform smoke test"

orientation_transform='{"rotation_x_deg":37,"rotation_y_deg":15,"rotation_z_deg":-5,"translate_to_floor":true,"translate_x_mm":10,"translate_z_mm":-5}'
response="$(
  curl -sS -X POST \
    -F "file=@${REAL_MODEL}" \
    -F "operations=analyze,print_check,prepare_package,apply_orientation" \
    -F "apply_orientation=true" \
    -F "orientation_transform=${orientation_transform}" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
)"
job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
if [[ -z "${job_id}" ]]; then
  echo "ERROR: upload did not return job_id: ${response}" >&2
  exit 1
fi

status=""
job_json=""
for _ in $(seq 1 120); do
  job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
  status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
  if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
    break
  fi
  sleep 3
done

if [[ "${status}" != "completed" ]]; then
  echo "ERROR: job status=${status}, job_id=${job_id}" >&2
  printf '%s\n' "${job_json}" >&2
  exit 1
fi

printf '%s' "${job_json}" > "tests/results/orientation_manual_transform_${job_id}.json"

printf '%s' "${job_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
orientation = result.get("apply_orientation", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
rotation = orientation.get("rotation") or {}
checks = {
    "apply_orientation.success": orientation.get("success") is True,
    "rotation_x_deg": abs(float(rotation.get("x", 0)) - 37) < 0.001,
    "rotation_y_deg": abs(float(rotation.get("y", 0)) - 15) < 0.001,
    "rotation_z_deg": abs(float(rotation.get("z", 0)) + 5) < 0.001,
    "translate_x_mm": abs(float(orientation.get("translate_x_mm", 0)) - 10) < 0.001,
    "translate_z_mm": abs(float(orientation.get("translate_z_mm", 0)) + 5) < 0.001,
    "oriented_model.generated": "oriented_model.stl" in generated,
    "final_model.oriented": result.get("final_model") == "oriented_model.stl",
    "final_download_url": bool(result.get("final_download_url")),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("manual orientation contract failed: " + ", ".join(failed))
print(json.dumps({
    "job_id": data.get("job_id"),
    "rotation": rotation,
    "translate_x_mm": orientation.get("translate_x_mm"),
    "translate_z_mm": orientation.get("translate_z_mm"),
    "final_model": result.get("final_model"),
    "final_download_url": result.get("final_download_url"),
}, ensure_ascii=False))
'

final_url="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('final_download_url')")"
headers="$(curl -sS -I "${API_BASE}${final_url}")"
http_code="$(printf '%s\n' "${headers}" | awk 'NR==1 {print $2}')"
if [[ "${http_code}" != "200" ]]; then
  echo "ERROR: ${final_url} returned HTTP ${http_code}" >&2
  printf '%s\n' "${headers}" >&2
  exit 1
fi

echo "Manual orientation transform smoke test passed."

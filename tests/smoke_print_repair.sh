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
OPERATIONS="analyze,print_check,model_improvement,prepare_package"

cd "${PROJECT_DIR}"

if [[ ! -f "${TEST_FILE}" ]]; then
  echo "ERROR: test STL not found: ${TEST_FILE}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

echo "STL Master Print Repair 2.0 smoke test"
echo "Model: ${TEST_FILE}"

response="$(curl -sS -X POST \
  -F "file=@${TEST_FILE}" \
  -F "operations=${OPERATIONS}" \
  -F "model_improvement_strength=balanced" \
  ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"

job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
if [[ -z "${job_id}" ]]; then
  echo "ERROR: upload did not return job_id: ${response}" >&2
  exit 1
fi

job_json=""
status=""
for _ in $(seq 1 120); do
  job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
  status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
  if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
    break
  fi
  sleep 5
done

if [[ "${status}" != "completed" ]]; then
  echo "ERROR: job status=${status}, job_id=${job_id}" >&2
  printf '%s\n' "${job_json}" >&2
  exit 1
fi

repair_success="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('print_repair', {}).get('success')")"
visible_created="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('print_repair', {}).get('visible_result', {}).get('created')")"

after_url="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('after_download_url')")"
if [[ -z "${after_url}" ]]; then
  echo "ERROR: after_download_url is empty, job_id=${job_id}" >&2
  exit 1
fi

zip_json="$(docker-compose exec -T worker python3 - "${job_id}" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

job_id = sys.argv[1]
result_dir = Path("/data/results") / job_id
zip_path = result_dir / "result.zip"
model_path = result_dir / "repaired_model.stl"
info = {
    "zip_exists": zip_path.exists(),
    "model_exists": model_path.exists(),
    "model_size": model_path.stat().st_size if model_path.exists() else 0,
    "contents": [],
}
if zip_path.exists():
    with zipfile.ZipFile(zip_path) as zf:
        info["contents"] = zf.namelist()
print(json.dumps(info, ensure_ascii=False))
PY
)"

zip_has_model="$(printf '%s' "${zip_json}" | json_value "'repaired_model.stl' in data.get('contents', [])")"
model_size="$(printf '%s' "${zip_json}" | json_value "data.get('model_size')")"
if [[ "${repair_success}" == "True" ]]; then
  if [[ "${visible_created}" != "True" ]]; then
    echo "ERROR: print_repair success without visible result, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi
  http_code="$(curl -sS -o /dev/null -w "%{http_code}" "${API_BASE}${after_url}")"
  if [[ "${http_code}" != "200" ]]; then
    echo "ERROR: after preview URL returned HTTP ${http_code}: ${after_url}" >&2
    exit 1
  fi
  file_http_code="$(curl -sS -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/jobs/${job_id}/files/repaired_model.stl")"
  if [[ "${file_http_code}" != "200" ]]; then
    echo "ERROR: repaired_model.stl returned HTTP ${file_http_code}" >&2
    exit 1
  fi
  if [[ "${zip_has_model}" != "True" || "${model_size}" == "0" ]]; then
    echo "ERROR: ZIP/model validation failed, job_id=${job_id}" >&2
    printf '%s\n' "${zip_json}" >&2
    exit 1
  fi
else
  if [[ "${visible_created}" != "False" ]]; then
    echo "ERROR: print_repair controlled no-op must have visible_result.created=false, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi
  if [[ "${zip_has_model}" == "True" || "${model_size}" != "0" ]]; then
    echo "ERROR: print_repair no-op exposed repaired_model.stl, job_id=${job_id}" >&2
    printf '%s\n' "${zip_json}" >&2
    exit 1
  fi
fi

print_repair="$(printf '%s' "${job_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get('result', {}).get('print_repair', {}), ensure_ascii=False, indent=2))")"
printf '%s\n' "OK print_repair: job_id=${job_id}; success=${repair_success}; visible_created=${visible_created}; after_url=${after_url}; repaired_model_size=${model_size}"
printf '%s\n' "${print_repair}"
echo "Smoke test passed."

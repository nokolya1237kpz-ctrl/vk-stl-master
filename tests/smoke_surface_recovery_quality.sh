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
MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"
RESULTS_DIR="${PROJECT_DIR}/tests/results"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}"

if [[ ! -f "${MODEL}" ]]; then
  echo "BROKEN missing test model: ${MODEL}" >&2
  exit 1
fi

echo "STL Master surface recovery quality smoke test"

response="$(
  curl -sS -X POST \
    -F "file=@${MODEL}" \
    -F 'operations=analyze,print_check,surface_recovery,prepare_package' \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
)"
job_id="$(printf '%s' "${response}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("job_id",""))')"
if [[ -z "${job_id}" ]]; then
  echo "BROKEN upload did not return job_id: ${response}" >&2
  exit 1
fi

job_json=""
status=""
for _ in $(seq 1 180); do
  job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
  status="$(printf '%s' "${job_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))')"
  if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
    break
  fi
  sleep 2
done

json_path="${RESULTS_DIR}/surface_recovery_quality_${job_id}.json"
printf '%s' "${job_json}" > "${json_path}"

python3 - "${json_path}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
surface = result.get("surface_recovery") or {}

if data.get("status") != "completed":
    raise SystemExit(f"BROKEN job status={data.get('status')}")
if not surface:
    raise SystemExit("BROKEN result.surface_recovery is missing")

before = surface.get("artifact_quality_before") or {}
after = surface.get("artifact_quality_after") or {}
delta = surface.get("delta") or {}

if surface.get("success"):
    score_ok = int(delta.get("health_score_delta") or 0) > 0
    penalty_ok = int(delta.get("artifact_penalty_delta") or 0) < 0
    if not (score_ok or penalty_ok):
        raise SystemExit(
            "BROKEN surface_recovery success without measurable QA improvement: "
            f"delta={delta}"
        )
else:
    if surface.get("output_file"):
        raise SystemExit("BROKEN failed surface_recovery must not expose output_file")
    if result.get("final_model") == "surface_recovered.stl":
        raise SystemExit("BROKEN failed surface_recovery must not become final_model")

print("QA before:")
print(json.dumps({
    "health_score": surface.get("health_score_before"),
    "artifact_quality": before,
}, ensure_ascii=False, indent=2))
print("QA after:")
print(json.dumps({
    "health_score": surface.get("health_score_after"),
    "artifact_quality": after,
}, ensure_ascii=False, indent=2))
print("Delta:")
print(json.dumps(delta, ensure_ascii=False, indent=2))
print("Result:")
print(json.dumps({
    "success": surface.get("success"),
    "reason": surface.get("reason"),
    "output_file": surface.get("output_file"),
}, ensure_ascii=False, indent=2))
PY

echo "Surface recovery quality smoke test passed. job_id=${job_id}"

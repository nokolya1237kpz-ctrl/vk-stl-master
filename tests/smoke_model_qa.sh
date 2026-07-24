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
REAL_FILE="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"
DAMAGED_FILE="${PROJECT_DIR}/test-data/damaged_model_qa.stl"
ISLAND_FILE="${PROJECT_DIR}/test-data/main_plus_far_island.stl"
ISLAND_FILE="${PROJECT_DIR}/test-data/main_plus_far_island.stl"
OPERATIONS="analyze,print_check,model_improvement,prepare_package"

cd "${PROJECT_DIR}"

if [[ ! -f "${REAL_FILE}" ]]; then
  echo "ERROR: real test STL not found: ${REAL_FILE}" >&2
  exit 1
fi

cat > "${DAMAGED_FILE}" <<'STL'
solid damaged_model_qa
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 1 1 0
      vertex 1 0 0
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 0 1 0
      vertex 1 1 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 0 1
      vertex 1 1 1
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 1 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 0
      vertex 1 1 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 1
      vertex 1 0 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 0 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 1 1
      vertex 0 1 0
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 0 1
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 1
      vertex 0 0 1
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 1
      vertex 0 0 1
    endloop
  endfacet
  facet normal 0 0 0
    outer loop
      vertex 0.5 0.5 0.5
      vertex 0.5 0.5 0.5
      vertex 0.5 0.5 0.5
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 5 5 5
      vertex 5.01 5 5
      vertex 5 5.01 5
    endloop
  endfacet
endsolid damaged_model_qa
STL


cat > "${ISLAND_FILE}" <<'STL'
solid main_plus_far_island
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 1 1 0
      vertex 1 0 0
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 0 1 0
      vertex 1 1 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 0 1
      vertex 1 1 1
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 1 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 0
      vertex 1 1 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 1
      vertex 1 0 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 0 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 1 1
      vertex 0 1 0
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 0 1
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 1
      vertex 0 0 1
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex 0 1 0
      vertex 0 1 1
      vertex 1 1 1
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex 0 1 0
      vertex 1 1 1
      vertex 1 1 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 1.2 0 0
      vertex 1.21 0 0
      vertex 1.2 0.01 0
    endloop
  endfacet
endsolid main_plus_far_island
STL

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

run_case() {
  local label="$1"
  local file_path="$2"
  local response job_id job_json status

  response="$(curl -sS -X POST \
    -F "file=@${file_path}" \
    -F "operations=${OPERATIONS}" \
    -F "model_improvement_strength=balanced" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR: upload failed for ${label}: ${response}" >&2
    exit 1
  fi

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

  local score repair qa_json repair_json
  score="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('model_qa', {}).get('health_score')")"
  repair="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('model_qa', {}).get('repair_recommended')")"
  qa_json="$(printf '%s' "${job_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get('result', {}).get('model_qa', {}), ensure_ascii=False, indent=2))")"
  repair_json="$(printf '%s' "${job_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get('result', {}).get('print_repair', {}), ensure_ascii=False, indent=2))")"
  echo "== ${label}: job_id=${job_id}; health_score=${score}; repair_recommended=${repair}"
  echo "${qa_json}"
  echo "-- print_repair"
  echo "${repair_json}"
  printf '%s' "${score}"
}

echo "STL Master Model QA smoke test"
real_score="$(run_case "real" "${REAL_FILE}" | tee /tmp/model_qa_real.out | tail -1)"
damaged_score="$(run_case "damaged" "${DAMAGED_FILE}" | tee /tmp/model_qa_damaged.out | tail -1)"
island_score="$(run_case "main_plus_far_island" "${ISLAND_FILE}" | tee /tmp/model_qa_island.out | tail -1)"

python3 - "${real_score}" "${damaged_score}" <<'PY'
import sys
real = int(float(sys.argv[1]))
damaged = int(float(sys.argv[2]))
if damaged >= real:
    raise SystemExit(f"damaged model score must be lower than real model score: real={real}, damaged={damaged}")
print(f"Score comparison OK: real={real}, damaged={damaged}")
PY

python3 - <<'PY'
import json, sys
from pathlib import Path
text = Path('/tmp/model_qa_island.out').read_text(encoding='utf-8')
marker = '-- print_repair\n'
repair = json.loads(text.split(marker, 1)[1].rsplit('\n', 1)[0])
gate = repair.get('quality_gate') or {}
if not repair.get('success'):
    raise SystemExit(f"island cleanup repair must be accepted: {json.dumps(gate, ensure_ascii=False)}")
if gate.get('islands_removed', 0) < 1 and repair.get('removed_islands', 0) < 1:
    raise SystemExit(f"expected island removal in quality gate: {json.dumps(gate, ensure_ascii=False)}")
print("Island cleanup gate OK:", json.dumps(gate, ensure_ascii=False))
PY

echo "Smoke test passed."

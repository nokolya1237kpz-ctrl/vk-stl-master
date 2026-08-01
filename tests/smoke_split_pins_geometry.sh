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

smoke_cleanup_run() {
  local api="${API_BASE:-http://localhost:8000}"
  if [[ "${SMOKE_SKIP_CLEANUP:-0}" == "1" || -z "${ADMIN_TOKEN:-}" ]]; then
    return 0
  fi
  local cleanup_response
  cleanup_response="$(curl --max-time 15 -sS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}" \
    "${api}/api/v1/admin/test-data/cleanup" || true)"
  [[ -z "${cleanup_response}" ]] && return 0
  python3 - "${cleanup_response}" <<'PY_SMOKE_CLEANUP'
import json, sys
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
API_BASE="${API_BASE:-http://localhost:8000}"
RESULT_DIR="${PROJECT_DIR}/tests/results/stage81_pins"
mkdir -p "${RESULT_DIR}"
cd "${PROJECT_DIR}"

echo "STL Master production pins geometry smoke test"

make_box() {
  local path="$1"
  local sx="$2"
  local sy="$3"
  local sz="$4"
  python3 - "$path" "$sx" "$sy" "$sz" <<'PY_BOX'
from pathlib import Path
import sys
path=Path(sys.argv[1])
sx,sy,sz=[float(v) for v in sys.argv[2:5]]
x,y,z=sx/2,sy/2,sz/2
verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
faces=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
with path.open('w', encoding='utf-8') as f:
    f.write('solid stage81_box\n')
    for a,b,c in faces:
        f.write(' facet normal 0 0 0\n  outer loop\n')
        for i in (a,b,c):
            vx,vy,vz=verts[i]
            f.write(f'   vertex {vx:.6f} {vy:.6f} {vz:.6f}\n')
        f.write('  endloop\n endfacet\n')
    f.write('endsolid stage81_box\n')
PY_BOX
}

upload_and_wait() {
  local model="$1"
  local depth="$2"
  local label="$3"
  local response job_id status job_json
  response="$(curl -sS -X POST \
    -F "file=@${model}" \
    -F "operations=analyze,print_check,split_model,prepare_package" \
    -F "split_axis=z" \
    -F "split_parts=2" \
    -F "split_mode=pins" \
    -F "split_engine=blender_boolean" \
    -F "connector_size_mm=4" \
    -F "connector_depth_mm=${depth}" \
    -F "connector_clearance_mm=0.25" \
    -F "connector_count=2" \
    "${SMOKE_UPLOAD_FIELDS[@]}" "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("job_id", ""))')"
  [[ -n "${job_id}" ]] || { echo "${label}: upload did not return job_id: ${response}" >&2; exit 1; }
  for _ in $(seq 1 120); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status", ""))')"
    [[ "${status}" == "completed" || "${status}" == "failed" ]] && break
    sleep 2
  done
  [[ "${status}" == "completed" ]] || { echo "${label}: job status=${status}" >&2; printf '%s\n' "${job_json}" >&2; exit 1; }
  printf '%s' "${job_json}" > "${RESULT_DIR}/${label}_${job_id}.json"
  printf '%s' "${job_json}"
}

valid_model="${RESULT_DIR}/box_60x40x24.stl"
thin_model="${RESULT_DIR}/plate_60x40x6.stl"
make_box "${valid_model}" 60 40 24
make_box "${thin_model}" 60 40 6

valid_json="$(upload_and_wait "${valid_model}" 6 valid_box)"
JOB_JSON="${valid_json}" python3 <<'PY_VALID'
import json, os, sys
data=json.loads(os.environ['JOB_JSON'])
s=(data.get('result') or {}).get('split_model') or {}
c=s.get('connectors') or {}
checks={
    'split_success': s.get('success') is True,
    'split_mode': s.get('split_mode') == 'pins',
    'two_parts': s.get('output_files') == ['split_part_1.stl', 'split_part_2.stl'],
    'integrated': c.get('integrated') is True,
    'connector_success': c.get('success') is True,
    'qa_passed': (c.get('qa') or {}).get('assembly_check_passed') is True,
    'clearance': (c.get('qa') or {}).get('minimum_clearance_mm') == 0.25,
}
if not all(checks.values()):
    raise SystemExit('valid pins geometry failed: '+json.dumps(checks, ensure_ascii=False))
print(json.dumps({'job_id': data.get('job_id'), 'checks': checks, 'qa': c.get('qa')}, ensure_ascii=False))
PY_VALID

thin_json="$(upload_and_wait "${thin_model}" 6 thin_plate)"
JOB_JSON="${thin_json}" python3 <<'PY_THIN'
import json, os
data=json.loads(os.environ['JOB_JSON'])
s=(data.get('result') or {}).get('split_model') or {}
c=s.get('connectors') or {}
reason=s.get('reason') or c.get('reason') or ''
checks={
    'split_failed': s.get('success') is False,
    'mode_kept': s.get('split_mode') == 'pins',
    'not_integrated': c.get('integrated') is False,
    'no_fake_parts': not s.get('output_files'),
    'clear_reason': 'штифт' in reason.lower() or 'диаметр' in reason.lower() or 'глубин' in reason.lower(),
}
if not all(checks.values()):
    raise SystemExit('thin pins failure contract failed: '+json.dumps({'checks': checks, 'reason': reason, 'split': s}, ensure_ascii=False))
print(json.dumps({'job_id': data.get('job_id'), 'checks': checks, 'reason': reason}, ensure_ascii=False))
PY_THIN

echo "Production pins geometry smoke test passed."

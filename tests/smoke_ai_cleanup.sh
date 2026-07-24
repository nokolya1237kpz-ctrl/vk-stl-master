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
SPIKE_FILE="${PROJECT_DIR}/test-data/cube_with_spikes.stl"
OPERATIONS="analyze,print_check,remove_ai_artifacts,prepare_package"

cd "${PROJECT_DIR}"

python3 - "${SPIKE_FILE}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
vertices = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
    (0.46, 0.46, 1), (0.54, 0.46, 1), (0.54, 0.54, 1), (0.46, 0.54, 1),
    (0.5, 0.5, 3.8),
]
faces = [
    (0, 2, 1), (0, 3, 2),
    (0, 1, 5), (0, 5, 4),
    (1, 2, 6), (1, 6, 5),
    (2, 3, 7), (2, 7, 6),
    (3, 0, 4), (3, 4, 7),
    (4, 5, 9), (4, 9, 8),
    (5, 6, 10), (5, 10, 9),
    (6, 7, 11), (6, 11, 10),
    (7, 4, 8), (7, 8, 11),
    (8, 9, 12), (9, 10, 12), (10, 11, 12), (11, 8, 12),
]

def normal(a, b, c):
    ax, ay, az = a
    bx, by, bz = b
    cx, cy, cz = c
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return nx, ny, nz

lines = ["solid cube_with_spikes"]
for face in faces:
    a, b, c = [vertices[index] for index in face]
    nx, ny, nz = normal(a, b, c)
    lines.append(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}")
    lines.append("    outer loop")
    for vertex in (a, b, c):
        lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
    lines.append("    endloop")
    lines.append("  endfacet")
lines.append("endsolid cube_with_spikes")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

echo "STL Master Advanced AI Cleanup smoke test"
response="$(curl -sS -X POST \
  -F "file=@${SPIKE_FILE}" \
  -F "operations=${OPERATIONS}" \
  -F "artifact_cleanup_strength=balanced" \
  ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
if [[ -z "${job_id}" ]]; then
  echo "ERROR: upload did not return job_id: ${response}" >&2
  exit 1
fi

for _ in $(seq 1 120); do
  job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
  status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
  if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
    break
  fi
  sleep 2
done

if [[ "${status}" != "completed" ]]; then
  echo "ERROR: status=${status}, job_id=${job_id}" >&2
  printf '%s\n' "${job_json}" >&2
  exit 1
fi

cleanup_json="$(printf '%s' "${job_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get('result', {}).get('ai_cleanup', {}), ensure_ascii=False, indent=2))")"
regions="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('ai_cleanup', {}).get('suspicious_regions')")"
spikes="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('ai_cleanup', {}).get('spikes_detected')")"
elongated="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('ai_cleanup', {}).get('elongated_faces')")"
score_before="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('ai_cleanup', {}).get('health_score_before')")"
score_after="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('ai_cleanup', {}).get('health_score_after')")"
qa_penalty="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('model_qa', {}).get('artifact_quality', {}).get('artifact_score_penalty')")"
qa_regions="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('model_qa', {}).get('artifact_quality', {}).get('suspicious_regions')")"

python3 - "${regions}" "${spikes}" "${elongated}" "${score_before}" "${qa_penalty}" "${qa_regions}" <<'PY'
import sys
regions, spikes, elongated, score_before, qa_penalty, qa_regions = [int(float(value or 0)) for value in sys.argv[1:]]
if regions <= 0:
    raise SystemExit("expected suspicious regions > 0")
if spikes <= 0 and elongated <= 0:
    raise SystemExit("expected spikes or elongated faces > 0")
if score_before >= 100:
    raise SystemExit(f"expected health_score_before < 100, got {score_before}")
if qa_penalty <= 0 or qa_regions <= 0:
    raise SystemExit("expected model_qa artifact_quality penalty and suspicious regions")
print(
    f"Detection OK: suspicious_regions={regions}, spikes={spikes}, "
    f"elongated_faces={elongated}, health_score_before={score_before}, qa_penalty={qa_penalty}"
)
PY

printf '%s\n' "OK ai_cleanup: job_id=${job_id}; health_score=${score_before}->${score_after}"
printf '%s\n' "${cleanup_json}"
echo "Smoke test passed."

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
RESULT_DIR="${PROJECT_DIR}/tests/results/stage82_zip_contract"
MODEL="${RESULT_DIR}/box_64x42x28.stl"
mkdir -p "${RESULT_DIR}"
cd "${PROJECT_DIR}"

python3 - "${MODEL}" <<'PY_MODEL'
from pathlib import Path
import sys
path = Path(sys.argv[1])
sx, sy, sz = 64.0, 42.0, 28.0
x, y, z = sx / 2, sy / 2, sz / 2
verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
faces = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
with path.open("w", encoding="utf-8") as f:
    f.write("solid stage82_zip_box\n")
    for a, b, c in faces:
        f.write(" facet normal 0 0 0\n  outer loop\n")
        for i in (a, b, c):
            vx, vy, vz = verts[i]
            f.write(f"   vertex {vx:.6f} {vy:.6f} {vz:.6f}\n")
        f.write("  endloop\n endfacet\n")
    f.write("endsolid stage82_zip_box\n")
PY_MODEL

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

run_case() {
  local mode="$1"
  local label="$2"
  echo "== ZIP result STL contract: ${label}"
  local response job_id status job_json
  for attempt in $(seq 1 20); do
    response="$(curl -sS -X POST \
      -F "file=@${MODEL}" \
      -F "operations=analyze,print_check,split_model,prepare_package" \
      -F "split_axis=z" \
      -F "split_parts=2" \
      -F "split_mode=${mode}" \
      -F "split_engine=blender_boolean" \
      -F "connector_size_mm=4" \
      -F "connector_depth_mm=6" \
      -F "connector_clearance_mm=0.25" \
      -F "connector_count=2" \
      "${SMOKE_UPLOAD_FIELDS[@]}" "${API_BASE}/api/v1/jobs/upload")"
    job_id="$(printf "%s" "${response}" | json_value "data.get('job_id')")"
    [[ -n "${job_id}" ]] && break
    if printf "%s" "${response}" | grep -q "задача в обработке"; then
      sleep 3
      continue
    fi
    break
  done
  [[ -n "${job_id}" ]] || { echo "upload did not return job_id: ${response}" >&2; exit 1; }
  for _ in $(seq 1 120); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf "%s" "${job_json}" | json_value "data.get('status')")"
    [[ "${status}" == "completed" || "${status}" == "failed" ]] && break
    sleep 2
  done
  [[ "${status}" == "completed" ]] || { echo "${label}: job status=${status}" >&2; printf "%s\n" "${job_json}" >&2; exit 1; }

  docker-compose exec -T worker python3 - "${job_id}" "${mode}" <<'PY_CHECK'
import json, sys, zipfile
from pathlib import Path
import trimesh
job_id, mode = sys.argv[1], sys.argv[2]
result_dir = Path('/data/results') / job_id
zip_path = result_dir / 'result.zip'
report_path = result_dir / 'split_report.json'
if not zip_path.exists():
    raise SystemExit('result.zip not found')
report = json.loads(report_path.read_text(encoding='utf-8'))
if report.get('success') is not True:
    raise SystemExit('split report is not successful: ' + json.dumps(report, ensure_ascii=False))
expected = {'split_part_1.stl', 'split_part_2.stl'}
with zipfile.ZipFile(zip_path) as archive:
    names = set(archive.namelist())
missing = sorted(expected - names)
if missing:
    raise SystemExit('ZIP missing result STL parts: ' + ', '.join(missing))
result_stl = sorted(name for name in names if name.endswith('.stl') and name != 'original.stl')
if not result_stl:
    raise SystemExit('ZIP contains only original STL and no result STL')
for name in expected:
    path = result_dir / name
    mesh = trimesh.load_mesh(str(path), force='mesh')
    if len(mesh.faces) <= 0 or len(mesh.vertices) <= 0:
        raise SystemExit(f'{name} cannot be re-imported as valid STL')
print(json.dumps({'job_id': job_id, 'mode': mode, 'zip_result_stl': result_stl}, ensure_ascii=False))
PY_CHECK
}

run_case "simple" "Плоский разрез"
run_case "pins" "Разрез со штифтами"

echo "Split result ZIP contract smoke test passed."

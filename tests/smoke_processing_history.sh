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
MODEL="${PROJECT_DIR}/test-data/cube_with_spikes.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}" "${PROJECT_DIR}/test-data"

python3 - "${MODEL}" <<'PY'
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
    return uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx

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

echo "STL Master processing history smoke test"

response="$(
  curl -sS -X POST \
    -F "file=@${MODEL}" \
    -F "operations=analyze,print_check,remove_ai_artifacts,apply_orientation,split_model,prepare_package" \
    -F "artifact_cleanup_strength=balanced" \
    -F "apply_orientation=true" \
    -F 'orientation_transform={"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}' \
    -F "split_axis=y" \
    -F "split_parts=2" \
    -F "split_mode=simple" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload"
)"
job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
if [[ -z "${job_id}" ]]; then
  echo "BROKEN upload did not return job_id: ${response}" >&2
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

result_path="${RESULTS_DIR}/processing_history_${job_id}.json"
printf '%s' "${job_json}" > "${result_path}"

python3 - "${result_path}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
history = result.get("processing_history") or []
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN status={data.get('status')}")
if not history:
    raise SystemExit("BROKEN processing_history is missing")

operations = [item.get("operation") for item in history]
if operations[0] != "original":
    raise SystemExit(f"BROKEN first history operation={operations[0] if operations else None}")
if "apply_orientation" not in operations:
    raise SystemExit(f"BROKEN apply_orientation missing from history: {operations}")
if "split_model" not in operations:
    raise SystemExit(f"BROKEN split_model missing from history: {operations}")
if result.get("remove_ai_artifacts", {}).get("success") and "remove_ai_artifacts" not in operations:
    raise SystemExit(f"BROKEN cleanup success but missing from history: {operations}")

files = []
for item in history:
    if item.get("file"):
        files.append((item["file"], item.get("download_url")))
    for file_item in item.get("files") or []:
        files.append((file_item.get("name"), file_item.get("download_url")))

expected = {"original.stl", "oriented_model.stl", "split_part_1.stl", "split_part_2.stl"}
names = {name for name, _ in files}
missing = expected - names
if missing:
    raise SystemExit(f"BROKEN history missing files: {sorted(missing)}; names={sorted(names)}")
for name, url in files:
    if not url:
        raise SystemExit(f"BROKEN missing download_url for {name}")

Path(sys.argv[1] + ".urls").write_text("\n".join(url for _, url in files), encoding="utf-8")
print(json.dumps(history, ensure_ascii=False, indent=2))
PY

while IFS= read -r url; do
  [[ -z "${url}" ]] && continue
  code="$(curl -sS -o /dev/null -w '%{http_code}' -I "${API_BASE}${url}")"
  if [[ "${code}" != "200" ]]; then
    echo "BROKEN history download_url returned ${code}: ${url}" >&2
    exit 1
  fi
done < "${result_path}.urls"

echo "Processing history smoke test passed. job_id=${job_id}"

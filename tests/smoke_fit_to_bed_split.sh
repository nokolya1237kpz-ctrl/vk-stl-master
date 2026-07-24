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
API_URL="http://localhost:8000"
RESULTS_DIR="${PROJECT_DIR}/tests/results"
BOX_STL="${PROJECT_DIR}/test-data/box_500_120_80.stl"
GEELY_STL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}" "${PROJECT_DIR}/test-data"

python3 - <<'PY'
from pathlib import Path

path = Path("/home/codex/projects/vk-stl-master/test-data/box_500_120_80.stl")
x0, x1 = 0.0, 500.0
y0, y1 = 0.0, 80.0
z0, z1 = 0.0, 120.0
v = {
    "000": (x0, y0, z0), "100": (x1, y0, z0), "110": (x1, y1, z0), "010": (x0, y1, z0),
    "001": (x0, y0, z1), "101": (x1, y0, z1), "111": (x1, y1, z1), "011": (x0, y1, z1),
}
faces = [
    ("000", "110", "100"), ("000", "010", "110"),
    ("001", "101", "111"), ("001", "111", "011"),
    ("000", "100", "101"), ("000", "101", "001"),
    ("010", "011", "111"), ("010", "111", "110"),
    ("000", "001", "011"), ("000", "011", "010"),
    ("100", "110", "111"), ("100", "111", "101"),
]
lines = ["solid box_500_120_80"]
for a, b, c in faces:
    lines.append("  facet normal 0 0 0")
    lines.append("    outer loop")
    for key in (a, b, c):
        lines.append("      vertex %.6f %.6f %.6f" % v[key])
    lines.append("    endloop")
    lines.append("  endfacet")
lines.append("endsolid box_500_120_80")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

wait_job() {
  local job_id="$1"
  local output_json="$2"
  local attempt
  for attempt in $(seq 1 180); do
    curl -fsS "${API_URL}/api/v1/jobs/${job_id}" -o "${output_json}"
    local status
    status="$(python3 - "${output_json}" <<'PY'
import json, sys
print(json.load(open(sys.argv[1])).get("status", ""))
PY
)"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      [[ "${status}" == "completed" ]]
      return
    fi
    sleep 2
  done
  echo "Timed out waiting for ${job_id}" >&2
  exit 1
}

upload_fit_to_bed() {
  local file_path="$1"
  local label="$2"
  local json_path="${RESULTS_DIR}/fit_to_bed_${label}.json"
  local upload_response="${RESULTS_DIR}/fit_to_bed_${label}_upload.json"
  curl -fsS \
    -F "file=@${file_path}" \
    -F 'operations=["analyze","print_check","fit_to_bed_split","prepare_package"]' \
    -F "fit_to_bed=true" \
    -F "bed_size_x=220" \
    -F "bed_size_y=250" \
    -F "bed_size_z=220" \
    -F "bed_connector_mode=none" \
    -F "bed_connector_clearance_mm=0.25" \
    "${API_URL}/api/v1/jobs/upload" -o "${upload_response}"
  local job_id
  job_id="$(python3 - "${upload_response}" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["job_id"])
PY
)"
  wait_job "${job_id}" "${json_path}"
  echo "${job_id}:${json_path}"
}

validate_box_result() {
  local job_id="$1"
  local json_path="$2"
  python3 - "${json_path}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
result = data.get("result", {})
fit = result.get("fit_to_bed_split") or {}
assert fit.get("success") is True, fit
assert fit.get("no_split_needed") is False, fit
assert fit.get("parts_grid", {}).get("x", 0) >= 3, fit
assert fit.get("total_parts", 0) >= 3, fit
assert len(fit.get("output_files", [])) == fit.get("total_parts"), fit
assert fit.get("all_parts_fit_bed") is True, fit
assert any(item.get("name", "").startswith("bed_part_") for item in result.get("generated_files", [])), result.get("generated_files")
print(json.dumps(fit, ensure_ascii=False, indent=2))
PY
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
import trimesh

job_id = sys.argv[1]
result_dir = Path("/data/results") / job_id
parts = sorted(result_dir.glob("bed_part_*.stl"))
assert len(parts) >= 3, parts
for path in parts:
    mesh = trimesh.load_mesh(path, force="mesh")
    if getattr(mesh, "geometry", None):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    size = mesh.bounds[1] - mesh.bounds[0]
    assert len(mesh.faces) > 0 and len(mesh.vertices) > 0, path
    assert size[0] <= 221 and size[1] <= 251 and size[2] <= 221, (path.name, size)
    print(f"{path.name}: size={path.stat().st_size} bytes dims={size.round(3).tolist()}")
PY
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

job_id = sys.argv[1]
zip_path = Path("/data/results") / job_id / "result.zip"
with ZipFile(zip_path) as archive:
    names = archive.namelist()
print("\n".join(names))
assert any(name.startswith("bed_part_") for name in names), names
PY
}

validate_geely_result() {
  local job_id="$1"
  local json_path="$2"
  python3 - "${json_path}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
fit = (data.get("result") or {}).get("fit_to_bed_split") or {}
assert fit.get("success") is True, fit
if fit.get("no_split_needed"):
    assert fit.get("output_files") == [], fit
else:
    assert fit.get("all_parts_fit_bed") is True, fit
    assert fit.get("output_files"), fit
print(json.dumps(fit, ensure_ascii=False, indent=2))
PY
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

job_id = sys.argv[1]
zip_path = Path("/data/results") / job_id / "result.zip"
with ZipFile(zip_path) as archive:
    print("\n".join(archive.namelist()))
PY
}

if [[ ! -f "${GEELY_STL}" ]]; then
  echo "Missing real test model: ${GEELY_STL}" >&2
  exit 1
fi

echo "START fit_to_bed generated large box"
box_result="$(upload_fit_to_bed "${BOX_STL}" "box")"
box_job="${box_result%%:*}"
box_json="${box_result#*:}"
validate_box_result "${box_job}" "${box_json}"
echo "OK fit_to_bed generated large box job=${box_job}"

echo "START fit_to_bed Geely_atlas_pro"
geely_result="$(upload_fit_to_bed "${GEELY_STL}" "geely")"
geely_job="${geely_result%%:*}"
geely_json="${geely_result#*:}"
validate_geely_result "${geely_job}" "${geely_json}"
echo "OK fit_to_bed Geely_atlas_pro job=${geely_job}"

echo "fit_to_bed smoke passed."

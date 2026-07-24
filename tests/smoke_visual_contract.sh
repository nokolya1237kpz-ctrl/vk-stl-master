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
SPIKE_MODEL="${PROJECT_DIR}/test-data/cube_with_spikes.stl"
CLEAN_MODEL="${PROJECT_DIR}/test-data/visual_contract_clean_cube.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}" "${PROJECT_DIR}/test-data"

python3 - "${SPIKE_MODEL}" "${CLEAN_MODEL}" <<'PY'
from pathlib import Path
import sys

spike_path = Path(sys.argv[1])
clean_path = Path(sys.argv[2])

def write_ascii_stl(path, name, vertices, faces):
    def normal(a, b, c):
        ax, ay, az = a
        bx, by, bz = b
        cx, cy, cz = c
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        return uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx

    lines = [f"solid {name}"]
    for face in faces:
        a, b, c = [vertices[index] for index in face]
        nx, ny, nz = normal(a, b, c)
        lines.append(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}")
        lines.append("    outer loop")
        for vertex in (a, b, c):
            lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

cube_vertices = [
    (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
    (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
]
cube_faces = [
    (0, 2, 1), (0, 3, 2),
    (0, 1, 5), (0, 5, 4),
    (1, 2, 6), (1, 6, 5),
    (2, 3, 7), (2, 7, 6),
    (3, 0, 4), (3, 4, 7),
    (4, 5, 6), (4, 6, 7),
]

spike_vertices = cube_vertices + [
    (0.46, 0.46, 1), (0.54, 0.46, 1), (0.54, 0.54, 1), (0.46, 0.54, 1),
    (0.5, 0.5, 3.8),
]
spike_faces = cube_faces[:-2] + [
    (4, 5, 9), (4, 9, 8),
    (5, 6, 10), (5, 10, 9),
    (6, 7, 11), (6, 11, 10),
    (7, 4, 8), (7, 8, 11),
    (8, 9, 12), (9, 10, 12), (10, 11, 12), (11, 8, 12),
]

write_ascii_stl(spike_path, "cube_with_spikes", spike_vertices, spike_faces)
write_ascii_stl(clean_path, "visual_contract_clean_cube", cube_vertices, cube_faces)
PY

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local label="$1"
  shift
  local response job_id job_json status
  response="$(curl -sS -X POST "$@" ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "BROKEN ${label}: upload did not return job_id: ${response}" >&2
    exit 1
  fi
  for _ in $(seq 1 160); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 2
  done
  printf '%s' "${job_json}" > "${RESULTS_DIR}/visual_contract_${label}_${job_id}.json"
  printf '%s:%s\n' "${job_id}" "${RESULTS_DIR}/visual_contract_${label}_${job_id}.json"
}

zip_contents() {
  local job_id="$1"
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile

zip_path = Path("/data/results") / sys.argv[1] / "result.zip"
with ZipFile(zip_path) as archive:
    print("\n".join(archive.namelist()))
PY
}

check_url_200() {
  local url="$1"
  local label="$2"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' -I "${API_BASE}${url}")"
  if [[ "${code}" != "200" ]]; then
    echo "BROKEN ${label}: ${url} returned ${code}" >&2
    exit 1
  fi
}

echo "STL Master visual contract smoke test"

visual_case="$(
  upload_and_wait "full" \
    -F "file=@${SPIKE_MODEL}" \
    -F "operations=analyze,print_check,remove_ai_artifacts,apply_orientation,split_model,prepare_package" \
    -F "artifact_cleanup_strength=balanced" \
    -F "apply_orientation=true" \
    -F 'orientation_transform={"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}' \
    -F "split_axis=y" \
    -F "split_parts=2" \
    -F "split_mode=simple"
)"
visual_job="${visual_case%%:*}"
visual_json="${visual_case#*:}"
visual_zip="${RESULTS_DIR}/visual_contract_full_${visual_job}.zip.txt"
zip_contents "${visual_job}" > "${visual_zip}"

python3 - "${visual_json}" "${visual_zip}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
zip_files = set(Path(sys.argv[2]).read_text().splitlines())
result = data.get("result") or {}
generated = result.get("generated_files") or []
generated_names = {item.get("name") for item in generated}
history = result.get("processing_history") or []
history_ops = [item.get("operation") for item in history]

if data.get("status") != "completed":
    raise SystemExit(f"BROKEN visual status={data.get('status')}")

change_map = result.get("change_map") or {}
artifact_map = result.get("artifact_map") or {}
if change_map.get("available") is not True:
    raise SystemExit(f"BROKEN change_map unavailable: {change_map}")
if artifact_map.get("available") is not True:
    raise SystemExit(f"BROKEN artifact_map unavailable: {artifact_map}")
if "change_map.json" not in generated_names or "change_map.json" not in zip_files:
    raise SystemExit("BROKEN change_map.json missing from generated_files or ZIP")
if "artifact_map.json" not in generated_names or "artifact_map.json" not in zip_files:
    raise SystemExit("BROKEN artifact_map.json missing from generated_files or ZIP")
if "original" not in history_ops or "apply_orientation" not in history_ops or "split_model" not in history_ops:
    raise SystemExit(f"BROKEN processing_history operations: {history_ops}")
if result.get("remove_ai_artifacts", {}).get("success") and "remove_ai_artifacts" not in history_ops:
    raise SystemExit(f"BROKEN cleanup success missing from history: {history_ops}")
if not result.get("final_model"):
    raise SystemExit("BROKEN final_model is empty")
if not result.get("final_download_url"):
    raise SystemExit("BROKEN final_download_url is empty")

urls = []
for item in generated:
    if item.get("download_url"):
        urls.append(("generated:" + str(item.get("name")), item["download_url"]))
for item in history:
    if item.get("download_url"):
        urls.append(("history:" + str(item.get("file")), item["download_url"]))
    if item.get("change_map_url"):
        urls.append(("history_change_map", item["change_map_url"]))
    if item.get("artifact_map_url"):
        urls.append(("history_artifact_map", item["artifact_map_url"]))
    for file_item in item.get("files") or []:
        if file_item.get("download_url"):
            urls.append(("history:" + str(file_item.get("name")), file_item["download_url"]))
urls.append(("final_download_url", result["final_download_url"]))
Path(sys.argv[1] + ".urls").write_text("\n".join(f"{label}\t{url}" for label, url in urls), encoding="utf-8")

summary = {
    "job_status": data.get("status"),
    "final_model": result.get("final_model"),
    "change_map": change_map,
    "artifact_map": artifact_map,
    "history_operations": history_ops,
    "generated_files": sorted(generated_names),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY

while IFS=$'\t' read -r label url; do
  [[ -z "${url}" ]] && continue
  check_url_200 "${url}" "${label}"
done < "${visual_json}.urls"

noop_case="$(
  upload_and_wait "noop" \
    -F "file=@${CLEAN_MODEL}" \
    -F "operations=analyze,print_check,apply_orientation,prepare_package" \
    -F "apply_orientation=true" \
    -F 'orientation_transform={"rotation_x":0,"rotation_y":0,"rotation_z":0,"translate_to_floor":false}'
)"
noop_job="${noop_case%%:*}"
noop_json="${noop_case#*:}"
noop_zip="${RESULTS_DIR}/visual_contract_noop_${noop_job}.zip.txt"
zip_contents "${noop_job}" > "${noop_zip}"

python3 - "${noop_json}" "${noop_zip}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
zip_files = set(Path(sys.argv[2]).read_text().splitlines())
result = data.get("result") or {}
generated_names = {item.get("name") for item in result.get("generated_files", [])}
history_ops = [item.get("operation") for item in result.get("processing_history") or []]
change_map = result.get("change_map") or {}

if data.get("status") != "completed":
    raise SystemExit(f"BROKEN no-op status={data.get('status')}")
if change_map.get("available") is not False:
    raise SystemExit(f"BROKEN no-op change_map should be unavailable: {change_map}")
if "change_map.json" in generated_names or "change_map.json" in zip_files:
    raise SystemExit("BROKEN no-op created fake change_map.json")
if "oriented_model.stl" in generated_names or "oriented_model.stl" in zip_files:
    raise SystemExit("BROKEN no-op created fake oriented_model.stl")
if "apply_orientation" in history_ops:
    raise SystemExit(f"BROKEN no-op apply_orientation appeared in history: {history_ops}")
print("No-op visual contract OK:", json.dumps({
    "change_map": change_map,
    "history_operations": history_ops,
    "zip_files": sorted(zip_files),
}, ensure_ascii=False))
PY

echo "Visual contract ZIP contents:"
cat "${visual_zip}"
echo "Visual contract smoke test passed. job_id=${visual_job}"

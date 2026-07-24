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

echo "STL Master artifact map smoke test"

response="$(
  curl -sS -X POST \
    -F "file=@${MODEL}" \
    -F "operations=analyze,print_check,prepare_package" \
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

result_path="${RESULTS_DIR}/artifact_map_${job_id}.json"
printf '%s' "${job_json}" > "${result_path}"

python3 - "${result_path}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
artifact_map = result.get("artifact_map") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
artifact_quality = (result.get("model_qa") or {}).get("artifact_quality") or {}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN status={data.get('status')}")
if artifact_map.get("available") is not True:
    raise SystemExit(f"BROKEN artifact_map unavailable: {artifact_map}")
if artifact_map.get("file") != "artifact_map.json":
    raise SystemExit(f"BROKEN artifact_map file={artifact_map.get('file')}")
if not artifact_map.get("download_url"):
    raise SystemExit("BROKEN artifact_map.download_url is empty")
if "artifact_map.json" not in generated:
    raise SystemExit("BROKEN artifact_map.json missing from generated_files")
if int(artifact_quality.get("suspicious_regions") or 0) <= 0:
    raise SystemExit(f"BROKEN suspicious_regions must be > 0: {artifact_quality}")
print(json.dumps(artifact_map, ensure_ascii=False, indent=2))
PY

artifact_map_url="$(python3 - "${result_path}" <<'PY'
import json
import sys

print((json.load(open(sys.argv[1])).get("result") or {}).get("artifact_map", {}).get("download_url") or "")
PY
)"
map_path="${RESULTS_DIR}/artifact_map_${job_id}.map.json"
code="$(curl -sS -o "${map_path}" -w '%{http_code}' "${API_BASE}${artifact_map_url}")"
if [[ "${code}" != "200" ]]; then
  echo "BROKEN artifact_map download returned ${code}: ${artifact_map_url}" >&2
  exit 1
fi

python3 - "${map_path}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
faces = data.get("faces") or []
regions = data.get("regions") or []
summary = data.get("summary") or {}
if data.get("type") != "artifact_map":
    raise SystemExit(f"BROKEN artifact_map type={data.get('type')}")
if not faces and not regions:
    raise SystemExit("BROKEN artifact_map has no faces or regions")
if int(summary.get("suspicious_regions") or 0) <= 0:
    raise SystemExit(f"BROKEN artifact_map summary={summary}")
print("artifact_map example:")
print(json.dumps({
    "summary": summary,
    "first_face": faces[0] if faces else None,
    "regions_count": len(regions),
}, ensure_ascii=False, indent=2))
PY

zip_listing="$(zip_contents "${job_id}")"
if ! printf '%s\n' "${zip_listing}" | grep -qx "artifact_map.json"; then
  echo "BROKEN ZIP missing artifact_map.json" >&2
  printf '%s\n' "${zip_listing}" >&2
  exit 1
fi

echo "ZIP contents:"
printf '%s\n' "${zip_listing}"
echo "Artifact map smoke test passed."

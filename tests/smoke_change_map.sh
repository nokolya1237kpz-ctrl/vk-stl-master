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
MODEL="${PROJECT_DIR}/test-data/change_map_box.stl"

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}" "${PROJECT_DIR}/test-data"

cat > "${MODEL}" <<'STL'
solid change_map_box
facet normal 0 0 -1
 outer loop
  vertex -10 -5 -3
  vertex 10 -5 -3
  vertex 10 5 -3
 endloop
endfacet
facet normal 0 0 -1
 outer loop
  vertex -10 -5 -3
  vertex 10 5 -3
  vertex -10 5 -3
 endloop
endfacet
facet normal 0 0 1
 outer loop
  vertex -10 -5 3
  vertex 10 5 3
  vertex 10 -5 3
 endloop
endfacet
facet normal 0 0 1
 outer loop
  vertex -10 -5 3
  vertex -10 5 3
  vertex 10 5 3
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex -10 -5 -3
  vertex -10 -5 3
  vertex 10 -5 3
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex -10 -5 -3
  vertex 10 -5 3
  vertex 10 -5 -3
 endloop
endfacet
facet normal 0 1 0
 outer loop
  vertex -10 5 -3
  vertex 10 5 3
  vertex -10 5 3
 endloop
endfacet
facet normal 0 1 0
 outer loop
  vertex -10 5 -3
  vertex 10 5 -3
  vertex 10 5 3
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex -10 -5 -3
  vertex -10 5 3
  vertex -10 -5 3
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex -10 -5 -3
  vertex -10 5 -3
  vertex -10 5 3
 endloop
endfacet
facet normal 1 0 0
 outer loop
  vertex 10 -5 -3
  vertex 10 -5 3
  vertex 10 5 3
 endloop
endfacet
facet normal 1 0 0
 outer loop
  vertex 10 -5 -3
  vertex 10 5 3
  vertex 10 5 -3
 endloop
endfacet
endsolid change_map_box
STL

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local transform="$1"
  local response job_id job_json status
  response="$(
    curl -sS -X POST \
      -F "file=@${MODEL}" \
      -F "operations=analyze,print_check,apply_orientation,prepare_package" \
      -F "apply_orientation=true" \
      -F "orientation_transform=${transform}" \
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
  printf '%s' "${job_json}" > "${RESULTS_DIR}/change_map_${job_id}.json"
  printf '%s:%s\n' "${job_id}" "${RESULTS_DIR}/change_map_${job_id}.json"
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

echo "STL Master change map smoke test"

changed_case="$(upload_and_wait '{"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}')"
changed_job="${changed_case%%:*}"
changed_json="${changed_case#*:}"
python3 - "${changed_json}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
change_map = result.get("change_map") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN status={data.get('status')}")
if change_map.get("available") is not True:
    raise SystemExit(f"BROKEN change_map unavailable: {change_map}")
if change_map.get("file") != "change_map.json":
    raise SystemExit(f"BROKEN change_map file={change_map.get('file')}")
if change_map.get("operation") != "apply_orientation":
    raise SystemExit(f"BROKEN change_map operation={change_map.get('operation')}")
if int(change_map.get("changed_vertices") or 0) <= 0:
    raise SystemExit("BROKEN changed_vertices must be > 0")
if "change_map.json" not in generated:
    raise SystemExit("BROKEN change_map.json missing from generated_files")
if not change_map.get("download_url"):
    raise SystemExit("BROKEN change_map.download_url is empty")
print(json.dumps(change_map, ensure_ascii=False, indent=2))
PY

change_map_url="$(python3 - "${changed_json}" <<'PY'
import json
import sys
print((json.load(open(sys.argv[1])).get("result") or {}).get("change_map", {}).get("download_url") or "")
PY
)"
code="$(curl -sS -o /dev/null -w '%{http_code}' -I "${API_BASE}${change_map_url}")"
if [[ "${code}" != "200" ]]; then
  echo "BROKEN change_map download returned ${code}: ${change_map_url}" >&2
  exit 1
fi
changed_zip="$(zip_contents "${changed_job}")"
if ! printf '%s\n' "${changed_zip}" | grep -qx "change_map.json"; then
  echo "BROKEN ZIP missing change_map.json" >&2
  printf '%s\n' "${changed_zip}" >&2
  exit 1
fi

noop_case="$(upload_and_wait '{"rotation_x":0,"rotation_y":0,"rotation_z":0,"translate_to_floor":false}')"
noop_job="${noop_case%%:*}"
noop_json="${noop_case#*:}"
python3 - "${noop_json}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
change_map = result.get("change_map") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}
if data.get("status") != "completed":
    raise SystemExit(f"BROKEN no-op status={data.get('status')}")
if change_map.get("available") is not False:
    raise SystemExit(f"BROKEN no-op change_map should be unavailable: {change_map}")
if "change_map.json" in generated:
    raise SystemExit("BROKEN no-op generated_files contains change_map.json")
print("No-op change_map:", json.dumps(change_map, ensure_ascii=False))
PY
noop_zip="$(zip_contents "${noop_job}")"
if printf '%s\n' "${noop_zip}" | grep -qx "change_map.json"; then
  echo "BROKEN no-op ZIP contains change_map.json" >&2
  printf '%s\n' "${noop_zip}" >&2
  exit 1
fi

echo "ZIP contents:"
printf '%s\n' "${changed_zip}"
echo "Change map smoke test passed."

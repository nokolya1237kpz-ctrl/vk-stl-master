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

echo "STL Master surface recovery smoke test"

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

json_path="${RESULTS_DIR}/surface_recovery_${job_id}.json"
printf '%s' "${job_json}" > "${json_path}"

python3 - "${json_path}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
result = data.get("result") or {}
surface = result.get("surface_recovery") or {}
generated = {item.get("name") for item in result.get("generated_files", [])}

if data.get("status") != "completed":
    raise SystemExit(f"BROKEN job status={data.get('status')}")
if not surface:
    raise SystemExit("BROKEN result.surface_recovery is missing")

if surface.get("success"):
    if surface.get("output_file") != "surface_recovered.stl":
        raise SystemExit(f"BROKEN unexpected output_file={surface.get('output_file')}")
    if result.get("final_model") != "surface_recovered.stl":
        raise SystemExit(f"BROKEN final_model={result.get('final_model')}")
    if "surface_recovered.stl" not in generated:
        raise SystemExit("BROKEN surface_recovered.stl missing in generated_files")
    if int(surface.get("regions_detected") or 0) <= 0:
        raise SystemExit("BROKEN success without detected regions")
    if int(surface.get("vertices_modified") or 0) <= 0:
        raise SystemExit("BROKEN success without modified vertices")
else:
    if "surface_recovered.stl" in generated:
        raise SystemExit("BROKEN controlled failure must not expose surface_recovered.stl")
    if result.get("final_model") == "surface_recovered.stl":
        raise SystemExit("BROKEN controlled failure must not set final_model to surface_recovered.stl")

print(json.dumps(surface, ensure_ascii=False, indent=2))
PY

zip_contents="$(
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile
zip_path = Path('/data/results') / sys.argv[1] / 'result.zip'
with ZipFile(zip_path) as archive:
    print('\n'.join(archive.namelist()))
PY
)"
printf '%s\n' "${zip_contents}" > "${RESULTS_DIR}/surface_recovery_${job_id}_zip.txt"

surface_success="$(python3 - "${json_path}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
print(str(bool((data.get("result") or {}).get("surface_recovery", {}).get("success"))).lower())
PY
)"
if [[ "${surface_success}" == "true" ]]; then
  if ! printf '%s\n' "${zip_contents}" | grep -qx 'surface_recovered.stl'; then
    echo "BROKEN ZIP missing surface_recovered.stl" >&2
    exit 1
  fi
  final_url="$(python3 - "${json_path}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
print((data.get("result") or {}).get("final_download_url") or "")
PY
)"
  code="$(curl -sS -o /dev/null -w '%{http_code}' -I "${API_BASE}${final_url}")"
  if [[ "${code}" != "200" ]]; then
    echo "BROKEN final_download_url returned ${code}: ${final_url}" >&2
    exit 1
  fi
fi

echo "ZIP contents:"
printf '%s\n' "${zip_contents}"
echo "Surface recovery smoke test passed. job_id=${job_id}"

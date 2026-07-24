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
TEST_FILE="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"
OPERATIONS="analyze,print_check,repair_mesh,split_model,prepare_package"
FORBIDDEN_FILES="improved_model.stl reduced.stl cleaned_artifacts.stl repaired.stl"

cd "${PROJECT_DIR}"

if [[ ! -f "${TEST_FILE}" ]]; then
  echo "ERROR: test STL not found: ${TEST_FILE}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

validate_result() {
  local job_id="$1"
  local mode="$2"
  docker-compose exec -T worker python3 - "${job_id}" "${mode}" ${FORBIDDEN_FILES} <<'PY'
import json
import sys
import zipfile
from pathlib import Path
import trimesh

job_id = sys.argv[1]
mode = sys.argv[2]
forbidden = set(sys.argv[3:])
result_dir = Path("/data/results") / job_id
zip_path = result_dir / "result.zip"
report_path = result_dir / "split_report.json"

info = {
    "ok": True,
    "reason": None,
    "contents": [],
    "part_sizes": {},
    "integrated": None,
    "connectors": {},
}

if not zip_path.exists():
    info.update(ok=False, reason="result.zip not found")
    print(json.dumps(info, ensure_ascii=False))
    raise SystemExit(0)
if not report_path.exists():
    info.update(ok=False, reason="split_report.json not found")
    print(json.dumps(info, ensure_ascii=False))
    raise SystemExit(0)

report = json.loads(report_path.read_text(encoding="utf-8"))
connectors = report.get("connectors") or {}
info["connectors"] = connectors
info["integrated"] = bool(connectors.get("integrated"))

with zipfile.ZipFile(zip_path) as zf:
    contents = zf.namelist()
info["contents"] = contents

extra = sorted(name for name in contents if name in forbidden)
if extra:
    info.update(ok=False, reason=f"ZIP contains forbidden files: {extra}")
    print(json.dumps(info, ensure_ascii=False))
    raise SystemExit(0)

for name in report.get("output_files", []):
    path = result_dir / name
    if not path.exists() or path.stat().st_size <= 0:
        info.update(ok=False, reason=f"{name} is missing or empty")
        print(json.dumps(info, ensure_ascii=False))
        raise SystemExit(0)
    mesh = trimesh.load_mesh(str(path), force="mesh")
    if len(mesh.faces) <= 0 or len(mesh.vertices) <= 0:
        info.update(ok=False, reason=f"{name} has invalid geometry")
        print(json.dumps(info, ensure_ascii=False))
        raise SystemExit(0)
    info["part_sizes"][name] = path.stat().st_size

if info["integrated"]:
    forbidden_guides = {"connector_pins.stl", "connector_slots.stl", "connector_guide.json"}
    leaked = sorted(name for name in contents if name in forbidden_guides)
    if leaked:
        info.update(ok=False, reason=f"integrated ZIP contains guide files: {leaked}")
else:
    expected = "connector_pins.stl" if mode == "pins" else "connector_slots.stl"
    if expected not in contents or "connector_guide.json" not in contents:
        info.update(ok=False, reason="fallback ZIP does not contain connector guide files")
    if not connectors.get("reason"):
        info.update(ok=False, reason="fallback connectors missing honest reason")

print(json.dumps(info, ensure_ascii=False))
PY
}

run_case() {
  local axis="$1"
  local mode="$2"
  local label="${axis}/${mode}"

  echo "== ${label}: upload"
  local response
  response="$(curl -sS -X POST \
    -F "file=@${TEST_FILE}" \
    -F "operations=${OPERATIONS}" \
    -F "split_axis=${axis}" \
    -F "split_parts=2" \
    -F "split_mode=${mode}" \
    -F "split_engine=blender_boolean" \
    -F "connector_size_mm=4" \
    -F "connector_clearance_mm=0.25" \
    -F "connector_count=2" \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"

  local job_id
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "ERROR: upload did not return job_id: ${response}" >&2
    exit 1
  fi

  local job_json=""
  local status=""
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

  local split_success
  split_success="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('split_model', {}).get('success')")"
  if [[ "${split_success}" != "True" ]]; then
    echo "ERROR: ${label} split_model.success=${split_success}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  local validation_json
  validation_json="$(validate_result "${job_id}" "${mode}")"
  local ok
  ok="$(printf '%s' "${validation_json}" | json_value "data.get('ok')")"
  if [[ "${ok}" != "True" ]]; then
    echo "ERROR: ${label} validation failed, job_id=${job_id}" >&2
    printf '%s\n' "${validation_json}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi

  local integrated contents sizes reason
  integrated="$(printf '%s' "${validation_json}" | json_value "data.get('integrated')")"
  contents="$(printf '%s' "${validation_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(','.join(data.get('contents', [])))")"
  sizes="$(printf '%s' "${validation_json}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(json.dumps(data.get('part_sizes', {}), ensure_ascii=False))")"
  reason="$(printf '%s' "${job_json}" | json_value "data.get('result', {}).get('split_model', {}).get('connectors', {}).get('reason')")"

  echo "OK ${label}: job_id=${job_id}; integrated=${integrated}; reason=${reason}; sizes=${sizes}; zip=${contents}"
  printf '%s\n' "${job_json}" > "tests/results/split_connectors_${mode}.json"
}

echo "STL Master Split 3.0 connectors smoke test"
echo "Model: ${TEST_FILE}"

mkdir -p tests/results
run_case "y" "pins"
run_case "z" "slots"

echo "Smoke test passed."

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
REAL_MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"

cd "${PROJECT_DIR}"

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

write_spike_model() {
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
}

upload_and_wait() {
  local file_path="$1"
  local operations="$2"
  shift 2
  local response job_id job_json status
  response="$(curl -sS -X POST -F "file=@${file_path}" -F "operations=${operations}" "$@" ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
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
    sleep 3
  done
  if [[ "${status}" != "completed" ]]; then
    echo "ERROR: job status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
    exit 1
  fi
  printf '%s\n' "${job_json}"
}

assert_head_stl() {
  local url="$1"
  local headers http_code content_type
  headers="$(curl -sS -I "${API_BASE}${url}")"
  http_code="$(printf '%s\n' "${headers}" | awk 'NR==1 {print $2}')"
  content_type="$(printf '%s\n' "${headers}" | awk 'BEGIN{IGNORECASE=1} /^content-type:/ {print $2}' | tr -d '\r')"
  if [[ "${http_code}" != "200" ]]; then
    echo "ERROR: ${url} returned HTTP ${http_code}" >&2
    printf '%s\n' "${headers}" >&2
    exit 1
  fi
  if [[ "${content_type}" != "model/stl" && "${content_type}" != "application/octet-stream" ]]; then
    echo "ERROR: unexpected content-type for ${url}: ${content_type}" >&2
    printf '%s\n' "${headers}" >&2
    exit 1
  fi
}

echo "STL Master final model contract smoke test"
write_spike_model

cleanup_json="$(upload_and_wait \
  "${SPIKE_FILE}" \
  "analyze,print_check,remove_ai_artifacts,prepare_package" \
  -F "artifact_cleanup_strength=balanced")"

printf '%s' "${cleanup_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
checks = {
    "model_qa.health_score": result.get("model_qa", {}).get("health_score") is not None,
    "ai_cleanup.health_score_after": result.get("ai_cleanup", {}).get("health_score_after") is not None,
    "final_model.cleaned_artifacts": result.get("final_model") == "cleaned_artifacts.stl",
    "final_download_url": bool(result.get("final_download_url")),
    "generated_files.cleaned_artifacts": "cleaned_artifacts.stl" in generated,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("cleanup contract failed: " + ", ".join(failed))
print(
    "OK cleanup contract:",
    "job_id={};".format(data.get("job_id")),
    "score={}->{};".format(result["model_qa"]["health_score"], result["ai_cleanup"]["health_score_after"]),
    "final_model={}".format(result.get("final_model")),
)
'

cleanup_final_url="$(printf '%s' "${cleanup_json}" | json_value "data.get('result', {}).get('final_download_url')")"
assert_head_stl "${cleanup_final_url}"

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "ERROR: real test STL not found: ${REAL_MODEL}" >&2
  exit 1
fi

repair_json="$(upload_and_wait \
  "${REAL_MODEL}" \
  "analyze,print_check,model_improvement,prepare_package" \
  -F "model_improvement_strength=balanced")"

printf '%s' "${repair_json}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
result = data.get("result", {})
repair = result.get("print_repair", {})
generated = {item.get("name") for item in result.get("generated_files", [])}
if repair.get("success") is True:
    expected_final = "repaired_model.stl"
    expected_generated = "repaired_model.stl" in generated
else:
    expected_final = "original.stl"
    expected_generated = "repaired_model.stl" not in generated and repair.get("visible_result", {}).get("created") is False
checks = {
    "print_repair.visible_contract": expected_generated,
    "final_model.visible_contract": result.get("final_model") == expected_final,
    "final_download_url": bool(result.get("final_download_url")),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("print repair contract failed: " + ", ".join(failed))
print(
    "OK print repair contract:",
    "job_id={};".format(data.get("job_id")),
    "success={};".format(repair.get("success")),
    "final_model={};".format(result.get("final_model")),
    "final_download_url={}".format(result.get("final_download_url")),
)
'

repair_final_url="$(printf '%s' "${repair_json}" | json_value "data.get('result', {}).get('final_download_url')")"
assert_head_stl "${repair_final_url}"

echo "Final model contract smoke test passed."

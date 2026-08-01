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
API_BASE="${API_BASE:-http://localhost:8000}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-stl-master-backend}"
REDIS_CONTAINER="${REDIS_CONTAINER:-$(docker-compose ps -q redis 2>/dev/null || true)}"
TEST_MODEL="${PROJECT_DIR}/test-data/cube_with_spikes.stl"

cd "${PROJECT_DIR}"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  echo "ADMIN_TOKEN is required for queue smoke test" >&2
  exit 1
fi
if [[ -z "${REDIS_CONTAINER}" ]]; then
  REDIS_CONTAINER="stl-master-redis"
fi

echo "STL Master queue limits smoke test"

admin_headers=(-H "X-Admin-Token: ${ADMIN_TOKEN}")

redis_cli() {
  docker exec "${REDIS_CONTAINER}" redis-cli "$@"
}

make_suffix() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(6))
PY
}

cleanup_ids=()
cleanup_keys=()
cleanup() {
  for job_id in "${cleanup_ids[@]:-}"; do
    redis_cli DEL "stl:job:${job_id}" >/dev/null 2>&1 || true
    redis_cli LREM stl:jobs:free 0 "{\"job_id\":\"${job_id}\",\"priority\":\"free\"}" >/dev/null 2>&1 || true
    redis_cli LREM stl:jobs:premium 0 "{\"job_id\":\"${job_id}\",\"priority\":\"premium\"}" >/dev/null 2>&1 || true
  done
  for key in "${cleanup_keys[@]:-}"; do
    redis_cli DEL "${key}" >/dev/null 2>&1 || true
  done
  smoke_cleanup_run
}
trap cleanup EXIT

create_fake_job() {
  local job_id="$1"
  local owner_key="$2"
  local access_level="$3"
  local priority="$4"
  cleanup_ids+=("${job_id}")
  redis_cli HSET "stl:job:${job_id}" \
    job_id "${job_id}" \
    status queued \
    progress 0 \
    message "queue smoke fake job" \
    queue_owner_key "${owner_key}" \
    access_level "${access_level}" \
    priority "${priority}" \
    is_test true \
    source smoke_test \
    environment test \
    test_run_id "${SMOKE_TEST_RUN_ID}" \
    test_name "${SMOKE_TEST_NAME}" \
    operations '["analyze","print_check"]' \
    queued_at "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" \
    size_bytes 1024 >/dev/null
}

upload_model() {
  local ip="$1"
  local access_code="${2:-}"
  local output_file="$3"
  local http_file="$4"
  local headers=(-H "X-Forwarded-For: ${ip}")
  if [[ -n "${access_code}" ]]; then
    headers+=(-H "X-Beta-Access-Code: ${access_code}")
  fi
  curl -sS -o "${output_file}" -w '%{http_code}' \
    "${headers[@]}" \
    -F "file=@${TEST_MODEL}" \
    -F 'operations=["analyze","print_check"]' \
    ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload" > "${http_file}"
}

curl -sS "${API_BASE}/health" >/dev/null

queue_json="$(curl -sS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/queue")"
printf '%s' "${queue_json}" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert "queue_size" in data and "jobs" in data; print("admin queue endpoint OK")'

suffix="$(make_suffix)"
no_code_body="/tmp/stl-queue-no-code-${suffix}.json"
no_code_status="/tmp/stl-queue-no-code-${suffix}.code"
upload_model "203.0.113.9-${suffix}" "" "${no_code_body}" "${no_code_status}"
if [[ "$(cat "${no_code_status}")" != "403" ]]; then
  echo "public upload without access code returned $(cat "${no_code_status}"), expected 403" >&2
  cat "${no_code_body}" >&2
  exit 1
fi
grep -q "ранний доступ или Premium" "${no_code_body}"
echo "public no-code upload gate OK"

free_user_json="$(curl -sS "${admin_headers[@]}" -H 'Content-Type: application/json' -d "{${SMOKE_JSON_META},\"contact\":\"queue-free-${suffix}@example.test\",\"name\":\"Queue Free\"}" "${API_BASE}/api/v1/admin/users")"
free_user_id="$(printf '%s' "${free_user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
free_access_code="$(printf '%s' "${free_user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_code"])')"
free_ip="203.0.113.10-${suffix}"
free_owner="user:${free_user_id}"
create_fake_job "queue-smoke-free-a-${suffix}" "${free_owner}" free free
create_fake_job "queue-smoke-free-b-${suffix}" "${free_owner}" free free

over_body="/tmp/stl-queue-over-${suffix}.json"
over_code="/tmp/stl-queue-over-${suffix}.code"
upload_model "${free_ip}" "${free_access_code}" "${over_body}" "${over_code}"
if [[ "$(cat "${over_code}")" != "429" ]]; then
  echo "free queue over-limit returned $(cat "${over_code}"), expected 429" >&2
  cat "${over_body}" >&2
  exit 1
fi
printf '%s' "$(cat "${over_body}")" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert "задача" in str(data.get("detail","")).lower() or "перегружен" in str(data.get("detail","")).lower(); print("free queue limit OK")'

rate_ip="203.0.113.20-${suffix}"
rate_key="upload_rate:user:${free_user_id}"
cleanup_keys+=("${rate_key}")
redis_cli SETEX "${rate_key}" 3600 5 >/dev/null
rate_body="/tmp/stl-queue-rate-${suffix}.json"
rate_code="/tmp/stl-queue-rate-${suffix}.code"
upload_model "${rate_ip}" "${free_access_code}" "${rate_body}" "${rate_code}"
if [[ "$(cat "${rate_code}")" != "429" ]]; then
  echo "free upload rate limit returned $(cat "${rate_code}"), expected 429" >&2
  cat "${rate_body}" >&2
  exit 1
fi
echo "free upload rate limit OK"
redis_cli DEL "${rate_key}" >/dev/null

real_body="/tmp/stl-queue-real-${suffix}.json"
real_code="/tmp/stl-queue-real-${suffix}.code"
real_user_json="$(curl -sS "${admin_headers[@]}" -H 'Content-Type: application/json' -d "{${SMOKE_JSON_META},\"contact\":\"queue-real-${suffix}@example.test\",\"name\":\"Queue Real\"}" "${API_BASE}/api/v1/admin/users")"
real_access_code="$(printf '%s' "${real_user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_code"])')"
upload_model "203.0.113.30-${suffix}" "${real_access_code}" "${real_body}" "${real_code}"
if [[ "$(cat "${real_code}")" != "200" ]]; then
  echo "real queue upload returned $(cat "${real_code}"), expected 200" >&2
  cat "${real_body}" >&2
  exit 1
fi
printf '%s' "$(cat "${real_body}")" | python3 -c '
import json, sys
data=json.load(sys.stdin)
assert data["status"] == "queued"
assert data["priority"] == "free"
assert data["access_level"] == "free"
assert "queue_position" in data and "queue_size" in data and "estimated_wait_seconds" in data
print("queue metadata OK")
'

user_json="$(curl -sS "${admin_headers[@]}" -H 'Content-Type: application/json' -d "{${SMOKE_JSON_META},\"contact\":\"queue-smoke-${suffix}@example.test\",\"name\":\"Queue Smoke\"}" "${API_BASE}/api/v1/admin/users")"
user_id="$(printf '%s' "${user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
access_code="$(printf '%s' "${user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_code"])')"
curl -sS "${admin_headers[@]}" -H 'Content-Type: application/json' -d '{"expires_at":"7 дней"}' "${API_BASE}/api/v1/admin/users/${user_id}/premium" >/dev/null
premium_owner="user:${user_id}"
create_fake_job "queue-smoke-premium-a-${suffix}" "${premium_owner}" premium premium
create_fake_job "queue-smoke-premium-b-${suffix}" "${premium_owner}" premium premium
premium_body="/tmp/stl-queue-premium-${suffix}.json"
premium_code="/tmp/stl-queue-premium-${suffix}.code"
upload_model "203.0.113.40-${suffix}" "${access_code}" "${premium_body}" "${premium_code}"
if [[ "$(cat "${premium_code}")" != "200" ]]; then
  echo "premium upload returned $(cat "${premium_code}"), expected 200" >&2
  cat "${premium_body}" >&2
  exit 1
fi
printf '%s' "$(cat "${premium_body}")" | python3 -c '
import json, sys
data=json.load(sys.stdin)
assert data["priority"] == "premium"
assert data["access_level"] == "premium"
print("premium priority OK")
'

cancel_id="queue-smoke-cancel-${suffix}"
create_fake_job "${cancel_id}" "ip:203.0.113.50-${suffix}" free free
redis_cli RPUSH stl:jobs:free "{\"job_id\":\"${cancel_id}\",\"priority\":\"free\"}" >/dev/null
cancel_json="$(curl -sS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/jobs/${cancel_id}/cancel")"
printf '%s' "${cancel_json}" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["status"] == "cancelled"; print("cancel queued OK")'
sleep 2
cancel_status="$(redis_cli HGET "stl:job:${cancel_id}" status)"
if [[ "${cancel_status}" != "cancelled" ]]; then
  echo "cancelled queued job was not preserved as cancelled: ${cancel_status}" >&2
  exit 1
fi
echo "cancelled job not processed OK"

grep -q "Очередь" frontend/src/main.jsx || { echo "frontend missing queue tab" >&2; exit 1; }
grep -q "Отменить задачу" frontend/src/main.jsx || { echo "frontend missing cancel action" >&2; exit 1; }
grep -q "queue_position" frontend/src/main.jsx || { echo "frontend missing queue_position UX" >&2; exit 1; }
grep -Eq "(Premium|Премиум)-задачи обрабатываются быстрее" frontend/src/main.jsx || { echo "frontend missing premium queue hint" >&2; exit 1; }

echo "Queue limits smoke test passed."

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
FRONTEND_MAIN="${PROJECT_DIR}/frontend/src/main.jsx"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-stl-master-backend}"
REDIS_CONTAINER="${REDIS_CONTAINER:-b7fed378bec5_stl-master-redis}"

cd "${PROJECT_DIR}"

echo "STL Master admin security smoke test"

require_http_status() {
  local expected="$1"
  shift
  local status
  status="$(curl -sS -o /dev/null -w '%{http_code}' "$@")"
  if [[ "${status}" != "${expected}" ]]; then
    echo "HTTP status ${status}, expected ${expected}: $*" >&2
    exit 1
  fi
}

require_secret_env() {
  local name="$1"
  if ! docker exec "${BACKEND_CONTAINER}" sh -c "test -n \"\${${name}:-}\""; then
    echo "${name} is not configured in backend container" >&2
    exit 1
  fi
}

audit_log_contains() {
  local pattern="$1"
  docker exec "${BACKEND_CONTAINER}" sh -c 'test -s /data/results/audit/admin_actions.jsonl && cat /data/results/audit/admin_actions.jsonl' | grep -F "${pattern}" >/dev/null
}

curl -sS "${API_BASE}/health" >/dev/null
require_secret_env "ADMIN_PASSWORD_HASH"
require_secret_env "ADMIN_SESSION_SECRET"

status_no_auth="$(curl -sS -o /dev/null -w '%{http_code}' "${API_BASE}/api/v1/admin/feedback/summary")"
if [[ "${status_no_auth}" != "401" && "${status_no_auth}" != "403" ]]; then
  echo "admin endpoint without auth returned ${status_no_auth}, expected 401/403" >&2
  exit 1
fi

unique_suffix="$(python3 - <<'PY'
import secrets
print(secrets.randbelow(1000000))
PY
)"
TEST_IP="203.0.113.${unique_suffix}"
LOGIN_IP="198.51.100.${unique_suffix}"

docker exec "${REDIS_CONTAINER}" redis-cli DEL \
  "admin_login_fail:${TEST_IP}" \
  "admin_login_lock:${TEST_IP}" \
  "admin_login_fail:${LOGIN_IP}" \
  "admin_login_lock:${LOGIN_IP}" >/dev/null 2>&1 || true

status_bad="$(curl -sS -o /dev/null -w '%{http_code}' -H "X-Forwarded-For: ${TEST_IP}" -H 'Content-Type: application/json' -d '{"password":"wrong-password"}' "${API_BASE}/api/v1/admin/login")"
if [[ "${status_bad}" != "401" ]]; then
  echo "wrong admin password returned ${status_bad}, expected 401" >&2
  exit 1
fi

locked_status="0"
for _ in $(seq 1 5); do
  locked_status="$(curl -sS -o /dev/null -w '%{http_code}' -H "X-Forwarded-For: ${TEST_IP}" -H 'Content-Type: application/json' -d '{"password":"wrong-password"}' "${API_BASE}/api/v1/admin/login")"
done
if [[ "${locked_status}" != "429" ]]; then
  echo "admin brute force lock returned ${locked_status}, expected 429" >&2
  exit 1
fi

fake_status="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer fake.token.value' "${API_BASE}/api/v1/admin/feedback/summary")"
if [[ "${fake_status}" != "401" && "${fake_status}" != "403" ]]; then
  echo "fake bearer token returned ${fake_status}, expected 401/403" >&2
  exit 1
fi

admin_password="${SMOKE_ADMIN_PASSWORD:-${ADMIN_SMOKE_PASSWORD:-}}"
if [[ -z "${admin_password}" ]]; then
  echo "SMOKE_ADMIN_PASSWORD is not set; positive admin login and Bearer session checks skipped safely."
  echo "Set SMOKE_ADMIN_PASSWORD only in the shell that runs this test to enable full production login verification."
else
  login_json="$(curl -sS -H "X-Forwarded-For: ${LOGIN_IP}" -H 'Content-Type: application/json' -d "{\"password\":\"${admin_password}\"}" "${API_BASE}/api/v1/admin/login")"
  session_token="$(printf '%s' "${login_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_token",""))')"
  if [[ -z "${session_token}" ]]; then
    echo "admin login did not return session_token" >&2
    exit 1
  fi

  curl -sS -H "Authorization: Bearer ${session_token}" "${API_BASE}/api/v1/admin/feedback/summary" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "total_feedback" in data
print("bearer session OK")
'

  curl -sS -H "Authorization: Bearer ${session_token}" "${API_BASE}/api/v1/admin/security" | python3 -c '
import json, sys
data = json.load(sys.stdin)
if not data.get("admin_auth_enabled"):
    raise SystemExit("admin_auth_enabled is false")
if "audit_events" not in data:
    raise SystemExit("audit_events missing")
print("admin security endpoint OK")
'

  if audit_log_contains "${admin_password}"; then
    echo "audit log contains admin password" >&2
    exit 1
  fi
fi

docker exec "${BACKEND_CONTAINER}" sh -c 'test -s /data/results/audit/admin_actions.jsonl'
if ! audit_log_contains "admin_login_failed"; then
  echo "audit log does not contain admin_login_failed" >&2
  exit 1
fi
if ! audit_log_contains "admin_locked"; then
  echo "audit log does not contain admin_locked" >&2
  exit 1
fi

grep -q "Пароль администратора" "${FRONTEND_MAIN}" || { echo "frontend missing admin password login" >&2; exit 1; }
grep -q "sessionStorage" "${FRONTEND_MAIN}" || { echo "frontend missing sessionStorage session" >&2; exit 1; }
grep -q "Authorization" "${FRONTEND_MAIN}" || { echo "frontend missing bearer auth" >&2; exit 1; }
grep -q "Выйти из админки" "${FRONTEND_MAIN}" || { echo "frontend missing logout" >&2; exit 1; }
grep -q "Журнал безопасности" "${FRONTEND_MAIN}" || { echo "frontend missing audit log" >&2; exit 1; }

echo "Admin security smoke test passed."

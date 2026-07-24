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
FRONTEND_MAIN="${PROJECT_DIR}/frontend/src/main.jsx"

cd "${PROJECT_DIR}"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  echo "ADMIN_TOKEN is required for admin auth smoke test" >&2
  exit 1
fi

echo "STL Master admin auth/users/cleanup smoke test"
test_run_id="${SMOKE_TEST_RUN_ID}"

status_no_token="$(curl -sS -o /dev/null -w '%{http_code}' "${API_BASE}/api/v1/admin/cleanup/status")"
if [[ "${status_no_token}" != "401" && "${status_no_token}" != "403" ]]; then
  echo "admin cleanup without token returned ${status_no_token}, expected 401/403" >&2
  exit 1
fi

headers=(-H "X-Admin-Token: ${ADMIN_TOKEN}")

curl -sS "${headers[@]}" "${API_BASE}/api/v1/admin/feedback/summary" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "real_feedback" in data
print("admin token OK")
'

user_payload="$(TEST_RUN_ID="${test_run_id}" SMOKE_TEST_NAME="${SMOKE_TEST_NAME}" python3 - <<'PY'
import json
import os
test_run_id = os.environ["TEST_RUN_ID"]
print(json.dumps({
    "contact": f"premium-smoke-{test_run_id}@example.test",
    "name": "Premium Smoke",
    "notes": "smoke user",
    "is_test": True,
    "source": "smoke_test",
    "environment": "test",
    "test_run_id": test_run_id,
    "test_name": os.environ.get("SMOKE_TEST_NAME", "smoke_admin_auth_users_cleanup.sh"),
}))
PY
)"
user_json="$(curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d "${user_payload}" "${API_BASE}/api/v1/admin/users")"
user_id="$(printf '%s' "${user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
access_code="$(printf '%s' "${user_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_code"])')"
if [[ -z "${user_id}" || -z "${access_code}" ]]; then
  echo "user creation did not return id/access_code" >&2
  exit 1
fi

curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d '{"expires_at":"30 дней"}' "${API_BASE}/api/v1/admin/users/${user_id}/premium" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["access_level"] == "premium"
print("premium OK")
'

curl -sS "${headers[@]}" -X POST "${API_BASE}/api/v1/admin/users/${user_id}/block" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["access_level"] == "blocked"
print("block OK")
'

curl -sS "${headers[@]}" -X POST "${API_BASE}/api/v1/admin/users/${user_id}/unblock" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["access_level"] == "free"
print("unblock OK")
'

curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d '{"include_items":false}' "${API_BASE}/api/v1/admin/test-data/scan" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "summary" in data
assert "test" in data["summary"] and "users" in data["summary"]["test"]
print("test data scan OK")
'

delete_preview_payload="$(python3 - <<PY
import json
print(json.dumps({
    "user_ids": ["${user_id}"],
    "mode": "delete",
    "options": {"delete_uploads": True, "delete_results": True, "delete_feedback": True, "revoke_codes": True},
}))
PY
)"
delete_preview_json="$(curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d "${delete_preview_payload}" "${API_BASE}/api/v1/admin/users/deletion-preview")"
delete_plan_id="$(printf '%s' "${delete_preview_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["plan_id"])')"
delete_confirm_token="$(printf '%s' "${delete_preview_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["confirmation_token"])')"
if [[ -z "${delete_plan_id}" || -z "${delete_confirm_token}" ]]; then
  echo "user deletion preview did not return plan_id/confirmation_token" >&2
  printf '%s\n' "${delete_preview_json}" >&2
  exit 1
fi
delete_execute_payload="$(python3 - <<PY
import json
print(json.dumps({"plan_id": "${delete_plan_id}", "confirmation": "${delete_confirm_token}"}))
PY
)"
curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d "${delete_execute_payload}" "${API_BASE}/api/v1/admin/users/delete" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["ok"] is True
assert data["removed"] >= 1
print("test user deletion OK")
'

curl -sS "${headers[@]}" "${API_BASE}/api/v1/admin/cleanup/status" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "disk" in data and "active_jobs" in data
print("cleanup status OK")
'

curl -sS "${headers[@]}" "${API_BASE}/api/v1/admin/overview" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "backend" in data and "queue" in data and "attention" in data
print("admin overview OK")
'

curl -sS "${headers[@]}" "${API_BASE}/api/v1/admin/premium-codes" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "items" in data and "total" in data
for item in data["items"]:
    assert "masked_code" in item
    assert "access_code" not in item
print("premium codes list OK")
'

curl -sS "${headers[@]}" "${API_BASE}/api/v1/admin/features" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert "items" in data and data["items"]
assert all("status" in item for item in data["items"])
print("feature readiness OK")
'

curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d '{"older_than_hours":6,"include_test_results":true,"dry_run":true}' "${API_BASE}/api/v1/admin/cleanup/run" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["dry_run"] is True
assert "would_delete" in data
print("cleanup dry-run OK")
'

fixture_name="smoke-cleanup-$(date +%s)-$$.tmp"
docker exec stl-master-backend sh -c "mkdir -p /data/admin-cleanup-test && printf smoke > /data/admin-cleanup-test/${fixture_name}"
scan_json="$(curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d '{"older_than_hours":6}' "${API_BASE}/api/v1/admin/cleanup/scan")"
scan_id="$(printf '%s' "${scan_json}" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["scan_id"])')"
confirm_token="$(printf '%s' "${scan_json}" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["confirmation_token"])')"
fixture_item_id="$(printf '%s' "${scan_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
for item in data.get("items", []):
    if item.get("category") == "marked_test_fixture" and item.get("path_masked", "").endswith("'"${fixture_name}"'"):
        print(item["id"])
        break
')"
if [[ -z "${scan_id}" || -z "${confirm_token}" || -z "${fixture_item_id}" ]]; then
  echo "cleanup scan did not include smoke fixture" >&2
  printf '%s\n' "${scan_json}" >&2
  exit 1
fi
execute_payload="$(python3 - <<PY
import json
print(json.dumps({"scan_id": "${scan_id}", "item_ids": ["${fixture_item_id}"], "confirmation_token": "${confirm_token}"}))
PY
)"
curl -sS "${headers[@]}" -H 'Content-Type: application/json' -d "${execute_payload}" "${API_BASE}/api/v1/admin/cleanup/execute" | python3 -c '
import json, sys
data = json.load(sys.stdin)
assert data["deleted"] == 1, data
assert data["failed"] == 0, data
print("cleanup scan/execute OK")
'
if docker exec stl-master-backend test -e "/data/admin-cleanup-test/${fixture_name}"; then
  echo "cleanup fixture still exists after execute" >&2
  exit 1
fi

users_count="$(docker exec stl-master-backend sh -c 'find /data/results/users -maxdepth 1 -type f 2>/dev/null | wc -l')"
feedback_dir_exists="$(docker exec stl-master-backend sh -c 'test -d /data/results/feedback && echo yes || echo no')"
if [[ "${users_count}" -lt 1 ]]; then
  echo "users storage missing after cleanup dry-run" >&2
  exit 1
fi
if [[ "${feedback_dir_exists}" != "yes" ]]; then
  echo "feedback storage directory missing after cleanup dry-run" >&2
  exit 1
fi

grep -q "Пользователи" "${FRONTEND_MAIN}" || { echo "frontend missing users tab" >&2; exit 1; }
grep -q "Файлы и очистка" "${FRONTEND_MAIN}" || { echo "frontend missing cleanup tab" >&2; exit 1; }
grep -q "Выдать Премиум" "${FRONTEND_MAIN}" || { echo "frontend missing premium action" >&2; exit 1; }
grep -q "Пароль администратора" "${FRONTEND_MAIN}" || { echo "frontend missing admin password login" >&2; exit 1; }
grep -q "Authorization" "${FRONTEND_MAIN}" || { echo "frontend missing bearer authorization" >&2; exit 1; }
grep -q "Выйти" "${FRONTEND_MAIN}" || { echo "frontend missing logout" >&2; exit 1; }
grep -q "Премиум и коды" "${FRONTEND_MAIN}" || { echo "frontend missing premium codes tab" >&2; exit 1; }
grep -q "Готовность функций" "${FRONTEND_MAIN}" || { echo "frontend missing feature readiness tab" >&2; exit 1; }
grep -q "cleanup/scan" "${FRONTEND_MAIN}" || { echo "frontend missing cleanup scan flow" >&2; exit 1; }
grep -q "test-data/scan" "${FRONTEND_MAIN}" || { echo "frontend missing test data scan flow" >&2; exit 1; }

echo "Admin auth/users/cleanup smoke test passed."

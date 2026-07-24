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
mkdir -p tests/results
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  echo "ADMIN_TOKEN is required for admin feedback smoke test" >&2
  exit 1
fi

echo "STL Master admin feedback smoke test"

TEST_JOB_ID="beta-admin-smoke-$(date +%s)"
REAL_JOB_ID="beta-real-admin-$(date +%s)"
export TEST_JOB_ID REAL_JOB_ID

test_payload="{${SMOKE_JSON_META},\"job_id\":\"${TEST_JOB_ID}\",\"operations\":[\"split_model\",\"apply_orientation\"],\"rating\":\"problem\",\"comment\":\"smoke admin feedback\",\"contact\":\"beta@example.com\"}"
real_payload="{${SMOKE_JSON_META},\"job_id\":\"${REAL_JOB_ID}\",\"operations\":[\"remove_ai_artifacts\",\"split_model\"],\"rating\":\"good\",\"comment\":\"second smoke feedback\",\"contact\":\"real-user@stlmaster.test\"}"

curl -sS -X POST -H 'Content-Type: application/json' -d "${test_payload}" "${API_BASE}/api/v1/feedback" >/dev/null
curl -sS -X POST -H 'Content-Type: application/json' -d "${real_payload}" "${API_BASE}/api/v1/feedback" >/dev/null

admin_headers=(-H "X-Admin-Token: ${ADMIN_TOKEN}")
feedback_json="$(curl -sS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/feedback")"
summary_json="$(curl -sS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/feedback/summary")"

printf '%s' "${feedback_json}" > "tests/results/admin_feedback_list.json"
printf '%s' "${summary_json}" > "tests/results/admin_feedback_summary.json"

printf '%s' "${feedback_json}" | python3 -c '
import json, os, sys
data = json.load(sys.stdin)
test_job = os.environ["TEST_JOB_ID"]
real_job = os.environ["REAL_JOB_ID"]
if not isinstance(data, list):
    raise SystemExit("feedback list is not a list")
test_item = next((item for item in data if item.get("job_id") == test_job), None)
real_item = next((item for item in data if item.get("job_id") == real_job), None)
if not test_item:
    raise SystemExit("feedback list does not contain test feedback")
if not real_item:
    raise SystemExit("feedback list does not contain real feedback")
if test_item.get("is_test") is not True:
    raise SystemExit("test feedback is_test is not true")
if real_item.get("is_test") is not True:
    raise SystemExit("second smoke feedback is_test is not true")
print("feedback list OK")
'

printf '%s' "${summary_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
if int(data.get("total_feedback", 0)) < 1:
    raise SystemExit("summary total_feedback < 1")
if int(data.get("test_feedback", 0)) < 2:
    raise SystemExit("summary test_feedback < 2")
if int(data.get("test_feedback", 0)) < 1:
    raise SystemExit("summary test_feedback < 1")
if "by_operation" not in data or "real_by_operation" not in data:
    raise SystemExit("summary missing operation stats")
print("feedback summary OK")
'

cleanup_json="$(curl -sS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/test-data/cleanup" \
  -H 'Content-Type: application/json' \
  -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}")"
printf '%s' "${cleanup_json}" > "tests/results/admin_feedback_cleanup.json"
printf '%s' "${cleanup_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
if data.get("ok") is not True:
    raise SystemExit("test-data cleanup did not return ok")
remaining = data.get("remaining_test_counts") or {}
if any(int(value or 0) for value in remaining.values()):
    raise SystemExit(f"test-data cleanup left records: {remaining}")
print("test-data cleanup OK")
'

post_cleanup_json="$(curl -sS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/feedback")"
printf '%s' "${post_cleanup_json}" | python3 -c '
import json, os, sys
data = json.load(sys.stdin)
test_job = os.environ["TEST_JOB_ID"]
real_job = os.environ["REAL_JOB_ID"]
if any(item.get("job_id") == test_job for item in data):
    raise SystemExit("test feedback remains in feedback after cleanup")
if any(item.get("job_id") == real_job for item in data):
    raise SystemExit("second smoke feedback remains in feedback after cleanup")
print("cleanup removes smoke feedback OK")
'

admin_status="$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/admin)"
if [[ "${admin_status}" != "200" ]]; then
  echo "/admin SPA route returned ${admin_status}, expected 200" >&2
  exit 1
fi

grep -q "/admin" "${FRONTEND_MAIN}" || { echo "frontend missing /admin" >&2; exit 1; }
grep -q "AdminFeedbackDashboard" "${FRONTEND_MAIN}" || { echo "frontend missing AdminFeedbackDashboard" >&2; exit 1; }
grep -q "Скопировать Job ID" "${FRONTEND_MAIN}" || { echo "frontend missing copy job id" >&2; exit 1; }
grep -q "Реальные" "${FRONTEND_MAIN}" || { echo "frontend missing real filter" >&2; exit 1; }
grep -q "Тестовые" "${FRONTEND_MAIN}" || { echo "frontend missing test filter" >&2; exit 1; }
grep -q "Архивировать тестовые отзывы" "${FRONTEND_MAIN}" || { echo "frontend missing cleanup button" >&2; exit 1; }
grep -q "Статистика по функциям" "${FRONTEND_MAIN}" || { echo "frontend missing operation analytics" >&2; exit 1; }
grep -q "Данные job" "${FRONTEND_MAIN}" || { echo "frontend missing job details panel" >&2; exit 1; }
grep -q "Отзыв сохранится вместе с Job ID" "${FRONTEND_MAIN}" || { echo "frontend missing feedback Job ID hint" >&2; exit 1; }
grep -q "Что изменилось" "${FRONTEND_MAIN}" || { echo "frontend missing what changed report" >&2; exit 1; }
grep -q "Что пошло не так" "${FRONTEND_MAIN}" || { echo "frontend missing problem placeholder" >&2; exit 1; }

echo "Admin feedback smoke test passed."

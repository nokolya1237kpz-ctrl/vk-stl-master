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

cd "${PROJECT_DIR}"
mkdir -p tests/results
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  echo "ADMIN_TOKEN is required for premium flow smoke test" >&2
  exit 1
fi

echo "STL Master premium request/code smoke test"

admin_headers=(-H "X-Admin-Token: ${ADMIN_TOKEN}")
suffix="$(date +%s)-$RANDOM"
client_id="premium-smoke-${suffix}"
idempotency_key="premium-smoke-key-${suffix}"

request_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium-requests" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: ${idempotency_key}" \
  -H 'X-Forwarded-For: 203.0.113.31' \
  -d "{${SMOKE_JSON_META},\"requested_plan\":\"premium_monthly_299\",\"client_id\":\"${client_id}\",\"contact\":\"premium-smoke@example.com\",\"comment\":\"Premium flow smoke\"}")"
printf '%s' "${request_json}" > tests/results/premium_flow_request.json

application_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["application_id"])' "${request_json}")"
request_number="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["request_number"])' "${request_json}")"
python3 - "${request_json}" <<'PY'
import json, re, sys
payload = json.loads(sys.argv[1])
if payload.get("ok") is not True:
    raise SystemExit("premium request did not return ok")
if not payload.get("application_id"):
    raise SystemExit("premium request did not return application_id")
if not re.fullmatch(r"STL-\d{8}-[A-HJ-NP-Z2-9]{6}", payload.get("request_number") or ""):
    raise SystemExit(f"premium request returned invalid public number: {payload.get('request_number')}")
print("premium request number OK")
PY

repeat_request_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium-requests" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: ${idempotency_key}" \
  -H 'X-Forwarded-For: 203.0.113.31' \
  -d "{${SMOKE_JSON_META},\"requested_plan\":\"premium_monthly_299\",\"client_id\":\"${client_id}\",\"contact\":\"premium-smoke@example.com\",\"comment\":\"Premium flow smoke retry\"}")"
printf '%s' "${repeat_request_json}" > tests/results/premium_flow_request_idempotent.json
python3 - "${repeat_request_json}" "${application_id}" "${request_number}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("application_id") != sys.argv[2] or payload.get("request_number") != sys.argv[3]:
    raise SystemExit("premium request idempotency did not return the original request")
print("premium request idempotency OK")
PY

public_request_status="$(curl -fsS "${API_BASE}/api/v1/premium-requests/${application_id}")"
printf '%s' "${public_request_status}" > tests/results/premium_flow_public_status_pending.json
public_request_number_status="$(curl -fsS "${API_BASE}/api/v1/premium-requests/by-number/${request_number}")"
printf '%s' "${public_request_number_status}" > tests/results/premium_flow_public_status_by_number_pending.json
python3 - "${public_request_status}" "${public_request_number_status}" "${application_id}" "${request_number}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
number_payload = json.loads(sys.argv[2])
application_id = sys.argv[3]
request_number = sys.argv[4]
if payload.get("application_id") != application_id:
    raise SystemExit("public request status returned wrong application id")
if payload.get("request_number") != request_number:
    raise SystemExit("public request status returned wrong request number")
if number_payload.get("application_id") != application_id or number_payload.get("request_number") != request_number:
    raise SystemExit("public request status by number returned the wrong request")
if payload.get("status") != "pending" or payload.get("code_issued") is not False:
    raise SystemExit("public request status did not expose pending safely")
if "access_code" in payload or "access_code" in number_payload:
    raise SystemExit("public request status leaked access code")
print("public pending status OK")
PY

applications_json="$(curl -fsS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/applications")"
printf '%s' "${applications_json}" > tests/results/premium_flow_applications.json
python3 - "${applications_json}" "${application_id}" "${request_number}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
application_id = sys.argv[2]
request_number = sys.argv[3]
items = payload.get("premium", [])
application = next((item for item in items if item.get("id") == application_id), None)
if not application:
    raise SystemExit("premium application missing from admin list")
if application.get("request_number") != request_number:
    raise SystemExit("premium application missing public request number in admin list")
if application.get("status") not in {"pending", "new"}:
    raise SystemExit(f"unexpected initial premium application status: {application.get('status')}")
print("premium application listed OK")
PY

approval_json="$(curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/applications/premium/${application_id}/approve" \
  -H 'Content-Type: application/json' \
  -d '{"premium_days":30}')"
printf '%s' "${approval_json}" > tests/results/premium_flow_approval.json

access_code="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["access_code"])' "${approval_json}")"
user_id="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("user") or {})["id"])' "${approval_json}")"
python3 - "${approval_json}" <<'PY'
import json, re, sys
payload = json.loads(sys.argv[1])
code = payload.get("access_code")
user = payload.get("user") or {}
if not code:
    raise SystemExit("premium access code missing")
if not re.fullmatch(r"STL-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}", code):
    raise SystemExit(f"premium access code has unexpected format: {code}")
if user.get("access_level") != "premium":
    raise SystemExit("approved user is not premium")
application = payload.get("application") or {}
if application.get("status") != "code_issued":
    raise SystemExit(f"premium application was not marked code_issued: {application.get('status')}")
print("premium approval OK")
PY

issued_status_json="$(curl -fsS "${API_BASE}/api/v1/premium-requests/by-number/${request_number}")"
printf '%s' "${issued_status_json}" > tests/results/premium_flow_public_status_issued.json
python3 - "${issued_status_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("status") != "code_issued" or payload.get("code_issued") is not True:
    raise SystemExit("public request status did not expose code_issued state")
if "access_code" in payload:
    raise SystemExit("public request status leaked access code after approval")
print("public code_issued status OK")
PY

activate_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium/activate" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${access_code}\",\"request_number\":\"${request_number}\"}")"
printf '%s' "${activate_json}" > tests/results/premium_flow_activate.json
python3 - "${activate_json}" "${user_id}" "${request_number}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
user_id = sys.argv[2]
request_number = sys.argv[3]
if payload.get("ok") is not True:
    raise SystemExit("premium activation did not return ok")
if payload.get("premium") is not True or payload.get("access_level") != "premium":
    raise SystemExit("premium activation did not return premium access")
if payload.get("user_id") != user_id:
    raise SystemExit("premium activation returned the wrong user")
if payload.get("upload_limit_mb") != 300:
    raise SystemExit("premium activation did not expose 300 MB limit")
if payload.get("request_number") != request_number:
    raise SystemExit("premium activation did not return request number")
print("premium activation OK")
PY

repeat_status="$(curl -sS -o tests/results/premium_flow_repeat_code.json -w '%{http_code}' -X POST "${API_BASE}/api/v1/premium/activate" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${access_code}\",\"request_number\":\"${request_number}\"}" || true)"
if [[ "${repeat_status}" != "409" ]]; then
  echo "repeat premium code returned ${repeat_status}, expected 409" >&2
  exit 1
fi
python3 - tests/results/premium_flow_repeat_code.json <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
detail = payload.get("detail", payload)
if detail.get("error") != "already_used":
    raise SystemExit("repeat premium code did not return already_used")
print("repeat premium code OK")
PY

status_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium/status" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${access_code}\"}")"
printf '%s' "${status_json}" > tests/results/premium_flow_status.json
python3 - "${status_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("ok") is not True:
    raise SystemExit("premium status did not return ok")
if payload.get("premium") is not True or payload.get("access_level") != "premium":
    raise SystemExit("premium status did not confirm premium access")
print("premium status OK")
PY

invalid_status="$(curl -sS -o tests/results/premium_flow_invalid.json -w '%{http_code}' -X POST "${API_BASE}/api/v1/premium/activate" \
  -H 'Content-Type: application/json' \
  -d '{"code":"BAD-CODE-12345"}' || true)"
if [[ "${invalid_status}" != "404" ]]; then
  echo "invalid premium code returned ${invalid_status}, expected 404" >&2
  exit 1
fi
python3 - tests/results/premium_flow_invalid.json <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
detail = payload.get("detail", payload)
if detail.get("error") != "invalid_code":
    raise SystemExit("invalid premium code did not return invalid_code")
print("invalid premium code OK")
PY

reset_json="$(curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/users/${user_id}/reset-code")"
printf '%s' "${reset_json}" > tests/results/premium_flow_reset_code.json
new_code="$(python3 - "${reset_json}" <<'PY'
import json, re, sys
payload = json.loads(sys.argv[1])
code = payload.get("access_code")
if not code:
    raise SystemExit("reset-code did not return a new code")
if not re.fullmatch(r"STL-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}", code):
    raise SystemExit(f"reset premium access code has unexpected format: {code}")
print(code)
PY
)"

old_status_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium/status" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${access_code}\"}")"
printf '%s' "${old_status_json}" > tests/results/premium_flow_old_code_status.json
python3 - "${old_status_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("premium") is not False or payload.get("access_level") != "free":
    raise SystemExit("old reset premium code is still active")
print("reset invalidated previous code OK")
PY

new_activate_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium/activate" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${new_code}\",\"request_number\":\"${request_number}\"}")"
printf '%s' "${new_activate_json}" > tests/results/premium_flow_new_activate.json
python3 - "${new_activate_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("premium") is not True:
    raise SystemExit("new premium code did not activate")
print("new premium code activation OK")
PY

curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/users/${user_id}/block" >/dev/null
blocked_status="$(curl -sS -o tests/results/premium_flow_blocked.json -w '%{http_code}' -X POST "${API_BASE}/api/v1/premium/activate" \
  -H 'Content-Type: application/json' \
  -d "{\"code\":\"${new_code}\",\"request_number\":\"${request_number}\"}" || true)"
if [[ "${blocked_status}" != "403" ]]; then
  echo "blocked premium user returned ${blocked_status}, expected 403" >&2
  exit 1
fi
python3 - tests/results/premium_flow_blocked.json <<'PY'
import json, sys
payload = json.loads(open(sys.argv[1], encoding="utf-8").read())
detail = payload.get("detail", payload)
if detail.get("error") != "user_blocked":
    raise SystemExit("blocked premium user did not return user_blocked")
print("blocked premium code OK")
PY

reject_request_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium-requests" \
  -H 'Content-Type: application/json' \
  -H 'X-Forwarded-For: 203.0.113.32' \
  -d "{${SMOKE_JSON_META},\"requested_plan\":\"premium_monthly_299\",\"client_id\":\"${client_id}-reject\",\"contact\":\"premium-reject@example.com\",\"comment\":\"Premium reject smoke\"}")"
reject_application_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["application_id"])' "${reject_request_json}")"
reject_request_number="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["request_number"])' "${reject_request_json}")"
reject_json="$(curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/applications/premium/${reject_application_id}/reject" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"smoke rejected"}')"
printf '%s' "${reject_json}" > tests/results/premium_flow_reject.json
rejected_public_json="$(curl -fsS "${API_BASE}/api/v1/premium-requests/by-number/${reject_request_number}")"
printf '%s' "${rejected_public_json}" > tests/results/premium_flow_public_status_rejected.json
python3 - "${rejected_public_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("status") != "rejected":
    raise SystemExit("public request status did not expose rejected state")
if payload.get("rejected_reason") != "smoke rejected":
    raise SystemExit("public request status did not expose rejected reason")
print("premium rejection status OK")
PY

echo "Premium request/code smoke test passed."

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
CSS_FILE="${PROJECT_DIR}/frontend/src/styles.css"
BACKEND_FILE="${PROJECT_DIR}/backend/app/main.py"

cd "${PROJECT_DIR}"
mkdir -p tests/results
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
  echo "ADMIN_TOKEN is required for public launch smoke test" >&2
  exit 1
fi

echo "STL Master public launch smoke test"

suffix="$(date +%s)"
access_payload="{${SMOKE_JSON_META},\"name\":\"Launch Smoke\",\"email\":\"launch-${suffix}@example.com\",\"telegram\":\"@launch_smoke\",\"occupation\":\"3D печать\",\"use_case\":\"Проверка публичного запуска\"}"
premium_payload="{${SMOKE_JSON_META},\"name\":\"Premium Smoke\",\"email\":\"premium-${suffix}@example.com\",\"telegram\":\"@premium_smoke\",\"comment\":\"Хочу подключить Premium по заявке\"}"

access_json="$(curl -fsS -X POST "${API_BASE}/api/v1/access-requests" -H 'Content-Type: application/json' -H 'X-Forwarded-For: 203.0.113.10' -d "${access_payload}")"
premium_json="$(curl -fsS -X POST "${API_BASE}/api/v1/premium-requests" -H 'Content-Type: application/json' -H 'X-Forwarded-For: 203.0.113.11' -d "${premium_payload}")"
printf '%s' "${access_json}" > tests/results/public_launch_access_request.json
printf '%s' "${premium_json}" > tests/results/public_launch_premium_request.json

access_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["application_id"])' "${access_json}")"
premium_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["application_id"])' "${premium_json}")"

admin_headers=(-H "X-Admin-Token: ${ADMIN_TOKEN}")
applications_json="$(curl -fsS "${admin_headers[@]}" "${API_BASE}/api/v1/admin/applications")"
printf '%s' "${applications_json}" > tests/results/public_launch_applications.json
python3 - "${applications_json}" "${access_id}" "${premium_id}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
access_id = sys.argv[2]
premium_id = sys.argv[3]
if not any(item.get("id") == access_id for item in payload.get("early_access", [])):
    raise SystemExit("early access application missing")
if not any(item.get("id") == premium_id for item in payload.get("premium", [])):
    raise SystemExit("premium application missing")
print("applications list OK")
PY

approval_json="$(curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/applications/early_access/${access_id}/approve" -H 'Content-Type: application/json' -d '{"premium_days":7}')"
premium_approval_json="$(curl -fsS "${admin_headers[@]}" -X POST "${API_BASE}/api/v1/admin/applications/premium/${premium_id}/approve" -H 'Content-Type: application/json' -d '{"premium_days":30}')"
printf '%s' "${approval_json}" > tests/results/public_launch_access_approval.json
printf '%s' "${premium_approval_json}" > tests/results/public_launch_premium_approval.json

access_code="$(python3 - <<'PY' "${approval_json}"
import json, sys
payload = json.loads(sys.argv[1])
if not payload.get("access_code"):
    raise SystemExit("access_code missing")
if "Ваша заявка одобрена" not in payload.get("message", ""):
    raise SystemExit("approval message missing")
if payload.get("user", {}).get("access_level") != "early_access":
    raise SystemExit("approved user is not early_access")
print(payload["access_code"])
PY
)"

python3 - <<'PY' "${premium_approval_json}"
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("user", {}).get("access_level") != "premium":
    raise SystemExit("premium approval did not create premium user")
if "Premium" not in payload.get("message", ""):
    raise SystemExit("premium approval message missing")
print("premium approval OK")
PY

stl_file="/tmp/stl-master-public-smoke.stl"
cat > "${stl_file}" <<'STL'
solid cube
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 1 0 0
vertex 0 1 0
endloop
endfacet
endsolid cube
STL

no_code_status="$(curl -sS -o tests/results/public_launch_no_code_upload.json -w '%{http_code}' -H 'X-Forwarded-For: 203.0.113.12' -F "file=@${stl_file};filename=public-smoke.stl" -F 'operations=["analyze","print_check"]' ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload" || true)"
if [[ "${no_code_status}" != "403" ]]; then
  echo "public upload without access code returned ${no_code_status}, expected 403" >&2
  exit 1
fi
grep -q "ранний доступ или Premium" tests/results/public_launch_no_code_upload.json

upload_json="$(curl -fsS -H 'X-Forwarded-For: 203.0.113.13' -H "X-Beta-Access-Code: ${access_code}" -F "file=@${stl_file};filename=public-smoke.stl" -F 'operations=["analyze","print_check"]' ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
rm -f "${stl_file}"
printf '%s' "${upload_json}" > tests/results/public_launch_access_upload.json
python3 - "${upload_json}" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
if payload.get("status") != "queued":
    raise SystemExit("access code upload did not queue job")
if payload.get("access_level") not in {"early_access", "premium"}:
    raise SystemExit("upload response missing access level")
print("access code upload OK")
PY

grep -q "function PublicLanding" "${FRONTEND_MAIN}" || { echo "frontend missing PublicLanding" >&2; exit 1; }
grep -q "Открыть приложение" "${FRONTEND_MAIN}" || { echo "frontend missing open application CTA" >&2; exit 1; }
grep -q "Загрузить STL" "${FRONTEND_MAIN}" || { echo "frontend missing upload CTA" >&2; exit 1; }
grep -q "Смотреть возможности" "${FRONTEND_MAIN}" || { echo "frontend missing feature CTA" >&2; exit 1; }
grep -q "Подключить Premium" "${FRONTEND_MAIN}" || { echo "frontend missing premium header CTA" >&2; exit 1; }
if grep -q "Получить доступ\|Попробовать бесплатно\|Смотреть демо" "${FRONTEND_MAIN}"; then echo "frontend has legacy public CTA label" >&2; exit 1; fi
if grep -q "href=\"#\"\|href=\"#footer\"\|Условия использования\|Политика конфиденциальности" "${FRONTEND_MAIN}"; then echo "frontend has empty or fake public link" >&2; exit 1; fi
grep -q "299 ₽ / месяц" "${FRONTEND_MAIN}" || { echo "frontend missing premium price" >&2; exit 1; }
grep -q "StudioMockup" "${FRONTEND_MAIN}" || { echo "frontend missing studio mockup" >&2; exit 1; }
grep -q "BeforeAfterShowcase" "${FRONTEND_MAIN}" || { echo "frontend missing before/after showcase" >&2; exit 1; }
grep -q "FeaturesSection" "${FRONTEND_MAIN}" || { echo "frontend missing features section" >&2; exit 1; }
grep -q "PremiumShowcase" "${FRONTEND_MAIN}" || { echo "frontend missing premium showcase" >&2; exit 1; }
grep -q "Активировать Premium" "${FRONTEND_MAIN}" || { echo "frontend missing premium code activation state" >&2; exit 1; }
grep -q "Проверить статус" "${FRONTEND_MAIN}" || { echo "frontend missing premium request status action" >&2; exit 1; }
grep -q "premium-requests/by-number" "${FRONTEND_MAIN}" || { echo "frontend missing premium request number status endpoint" >&2; exit 1; }
grep -q "https://vk.ru/3dmodeliron" "${FRONTEND_MAIN}" || { echo "frontend missing official VK support URL" >&2; exit 1; }
grep -q "Написать в поддержку" "${FRONTEND_MAIN}" || { echo "frontend missing VK support CTA" >&2; exit 1; }
if grep -q "vk.com/im?sel=3dmodeliron" "${FRONTEND_MAIN}"; then echo "frontend has forbidden VK dialog URL" >&2; exit 1; fi
if grep -q "https://vk.com/3dmodeliron\|https://vk.com/pechatdlyadoma\|mailto:\|#support" "${FRONTEND_MAIN}"; then echo "frontend has legacy public support URL" >&2; exit 1; fi
grep -q "Заявки" "${FRONTEND_MAIN}" || { echo "frontend missing admin applications tab" >&2; exit 1; }
grep -q "Скопировать сообщение" "${FRONTEND_MAIN}" || { echo "frontend missing copy approval message" >&2; exit 1; }
grep -q "/api/v1/access-requests" "${BACKEND_FILE}" || { echo "backend missing access request endpoint" >&2; exit 1; }
grep -q "/api/v1/premium-requests" "${BACKEND_FILE}" || { echo "backend missing premium request endpoint" >&2; exit 1; }
grep -q "publicSite.*heroV8" "${CSS_FILE}" || { echo "css missing public hero styles" >&2; exit 1; }
grep -q "launchSectionHeader" "${CSS_FILE}" || { echo "css missing public section header styles" >&2; exit 1; }
grep -q "premiumShowcase" "${CSS_FILE}" || { echo "css missing public premium styles" >&2; exit 1; }

echo "Public launch smoke test passed."

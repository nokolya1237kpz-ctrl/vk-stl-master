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
FRONTEND_FILE="${PROJECT_DIR}/frontend/src/main.jsx"
CSS_FILE="${PROJECT_DIR}/frontend/src/styles.css"
BACKEND_FILE="${PROJECT_DIR}/backend/app/main.py"
FEATURES_FILE="${PROJECT_DIR}/config/features.json"

cd "${PROJECT_DIR}"

echo "STL Master public readiness smoke test"

python3 - "${FRONTEND_FILE}" "${CSS_FILE}" "${BACKEND_FILE}" "${FEATURES_FILE}" <<'PY'
from pathlib import Path
import json
import sys

main = Path(sys.argv[1]).read_text(encoding="utf-8")
css = Path(sys.argv[2]).read_text(encoding="utf-8")
backend = Path(sys.argv[3]).read_text(encoding="utf-8")
features = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))

checks = {
    "feature flags file": (
        features.get("surface_recovery") is False
        and features.get("fix_symmetry") is False
        and features.get("local_smoothing") is True
        and features.get("beta_upload_limit_mb") == 100
    ),
    "frontend loads flags": "DEFAULT_FEATURE_FLAGS" in main and "visiblePresetsForFlags" in main and "/config/features.json" in main,
    "public frontend uses same-origin api": (
        "return origin;" in main
        and "hostname === \"localhost\"" in main
        and "`${window.location.protocol}//${window.location.hostname}:8000`" not in main
    ),
    "production frontend forces https api": (
        "hostname === \"app.stlmaster.online\"" in main
        and "hostname.endsWith(\".stlmaster.online\")" in main
        and "return protocol === \"http:\" ? `https://${hostname}` : \"\";" in main
    ),
    "surface hidden by flag": 'featureKey: "surface_recovery"' in main,
    "symmetry hidden by flag": 'featureKey: "fix_symmetry"' in main and "fix_symmetry: false" in main,
    "public launch landing": (
        "function PublicLanding" in main
        and "STL Master" in main
        and "Открыть приложение" in main
        and "Смотреть возможности" in main
        and "Получить ранний доступ" in main
        and "Premium" in main
    ),
    "public access copy": "В режиме раннего доступа принимаются STL до" in main and "Как тестировать" in main,
    "public access form": "function AccessRequestForm" in main and "/api/v1/access-requests" in main,
    "premium request form": "function PremiumAccessModal" in main and "/api/v1/premium-requests" in main and "premium-requests/by-number" in main and "299 ₽ / месяц" in main and "/api/v1/premium/activate" in main,
    "public launch css": ".publicLanding" in css and ".launchHero" in css and ".premiumShowcase" in css and ".premiumComparePanel" in css,
    "feedback panel": (
        "function FeedbackPanel" in main
        and "/api/v1/feedback" in main
        and "data-feedback-panel" in main
        and ".feedbackPanel" in css
        and "Всё хорошо" in main
        and "Опишите проблему перед отправкой." in main
    ),
    "job info panel": (
        "function JobInfoPanel" in main
        and "data-job-info" in main
        and "processing_seconds" in main
        and "Скопировать Job ID" in main
        and ".copyJobButton" in css
        and ".jobInfoPanel" in css
    ),
    "backend features endpoint": (
        "@app.get(\"/api/v1/config/features\")" in backend
        and "load_features" in backend
        and "active_upload_limit_mb" in backend
        and "beta_upload_limit_bytes" in backend
    ),
    "backend public applications": (
        "@app.post(\"/api/v1/access-requests\")" in backend
        and "@app.post(\"/api/v1/premium-requests\")" in backend
        and "@app.get(\"/api/v1/admin/applications\")" in backend
    ),
    "backend feedback endpoint": "@app.post(\"/api/v1/feedback\")" in backend and "FEEDBACK_ROOT" in backend,
    "download contract still present": "final_download_url" in main and "generated_files" in main,
}

missing = [name for name, ok in checks.items() if not ok]
if missing:
    raise SystemExit("BROKEN public readiness contract: " + ", ".join(missing))

print("Static public readiness contract OK")
PY

features_json="$(curl -fsS http://localhost:8000/api/v1/config/features)"
python3 - <<'PY' "${features_json}"
import json
import sys

features = json.loads(sys.argv[1])
assert features["beta_mode"] is True
assert features["surface_recovery"] is False
assert features["fix_symmetry"] is False
assert features["local_smoothing"] is True
assert features["active_upload_limit_mb"] == 100
assert features["absolute_upload_limit_mb"] == 500
print("Feature flags endpoint OK")
PY

oversize_file="/tmp/stl-master-public-oversize.stl"
truncate -s 101M "${oversize_file}"
oversize_response="$(curl --max-time 60 -sS -w $'\nHTTP:%{http_code}\n' \
  -F "file=@${oversize_file};filename=oversize.stl" \
  ${SMOKE_UPLOAD_FIELDS[@]} http://localhost:8000/api/v1/jobs/upload || true)"
rm -f "${oversize_file}"
echo "${oversize_response}" | grep -q "HTTP:413"
echo "${oversize_response}" | grep -q "Для раннего доступа принимаются STL до 100 МБ"
echo "Public upload limit endpoint OK"

feedback_json="$(curl -fsS -X POST http://localhost:8000/api/v1/feedback \
  -H 'Content-Type: application/json' \
  -d "{${SMOKE_JSON_META},\"job_id\":\"beta-smoke\",\"operations\":[\"analyze\",\"print_check\"],\"rating\":\"good\",\"comment\":\"smoke\",\"contact\":\"tester@example.com\"}")"
python3 - <<'PY' "${feedback_json}"
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["status"] == "ok"
assert payload["feedback_id"]
print("Feedback endpoint OK")
PY

feedback_id="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["feedback_id"])' "${feedback_json}")"
feedback_file_json="$(docker-compose exec -T backend cat "/data/results/feedback/${feedback_id}.json")"
python3 - <<'PY' "${feedback_file_json}"
import json
import sys

feedback = json.loads(sys.argv[1])
assert feedback["job_id"] == "beta-smoke"
assert feedback["operations"] == ["analyze", "print_check"]
assert feedback["rating"] == "good"
assert feedback["comment"] == "smoke"
assert feedback["contact"] == "tester@example.com"
assert feedback["timestamp"]
print("Feedback file contract OK")
PY

echo "Public readiness smoke test passed."

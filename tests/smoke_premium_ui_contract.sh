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
  cleanup_response="$(curl --max-time 15 -sS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H 'Content-Type: application/json' \
    -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}" \
    "${api}/api/v1/admin/test-data/cleanup" || true)"
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
MAIN_FILE="${PROJECT_DIR}/frontend/src/main.jsx"
STUDIO_COMPONENTS_FILE="${PROJECT_DIR}/frontend/src/studio/StudioComponents.jsx"
CSS_FILE="${PROJECT_DIR}/frontend/src/styles.css"
STUDIO_CSS_FILE="${PROJECT_DIR}/frontend/src/studio/studio.css"

cd "${PROJECT_DIR}"

echo "STL Master Studio premium/result UI contract smoke test"

python3 - "${MAIN_FILE}" "${STUDIO_COMPONENTS_FILE}" "${CSS_FILE}" "${STUDIO_CSS_FILE}" <<'PY'
from pathlib import Path
import re
import sys

main = Path(sys.argv[1]).read_text(encoding="utf-8")
studio_components = Path(sys.argv[2]).read_text(encoding="utf-8")
css = Path(sys.argv[3]).read_text(encoding="utf-8")
studio_css = Path(sys.argv[4]).read_text(encoding="utf-8")
all_css = css + "\n" + studio_css

legacy_texts = [
    "Пять шагов проверки",
    "Подготовка 3D-моделей к печати",
    "Модель появится здесь",
    "Выберите STL-файл",
]
legacy_selectors = [
    ".appIntro",
    ".uploadPanel",
    ".dropZone",
    ".betaAccessPanel",
    ".operationsPanel",
    ".presetGrid",
    ".actionCard",
]

checks = {
    "no old show changes button": "Показать изменения" not in main,
    "no legacy editor text": not any(text in main for text in legacy_texts),
    "no legacy editor selectors": not any(selector in all_css for selector in legacy_selectors),
    "Studio shell": "className=\"studioShell\"" in main and ".studioShell" in studio_css,
    "Studio header": "function StudioHeader" in studio_components and ".studioHeader" in studio_css,
    "Studio sidebar": "function StudioSidebar" in studio_components and ".studioSidebar" in studio_css,
    "Studio empty state": "function StudioEmptyState" in studio_components and "Загрузите STL-модель" in studio_components,
    "Studio workflow": "function StudioWorkflowBar" in studio_components and ".studioWorkflowBar" in studio_css,
    "Studio inspector": "studioInspector" in main and ".studioInspector" in studio_css,
    "single STL input flow": "studioFileInputRef" in main and "accept=\".stl\"" in main,
    "premium state preserved": "fetchCurrentUser" in main and "currentUser" in main and "Premium" in main,
    "result panels preserved": "function AnalysisResult" in main and "function JobInfoPanel" in main and "function JobHistory" in main,
    "local smoothing preview preserved": "Ожидаемое воздействие" in main and "localSelectionImpact" in main,
    "demo polling skipped": "jobId === \"demo\"" in main,
    "responsive Studio layout": (
        "height: 100dvh" in studio_css
        and "@media (max-width: 1180px)" in studio_css
        and "@media (max-width: 760px)" in studio_css
    ),
}

missing = [name for name, ok in checks.items() if not ok]
if missing:
    raise SystemExit("BROKEN Studio premium/result UI contract: " + ", ".join(missing))

if len(re.findall(r'type=\"file\"', main)) != 1:
    raise SystemExit("BROKEN Studio premium/result UI contract: expected exactly one file input")

print("Studio premium/result UI contract OK")
PY

echo "Studio premium/result UI contract smoke test passed."

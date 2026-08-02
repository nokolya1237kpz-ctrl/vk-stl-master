#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
MAIN_FILE="${PROJECT_DIR}/frontend/src/main.jsx"
COMPONENTS_FILE="${PROJECT_DIR}/frontend/src/studio/StudioComponents.jsx"
CSS_FILE="${PROJECT_DIR}/frontend/src/studio/studio.css"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

grep -q "const resetStudioModel = () =>" "${MAIN_FILE}" || fail "missing root model reset flow"
grep -q "onClearModel={resetStudioModel}" "${MAIN_FILE}" || fail "viewer clear does not call root reset"
grep -q "onSelectFile={requestStudioFile}" "${MAIN_FILE}" || fail "viewer replace-model action is not wired"
grep -q "Загрузить другую модель" "${MAIN_FILE}" || fail "missing replace-model visible label"
grep -q "Сделать снимок" "${MAIN_FILE}" || fail "missing screenshot toolbar label"
grep -q "Сбросить вид" "${MAIN_FILE}" || fail "missing reset-view toolbar label"
grep -q "aria-label=\"Загрузить другую STL-модель\"" "${MAIN_FILE}" || fail "replace-model aria label missing"
grep -q "LaunchIcon type=\"target\"" "${MAIN_FILE}" || fail "toolbar does not use explicit SVG icons"

if grep -q "<span className=\"viewerToolbarHint\"" "${MAIN_FILE}"; then
  fail "legacy viewerToolbarHint markup is still used"
fi

grep -q "useState(activeGroupTitle)" "${COMPONENTS_FILE}" || fail "operation groups are not accordion-controlled"
grep -q "aria-expanded={isOpen}" "${COMPONENTS_FILE}" || fail "accordion aria-expanded missing"
grep -q "Подготовка к печати" "${COMPONENTS_FILE}" || fail "print preparation group missing"
grep -q "Этапы обработки" "${COMPONENTS_FILE}" || fail "process panel label was not renamed"
grep -q "Выбрать STL-файл" "${COMPONENTS_FILE}" || fail "empty state upload button label missing"
grep -q "Результат: STL, ZIP, JSON, TXT" "${COMPONENTS_FILE}" || fail "result format text is not normalized"
grep -q "comingSoon" "${COMPONENTS_FILE}" || fail "unfinished split modes do not keep comingSoon class"

grep -q "Stage 8.1-R: Studio workspace correction" "${CSS_FILE}" || fail "stage correction CSS block missing"
grep -q ".studioToolList\\[hidden\\]" "${CSS_FILE}" || fail "accordion hidden state CSS missing"
grep -q ".viewerToolButton" "${CSS_FILE}" || fail "new viewer toolbar button CSS missing"
grep -q ".studioViewerWorkspace .viewerAxisGizmo" "${CSS_FILE}" || fail "axis gizmo correction CSS missing"
grep -q "min-height: 100dvh" "${CSS_FILE}" || fail "studio shell height correction missing"
grep -q "Скоро" "${CSS_FILE}" || fail "unfinished split modes badge text missing"

echo "Studio workspace correction contract passed."

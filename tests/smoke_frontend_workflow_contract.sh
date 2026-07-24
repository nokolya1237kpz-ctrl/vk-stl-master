#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"
FRONTEND_FILE="${PROJECT_DIR}/frontend/src/main.jsx"
STUDIO_COMPONENTS="${PROJECT_DIR}/frontend/src/studio/StudioComponents.jsx"
STUDIO_CSS="${PROJECT_DIR}/frontend/src/studio/studio.css"

cd "${PROJECT_DIR}"

echo "STL Master frontend workflow contract smoke test"

python3 - "${FRONTEND_FILE}" "${STUDIO_COMPONENTS}" "${STUDIO_CSS}" <<'PY'
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
studio_components = Path(sys.argv[2]).read_text(encoding="utf-8")
studio_css = Path(sys.argv[3]).read_text(encoding="utf-8")

checks = {
    "activePanel state": "const [activePanel, setActivePanel]" in source,
    "StudioHeader component": "function StudioHeader" in studio_components,
    "StudioSidebar component": "function StudioSidebar" in studio_components,
    "StudioEmptyState component": "function StudioEmptyState" in studio_components,
    "StudioWorkflowBar component": "function StudioWorkflowBar" in studio_components,
    "renderStudioSettings": "const renderStudioSettings = () =>" in source,
    "selected operations expansion": "const studioSelectedOperations = expandOperationsForUpload(operationsForMode(selectedMode))" in source,
    "single studio file input": 'className="studioFileInput" type="file" accept=".stl"' in source,
    "demo polling skipped": 'jobId === "demo"' in source,
    "history step activePanel": "activePanel === stepPanelId" in source and "const stepPanelId = `history:${item.step}`" in source,
    "workflow steps": 'const studioSteps = ["Загрузка", "Анализ", "Настройка", "Обработка", "Проверка", "Экспорт"]' in studio_components,
    "studio shell css": ".studioShell" in studio_css and "height: 100dvh" in studio_css,
}

missing = [name for name, ok in checks.items() if not ok]
if missing:
    raise SystemExit("BROKEN missing Studio workflow contract parts: " + ", ".join(missing))

for legacy in [
    "Пять шагов проверки",
    "Новая обработка",
    "Модель появится здесь",
    "Подготовка 3D-моделей к печати",
    "OperationActionCard",
    "AccessNotice",
    "uploadPanel",
    "dropZone",
    "betaAccessPanel",
    "presetGrid",
    "actionCard",
]:
    if legacy in source or legacy in studio_components or legacy in studio_css:
        raise SystemExit(f"BROKEN legacy editor artifact still present: {legacy}")

match = re.search(r"function ProcessingHistoryTimeline\([\s\S]*?\nfunction AnalysisResult\(", source)
if not match:
    raise SystemExit("BROKEN cannot locate ProcessingHistoryTimeline body")
history_body = match.group(0)
if "<details" in history_body or "</details>" in history_body:
    raise SystemExit("BROKEN ProcessingHistoryTimeline still uses uncontrolled <details>")
if "defaultOpen" in history_body:
    raise SystemExit("BROKEN ProcessingHistoryTimeline still uses defaultOpen")
if "aria-expanded={stepOpen}" not in history_body:
    raise SystemExit("BROKEN history steps are not controlled by activePanel")

print("Frontend Studio workflow contract OK")
PY

echo "Frontend workflow contract smoke test passed."

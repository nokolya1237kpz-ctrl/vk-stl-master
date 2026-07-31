# STAGE 7.2.7 — Contextual Workspace Panel

## Scope

Stage 7.2.7 changes only the Studio `/app` right inspector behavior and styling.

No backend, worker, API, processing pipeline, viewer logic, history logic, compare logic, premium logic, routing, or admin code was changed.

## Problem

The previous right panel tried to show too many unrelated surfaces at once:

- current operation settings;
- analysis result;
- job technical information;
- feedback form;
- processing history;
- generated files and technical artifacts.

This made the workspace feel noisy and reduced focus while working with a model.

## New Behavior

The right panel is now contextual:

- **No STL loaded:** a short start hint and upload context only.
- **STL loaded:** current model data and current operation settings.
- **Analysis result:** compact errors, warnings, score, and recommendations.
- **Processing:** active operation, progress, status, estimated wait, and next step.
- **Result:** ZIP/STL/JSON/TXT actions when available, compare, open result, repeat, history, details, and feedback.

History, feedback, technical job details, manifest-like generated data, and full analysis are no longer permanently visible in the inspector.

## Separate Modes

The following content moved behind explicit actions:

- **История:** opens as a separate drawer.
- **Подробнее:** opens job info, full analysis, and generated files.
- **Отзыв:** opens feedback as a separate drawer only after a completed result.

## Changed Files

- `frontend/src/main.jsx`
- `frontend/src/studio/StudioComponents.jsx`
- `frontend/src/studio/studio.css`

## Added UI Structures

- `ContextStartPanel`
- `ContextModelPanel`
- `ContextAnalysisPanel`
- `ContextProcessingPanel`
- `ContextResultPanel`
- `ContextPanelActions`
- `ContextOverlay`

These components are local to the current monolithic frontend file and do not change application routing or data flow.

`StudioComponents.jsx` keeps the Studio workflow contract step labels expected by smoke tests:
`Загрузка`, `Анализ`, `Настройка`, `Обработка`, `Проверка`, `Экспорт`.

## Validation

Build:

- `npm run build` — PASS

Preview checks on `/app`:

- Empty state inspector class: `studioInspector isEmpty contextState-start`
- Demo result inspector class: `studioInspector hasModel contextState-result`
- Horizontal scroll: false
- Old constant blocks inside inspector:
  - `historySection`: false
  - `feedbackPanel`: false
  - `jobInfoPanel`: false
  - `analysisPanel`: false
- Details drawer:
  - overlay visible: true
  - `jobInfoPanel`: true
  - `analysisPanel`: true

Screenshots:

- `docs/stage-07-2.7-context-panel/history-drawer.png`
- `docs/stage-07-2.7-context-panel/result-context.png`

## Notes

The current operation settings remain visible in the model state because they are the active controls for running processing. The old always-visible history, feedback, job info, and generated technical surfaces were moved out of the main inspector.

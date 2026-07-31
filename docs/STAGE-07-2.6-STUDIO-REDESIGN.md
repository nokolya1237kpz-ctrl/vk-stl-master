# Stage 07.2.6 — Studio Workspace Redesign

## Scope

Route: `/app`.

This stage redesigns the Studio workspace UX without changing backend, worker, API, upload logic, viewer processing logic, history logic, compare logic, or premium logic.

Changed implementation files:

- `frontend/src/main.jsx`
- `frontend/src/studio/StudioComponents.jsx`
- `frontend/src/studio/studio.css`

Verification artifacts:

- `docs/stage-07-2.6-studio-redesign/before/`
- `docs/stage-07-2.6-studio-redesign/after/`

## UX Audit Before

The previous Studio screen looked visually polished, but behaved more like a collection of independent cards than a focused production workspace.

Main issues:

- The first action was not obvious. Upload, demo, premium, export, operations, inspector, and workflow competed for attention.
- The demo model could feel like the primary state of the app, while real STL upload should be the first user action.
- The left operation panel was a long flat list. It mixed analysis, repair, optimization, preparation, and export-level actions without a clear mental model.
- The right inspector showed too much information too early. Before a model was loaded, it created noise instead of guiding the user.
- The bottom area felt like a wizard, but the actual product flow is a processing pipeline.
- Viewer actions were visually heavy and competed with the 3D scene.
- Scroll behavior was page-like in places where Studio should feel closer to a desktop app.

User confusion risks:

- "Where do I start?"
- "Is this demo the thing I should edit?"
- "Which actions are required?"
- "What happens after I run processing?"
- "Where is the result?"

## New Workspace Model

The screen is now organized around one primary object: the Viewer.

Hierarchy:

1. Primary: central viewer and upload state.
2. Secondary: grouped operations and current inspector.
3. Supporting: pipeline status, header actions, contextual cards.

## Empty State

The empty Studio state now makes STL upload the primary action:

- Main headline: `Загрузите STL`.
- Supporting concept: `Drag & Drop`.
- Primary CTA: `Выбрать файл`.
- Secondary CTA: `Попробовать демо`.
- The right inspector shows only the next step and expected limits/result formats.

This keeps demo available without presenting it as the main product state.

## Operations

The left panel was reorganized into logical groups:

- `Анализ`
- `Ремонт`
- `Оптимизация`
- `Подготовка`

The long flat list was replaced by grouped cards with short captions. Operations remain the same actions and use the same existing IDs/handlers.

## Viewer

The viewer remains the central workspace.

Changes:

- Viewer keeps the most space in the grid.
- Viewer toolbar was converted into a compact vertical icon rail.
- Toolbar no longer appears as a large text menu over the scene.
- The 3D canvas, preview loading, camera, rotation, screenshot, and status logic are unchanged.

## Inspector

The right panel now uses progressive disclosure:

- Before a file is loaded, it shows only "next step" guidance.
- After a file/demo is loaded, it shows the existing scene, settings, processing, analysis, job info, feedback, and history panels.

No inspector logic was removed.

## Pipeline

The bottom panel now reads as a pipeline:

`Загрузка → Анализ → Ремонт → Оптимизация → Подготовка → Скачать`

The run/download area remains connected to the existing processing handler. Desktop layout was tightened so the button remains visible inside the app shell.

## Responsive Behavior

Checked viewports:

- 1440 × 1000 desktop empty state
- 1440 × 1000 desktop demo state
- 1024 × 900 tablet demo state
- 390 × 900 mobile demo state

Mobile order:

1. Viewer
2. Operations
3. Pipeline
4. Inspector

## Verification

Build:

- `npm run build` PASS.

Automated browser audit:

- Desktop empty: no horizontal scroll.
- Desktop demo: no horizontal scroll.
- Tablet demo: no horizontal scroll.
- Mobile demo: no horizontal scroll.
- Console errors: 0.
- Request failures: 0.

Known build warnings:

- VKUI and VK icons emit existing `"use client"` Rollup warnings.
- Bundle size warning remains unchanged in nature.

## Business Logic

No changes were made to:

- backend;
- worker;
- API;
- route structure;
- upload handlers;
- processing handlers;
- history logic;
- compare logic;
- premium logic;
- admin logic.

The redesign is limited to Studio workspace structure and CSS presentation for the `/app` route.

# STAGE 8.2 — Real Split Geometry and Processing Functionality

## Исходный SHA

`bbb4001bb0b5e7f4c300452baec06a88d6728271`

## Что исправлено

- Убрано двойное отображение иконок Viewer toolbar: старый CSS-блок `::before` с символами `X/Y/Z/◎` удалён, кнопки теперь показывают один SVG и одну подпись при раскрытии.
- Исправлен пользовательский текст в панели результата split: `Clearance/Intersection` заменены на русские подписи `Зазор/Пересечение`.
- Усилен ZIP-export: при успешном split builder дополнительно сверяет реальные `split_part_*.stl` в result directory и добавляет их в `zip_files`, а в конце записывает каждый заявленный файл ровно один раз.
- Исправлена утечка промежуточного `repaired.stl` в split ZIP: если split создал результатные части, fallback `after_file` не добавляет промежуточную модель.
- Добавлен контрактный smoke `tests/smoke_split_result_zip_contract.sh`: ZIP для плоского разреза и разреза со штифтами обязан содержать `split_part_1.stl` и `split_part_2.stl`, а STL должны повторно импортироваться.
- Усилен `tests/smoke_split_pins.sh`: теперь проверяет наличие `split_part_1.stl` и `split_part_2.stl` внутри ZIP.
- Усилен `tests/smoke_split_pins_geometry.sh`: добавлен retry на кратковременный queue-limit между двумя тестовыми jobs.

## Причина двойных иконок

После Stage 8.1-R JSX уже рендерил локальные SVG через `LaunchIcon`, но в `frontend/src/studio/studio.css` остались legacy-правила `.studioViewerWorkspace .viewerToolbar ...::before`, которые добавляли текстовые символы поверх SVG. Источник дублирования удалён, не скрыт через opacity.

## Audit операций

| Операция | Frontend key | Backend/worker | Реальная геометрия | Production-ready |
|---|---|---|---|---|
| Проверить модель | `analyze`, `print_check` | `model_qa`, reports | Геометрию не меняет, создаёт анализ | Да |
| Удалить AI-артефакты | `remove_ai_artifacts` | worker cleanup | Создаёт `cleaned_artifacts.stl` при наличии результата | Частично |
| Улучшить модель | `model_improvement` | worker improvement | Создаёт `improved_model.stl` | Частично |
| Выборочная правка | `local_smoothing` | worker local smoothing | Создаёт `local_smoothed.stl` | Частично |
| Уменьшить вес | `reduce_polygons` | worker reduction | Создаёт `reduced.stl` | Да для базового decimation |
| Применить ориентацию | `apply_orientation` | worker orientation | Создаёт `oriented_model.stl` | Да |
| Подобрать ориентацию | `auto_orientation` | worker auto orientation | Создаёт `oriented_auto.stl` | Да |
| Плоский разрез | `split_model` + `split_mode=simple` | `run_blender_boolean_split` | Создаёт `split_part_1.stl`, `split_part_2.stl` | Да |
| Разрез со штифтами | `split_model` + `split_mode=pins` | Blender boolean integration | Встраивает штифты в часть A и отверстия в часть B | Да для 2 частей и валидного сечения |
| Разрез под стол | `fit_to_bed_split` | worker bed split | Создаёт `bed_part_*.stl` | Да для базового split без интегрированных соединителей |
| Паз-гребень / slots / lock | `split_mode=lock/slots` | Blender/fallback | Есть базовая геометрия/guide, требует отдельного quality pass | Не объявлять как полностью готовое |
| Подготовка пакета | `prepare_package` | ZIP builder | Создаёт `print_report.txt`, `manifest.json`, ZIP | Да |

## Flat split

Основной путь использует Blender `bisect + fill` для planar cut по оси `x/y/z`. После экспорта каждая часть проходит `validate_split_parts`: файл существует, не пустой, содержит vertices/faces и валидный bounding box. ZIP содержит обе части.

## Split with pins

Для `split_mode=pins` worker сначала создаёт две части, затем `integrate_connectors_with_blender` применяет boolean `UNION` для штифтов на `split_part_1.stl` и `DIFFERENCE` для увеличенных отверстий на `split_part_2.stl`. Технологический зазор берётся из `connector_clearance_mm`; smoke проверяет `0.25 мм` и QA `assembly_check_passed`.

## Boolean engine

Используется Blender в worker-контейнере. Если Blender недоступен или QA не проходит, режим pins не маскируется успешным flat split: `require_integrated_pins_or_fail` очищает части и возвращает понятную ошибку.

## ZIP contract

Пользовательский `result.zip` больше не должен содержать только `original.stl` при успешном split. Для split-операций обязательны результатные STL `split_part_1.stl` и `split_part_2.stl`. Промежуточные STL вроде `repaired.stl` не добавляются в split ZIP, если итоговыми результатами являются split parts.

## Tests

Пройдено локально на сервере:

- `npm run build` — PASS.
- `tests/smoke_split_real_model.sh` — PASS.
- `tests/smoke_split_pins.sh` — PASS.
- `tests/smoke_split_pins_geometry.sh` — PASS.
- `tests/smoke_split_result_zip_contract.sh` — PASS.
- `tests/smoke_studio_workspace_correction.sh` — PASS.

## Known limitations

- Полный product-grade auto placement по реальному контуру сечения и внутренним отверстиям остаётся backlog для более сложных моделей.
- Lock/slots/magnets требуют отдельной итерации quality validation перед тем, как обещать их как полностью production-ready.
- VKUI build warnings и large chunk warning остаются существующими не блокирующими предупреждениями.

# STL Master

STL Master - сервис для загрузки, анализа и подготовки STL-моделей к 3D-печати.

Подробная архитектура описана в [ARCHITECTURE.md](ARCHITECTURE.md).
Подробный статус Split 2.0 зафиксирован в [docs/SPLIT_2_STATUS.md](docs/SPLIT_2_STATUS.md).

Текущее стабильное состояние Split 3.1 зафиксировано в [docs/SPLIT_3_1_STATUS.md](docs/SPLIT_3_1_STATUS.md).

## Запуск

На сервере используется `docker-compose` 1.29.2, поэтому команды выполняются через дефис.

Первый запуск или обычный безопасный перезапуск:

```bash
./scripts/restart.sh
```

Скрипт выполняет:

```bash
docker-compose down
docker-compose up -d
```

Volumes не удаляются. Загруженные файлы, Redis data и результаты сохраняются.

## Пересборка frontend

После изменений только во frontend используйте:

```bash
./scripts/rebuild-frontend.sh
```

Скрипт выполняет:

```bash
docker-compose build frontend
docker-compose rm -sf frontend
docker-compose up -d frontend
```

Это обходит проблему `KeyError: ContainerConfig`, которая иногда возникает в `docker-compose` 1.29.2 при обычном пересоздании контейнера после смены image.

## Пересборка всего проекта

После изменений backend, worker или нескольких сервисов используйте:

```bash
./scripts/rebuild-all.sh
```

Скрипт выполняет:

```bash
docker-compose build
docker-compose down
docker-compose up -d
```

`down/up` используется вместо простого `docker-compose up -d`, потому что старая версия `docker-compose` 1.29.2 на сервере иногда падает с `KeyError: ContainerConfig` после изменения образов или volume mounts. Команда `docker-compose down` удаляет контейнеры и network, но не удаляет volumes, если не передавать флаг `-v`.

## Сервисы

- `backend` - FastAPI API для загрузки STL, статусов задач и скачивания результата.
- `frontend` - React + Vite интерфейс с VKUI, Three.js preview и управлением pipeline.
- `worker` - Python worker, читает Redis queue, анализирует STL и формирует ZIP результат.
- `redis` - Redis для очередей и статусов задач.

## Операции обработки

Frontend предлагает готовые режимы, чтобы пользователь не собирал конфликтующие операции вручную:

- `Проверить модель` - анализ, проверка к печати и ZIP-отчёт.
- `Улучшить модель` - исправление сетки, удаление артефактов, исправление нормалей и сглаживание.
- `Уменьшить вес` - улучшение сетки и уменьшение количества полигонов.
- `Разрезать для склейки` - улучшение сетки и разрезание на части.

- `analyze` - легкий анализ STL: тип файла, треугольники, bounding box и габариты.
- `print_check` - базовая проверка пригодности к печати под стол 220x220x250 мм.
- `prepare_package` - формирование ZIP с исходником, отчетами, manifest и normalized info.
- `model_improvement` - пользовательская операция "Улучшить модель": внутри выполняет Print Repair 2.0 через Blender headless и сохраняет `result.print_repair`.
- `fix_symmetry` - пользовательская операция "Исправить симметрию": анализирует симметрию по выбранной оси `x|y|z`, а в режиме `fix` зеркально восстанавливает вторую сторону от более полной половины модели.
- `repair_mesh` и `ai_cleanup` остаются внутренними помощниками старого API. Отдельно пользователю доступна операция `remove_ai_artifacts`.
- `surface_recovery` - пользовательская операция "Восстановить поверхность": через Blender локально сглаживает найденные проблемные зоны поверхности, не трогая острые кромки и границы.
- `reduce_polygons` - MVP-уменьшение полигонов через возможности `trimesh`, если decimation backend доступен в локальном окружении.
- `split_model` - MVP-разделение модели на 2-4 STL-части по выбранной оси. Текущая реализация группирует грани по центроидам и не является точным boolean-разрезанием.

`Улучшить модель` не гарантирует идеальный результат на сложных моделях. Перед печатью итоговый STL нужно проверять в slicer или профильном 3D-инструменте.

`reduce_polygons` не гарантирует выполнение на каждом сервере: в некоторых окружениях `trimesh` не имеет доступного decimation backend. В этом случае задача завершается успешно, но `result.reduce_polygons.success=false`, а ZIP содержит `reduction_report.json` с причиной и рекомендацией подключить более мощный backend decimation позже.

`Улучшить модель` использует мягкую очистку моделей после генераторов и невалидных STL. Параметр `model_improvement_strength` принимает значения:

- `light` - аккуратно: минимально исправляет сетку и нормали.
- `balanced` - баланс: сглаживает поверхность и убирает мелкие артефакты.
- `strong` - сильно: заметнее сглаживает AI-шум, но может немного изменить форму.

`Улучшить модель` сначала выполняет безопасные шаги на `trimesh`, а затем пытается применить Blender headless внутри worker-контейнера. Blender-проход не делает remesh и не уменьшает полигоны внутри улучшения: он удаляет loose geometry, аккуратно объединяет близкие вершины, исправляет нормали и применяет weighted normals. Мягкое сглаживание включается только для `strong`, с очень малым коэффициентом.

Перед принятием `improved_model.stl` worker проверяет quality gate: файл должен существовать, иметь грани, сохранять габариты с отклонением не больше 2% и не терять больше 40% граней, если пользователь отдельно не выбрал уменьшение полигонов. Если проверка не проходит, результат Blender отклоняется, а "После обработки" указывает на более безопасный `repaired.stl` или `original.stl`.

Опциональное поле `model_name` используется только в отчёте. STL Master не восстанавливает геометрию по названию модели.

`Улучшить модель` не гарантирует идеальную параметрическую модель и не заменяет профессиональный ремешинг. Перед печатью итоговый STL нужно открыть в slicer или профильном 3D-инструменте. Если часть действий недоступна в текущем окружении, подробности записываются в отчёты внутри ZIP.

`remove_ai_artifacts` удаляет только отдельные мусорные островки и disconnected components. Если нарост слит с основным корпусом, эта операция его не вырезает: для такого случая нужен advanced cleanup или boolean-обработка.

Параметр `artifact_cleanup_strength` принимает значения `light`, `balanced`, `strong` и управляет тем, насколько агрессивно удаляются отдельные островки.

`Восстановить поверхность` ищет локальный шум, рябь, волнистость, бугры, вытянутые полигоны и неестественные пики. Worker создаёт Blender vertex group только для подозрительных участков и применяет мягкое локальное сглаживание. Результат принимается только если Model QA показывает измеримое улучшение: вырос `health_score` или уменьшился `artifact_score_penalty`. Если проблемных зон нет, STL не создан, quality gate видит изменение bbox больше 3%/объёма больше 5% или значимых улучшений QA не обнаружено, операция завершается controlled failure и `surface_recovered.stl` не применяется.

Smoke-проверка восстановления поверхности:

```bash
./tests/smoke_surface_recovery.sh
./tests/smoke_surface_recovery_quality.sh
```

### Visible Result Contract

Операции, которые обещают улучшение или изменение модели, не должны создавать итоговый STL без измеримого результата. Для таких операций worker добавляет `visible_result`:

```json
{
  "created": true,
  "reason": "Значимые исправления найдены.",
  "changed_metrics": ["health_score", "artifact_penalty"]
}
```

Контракт применяется к `print_repair`, `remove_ai_artifacts`/`ai_cleanup`, `surface_recovery`, `auto_orientation` и `apply_orientation`.

- `print_repair` не публикует `repaired_model.stl`, если health score, artifact penalty, holes, islands и merged vertices не изменились.
- `remove_ai_artifacts` не публикует `cleaned_artifacts.stl`, если артефакты не уменьшились.
- `surface_recovery` не публикует `surface_recovered.stl`, если QA не улучшилась.
- `auto_orientation` при уже оптимальном положении возвращает `no_change_needed=true` и не создаёт `oriented_auto.stl`.
- `apply_orientation` без поворота и без постановки на стол возвращает controlled failure и не создаёт `oriented_model.stl`.

Smoke-проверка:

```bash
./tests/smoke_visible_result_contract.sh
```

### Change Map Contract

Если операция реально создала новый цельный STL и `visible_result.created=true`, worker пытается создать `change_map.json`. Карта изменений сравнивает исходный и итоговый STL по вершинам:

- при одинаковом количестве вершин используется vertex-to-vertex distance;
- при разном количестве вершин используется ближайшая вершина target mesh через KDTree;
- если в исходной модели больше 200 000 вершин, в JSON сохраняются только изменённые вершины.

`result.change_map` содержит:

```json
{
  "available": true,
  "file": "change_map.json",
  "operation": "apply_orientation",
  "changed_vertices": 512,
  "max_distance": 0.82,
  "mean_distance": 0.04,
  "download_url": "/api/v1/jobs/{job_id}/files/change_map.json"
}
```

Карта создаётся для `remove_ai_artifacts`, `surface_recovery`, `print_repair`, `apply_orientation`, `auto_orientation` и `reduce_polygons`. Для `split_model` и `fit_to_bed_split` карта пока не создаётся, потому что результат состоит из нескольких частей.

Smoke-проверка:

```bash
./tests/smoke_change_map.sh
```

### Artifact Map Contract

Если Model QA находит возможные AI-дефекты до обработки, worker создаёт `artifact_map.json`. Карта привязана к исходному STL и содержит индексы подозрительных граней:

- `elongated_face` — вытянутые полигоны;
- `spike` — шипы и наросты;
- `dense_region` / `sparse_region` — подозрительная локальная плотность геометрии.

`result.artifact_map` содержит:

```json
{
  "available": true,
  "file": "artifact_map.json",
  "download_url": "/api/v1/jobs/{job_id}/files/artifact_map.json",
  "faces_count": 43
}
```

Frontend использует эту карту для кнопки `Показать найденные дефекты` и подсвечивает проблемные зоны на исходной модели.

Smoke-проверка:

```bash
./tests/smoke_artifact_map.sh
```

`Исправить симметрию` использует `trimesh`, `numpy` и `scipy.spatial.cKDTree`. Режим `analyze` только считает `symmetry_score` от 0 до 100 и не меняет геометрию. Режим `fix` выбирает более полную сторону модели, зеркалит её относительно центральной плоскости выбранной оси и сохраняет `symmetry_fixed.stl`, если результат валиден и score не стал хуже. Это MVP: перед печатью результат нужно проверить визуально.

`split_model` поддерживает `split_mode`:

- `simple` - простой разрез на части без соединителей.
- `pins` - дополнительно создает отдельный файл `connector_pins.stl` с цилиндрическими штифтами-подсказками.
- `slots` - дополнительно создает отдельный файл `connector_slots.stl` с прямоугольными направляющими/пазами-подсказками.

Для `pins` и `slots` также создается `connector_guide.json`. Соединители пока экспортируются отдельной направляющей геометрией и не встраиваются в детали через boolean-операции. Boolean-встраивание соединителей в части будет следующим этапом.

`split_model` может не сработать на сложных, плоских или невалидных STL, а также не закрывает срезы крышками. Если операция невозможна, задача не падает: `result.split_model.success=false`, а ZIP содержит `split_report.json` с причиной и рекомендациями.






## Advanced AI Cleanup 1.0

`remove_ai_artifacts` теперь не только удаляет disconnected components, но и диагностирует подозрительную геометрию внутри основного mesh:

- вытянутые полигоны;
- длинные тонкие пики;
- аномально плотные участки;
- аномально редкие участки.

На подозрительных вершинах применяется ограниченное локальное сглаживание. Результат проходит quality gate по главному компоненту: bbox не должен измениться больше чем на 3%, volume - больше чем на 5%.

Краткая проверка:

```bash
./tests/smoke_ai_cleanup.sh
```

## Smart Quality Gate 2.0

Print Repair проверяет не только общий bounding box всей сцены, но и главный connected component модели. Это снижает ложные отказы, когда Blender удалил отдельный мусорный остров и поэтому изменился общий bounding box.

В `result.print_repair.quality_gate` сохраняются:

- `main_component_faces_before`;
- `main_component_faces_after`;
- `main_component_bbox_change`;
- `main_component_volume_change`;
- `islands_removed`;
- `reason`.

Ремонт принимается, если главный компонент сохранил не меньше 90% граней, изменил bbox не больше чем на 5% и объём не больше чем на 10%. Удаление отдельных островков допускает больший общий bbox change, если основная геометрия сохранена.

## Model QA

Перед Print Repair 2.0 worker выполняет диагностику STL и сохраняет `result.model_qa`.
Проверяются watertight, non-manifold/open edges, duplicate vertices/faces, degenerate/zero-area faces, disconnected components, tiny islands и inverted normals.

`health_score` от 0 до 100 отображается во frontend как состояние модели:

- `90-100` - отличное;
- `75-89` - хорошее;
- `50-74` - требует исправления;
- `0-49` - плохое.

Smoke-проверка диагностики:

```bash
./tests/smoke_model_qa.sh
```

## Полная проверка проекта

Для регрессионной проверки основных функций используйте:

```bash
./tests/run_all_smoke_tests.sh
```

Скрипт последовательно запускает Model QA, Print Repair, AI Cleanup, Split 2.0 и Final Model Contract. Если любой тест падает, общий запуск завершается ошибкой.

## Очистка тестовых артефактов и места на диске

Smoke-тесты создают реальные STL uploads/results в Docker volumes. Для просмотра занятого места используйте:

```bash
./scripts/disk-usage.sh
```

Для безопасной очистки старых тестовых JSON/ZIP/listing файлов и job-директорий `/data/uploads` и `/data/results` используйте:

```bash
./scripts/cleanup-test-artifacts.sh 24
```

Аргумент задаёт возраст в часах. Например, `./scripts/cleanup-test-artifacts.sh 6` удалит артефакты старше 6 часов. Скрипт не удаляет Docker volumes целиком, не трогает `test-data/Geely_atlas_pro.stl`, код, README, tests и docs, а также защищает активные job со статусом `queued` или `processing`.

## Smoke-тест Print Repair 2.0

Для проверки Blender pipeline подготовки STL к печати используйте:

```bash
./tests/smoke_print_repair.sh
```

Скрипт загружает `test-data/Geely_atlas_pro.stl`, запускает режим "Улучшить модель", проверяет `result.print_repair.success`, скачивание обработанной модели и наличие `repaired_model.stl` в ZIP.

## Smoke-тест Final Model Contract

3D-переключатель "После обработки" зависит от стабильного контракта результата:

- `result.final_model` - имя финального STL-файла;
- `result.final_download_url` - endpoint для скачивания финальной модели;
- файл должен присутствовать в `result.generated_files`.

Для проверки контракта используйте:

```bash
./tests/smoke_final_model_contract.sh
```

Скрипт проверяет `cleaned_artifacts.stl` после удаления AI-артефактов и `repaired_model.stl` после Print Repair, а также делает `curl -I` на `final_download_url`.

## Smoke-тест Split 2.0

Для проверки разрезания на реальной STL-модели используйте:

```bash
./tests/smoke_split_real_model.sh
```

Скрипт прогоняет сценарии `x/simple`, `y/pins`, `z/slots` на `test-data/Geely_atlas_pro.stl`, проверяет успешный статус задачи, скачивание `split_part_1.stl` и отсутствие лишних файлов других операций в ZIP.


## Полная проверка Split 3.1

Для проверки split-модуля используйте:

```bash
./tests/run_split_tests.sh
```

Скрипт запускает базовый split smoke, проверку встроенных connectors и assembly QA.

## Smoke-тест цепочек обработки

Для проверки повторной обработки уже созданных результатов используйте:

```bash
./tests/smoke_chained_processing.sh
```

Скрипт проверяет цепочки `apply_orientation + split_model`, `model_improvement + apply_orientation` и `remove_ai_artifacts + apply_orientation`. Worker выбирает лучший доступный вход для следующей операции в порядке:

```text
oriented_model.stl > cleaned_artifacts.stl > repaired_model.stl > reduced.stl > repaired.stl > original.stl
```

Это нужно, чтобы разрезание резало уже ориентированную модель, а ориентация применялась к отремонтированной, очищенной или уменьшенной модели, если такая модель создана раньше в той же задаче.

## Smoke-тест разрезания под стол

Для проверки автоматического раскроя модели под размер стола принтера используйте:

```bash
./tests/smoke_fit_to_bed_split.sh
```

Скрипт генерирует длинную тестовую коробку 500x120x80 мм, проверяет разрезание под стол 220x220x250 мм, валидность `bed_part_*.stl`, попадание частей в ZIP и отдельно прогоняет реальную модель `test-data/Geely_atlas_pro.stl`.

Полный regression pack также запускает этот тест:

```bash
./tests/run_all_smoke_tests.sh
```

## Лимиты безопасности

- Beta upload limit: 100 MB. В первой волне тестирования backend отклоняет файлы больше лимита с HTTP 413 и сообщением “В beta-тесте принимаются STL до 100 МБ”.
- Absolute safety hard limit: 500 MB. Этот технический потолок остаётся в коде как защита сервера и не является публичным beta-лимитом.
- Processing soft limit по размеру: 300 MB. Для таких файлов worker выполняет только `analyze`, `print_check` и `prepare_package`; тяжелые операции пропускаются.
- Processing soft limit по геометрии: 2 000 000 треугольников. `repair_mesh`, `reduce_polygons` и `split_model` пропускаются, чтобы не перегрузить сервер.

Если операция пропущена лимитами, job остается `completed`, а причины записываются в `result.skipped_operations` и отчеты внутри ZIP.

## Состав результата

После завершения задачи worker добавляет в `result.generated_files` список файлов, реально попавших в ZIP. Каждый элемент содержит `name`, `type`, русскую `label` и `download_url`, например:

```json
{"name": "reduced.stl", "type": "model", "label": "Уменьшенная модель", "download_url": "/api/v1/jobs/{job_id}/files/reduced.stl"}
```

Frontend использует этот список для блока "Состав результата" и группирует файлы на модели, части и отчеты. `manifest.json` внутри ZIP содержит тот же `generated_files`, чтобы состав архива можно было проверить без обращения к API.

Скачать весь результат можно через:

```bash
GET /api/v1/jobs/{job_id}/download
```

Скачать отдельный файл можно через:

```bash
GET /api/v1/jobs/{job_id}/files/{filename}
```

Backend отдает только файлы, которые перечислены в `result.generated_files`, и отклоняет вложенные пути или `../`.

## Порты

- `3000` - frontend через Nginx.
- `8000` - backend FastAPI.
- Redis доступен внутри Docker-сети на `redis:6379` и не публикуется наружу.

## Проверка

Backend healthcheck:

```bash
curl http://localhost:8000/health
```

Backend status:

```bash
curl http://localhost:8000/api/v1/status
```

Frontend:

```bash
curl -I http://localhost:3000
```

## Beta release preparation

Документы для закрытого тестирования:

- `docs/BETA_READINESS_REPORT.md` - аудит готовности, риски и список того, что нельзя рекламировать.
- `docs/BETA_TEST_GUIDE.md` - короткая инструкция для beta-тестировщиков.
- `docs/BETA_LAUNCH_CHECKLIST.md` - checklist перед приглашением пользователей.
- `docs/BETA_LAUNCH_SUMMARY.md` - итоговая сводка первого beta-запуска.

Feature flags находятся в:

```bash
config/features.json
```

Frontend читает `/config/features.json` и скрывает отключённые функции. Backend также отдаёт текущие флаги:

```bash
curl http://localhost:8000/api/v1/config/features
```

Для первой закрытой beta-волны активный upload limit задаётся через `beta_upload_limit_mb` в `config/features.json` или env `BETA_UPLOAD_LIMIT_MB`. Сейчас публичный лимит: 100 МБ. Абсолютный защитный лимит backend: 500 МБ.

В beta-режиме frontend показывает предупреждение:

```text
STL Master находится в стадии тестирования.
Некоторые функции могут работать неидеально.
```

После завершения обработки пользователь видит:

- блок “Информация о задаче”;
- итоговый STL и ZIP;
- форму обратной связи.

Отзывы сохраняются JSON-файлами в `/data/results/feedback` через endpoint:

```bash
POST /api/v1/feedback
```

Beta smoke-тест:

```bash
./tests/smoke_beta_readiness.sh
```

Полная проверка проекта:

```bash
./tests/run_all_smoke_tests.sh
```

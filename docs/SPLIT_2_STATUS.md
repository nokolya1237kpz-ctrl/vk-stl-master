# Split 2.0 Status

Документ фиксирует стабильное состояние функции `split_model` перед следующим этапом разработки.

## Что уже работает

- `split_engine=blender_boolean` используется как основной движок разрезания, если Blender доступен в `worker`-контейнере.
- `safe_mvp` сохранён как fallback-движок для окружений без Blender или для ручной диагностики.
- Worker проверяет валидность каждой созданной части:
  - STL-файл существует;
  - размер файла больше 0;
  - `faces > 0`;
  - `vertices > 0`;
  - bounding box валиден;
  - часть не выглядит подозрительно маленькой относительно исходной модели.
- Пустые или битые `split_part_*.stl` не попадают в результат.
- Если разрезание не может создать валидные части, задача завершается controlled failure: `job` не падает, но `result.split_model.success=false`.
- ZIP содержит только файлы, относящиеся к выбранной обработке:
  - `original.stl`;
  - `split_part_*.stl`, если части валидны;
  - `connector_pins.stl` или `connector_slots.stl`, если выбран соответствующий режим и guide-файл валиден;
  - `connector_guide.json`, если есть guide-соединители;
  - `print_report.txt`;
  - `manifest.json`.
- `pins` и `slots` пока создаются как отдельные guide STL-файлы:
  - `connector_pins.stl`;
  - `connector_slots.stl`;
  - `connector_guide.json`.
- В `result.split_model.connectors.integrated` честно возвращается `false`, если соединители не встроены в детали.

## Что ещё не реализовано

- Встроенные штифты и пазы внутри самих `split_part_*.stl`.
- Boolean add/subtract connectors в деталях:
  - добавление выступа на одной части;
  - вычитание ответного отверстия или паза на соседней части.
- Допуски посадки для печати:
  - зазор под FDM/SLA;
  - компенсация усадки;
  - настройка диаметра штифтов и размеров пазов.
- Автоматическая проверка собираемости:
  - совпадение пар соединителей;
  - отсутствие пересечений;
  - проверка, что части можно собрать после печати.

## Текущая проверка

Smoke-тест для реальной модели:

```bash
./tests/smoke_split_real_model.sh
```

Тест использует:

```text
/home/codex/projects/vk-stl-master/test-data/Geely_atlas_pro.stl
```

Проверяемые сценарии:

- `x/simple`
- `y/pins`
- `z/slots`

Для каждого сценария проверяется:

- `status=completed`;
- `result.split_model.success=true`;
- `split_part_1.stl` скачивается через API с HTTP 200;
- ZIP не содержит лишние пользовательские модели из других операций:
  - `improved_model.stl`;
  - `reduced.stl`;
  - `cleaned_artifacts.stl`;
  - `repaired.stl`.

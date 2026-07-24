# Split 3.1 Status

Split 3.1 зафиксирован как стабильный модуль инженерного разрезания STL для печати и склейки.

## Что работает

- `split_engine=blender_boolean` используется как основной путь разрезания.
- `safe_mvp` остается fallback-режимом для случаев, когда Blender недоступен или boolean/bisect не дает валидные части.
- `split_mode=pins` создает встроенные штифты в `split_part_*.stl`.
- `split_mode=slots` создает встроенные пазы/направляющие в `split_part_*.stl`.
- Для успешного встраивания `result.split_model.connectors.integrated=true`.
- Настройки соединителей:
  - `connector_size_mm`;
  - `connector_clearance_mm`;
  - `connector_count`.
- После встраивания выполняется connector QA:
  - bounding box обеих частей;
  - площадь плоскости разреза;
  - количество соединителей;
  - проверка расположения рядом с плоскостью разреза;
  - проверка, что соединители не выходят за расчетные границы;
  - `minimum_clearance_mm`;
  - `maximum_intersection_mm`;
  - `assembly_check_passed`.
- Если boolean-встраивание или QA не проходят, модуль не делает вид, что соединители встроены:
  - `integrated=false`;
  - сохраняется честная `reason`;
  - при возможности создаются отдельные guide-файлы как fallback.
- ZIP для `integrated=true` содержит только пользовательские файлы:
  - `original.stl`;
  - `split_part_1.stl`;
  - `split_part_2.stl`;
  - `print_report.txt`;
  - `manifest.json`.

## Ограничения

- Проверка посадки математическая и не заменяет тестовую печать.
- На сложных, поврежденных или нестандартных STL возможен fallback.
- Boolean-операции Blender могут быть чувствительны к качеству сетки.
- Допуски посадки зависят от принтера, пластика, сопла, усадки материала и настроек слайсера.
- Даже при `assembly_check_passed=true` пользователь должен проверить посадку в слайсере и при необходимости сделать тестовую печать небольшого участка.

## Smoke-тесты

Для проверки только split-модуля:

```bash
./tests/run_split_tests.sh
```

Скрипт запускает:

- `tests/smoke_split_real_model.sh`;
- `tests/smoke_split_connectors.sh`;
- `tests/smoke_split_assembly.sh`.

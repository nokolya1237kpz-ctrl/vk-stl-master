# Screenshots Blocked

Stage: 05.4 Features

## Проверенные варианты

- Серверные браузеры:
  - `chromium`
  - `chromium-browser`
  - `google-chrome`
  - `google-chrome-stable`
- Проектные scripts:
  - `dev`
  - `build`
  - `preview`
- Локальный CDP endpoint:
  - `http://127.0.0.1:9222/json/version`

## Результат

- На сервере Chrome/Chromium не найден.
- CDP endpoint не ответил.
- В Stage 5.3 уже подтверждено, что локальный headless Chrome завершается с macOS `EPERM`.
- В Stage 5.3 также была недоступна npm registry для временной установки Playwright.

## Что требуется для будущей визуальной проверки

Один из вариантов:

- установить Chromium/Chrome на сервер для headless screenshot sweep;
- либо поднять стабильный Chrome с remote debugging port на локальной машине;
- либо добавить Playwright как dev-зависимость отдельным согласованным этапом.

Без этого screenshots, viewport sweep, zoom check и manual screenshot review остаются `BLOCKED`, а не `PASS`.

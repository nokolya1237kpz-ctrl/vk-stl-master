# ЭТАП 1 — HERO SCREEN + STICKY HEADER

## Цель
Первый экран должен выглядеть как профессиональный CAD/SaaS-продукт, а не как обычный лендинг.

Пользователь за 5 секунд должен понять:

- STL Master работает с STL-моделями;
- сервис исправляет модели;
- умеет разрезать большие STL;
- добавляет штифты, магниты и фигурные замки;
- готовит модель к 3D-печати;
- отдаёт ZIP с готовыми файлами.

---

## Desktop Artboard

- artboard: `1920×1080`
- content container: `1440 px`
- hero max width: `1520 px`
- hero min height: `920 px`
- background: `#05070D`
- secondary background: `#07101D`

Фон: тёмный, инженерный, с мягкими cyan/blue glow.  
Запрещены ромбики, случайные декоративные линии, слабые силуэты машин.

---

## Sticky Header

Header должен быть всегда виден при скролле.

Размер:

- width: `1200 px`
- height: `66 px`
- top: `16 px`
- border-radius: `999 px`
- z-index: `100+`

Стиль:

```css
background: rgba(8,14,26,.76);
backdrop-filter: blur(24px);
border: 1px solid rgba(255,255,255,.12);
box-shadow: 0 18px 70px rgba(0,0,0,.34);
```

Состав:

```text
STL Master

Возможности
Соединения
До / После
Premium
Контакты

Получить доступ
```

CTA `Получить доступ`:

- gradient: `#35D7FF → #6379FF`
- text: `#04111D`
- height: `44 px`
- radius: `999 px`

---

## Hero Layout

Две колонки:

```text
Left: 45%
Right: 55%
Gap: 58–64 px
```

Контейнер hero:

- width: `1280–1440 px`
- top spacing после header: `70–90 px`

---

## Left Column

Label:

```text
⚡ Профессиональная подготовка STL
```

Hero title:

```text
Подготовьте STL к печати за минуты
```

Параметры:

- font-size: `78–84 px`
- line-height: `0.92–0.96`
- font-weight: `900`
- letter-spacing: `-0.075em`

`STL к печати` — gradient text:

```css
linear-gradient(90deg,#fff,#8CEBFF,#8C9AFF)
```

Description:

```text
Исправляйте модели, разрезайте большие STL, добавляйте штифты, магниты и замки, проверяйте результат перед отправкой в слайсер.
```

Buttons:

```text
Открыть демонстрацию
Получить ранний доступ
Premium
```

Chips:

```text
Разрез
Штифты
Магниты
Замки
AI Cleanup
```

---

## Right Column — STL Master Studio

Справа не картинка, а mockup приложения.

Размер:

- width: `760–820 px`
- height: `590–620 px`
- radius: `36–38 px`

Верхняя панель:

```text
Repair
Split + Pins
Check
```

Активная вкладка:

```text
Split + Pins
```

Левая панель инструментов:

```text
Исправление
Разрез
Штифты
Магниты
Замок
Проверка
```

Активные:

```text
Разрез
Штифты
```

Центральный viewport:

- тёмная CAD-сцена;
- grid;
- модель sci-fi drone / mechanical model;
- тонкая split plane;
- visible pins;
- HUD.

Правый meta panel:

```text
original.stl загружен
Split plane готов
connector_report.json
ZIP результата
Скачать STL
```

---

## HUD

Внизу viewport:

```text
Качество
65 → 88
```

```text
Результат
part_A/B.stl
```

```text
Очередь
#1
```

---

## Animations

Header:

- остаётся сверху;
- при scroll становится чуть темнее;
- shadow усиливается.

Buttons:

```css
transform: translateY(-2px);
filter: saturate(1.12);
```

Studio mockup:

- optional режимы каждые 3–4 секунды:
  - Repair
  - Split + Pins
  - Magnets
  - Print Check

Переход:

`350–500ms ease`

Не делать быстрое вращение, кислотные эффекты и мигание.

---

## Mobile

- header compact;
- menu → hamburger;
- hero в одну колонку;
- сначала текст, потом studio mockup;
- кнопки в столбик;
- mobile h1: `42–48 px`.

---

## Acceptance Checklist

- sticky header виден после scroll;
- меню desktop в одну строку;
- справа есть STL Master Studio mockup;
- видны Split + Pins;
- есть `part_A/B.stl`;
- есть `connector_report.json`;
- есть `65 → 88`;
- нет старых ромбиков;
- нет 990 ₽.

---

## Codex Scope

Работать только:

```text
frontend/src/main.jsx
frontend/src/styles.css
frontend/public/assets/marketing/*
tests/smoke_public_design_contract.sh
```

Не менять backend, worker, API, очередь, заявки, админку и бизнес-логику.

Проверки:

```bash
npm run build
./tests/smoke_public_design_contract.sh
./tests/smoke_public_launch.sh
./tests/run_all_smoke_tests.sh
```

# FINAL CODEX PROMPT — STL Master Public Website Redesign

## ВАЖНО

Это новая сессия Codex. Не пытайся продолжать старую сессию, где была ошибка `Bad Request`.

Используй текущее состояние проекта на диске как исходную точку.

Рабочая директория проекта:

```bash
/home/codex/projects/vk-stl-master
```

Перед началом обязательно:

```bash
cd /home/codex/projects/vk-stl-master
git status --short || true
ls -la
```

Ничего не откатывай без отдельного запроса.

## Главная задача

Аккуратно обновить публичную часть сайта STL Master по дизайн-пакету из четырёх этапов.

Папки дизайн-пакета:

```text
STL_Master_Stage_01_Hero/
STL_Master_Stage_02_Product_Sections/
STL_Master_Stage_03_Premium_Forms_Footer/
STL_Master_Stage_04_Motion_Final_Polish/
```

В каждой папке есть:

```text
SPEC.md
*_preview.html
CODEX_PROMPT_STAGE_*.md
README.md
```

Сначала изучи все 4 этапа, затем сделай один цельный план внедрения.

## Что НЕ менять

Не менять:

```text
backend
worker
API
очередь
админку
заявки
business logic
upload gate
docker-compose.yml
.env
production secrets
```

Не запускать команды, которые меняют `.env`, пароли, nginx, systemd или backend-секреты.

Работать только:

```text
frontend/src/main.jsx
frontend/src/styles.css
frontend/public/assets/marketing/*
tests/smoke_public_design_contract.sh
```

## Обязательные требования

### 1. Hero + Sticky Header

По Stage 01:

- sticky glass header всегда виден при скролле;
- пункты desktop menu помещаются в один ряд;
- CTA справа: `Получить доступ`;
- Hero headline: `Подготовьте STL к печати за минуты`;
- справа mockup `STL Master Studio`;
- в mockup видны:
  - `Repair / Split + Pins / Check`;
  - `Исправление / Разрез / Штифты / Магниты / Замок / Проверка`;
  - viewport с моделью;
  - split plane;
  - pins;
  - `65 → 88`;
  - `part_A/B.stl`;
  - `connector_report.json`;
  - `Скачать STL`.

### 2. Product Sections

По Stage 02:

- секция `Как STL Master готовит модель`;
- 5 шагов:
  - Загрузить STL;
  - Исправить;
  - Разрезать;
  - Соединения;
  - Скачать ZIP;
- секция `Соединения после разреза`;
- показать:
  - Обычный разрез;
  - Стык под клей;
  - Штифты;
  - Магниты `5×2 / 6×2 / 8×3 / 10×3`;
  - Фигурный замок;
- секция `Ключевые функции`;
- блок `До / После`;
- полный список возможностей.

### 3. Premium + Forms + Footer

По Stage 03:

- Premium section;
- цена строго `690 ₽ / месяц`;
- не использовать `990 ₽`;
- Early Access form;
- Premium Request form;
- success state для Early Access;
- success state для Premium;
- кнопка `Скопировать сообщение`;
- ссылки:
  - `https://vk.com/3dmodeliron`
  - `https://vk.com/pechatdlyadoma`
  - `https://t.me/chat_pechatdlyadoma`
- не использовать `vk.com/im?sel=3dmodeliron`;
- Reviews section;
- FAQ section;
- Footer.

### 4. Motion + Final Polish

По Stage 04:

- единая motion system;
- reveal-анимации секций;
- hover-анимации карточек;
- живые кнопки;
- sticky header compact-on-scroll;
- активный пункт меню;
- плавные transitions;
- mobile адаптив;
- без лишних библиотек, если можно сделать на CSS/React.

## Дизайн-ограничения

Запрещено:

```text
старые CSS-ромбики
слабые силуэты автомобилей
огромные светящиеся стены вместо разреза
большие чёрные ползунки
кислотный неон
перегруженные панели
```

Сайт должен выглядеть как профессиональный SaaS/CAD продукт, а не как обычный лендинг.

## Безопасный порядок работы

1. Изучи текущие файлы:

```bash
sed -n '1,240p' frontend/src/main.jsx
sed -n '1,260p' frontend/src/styles.css
```

2. Изучи дизайн-пакет:

```bash
find . -maxdepth 3 -type f | sort
```

3. Составь короткий план.

4. Внеси изменения только во frontend.

5. Запусти сборку:

```bash
npm run build
```

6. Запусти тесты:

```bash
./tests/smoke_public_design_contract.sh
./tests/smoke_public_launch.sh
./tests/run_all_smoke_tests.sh
```

Если один тест падает из-за устаревшего визуального контракта, обнови только `tests/smoke_public_design_contract.sh`, не меняя backend/API.

## Перед изменениями сделай backup

```bash
mkdir -p /home/codex/projects/vk-stl-master/.codex-backups/public-redesign
cp frontend/src/main.jsx /home/codex/projects/vk-stl-master/.codex-backups/public-redesign/main.jsx.$(date +%Y%m%d-%H%M%S).bak
cp frontend/src/styles.css /home/codex/projects/vk-stl-master/.codex-backups/public-redesign/styles.css.$(date +%Y%m%d-%H%M%S).bak
```

## Отчёт в конце

Показать:

- изменённые файлы;
- что сделано по Stage 01;
- что сделано по Stage 02;
- что сделано по Stage 03;
- что сделано по Stage 04;
- что не менялось;
- результаты `npm run build`;
- результаты smoke tests;
- есть ли оставшиеся проблемы.

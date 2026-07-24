# Component Priority

Статус: оценка для будущего восстановления. Ничего не заменяется на этом этапе.

## 1. Можно использовать без изменений

Эти элементы уже имеют понятную роль и могут быть сохранены как основа после проверки скриншотами.

- `SectionHeader` / `launchSectionHeader`: единый паттерн секционных заголовков уже существует.
- `LaunchIcon`: локальный SVG helper покрывает несколько действий и не требует нового icon kit.
- `historyStatus`: существующие state classes подходят для нормализации статусов.
- `qualityPill`: понятный status pill для качества модели.
- `compareModeTabs`: повторяемый segmented control для compare.
- `workflowPanel`: существующий accordion-паттерн для этапов обработки.
- `historyFiles`: раскрываемый список файлов результата.
- `premiumButtonSpinner`: существующий loader для Premium flow.
- `adminTable`: базовая таблица уже присутствует и может быть стабилизирована визуально.

## 2. Нужно немного доработать

Эти элементы лучше сохранить, но привести к единой системе размеров, radius, spacing, hover/focus states.

- `primaryCta`, `secondaryCta`: привести размеры, icon/text alignment и mobile wrapping.
- `publicTopCta`, `premiumHeaderButtonV9`: стабилизировать ширину, иконку и текст в header.
- `connectionsCtaButton`: привести к общей CTA системе.
- `heroBenefits`: нормализовать card height/gap/icon placement.
- `connectionCard`: выровнять media crop, убрать артефакты изображений, сохранить текущую структуру.
- `demoCompareCard`: выровнять slider, metrics и panels без изменения logic.
- `previewPanel`: нормализовать header/status/help/actions spacing.
- `compareToolbar`: унифицировать toolbar density with Studio controls.
- `generatedFilesPanel`: привести списки файлов к History card grammar.
- `premiumAccessModal`: сохранить state machine, стабилизировать размеры/scroll/content.
- `adminToolbar`, `adminBulkBar`, `adminPagination`: привести к одному размерному ряду.
- `adminSidebar`: стабилизировать collapsed/expanded rhythm.

## 3. Нужно полностью заменить или переосмыслить визуально

Это не означает удалить компонент. Это означает, что в будущем визуальный паттерн надо заменить аккуратно, сохраняя DOM/API/state до отдельного разрешения.

- Разрозненные legacy button rules в `styles.css`: много перекрытий и `!important`, нужен единый button grammar.
- Повторяющиеся card patterns между Landing/Studio/Admin: нужен общий визуальный язык, но не общий React-компонент на ближайшем этапе.
- Tooltip/dropdown layer: проектного паттерна почти нет; при появлении нужно описать заново, а не копировать VKUI/Material шаблон.
- Skeleton layer: проектный reusable skeleton не найден; будущий skeleton надо создавать только после подтверждения реальных loading states.
- Admin destructive action visuals: требуют отдельной визуальной модели безопасности, но без изменения бизнес-логики.
- Marketing Studio mockup visual layer: можно восстановить визуально, но нельзя заменять настоящую верстку скриншотом.

## Правило приоритета

Компоненты категории 2 сначала исправлять scoped CSS. Категория 3 требует отдельного задания, скриншотов до/после и проверки `/`, `/app`, `/admin`.

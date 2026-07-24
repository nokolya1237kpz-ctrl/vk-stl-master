# UI Rules

Статус: правила будущего UI Framework на основе существующего STL Master. Не подключено к приложению.

## Общие правила

- Не менять бизнес-логику ради визуального порядка.
- Не менять API calls, routing, upload, processing, premium state, admin mutations.
- Не подключать новый UI kit.
- Не вводить Bootstrap/Material/Tailwind UI patterns.
- Использовать существующие компоненты и class contracts как источник истины.

## Карточки

- Карточки одного ряда используют согласованный radius и высоту.
- Media внутри карточек не получает случайных белых рамок и не растягивается непропорционально.
- Hover применяется только к интерактивным карточкам.
- Карточка не должна быть декоративной оболочкой вокруг другой декоративной карточки.

## Панели

- Панель имеет header, content и optional actions.
- Viewer/panel borders должны быть тонкими и инженерными.
- Elevation используется для слоя, а не для украшения.
- Панели Studio плотнее Landing-панелей.

## Секции

- Каждая landing section использует единый section header pattern.
- Section kicker: номер акцентный, label muted, uppercase.
- Вертикальные отступы секций должны быть из spacing scale.
- Mobile spacing уменьшается, но hierarchy сохраняется.

## Кнопки

- Primary action один на визуальную область.
- Secondary/ghost actions не конкурируют с primary.
- Icon + text выравниваются по одной системе.
- Кнопка не меняет размер при loading/success/error.
- Danger actions не используют primary gradient.
- Disabled state сохраняет читаемость текста.

## Поля и формы

- Поля используют единый height ряд.
- Label, helper text и error text имеют стабильные отступы.
- Ошибка не должна менять ширину формы.
- Admin forms должны быть плотнее public forms.

## Таблицы

- Таблицы используют фиксированную визуальную плотность.
- Bulk action bar появляется как отдельный слой и не сдвигает смысловые controls хаотично.
- Status, actions и pagination имеют повторяемые размеры.
- Длинный текст truncates predictable.

## Viewer

- Модель главный объект; UI overlays вторичны.
- Grid, gizmo, section plane, legend не должны перекрывать ключевые части модели.
- Cyan используется как акцент, не как заливка всей модели.
- HUD/toolbar не должны пересекаться с моделью и важными controls.

## Sidebar

- Один active state.
- Icons and labels use consistent spacing.
- Collapsed sidebar keeps recognizable icons.
- Sidebar actions do not change width on hover.

## Модальные окна

- Modal keeps one primary action.
- Close button always visible.
- Error/success/loading states preserve modal width.
- Long content uses internal scroll only when necessary.
- Premium flow visuals cannot change flow logic.

## Уведомления и предупреждения

- Warning is informative, danger is actionable.
- Inline alert must contain cause and next step.
- Admin dangerous operations require stronger visual separation.

## Progress, skeleton, loaders

- Spinner size is stable.
- Progress labels use existing status language.
- Skeleton pattern is not established yet; do not invent until loading states are mapped.
- Loader cannot hide recoverable errors.

## Hover/focus/motion

- Hover model: slight border/elevation change, not dramatic movement.
- Focus visible required for keyboard actions.
- Motion uses shared duration and easing tokens from Stage 02 docs.
- No aggressive glow pulse for work tools.

## Containers

- Public containers follow the established landing width system.
- Studio uses full working area and avoids marketing-style whitespace.
- Admin uses table-first density.

## Проверка будущей правки

Каждая визуальная правка обязана проверить:

- build;
- `/`;
- `/app`;
- `/admin`;
- no horizontal scroll;
- no console errors;
- no failed API requests introduced;
- screenshots before/after.

# Button Example

Описание будущего восстановления существующих кнопок, без кода.

Источник: `primaryCta`, `secondaryCta`, `premiumFlowButton`, `adminToolbar button`, `compareModeTabs button`.

## Состояния

- Default: текст и иконка выровнены, размер стабилен.
- Hover: лёгкое усиление border/elevation.
- Focus: видимая обводка без сдвига layout.
- Disabled: доступный muted text, действие явно недоступно.
- Loading: spinner не меняет ширину кнопки.
- Danger: отдельная визуальная модель, не primary gradient.

## После восстановления

Все существующие кнопки должны сохранять текущие действия и обработчики. Меняется только визуальная согласованность.

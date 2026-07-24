# Spacing System

Статус: документация. Не подключено к приложению.

STL Master использует 4px-based spacing scale. Сетка должна помогать инженерной точности: одинаковые интервалы, предсказуемые группы controls, стабильные панели.

| Token | Value | Use |
|---|---:|---|
| 1 | 4px | micro gaps, icon/text adjustment |
| 2 | 8px | compact controls, table cell inner gaps |
| 3 | 12px | button padding, compact card content |
| 4 | 16px | default component padding, toolbar gaps |
| 5 | 20px | medium card padding, modal inner rhythm |
| 6 | 24px | section subgroups, form groups |
| 8 | 32px | landing block internal gaps, panel groups |
| 10 | 40px | desktop section rhythm |
| 12 | 48px | hero grid gap, major column gap |
| 16 | 64px | section vertical spacing |
| 20 | 80px | desktop container gutter |
| 24 | 96px | large landing section separation |

## Правила

- Не использовать случайные значения, если есть близкий шаг шкалы.
- Для Studio отдавать приоритет плотности: 8, 12, 16, 20.
- Для Landing отдавать приоритет дыханию: 24, 32, 48, 64, 80.
- Для Admin использовать предсказуемую табличную плотность: 8, 12, 16, 24.
- Mobile layout должен сжимать интервалы на 1-2 шага, но не ломать иерархию.
- Визуальные правки будущих этапов должны описывать, какой spacing token был применён и почему.

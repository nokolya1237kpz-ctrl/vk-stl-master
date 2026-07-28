# Stage 05.8 - FAQ and Footer

## Source

Repository: https://github.com/nokolya1237kpz-ctrl/vk-stl-master
Initial SHA: 0b59487a5cf95a26ed54513acb938a74ba8b096e
Scope: public landing FAQ, Footer and transitions between Premium, FAQ and Footer.

## Boundaries

Changed runtime file:
- frontend/src/styles.css

Documentation and screenshots:
- docs/STAGE-05-8-FAQ-FOOTER.md
- docs/stage-05-8-faq-footer/before/
- docs/stage-05-8-faq-footer/after/

No JSX, API, backend, worker, Studio, Admin, Premium logic, routing, upload, viewer or history logic was changed.

## FAQ Content

FAQ item count: 12

Questions in preserved order:
1. Какие файлы поддерживает STL Master?
2. Нужно ли устанавливать программу?
3. Что STL Master проверяет в модели?
4. Может ли STL Master исправить повреждённую модель?
5. Можно ли уменьшить количество полигонов?
6. Можно ли разрезать модель на части?
7. Какие соединения поддерживаются?
8. Сохраняется ли исходная модель?
9. Что я получу после обработки?
10. Гарантирует ли сервис успешную печать?
11. Чем бесплатный режим отличается от Premium?
12. Как связаться с поддержкой?

Categories preserved:
- Начало работы
- Обработка
- Файлы и результаты
- Тарифы и доступ
- Поддержка

Answers were not changed.
Search text, categories and empty state text were not changed.
FAQ JSON-LD schema was not changed.

## Interaction Model

The existing model is preserved:
- one open item at a time through openId state;
- first item is open by default;
- clicking the currently open item closes it;
- category filtering and search remain unchanged;
- no new questions or answers were added.

## Accessibility

Existing accessibility is preserved and visually supported:
- FAQ question is a real button;
- button type is button;
- aria-expanded is present;
- aria-controls is present;
- answer panel has id;
- answer panel has role region;
- answer panel has aria-labelledby;
- aria-hidden is updated;
- focus-visible styles are now explicit for FAQ controls and Footer links;
- Enter and Space behavior remains native button behavior.

## Footer Structure

Footer structure preserved:
- brand column with STL Master logo and description;
- CTA button Открыть приложение;
- Product navigation group;
- Tools navigation group;
- Support group;
- social links;
- bottom copyright and Telegram link.

## Footer Link Groups and URLs

Product:
- Возможности -> #features
- Соединения -> #connectors
- До / После -> #compare
- Тарифы -> #premium
- FAQ -> #faq

Tools:
- Проверка STL -> #features
- Ремонт модели -> #features
- Разрез модели -> #connectors
- Подготовка соединений -> #connectors
- Ориентация -> #features
- Экспорт результатов -> #features

Support:
- FAQ -> #faq
- Написать в поддержку -> https://vk.ru/3dmodeliron
- Сообщество ВКонтакте -> https://vk.ru/pechatdlyadoma
- Telegram-чат -> https://t.me/chat_pechatdlyadoma
- Канал на Pikabu -> https://pikabu.ru/@PechatDlyaDoma

Social:
- VK -> https://vk.ru/pechatdlyadoma
- Telegram -> https://t.me/chat_pechatdlyadoma
- Pikabu -> https://pikabu.ru/@PechatDlyaDoma

Footer bottom:
- © currentYear STL Master. Все права защищены.
- Telegram: @chat_pechatdlyadoma -> https://t.me/chat_pechatdlyadoma

No URL was changed.
No new legal document, social network or contact was added.

## Visual Work

FAQ:
- restored professional accordion styling for current faqAccordion markup;
- styled category filters as real controls instead of native button fragments;
- styled search row, open state, answer panel and empty state;
- added controlled desktop two-column layout and tablet/mobile one-column layout;
- added readable answer spacing and focus-visible states;
- reduced native UI artifacts and text collisions.

Footer:
- upgraded footer from plain strip to product closing surface;
- preserved all groups and links;
- improved brand column, CTA button, social pills and bottom line;
- added responsive grid for desktop, tablet and mobile;
- kept footer compact and connected with the landing background.

Transitions:
- added local spacing and scroll-margin for FAQ and Footer;
- visually separated FAQ from Premium and Footer from FAQ.

## Build

Build command used:
cd /home/codex/projects/vk-stl-master/frontend && npm run build

Result: PASS

Notes:
- VKUI use client warnings are existing dependency warnings.
- Chunk size warning is existing and not caused by Stage 5.8.

## Screenshots

Before screenshots saved in:
- docs/stage-05-8-faq-footer/before/

After screenshots are captured during post-build and production verification.
Local after path during verification:
- /private/tmp/stage-05-8-faq-footer/after/

## Checksums

Protected checksum before:
869a67de46ee887b3223c5e6ce39dcf68fe784ba662db3d8dcde68468b13c871

Protected checksum after must match before during final regression.

## Business Logic

Confirmed by code scope:
- no Premium request logic changed;
- no API endpoints changed;
- no upload logic changed;
- no authentication changed;
- no Studio or Admin source changed;
- no routing changed.

## Deferred Notes

General Landing Polish remains out of scope for this stage.
Header and previous sections were not changed by this stage.

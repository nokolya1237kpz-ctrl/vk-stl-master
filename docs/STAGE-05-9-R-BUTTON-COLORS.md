# Stage 05.9-R: Button Color System + Numbered Badge Consistency

Source SHA: `6f0cdc8243e04bfbdc0635323148a019b55d3aec`

## Scope

This stage updates only the Landing visual color system for buttons and numbered badges. No React, JSX, routes, backend, worker, API, Studio, Admin, Premium logic, upload logic, assets, images, package files, Docker, nginx, or application behavior were changed.

## Changed Files

- `frontend/src/landing/landing.css`
- `docs/STAGE-05-9-R-BUTTON-COLORS.md`
- `docs/stage-05-9-r-button-colors/results-before.json`
- `docs/stage-05-9-r-button-colors/results.json`
- `docs/stage-05-9-r-button-colors/after/*.png`

## Button Variants

Primary buttons:

- Selectors: `.primaryCta`, `.connectionsCtaButton`, `.featuresPrimaryCta`, `.premiumPrimaryButton`
- Background: `linear-gradient(135deg, #35d7ff 0%, #347aff 52%, #704cff 100%)`
- Text: `#ffffff`
- Border: `rgba(255,255,255,.18)`
- Shadow: cyan/blue glow tokenized as `--button-primary-shadow`

Secondary buttons:

- Selectors: `.secondaryCta`, `.appOpenButton`, `.featuresSecondaryLink`, `.footerAppButton`, `.compareMoreLink`, `.faqHeaderSupport`
- Background: `linear-gradient(180deg, rgba(20,35,58,.92), rgba(8,17,31,.90))`
- Text: `#edf7ff`
- Border: `rgba(84,150,230,.42)`
- Hover border: `rgba(53,215,255,.66)`

Premium buttons:

- Selectors: `.publicTopCta`, `.premiumHeaderButtonV9`, `.premiumStatusControl`
- Background: `linear-gradient(135deg, rgba(53,215,255,.16), rgba(111,76,255,.72))`
- Text: `#ffffff`
- Border: `rgba(166,145,255,.48)`

Icon buttons:

- Selector: `.mobileSupportButton`
- Background: `radial-gradient(circle at 50% 38%, rgba(53,215,255,.32), rgba(13,28,48,.82) 58%)`
- Text/icon color: `#b7ecff`
- Border: `rgba(53,215,255,.42)`

Ghost/text actions:

- Footer social links and text actions keep muted cyan text and restrained transparent surfaces.

## Numbered Badges

Unified numbered badges:

- Selectors: `.workflowStepNumber`, `.connectionCardNumber`
- Background: `linear-gradient(135deg, #35d7ff 0%, #347aff 52%, #704cff 100%)`
- Text: `#ffffff`
- Border: `rgba(255,255,255,.22)`
- Shadow: `0 12px 28px rgba(48,129,255,.34), inset 0 1px 0 rgba(255,255,255,.25)`

Technical badges remain muted:

- Selectors: `.connectionPill`, `.workflowPill`, `.featureToolTag`, `.formatTag`, `.compareChip`, `.featureBadge`
- Background: `rgba(10,24,42,.72)`
- Text: `#b8d8ee`
- Border: `rgba(92,142,190,.24)`

## CSS Conflicts Fixed

- Feature tool tabs inherited dark or black text from older generic button rules. Fixed with high-specificity Landing-only selectors under `.publicSite .featuresToolSection`.
- Feature CTA buttons had older local gradients and dark text. Fixed with explicit primary/secondary token selectors.
- Header application button used an older weak dark style. Recolored to the shared secondary button system.
- Header Premium and VK support controls now use distinct Premium and icon variants without changing geometry.
- Workflow and Connection numbered badges had different text colors and visual weight. They now use the same gradient, white text, border, and shadow.
- A final 320px brand overflow was caused by `strong` inside `.publicTopBrand.topBrandV8` retaining desktop `28px` typography. Fixed only inside `@media (max-width: 340px)`.

## Verification

Build:

- `npm run build`: PASS
- Existing VKUI `use client` and bundle-size warnings remain unchanged.

Regression:

- `/`: no horizontal overflow, no console errors, no page errors, no failed requests.
- `/app`: no horizontal overflow, no console errors, no page errors, no failed requests.
- `/admin`: no horizontal overflow, no console errors, no page errors, no failed requests.
- `/api/v1/me`: `200`

Viewport checks:

- `1920`, `1536`, `1440`, `1366`, `1280`, `1024`, `900`, `768`, `430`, `390`, `375`, `360`, `320`: PASS, no horizontal overflow.

Zoom checks:

- `67%`, `80%`, `100%`, `110%`, `125%`: PASS, no horizontal overflow.

Screenshots saved:

- `docs/stage-05-9-r-button-colors/after/header-buttons-1440.png`
- `docs/stage-05-9-r-button-colors/after/header-buttons-1280.png`
- `docs/stage-05-9-r-button-colors/after/hero-buttons-1440.png`
- `docs/stage-05-9-r-button-colors/after/workflow-step-numbers-1440.png`
- `docs/stage-05-9-r-button-colors/after/connections-step-numbers-1440.png`
- `docs/stage-05-9-r-button-colors/after/features-controls-1440.png`
- `docs/stage-05-9-r-button-colors/after/compare-actions-1440.png`
- `docs/stage-05-9-r-button-colors/after/premium-buttons-1440.png`
- `docs/stage-05-9-r-button-colors/after/footer-buttons-1440.png`
- `docs/stage-05-9-r-button-colors/after/buttons-mobile-390.png`
- `docs/stage-05-9-r-button-colors/after/step-numbers-mobile-390.png`
- `docs/stage-05-9-r-button-colors/after/button-variants-catalog.png`

## Logic Safety

No application logic was changed. The stage is CSS-only plus documentation and screenshot artifacts.


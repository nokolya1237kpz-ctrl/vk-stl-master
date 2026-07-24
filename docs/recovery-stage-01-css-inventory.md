# Recovery Stage 01 CSS Inventory

Аудит чтением. Содержимое CSS не изменялось.

## Подключение CSS

Фактический порядок импортов в `frontend/src/main.jsx`:

- L4: `import "@vkontakte/vkui/dist/vkui.css";`
- L8: `import "./styles.css";`
- L9: `import "./studio/studio.css";`
- L10: `import "./styles/tokens.css";`
- L11: `import "./styles/reset.css";`
- L12: `import "./styles/shared.css";`
- L13: `import "./landing/landing.css";`
- L14: `import "./admin/admin.css";`

## Файлы

### `frontend/src/styles.css`

- lines: 11849
- sha256: `8a6acd47892c644400064f7a797e46f26d76dc730a26b94c826720056a7119e4`
- selector entries: 2019
- unique selectors: 1128
- duplicate selectors in file: 464
- media queries: 61
- keyframes: 2 (premiumSpin, stlSpin)
- CSS variables defined: 46
- `!important`: 4441
- global/base selectors detected: body, button, input, a, img, *, :root

Representative duplicate selectors:
- `.shell` at lines 15, 2423, 2936
- `.hero` at lines 25, 2406, 2426
- `.featureCard` at lines 49, 2203
- `.heroCopy` at lines 49, 59, 2412, 2430
- `.previewPanel` at lines 49, 116, 2430, 2925
- `.workflowCard` at lines 49, 2203
- `h1` at lines 78, 85, 2435
- `.previewHeader` at lines 126, 2439, 2524
- `.previewHeader h2` at lines 133, 2528
- `.previewStatus` at lines 140, 2533
- `.previewCanvas` at lines 162, 2538
- `.previewWarning` at lines 192, 204
- `.previewActions` at lines 275, 2543
- `.changeMapPanel p` at lines 297, 302
- `.operationCard` at lines 328, 2456
- `.operationCheck` at lines 350, 2463
- `.operationContent` at lines 366, 2469
- `.operationContent strong` at lines 371, 2473
- `.operationContent em` at lines 376, 2477
- `.operationContent small` at lines 383, 2484
- `.orientationControl` at lines 403, 2488
- `.reductionControl` at lines 403, 2488
- `.surfaceRecoverySetup` at lines 413, 2488
- `.localSmoothingControl` at lines 424, 2488
- `.localSmoothingControl h3` at lines 435, 2499
- `.surfaceRecoverySetup h3` at lines 510, 2499
- `.orientationCommitHint` at lines 531, 546
- `.orientationSaveHint` at lines 531, 540
- `.adminDashboard` at lines 610, 956, 1142, 1163
- `.adminSummaryGrid` at lines 628, 1170
- `.adminLoginPanel` at lines 662, 691, 1193, 1256
- `.adminUserForm` at lines 662, 691
- `.adminTable td` at lines 819, 834
- `.adminTable th` at lines 819, 827
- `.adminJobGrid` at lines 913, 1170

### `frontend/src/landing/landing.css`

- lines: 507
- sha256: `a468c70f22c2e4be5f321fcbf77b14f0c48610e95f6b317e845776d898a9a1f2`
- selector entries: 256
- unique selectors: 176
- duplicate selectors in file: 43
- media queries: 7
- keyframes: 0 ()
- CSS variables defined: 0
- `!important`: 13
- global/base selectors detected: button, a, img, *

Representative duplicate selectors:
- `.publicTopNav.topNavV8` at lines 25, 352, 377, 422, 437, 470
- `.publicTopBrand.topBrandV8` at lines 46, 476
- `.publicTopBrand strong` at lines 58, 353, 386
- `.publicTopBrand em` at lines 60, 354, 387
- `.publicTopPanel` at lines 70, 357, 398, 478
- `.publicTopLinks.topLinksV8` at lines 78, 341, 359, 413
- `.publicTopActions.topActionsV8` at lines 105, 359, 413, 484
- `.publicTopActions .appOpenButton` at lines 107, 121, 342, 415
- `.publicTopActions .mobileSupportButton` at lines 107, 124, 360, 415, 418
- `.publicTopActions .publicTopCta` at lines 107, 122, 415
- `.publicMenuButton` at lines 159, 355, 388
- `.launchContacts.footerV9` at lines 161, 330, 361, 365, 463
- `.launchHero.heroV8` at lines 161, 168, 343, 361, 362, 443, 490
- `.publicSection` at lines 161, 281, 361, 463
- `.heroCopyV8 h1` at lines 195, 363
- `.heroBenefitsV8` at lines 213, 365
- `.heroActionsV8 button` at lines 231, 366
- `.studioShellV8` at lines 238, 344, 450
- `.studioTopbarV8 div` at lines 241, 242
- `.studioBodyV8` at lines 245, 367, 456
- `.studioToolsV8` at lines 246, 368
- `.studioViewportV8` at lines 251, 369
- `.studioInfoV8` at lines 262, 368
- `.quickActions button` at lines 267, 269
- `.heroMetricsV8` at lines 270, 365
- `.heroMetricsV8 article` at lines 272, 370
- `.browserNoteV8 span` at lines 278, 279
- `.launchSectionHeader` at lines 286, 365
- `.workflowGrid` at lines 291, 345, 365
- `.workflowArrow` at lines 298, 346
- `.connectionsHeading` at lines 300, 365
- `.connectionsGrid` at lines 302, 347, 365
- `.connectionCard` at lines 303, 372
- `.connectionVisual` at lines 309, 373
- `.connectionParameters` at lines 312, 313, 365

### `frontend/src/studio/studio.css`

- lines: 1031
- sha256: `7c0676926161cb65c441bde9731178f6fe793ab3318551ca556bcd17c4347436`
- selector entries: 290
- unique selectors: 122
- duplicate selectors in file: 75
- media queries: 5
- keyframes: 0 ()
- CSS variables defined: 0
- `!important`: 14
- global/base selectors detected: button, input

Representative duplicate selectors:
- `.studioShell` at lines 1, 698, 723, 781, 945, 955, 974
- `.studioAccessBanner` at lines 31, 53, 208, 221
- `.studioHeader` at lines 31, 41, 726, 792, 958, 981
- `.studioInspector` at lines 31, 242, 458, 716, 837, 900, 953, 968
- `.studioSidebar` at lines 31, 242, 251, 708, 837, 846, 949, 964
- `.studioViewerWorkspace` at lines 31, 242, 339, 712, 760, 837, 869, 967
- `.studioWorkflowBar` at lines 31, 242, 602, 703, 837, 917, 954, 969
- `.studioBrand` at lines 53, 67, 800, 960, 987
- `.studioEmptyActions` at lines 53, 411, 897
- `.studioHeaderActions` at lines 53, 119, 737, 817, 962, 987, 993
- `.studioInlineActions` at lines 53, 578
- `.studioMovePad` at lines 53, 589
- `.studioProjectStatus` at lines 53, 107, 731, 806, 960, 987
- `.studioRunActions` at lines 53, 683, 944, 972
- `.studioSizeGrid` at lines 53, 551
- `.studioToolButton` at lines 53, 283, 852, 951, 966, 1020
- `.studioBrand .launchSvgIcon` at lines 77, 801
- `.studioBrand b` at lines 83, 805
- `.studioBrand small` at lines 89, 103, 806
- `.studioEmptyState p` at lines 89, 404, 896
- `.studioFileLimits span` at lines 89, 450, 899
- `.studioInspectorCard dd` at lines 89, 506
- `.studioProjectStatus em` at lines 89, 814
- `.studioRunMeta em` at lines 89, 663, 942
- `.studioRunMeta span` at lines 89, 663, 942
- `.studioToolButton small` at lines 89, 308, 317, 867, 949, 1013
- `.studioProjectStatus span` at lines 115, 813
- `.studioExportButton` at lines 138, 156, 162, 753
- `.studioIconButton` at lines 138, 156
- `.studioInlineActions button` at lines 138, 583
- `.studioMovePad button` at lines 138, 583
- `.studioPrimaryAction` at lines 138, 162, 418, 898
- `.studioSecondaryAction` at lines 138, 427, 898
- `.studioSegmentGroup button` at lines 138, 518, 914
- `.studioTextAction` at lines 138, 427, 437, 898

### `frontend/src/admin/admin.css`

- lines: 161
- sha256: `3889c93b0acd8094d4deab09cd743b9dce7ff35b35bfa3b710f66eb14921a287`
- selector entries: 106
- unique selectors: 75
- duplicate selectors in file: 22
- media queries: 2
- keyframes: 0 ()
- CSS variables defined: 0
- `!important`: 0
- global/base selectors detected: button, input

Representative duplicate selectors:
- `.adminDashboard` at lines 1, 29, 145, 151
- `.adminLoginScreen` at lines 1, 11, 151
- `.adminLoginInfo` at lines 13, 19, 152
- `.adminLoginPanel` at lines 13, 20
- `.adminSidebar` at lines 39, 47, 153
- `.adminWorkspace` at lines 39, 83, 156
- `.adminLogout` at lines 48, 146
- `.adminTabs` at lines 49, 154
- `.adminTabs button` at lines 50, 155
- `.adminVersion` at lines 82, 146
- `.adminTopbar` at lines 85, 147
- `.adminSummaryGrid` at lines 108, 148, 157
- `.adminAnalyticsPanel` at lines 109, 125
- `.adminBulkBar` at lines 109, 128
- `.adminDangerPanel` at lines 109, 125
- `.adminFilters` at lines 109, 128
- `.adminJobPanel` at lines 109, 125
- `.adminSummaryCard` at lines 109, 122
- `.adminTableWrap` at lines 109, 132, 158
- `.adminToolbar` at lines 109, 128
- `.adminTable th` at lines 134, 135
- `.adminJobGrid` at lines 139, 148, 157

### `frontend/src/styles/tokens.css`

- lines: 39
- sha256: `8087aa9af4ca90d4260af669ec0d2e5f8d844bcf6a650838ac042b9a45a77750`
- selector entries: 1
- unique selectors: 1
- duplicate selectors in file: 0
- media queries: 0
- keyframes: 0 ()
- CSS variables defined: 36
- `!important`: 0
- global/base selectors detected: :root

### `frontend/src/styles/reset.css`

- lines: 42
- sha256: `80007f10bb097fbea33375cf285a072bdf86703cbfda709b7ab3d5eeaa2c7116`
- selector entries: 60
- unique selectors: 15
- duplicate selectors in file: 5
- media queries: 0
- keyframes: 0 ()
- CSS variables defined: 0
- `!important`: 0
- global/base selectors detected: button, input, a, *

Representative duplicate selectors:
- `.adminDashboard` at lines 1, 1, 1, 5, 11, 11, 11, 11
- `.adminLoginScreen` at lines 1, 1, 1, 5, 11, 11, 11, 11
- `.studioShell` at lines 1, 1, 1, 5, 11, 11, 11, 11
- `:where(.publicSite` at lines 1, 1, 1, 5, 11, 11, 11, 11
- `.publicFormPage) button` at lines 11, 18

### `frontend/src/styles/shared.css`

- lines: 77
- sha256: `726e054ecb4e9348f3cdefbd07364d5deb08e19464a013ed59a4eb83c3480cbc`
- selector entries: 73
- unique selectors: 47
- duplicate selectors in file: 20
- media queries: 0
- keyframes: 0 ()
- CSS variables defined: 0
- `!important`: 0
- global/base selectors detected: button, input, a

Representative duplicate selectors:
- `.adminDashboard` at lines 12, 58
- `.studioShell` at lines 12, 58, 65, 70, 71
- `:where(.publicSite` at lines 12, 58, 65, 70, 71
- `textarea` at lines 12, 58
- `.adminCleanupButton` at lines 17, 28
- `.adminDashboard :is(.adminLoginButton` at lines 17, 28
- `.connectionsCtaButton` at lines 17, 28
- `.modalPrimaryButton` at lines 17, 28
- `.pricingPrimaryButton` at lines 17, 28
- `.publicSite :is(.primaryCta` at lines 17, 28
- `.publicTopCta` at lines 17, 28
- `.studioShell :is(.studioPrimaryAction` at lines 17, 28
- `.adminDashboard :is(.adminToolbar button` at lines 36, 49
- `.adminRowActions button` at lines 36, 49
- `.adminSidebarToggle` at lines 36, 49
- `.appOpenButton` at lines 36, 49
- `.mobileSupportButton` at lines 36, 49
- `.publicSite :is(.secondaryCta` at lines 36, 49
- `.studioShell :is(.studioIconButton` at lines 36, 49
- `.studioTextAction` at lines 36, 49

## Селекторы, встречающиеся в нескольких CSS-файлах

Всего: 89

- `.adminAnalyticsPanel` -> frontend/src/styles.css:L798, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L125
- `.adminAnalyticsPanel h2` -> frontend/src/styles.css:L808, frontend/src/admin/admin.css:L126
- `.adminBackLink` -> frontend/src/styles.css:L1249, frontend/src/admin/admin.css:L28
- `.adminBadge` -> frontend/src/styles.css:L890, frontend/src/admin/admin.css:L66
- `.adminBadge.danger` -> frontend/src/styles.css:L1090, frontend/src/admin/admin.css:L80
- `.adminBadge.real` -> frontend/src/styles.css:L901, frontend/src/admin/admin.css:L79
- `.adminBadge.test` -> frontend/src/styles.css:L907, frontend/src/admin/admin.css:L81
- `.adminBrand` -> frontend/src/styles.css:L980, frontend/src/admin/admin.css:L21
- `.adminBrand strong` -> frontend/src/styles.css:L988, frontend/src/styles.css:L993, frontend/src/admin/admin.css:L23
- `.adminBulkBar` -> frontend/src/styles.css:L1488, frontend/src/styles.css:L1496, frontend/src/styles.css:L1622, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L128
- `.adminCleanupButton` -> frontend/src/styles.css:L732, frontend/src/styles/shared.css:L17, frontend/src/styles/shared.css:L28
- `.adminCleanupStatus` -> frontend/src/styles.css:L743, frontend/src/admin/admin.css:L137
- `.adminDangerPanel` -> frontend/src/styles.css:L1488, frontend/src/styles.css:L1519, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L125
- `.adminDashboard` -> frontend/src/styles.css:L610, frontend/src/styles.css:L956, frontend/src/styles.css:L1142, frontend/src/styles.css:L1163, frontend/src/admin/admin.css:L1, frontend/src/admin/admin.css:L29, frontend/src/admin/admin.css:L145, frontend/src/admin/admin.css:L151, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1
- `.adminDashboard.sidebarCollapsed` -> frontend/src/styles.css:L1361, frontend/src/styles.css:L1596, frontend/src/admin/admin.css:L38
- `.adminEmpty` -> frontend/src/styles.css:L885, frontend/src/admin/admin.css:L137
- `.adminFilters` -> frontend/src/styles.css:L655, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L128
- `.adminGlobalSearch input` -> frontend/src/styles.css:L1404, frontend/src/admin/admin.css:L101
- `.adminJobGrid` -> frontend/src/styles.css:L913, frontend/src/styles.css:L1170, frontend/src/admin/admin.css:L139, frontend/src/admin/admin.css:L148, frontend/src/admin/admin.css:L157
- `.adminJobGrid em` -> frontend/src/styles.css:L929, frontend/src/admin/admin.css:L141
- `.adminJobGrid span` -> frontend/src/styles.css:L919, frontend/src/admin/admin.css:L140
- `.adminJobGrid strong` -> frontend/src/styles.css:L937, frontend/src/admin/admin.css:L142
- `.adminJobPanel` -> frontend/src/styles.css:L798, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L125
- `.adminJobPanel h2` -> frontend/src/styles.css:L808, frontend/src/admin/admin.css:L126
- `.adminJsonPreview` -> frontend/src/styles.css:L944, frontend/src/admin/admin.css:L138
- `.adminLoginButton` -> frontend/src/styles.css:L1283, frontend/src/admin/admin.css:L27
- `.adminLoginInfo` -> frontend/src/styles.css:L1193, frontend/src/styles.css:L1198, frontend/src/admin/admin.css:L13, frontend/src/admin/admin.css:L19, frontend/src/admin/admin.css:L152
- `.adminLoginInfo p` -> frontend/src/styles.css:L1220, frontend/src/admin/admin.css:L25
- `.adminLoginPanel` -> frontend/src/styles.css:L662, frontend/src/styles.css:L691, frontend/src/styles.css:L1193, frontend/src/styles.css:L1256, frontend/src/admin/admin.css:L13, frontend/src/admin/admin.css:L20
- `.adminLoginPanel h2` -> frontend/src/styles.css:L1264, frontend/src/admin/admin.css:L24
- `.adminLoginPanel p` -> frontend/src/styles.css:L1271, frontend/src/admin/admin.css:L25
- `.adminLoginScreen` -> frontend/src/styles.css:L1180, frontend/src/styles.css:L1593, frontend/src/styles.css:L1615, frontend/src/admin/admin.css:L1, frontend/src/admin/admin.css:L11, frontend/src/admin/admin.css:L151, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L5
- `.adminLogout` -> frontend/src/styles.css:L1018, frontend/src/styles.css:L1027, frontend/src/admin/admin.css:L48, frontend/src/admin/admin.css:L146
- `.adminNavBadge` -> frontend/src/styles.css:L1307, frontend/src/styles.css:L1335, frontend/src/admin/admin.css:L66
- `.adminNavBadge.danger` -> frontend/src/styles.css:L1349, frontend/src/admin/admin.css:L80
- `.adminNavIcon` -> frontend/src/styles.css:L1307, frontend/src/styles.css:L1320, frontend/src/admin/admin.css:L65
- `.adminNavTitle` -> frontend/src/styles.css:L1307, frontend/src/styles.css:L1330, frontend/src/admin/admin.css:L146
- `.adminNotice` -> frontend/src/styles.css:L721, frontend/src/admin/admin.css:L137
- `.adminRowActions` -> frontend/src/styles.css:L866, frontend/src/admin/admin.css:L130
- `.adminRowActions button` -> frontend/src/styles.css:L872, frontend/src/admin/admin.css:L131, frontend/src/styles/shared.css:L36, frontend/src/styles/shared.css:L49
- `.adminSectionStack` -> frontend/src/styles.css:L1097, frontend/src/admin/admin.css:L106
- `.adminSidebar` -> frontend/src/styles.css:L967, frontend/src/styles.css:L1145, frontend/src/admin/admin.css:L39, frontend/src/admin/admin.css:L47, frontend/src/admin/admin.css:L153
- `.adminSidebarToggle` -> frontend/src/styles.css:L1297, frontend/src/admin/admin.css:L48, frontend/src/styles/shared.css:L36, frontend/src/styles/shared.css:L49
- `.adminSummaryCard` -> frontend/src/styles.css:L634, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L122
- `.adminSummaryCard span` -> frontend/src/styles.css:L643, frontend/src/admin/admin.css:L123
- `.adminSummaryCard strong` -> frontend/src/styles.css:L649, frontend/src/admin/admin.css:L124
- `.adminSummaryGrid` -> frontend/src/styles.css:L628, frontend/src/styles.css:L1170, frontend/src/admin/admin.css:L108, frontend/src/admin/admin.css:L148, frontend/src/admin/admin.css:L157
- `.adminSystemPills` -> frontend/src/styles.css:L1065, frontend/src/admin/admin.css:L102
- `.adminSystemPills .danger` -> frontend/src/styles.css:L1090, frontend/src/admin/admin.css:L105
- `.adminSystemPills .ok` -> frontend/src/styles.css:L1085, frontend/src/admin/admin.css:L104
- `.adminSystemPills span` -> frontend/src/styles.css:L1072, frontend/src/admin/admin.css:L103
- `.adminTable` -> frontend/src/styles.css:L814, frontend/src/admin/admin.css:L133
- `.adminTable td` -> frontend/src/styles.css:L819, frontend/src/styles.css:L834, frontend/src/admin/admin.css:L134
- `.adminTable th` -> frontend/src/styles.css:L819, frontend/src/styles.css:L827, frontend/src/admin/admin.css:L134, frontend/src/admin/admin.css:L135
- `.adminTableWrap` -> frontend/src/styles.css:L770, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L132, frontend/src/admin/admin.css:L158
- `.adminTabs` -> frontend/src/styles.css:L662, frontend/src/admin/admin.css:L49, frontend/src/admin/admin.css:L154
- `.adminTabs button` -> frontend/src/styles.css:L671, frontend/src/admin/admin.css:L50, frontend/src/admin/admin.css:L155
- `.adminTabs button.active` -> frontend/src/styles.css:L684, frontend/src/admin/admin.css:L64
- `.adminToolbar` -> frontend/src/styles.css:L1466, frontend/src/admin/admin.css:L109, frontend/src/admin/admin.css:L128
- `.adminToolbar input` -> frontend/src/styles.css:L1404, frontend/src/admin/admin.css:L129
- `.adminToolbar select` -> frontend/src/styles.css:L1404, frontend/src/admin/admin.css:L129
- `.adminTopbar` -> frontend/src/styles.css:L1042, frontend/src/styles.css:L1155, frontend/src/admin/admin.css:L85, frontend/src/admin/admin.css:L147
- `.adminTopbar h1` -> frontend/src/styles.css:L1053, frontend/src/styles.css:L1175, frontend/src/admin/admin.css:L99
- `.adminTopbar p` -> frontend/src/styles.css:L1060, frontend/src/admin/admin.css:L100
- `.adminVersion` -> frontend/src/styles.css:L1354, frontend/src/admin/admin.css:L82, frontend/src/admin/admin.css:L146
- `.adminWorkspace` -> frontend/src/styles.css:L1036, frontend/src/admin/admin.css:L39, frontend/src/admin/admin.css:L83, frontend/src/admin/admin.css:L156
- `.compareMetrics` -> frontend/src/styles.css:L10582, frontend/src/styles.css:L10600, frontend/src/landing/landing.css:L323
- `.connectionsCtaButton` -> frontend/src/landing/landing.css:L319, frontend/src/styles/shared.css:L17, frontend/src/styles/shared.css:L28
- `.panelLabel` -> frontend/src/styles.css:L68, frontend/src/admin/admin.css:L127
- `.premiumStatusControl` -> frontend/src/styles.css:L3325, frontend/src/landing/landing.css:L128
- `.premiumStatusControl b` -> frontend/src/styles.css:L3367, frontend/src/styles.css:L3375, frontend/src/landing/landing.css:L140
- `.premiumStatusControl small` -> frontend/src/styles.css:L3367, frontend/src/styles.css:L3380, frontend/src/landing/landing.css:L141
- `.premiumStatusControl span` -> frontend/src/styles.css:L3360, frontend/src/landing/landing.css:L139
- `.premiumStatusPopover` -> frontend/src/styles.css:L3386, frontend/src/styles.css:L3618, frontend/src/landing/landing.css:L142
- `.premiumStatusPopover button` -> frontend/src/styles.css:L3439, frontend/src/landing/landing.css:L158
- `.premiumStatusPopover dd` -> frontend/src/styles.css:L3421, frontend/src/styles.css:L3426, frontend/src/landing/landing.css:L156
- `.premiumStatusPopover dl` -> frontend/src/styles.css:L3407, frontend/src/landing/landing.css:L153
- `.premiumStatusPopover dl div` -> frontend/src/styles.css:L3413, frontend/src/landing/landing.css:L154
- `.premiumStatusPopover dt` -> frontend/src/styles.css:L3421, frontend/src/landing/landing.css:L155
- `.premiumStatusWrap` -> frontend/src/styles.css:L3321, frontend/src/landing/landing.css:L126
- `.publicSite` -> frontend/src/styles.css:L4887, frontend/src/styles.css:L4941, frontend/src/styles.css:L10677, frontend/src/styles.css:L10737, frontend/src/landing/landing.css:L1
- `.publicSite .launchSvgIcon` -> frontend/src/styles.css:L10603, frontend/src/styles/shared.css:L1
- `.studioShell` -> frontend/src/studio/studio.css:L1, frontend/src/studio/studio.css:L698, frontend/src/studio/studio.css:L723, frontend/src/studio/studio.css:L781, frontend/src/studio/studio.css:L945, frontend/src/studio/studio.css:L955, frontend/src/studio/studio.css:L974, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1
- `.studioShell .launchSvgIcon` -> frontend/src/studio/studio.css:L124, frontend/src/styles/shared.css:L1
- `.studioTextAction` -> frontend/src/studio/studio.css:L138, frontend/src/studio/studio.css:L427, frontend/src/studio/studio.css:L437, frontend/src/studio/studio.css:L898, frontend/src/styles/shared.css:L36, frontend/src/styles/shared.css:L49
- `.workflowCard` -> frontend/src/styles.css:L49, frontend/src/styles.css:L2203, frontend/src/landing/landing.css:L292
- `.workflowCard h3` -> frontend/src/styles.css:L2215, frontend/src/landing/landing.css:L295
- `:root` -> frontend/src/styles.css:L1, frontend/src/styles/tokens.css:L1
- `:where(.publicSite` -> frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L1, frontend/src/styles/reset.css:L5, frontend/src/styles/reset.css:L11, frontend/src/styles/reset.css:L11, frontend/src/styles/reset.css:L11, frontend/src/styles/reset.css:L11, frontend/src/styles/reset.css:L18, frontend/src/styles/reset.css:L24

## CSS variables defined multiple times

Всего: 14
- `--connection-glow` -> frontend/src/styles.css:L7247, frontend/src/styles.css:L7248, frontend/src/styles.css:L7249, frontend/src/styles.css:L7250, frontend/src/styles.css:L7251
- `--mode-glow` -> frontend/src/styles.css:L7451, frontend/src/styles.css:L7478, frontend/src/styles.css:L7479, frontend/src/styles.css:L7480, frontend/src/styles.css:L7481, frontend/src/styles.css:L7482, frontend/src/styles.css:L7483
- `--ref-bg` -> frontend/src/styles.css:L4897, frontend/src/styles.css:L10721
- `--ref-blue` -> frontend/src/styles.css:L4902, frontend/src/styles.css:L10726
- `--ref-border` -> frontend/src/styles.css:L4900, frontend/src/styles.css:L10724
- `--ref-card` -> frontend/src/styles.css:L4899, frontend/src/styles.css:L10723
- `--ref-cyan` -> frontend/src/styles.css:L4901, frontend/src/styles.css:L10725
- `--ref-green` -> frontend/src/styles.css:L4904, frontend/src/styles.css:L10728
- `--ref-panel` -> frontend/src/styles.css:L4898, frontend/src/styles.css:L10722
- `--ref-red` -> frontend/src/styles.css:L4906, frontend/src/styles.css:L10730
- `--ref-violet` -> frontend/src/styles.css:L4903, frontend/src/styles.css:L10727
- `--ref-yellow` -> frontend/src/styles.css:L4905, frontend/src/styles.css:L10729
- `--step-color` -> frontend/src/styles.css:L6863, frontend/src/styles.css:L6878, frontend/src/styles.css:L6879, frontend/src/styles.css:L6880, frontend/src/styles.css:L6881, frontend/src/styles.css:L6882, frontend/src/styles.css:L6883
- `--step-glow` -> frontend/src/styles.css:L6179, frontend/src/styles.css:L6194, frontend/src/styles.css:L6195, frontend/src/styles.css:L6196, frontend/src/styles.css:L6197, frontend/src/styles.css:L6198, frontend/src/styles.css:L6199

## Каскад и зоны риска

- `styles.css` импортируется раньше специализированных CSS, но содержит legacy/shared правила и глобальные селекторы. Удалять или переносить его нельзя.
- `landing.css` идёт после shared-слоёв и перед `admin.css`, поэтому landing-правила выигрывают у `styles.css` при равной специфичности.
- `admin.css` импортируется последним и может переопределять общие классы, если имена совпадают.
- Подтверждённые пересечения перечислены выше; перед визуальным восстановлением менять только точечные селекторы конкретного маршрута.
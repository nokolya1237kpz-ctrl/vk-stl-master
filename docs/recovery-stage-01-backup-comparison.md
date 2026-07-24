# Recovery Stage 01 Backup Comparison

Сравнение только чтением. Никакие backup-файлы не копировались.

## Current frontend key files

- `frontend/src/main.jsx`: exists=True, lines=9168, sha256=`a11f89932b7591124eaa6fb6d13a7cce552d3144394b5e4bb1f067250c1adc64`
- `frontend/src/styles.css`: exists=True, lines=11849, sha256=`8a6acd47892c644400064f7a797e46f26d76dc730a26b94c826720056a7119e4`
- `frontend/src/landing/landing.css`: exists=True, lines=507, sha256=`a468c70f22c2e4be5f321fcbf77b14f0c48610e95f6b317e845776d898a9a1f2`
- `frontend/src/studio/studio.css`: exists=True, lines=1031, sha256=`7c0676926161cb65c441bde9731178f6fe793ab3318551ca556bcd17c4347436`
- `frontend/src/admin/admin.css`: exists=True, lines=161, sha256=`3889c93b0acd8094d4deab09cd743b9dce7ff35b35bfa3b710f66eb14921a287`
- `frontend/src/styles/tokens.css`: exists=True, lines=39, sha256=`8087aa9af4ca90d4260af669ec0d2e5f8d844bcf6a650838ac042b9a45a77750`
- `frontend/src/styles/reset.css`: exists=True, lines=42, sha256=`80007f10bb097fbea33375cf285a072bdf86703cbfda709b7ab3d5eeaa2c7116`
- `frontend/src/styles/shared.css`: exists=True, lines=77, sha256=`726e054ecb4e9348f3cdefbd07364d5deb08e19464a013ed59a4eb83c3480cbc`

## Backup directories

### `.codex-backups`

- exists: True
- file count: 8
- candidates for `frontend/src/main.jsx`: none
- candidates for `frontend/src/styles.css`: none
- candidates for `frontend/src/landing/landing.css`: none
- candidates for `frontend/src/studio/studio.css`: none
- candidates for `frontend/src/admin/admin.css`: none
- candidates for `frontend/src/styles/tokens.css`: none
- candidates for `frontend/src/styles/reset.css`: none
- candidates for `frontend/src/styles/shared.css`: none
- asset-like files: 0

### `__incoming_public_redesign__`

- exists: True
- file count: 5
- candidates for `frontend/src/main.jsx`:
  - `__incoming_public_redesign__/main.jsx` lines=6551 sha256=`c020cb06615afbe7ae33238ddb3e98ef892c9cbbf02b8d8f1d8c3f4d4fe87df0`
- candidates for `frontend/src/styles.css`:
  - `__incoming_public_redesign__/styles.css` lines=5560 sha256=`54ddaae0f7b5af3e793aeadc02193d41e2076748f5a6e18f3a6f19b61c78720e`
- candidates for `frontend/src/landing/landing.css`: none
- candidates for `frontend/src/studio/studio.css`: none
- candidates for `frontend/src/admin/admin.css`: none
- candidates for `frontend/src/styles/tokens.css`: none
- candidates for `frontend/src/styles/reset.css`: none
- candidates for `frontend/src/styles/shared.css`: none
- asset-like files: 0

### `__incoming_public_polish__`

- exists: True
- file count: 3
- candidates for `frontend/src/main.jsx`:
  - `__incoming_public_polish__/main.jsx` lines=6578 sha256=`a03497d2f876af9c1b136594baf996db3856a3a89a8de1cab0cc471729a82c23`
- candidates for `frontend/src/styles.css`:
  - `__incoming_public_polish__/styles.css` lines=7800 sha256=`a137db8028a86b41ea509eec5fa2734bfa9a8454b41e83e3245ca3b2d558943f`
- candidates for `frontend/src/landing/landing.css`: none
- candidates for `frontend/src/studio/studio.css`: none
- candidates for `frontend/src/admin/admin.css`: none
- candidates for `frontend/src/styles/tokens.css`: none
- candidates for `frontend/src/styles/reset.css`: none
- candidates for `frontend/src/styles/shared.css`: none
- asset-like files: 0

### `tmp_polish_sync`

- exists: True
- file count: 3
- candidates for `frontend/src/main.jsx`:
  - `tmp_polish_sync/main.jsx` lines=6588 sha256=`1b22d1233d9209a651824e16180a01edd9f3fe53524a55fabc20715e5966911f`
- candidates for `frontend/src/styles.css`:
  - `tmp_polish_sync/styles.css` lines=8293 sha256=`3d793c298148a5844bf3f92e4115d0679f30ec6e8743c3d414a89f003752c44d`
- candidates for `frontend/src/landing/landing.css`: none
- candidates for `frontend/src/studio/studio.css`: none
- candidates for `frontend/src/admin/admin.css`: none
- candidates for `frontend/src/styles/tokens.css`: none
- candidates for `frontend/src/styles/reset.css`: none
- candidates for `frontend/src/styles/shared.css`: none
- asset-like files: 0

## Practical conclusions

- Full replacement from backup is unsafe: current source is split across `landing.css`, `studio.css`, `admin.css`, shared styles and large `main.jsx`, while incoming folders mostly contain partial public redesign files.
- Backup folders may be used only as visual/style donors after diff review, not as wholesale source replacement.
- Marketing assets can be compared and reused only if filenames and rendered sections match; no automatic copy was performed.
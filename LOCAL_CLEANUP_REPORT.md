# Local Cleanup Report

## Initial Git Status

```text
 M .gitignore
 M frontend/public/sitemap.xml
?? .venv-edge/
```

## Decisions

### `.gitignore`

Decision: keep and commit a safe targeted ignore.

- Replaced the broad local `.env*` change with a specific `.venv-edge/` ignore.
- The repo already has safer environment handling with `.env`, `.env.*`, and `!.env.example`.
- `.venv-edge/` is now ignored and will not be committed.

### `frontend/public/sitemap.xml`

Decision: keep and commit the regenerated sitemap.

- Regenerated with `npm --prefix frontend run prebuild`.
- Output contains 124 URLs.
- Confirmed the sitemap does not contain:
  - `patterned-wrap-dress`
  - `denim`
  - `fashion`
  - `woocommerce`
  - `clothing`
  - `apparel`
  - `/shop`
  - `/product/`
  - `/products/`
  - `/product-category/`

### `.venv-edge/`

Decision: do not commit.

- `.venv-edge/` is a local Python virtual environment for edge TTS tooling.
- It is now ignored by `.gitignore`.
- The folder was left locally and not staged.

## Validation Commands

```bash
python3 -m py_compile backend/server.py
node --check scripts/audit-public-content.mjs
node --check regression/modules/13-public-content-governance.test.js
npm run catalog:audit
npm run regression -- modules/13-public-content-governance.test.js
npm --prefix frontend run build
```

## Validation Results

- Backend syntax check passed.
- Catalog audit script syntax check passed.
- Governance regression syntax check passed.
- Catalog audit passed, 251 items audited.
- Public content governance regression passed, 15/15 tests.
- Frontend build passed.

## Final Git Status

Expected after commit:

```text
clean working tree, with .venv-edge/ ignored locally
```

## Commit

Created commit:

```text
Clean local generated and environment artifacts
```


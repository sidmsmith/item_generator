# Item Copy — Project Instructions

This project follows the global `AGENTS.md` and `SECURITY_BASELINE.md`.
The notes below cover only what's specific to this repository.

## Version identifiers

Three places, in sync at `v1.0.5`:

- `package.json` — the `version` field
- `index.html` — the `<title>`
- `api/index.py` — the `APP_VERSION` constant

## Local development

- `node server.js` — Express, serves `index.html` and proxies `/api/*`
  to the Flask backend (port 3000 by default, via `PORT` env var)
- `python api/index.py` — Flask backend, port 5000 (`app.run(debug=True,
  port=5000)`)

## Package cloning rule

When adding a package via "Add Package," MAWM enforces only one
`Standard: true` package per `StandardQuantityUomId` level — cloned
packages default to `Standard: false` to avoid violating this.

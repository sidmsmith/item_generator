# Item Copy — Project Instructions

This project follows the global `AGENTS.md` and `SECURITY_BASELINE.md`.
The notes below cover only what's specific to this repository.

## Version identifiers

Three places, in sync at `v1.0.7`:

- `package.json` — the `version` field
- `index.html` — the `<title>`
- `api/index.py` — the `APP_VERSION` constant

## Authentication

Login is **Environment + Username** (not a bare ORG). The
`MANHATTAN_ENV` Vercel var is a JSON map of environment key → API host
(e.g. `{"SALEP":"salep.sce.manh.com","SALES3":"sales3.sce.manh.com"}`);
`DEFAULT_MANHATTAN_ENV` in `api/index.py` covers SALEP and SALES3 if the
var is unset. The auth host is derived by inserting `-auth` before the
first dot. The org/facility prefix is derived server-side from the
username: the part **after** `@` by default (`demoweb@SS-DEMO` → `SS-DEMO`),
or the part **before** `@` for environments in
`ORG_BEFORE_AT_ENVIRONMENTS` (SALES3: `masc@sdt-demo` → `MASC`). The
client uses this server-derived org (`res.org`) for `ProfileId`.

URL params for auto-auth: `?Environment=<key>&Username=<user>&ItemId=<id>`
— names are case-insensitive and accept `env` / `user` aliases; both
Environment and Username must be present to auto-authenticate.

## Local development

- `node server.js` — Express, serves `index.html` and proxies `/api/*`
  to the Flask backend (port 3000 by default, via `PORT` env var)
- `python api/index.py` — Flask backend, port 5000 (`app.run(debug=True,
  port=5000)`)

## Package cloning rule

When adding a package via "Add Package," MAWM enforces only one
`Standard: true` package per `StandardQuantityUomId` level — cloned
packages default to `Standard: false` to avoid violating this.

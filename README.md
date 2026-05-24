# Item Copy

**Version 1.0.0** — Copy an existing Item Master record and create a new item.

## Features

- OAuth authentication with Manhattan WMS (ORG-based)
- Load item by Item ID (`item-master/item/search`)
- Editable summary: Item ID, Description (syncs PrimaryBarCode, ShortDescription)
- Item Package accordion (add / remove / edit packages)
- Full JSON editor (CodeMirror)
- Duplicate Item ID check before create
- Usage tracking via Neon (`item-generator-app`)

## Environment Variables (Vercel)

- `MANHATTAN_PASSWORD`
- `MANHATTAN_SECRET`
- `MANHATTAN_USAGE_INGEST_URL`
- `MANHATTAN_USAGE_INGEST_SECRET` (optional)

## API Routes

- `POST /api/auth`
- `POST /api/find_item` — search `ItemId='…'`
- `POST /api/create_item` — `item-master/item/save`
- `POST /api/usage-track`

## Deployment

Vercel project: **item-generator**  
Repository: https://github.com/sidmsmith/item_generator

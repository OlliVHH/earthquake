# Earthquake Analytics

Web-based earthquake data evaluation application. Imports events from the [USGS FDSN Event API](https://earthquake.usgs.gov/fdsnws/event/1/), stores them in MySQL, and provides filtering, tabular views, world map, and heatmap visualizations.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic
- **Frontend:** React 18, Vite, MapLibre GL JS, i18n (DE/EN)
- **Database:** MySQL 9
- **Runtime:** Docker Compose

## Quick start

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env and set ADMIN_PASSWORD_HASH (see below)

# 2. Start stack
docker compose up --build -d

# 3. Open UI
# http://localhost:8080  (default login: admin / admin after hash setup)
```

### Admin password

Default development login: **admin / admin** (when `ADMIN_PASSWORD_HASH` is empty).

For production, generate a bcrypt hash:

```bash
docker compose run --rm backend python scripts/hash_password.py your-password
```

Copy the output into `ADMIN_PASSWORD_HASH` in `.env`, then restart the backend.

## Services

| Service  | URL / Port        | Description              |
|----------|-------------------|--------------------------|
| frontend | http://localhost:8080 | Web GUI              |
| backend  | http://localhost:8000 | REST API             |
| sync     | (internal)        | USGS import worker       |
| db       | localhost:3306    | MySQL (internal in prod) |

## Development

```bash
# Backend tests
cd backend && pip install -r requirements.txt && pytest

# Frontend
cd frontend && npm install && npm run dev
```

## Data sync

- **Backfill:** On first start, the sync worker imports historical data from `USGS_BACKFILL_START` (default `2010-01-01`) in time chunks.
- **Incremental:** Every `USGS_SYNC_INTERVAL_MINUTES` (default 15), new/updated events are fetched via `updatedafter`.

Check sync status in the UI or via `GET /api/v1/sync/status`.

## Stop stack (keeps database volume)

```bash
./scripts/compose-dev-down.sh
```

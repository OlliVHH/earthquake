"""Database upsert and sync orchestration for USGS imports."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.earthquake import Earthquake
from app.models.sync_state import SyncState
from app.services.usgs_client import ParsedEarthquake, UsgsClient, USGS_LIMIT

logger = logging.getLogger(__name__)

SYNC_BACKFILL = "backfill"
SYNC_INCREMENTAL = "incremental"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_or_create_sync_state(db: Session, key: str) -> SyncState:
    """Load sync state row or create idle default."""
    state = db.get(SyncState, key)
    if state:
        return state
    state = SyncState(key=key, status="idle")
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def upsert_earthquakes(db: Session, records: Iterable[ParsedEarthquake]) -> int:
    """Bulk upsert parsed earthquakes; returns number of rows touched."""
    count = 0
    now = _utcnow()
    for record in records:
        stmt = insert(Earthquake).values(
            event_id=record.event_id,
            time_utc=record.time_utc,
            latitude=record.latitude,
            longitude=record.longitude,
            depth_km=record.depth_km,
            magnitude=record.magnitude,
            mag_type=record.mag_type,
            location_name=record.location_name,
            author=None,
            catalog=None,
            contributor=None,
            updated_at=record.updated_at,
            fetched_at=now,
        )
        stmt = stmt.on_duplicate_key_update(
            time_utc=record.time_utc,
            latitude=record.latitude,
            longitude=record.longitude,
            depth_km=record.depth_km,
            magnitude=record.magnitude,
            mag_type=record.mag_type,
            location_name=record.location_name,
            updated_at=record.updated_at,
            fetched_at=now,
        )
        db.execute(stmt)
        count += 1
    db.commit()
    return count


def _split_window(start: datetime, end: datetime, parts: int) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into `parts` contiguous sub-windows."""
    if parts <= 1:
        return [(start, end)]
    delta = (end - start) / parts
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    for i in range(parts):
        window_end = end if i == parts - 1 else cursor + delta
        windows.append((cursor, window_end))
        cursor = window_end
    return windows


def fetch_window_adaptive(
    client: UsgsClient,
    db: Session,
    start: datetime,
    end: datetime,
) -> int:
    """Fetch a time window, subdividing if USGS limit is hit."""
    records = client.fetch_window(start, end)
    if len(records) < USGS_LIMIT:
        return upsert_earthquakes(db, records)

    # Window saturated — split and recurse
    total = 0
    for sub_start, sub_end in _split_window(start, end, 2):
        if sub_start >= sub_end:
            continue
        total += fetch_window_adaptive(client, db, sub_start, sub_end)
    return total


def run_backfill(db: Session, settings: Settings | None = None) -> None:
    """Import historical earthquakes from USGS_BACKFILL_START to now."""
    cfg = settings or get_settings()
    state = get_or_create_sync_state(db, SYNC_BACKFILL)
    if state.status == "completed":
        return

    state.status = "running"
    state.message = "Backfill in progress"
    db.commit()

    client = UsgsClient(cfg)
    start = datetime.fromisoformat(f"{cfg.usgs_backfill_start}T00:00:00")
    end = _utcnow()
    cursor = start
    imported = 0

    try:
        while cursor < end:
            window_end = min(cursor + timedelta(days=30), end)
            batch = fetch_window_adaptive(client, db, cursor, window_end)
            imported += batch
            state.message = f"Backfill through {window_end.date()} ({imported} rows)"
            db.commit()
            cursor = window_end

        state.status = "completed"
        state.last_success_at = _utcnow()
        state.message = f"Backfill complete ({imported} rows imported/updated)"
        db.commit()
        logger.info("Backfill finished: %s rows", imported)
    except Exception as exc:
        logger.exception("Backfill failed")
        state.status = "error"
        state.message = str(exc)[:2000]
        db.commit()
        raise


def run_incremental(db: Session, settings: Settings | None = None) -> int:
    """Fetch events updated since last incremental sync."""
    cfg = settings or get_settings()
    state = get_or_create_sync_state(db, SYNC_INCREMENTAL)
    backfill = get_or_create_sync_state(db, SYNC_BACKFILL)

    if backfill.status != "completed":
        run_backfill(db, cfg)

    state.status = "running"
    state.message = "Incremental sync running"
    db.commit()

    client = UsgsClient(cfg)
    updatedafter = state.last_updatedafter or (_utcnow() - timedelta(days=30))

    try:
        records = client.fetch_window(updatedafter, _utcnow(), updatedafter=updatedafter)
        count = upsert_earthquakes(db, records)
        now = _utcnow()
        state.status = "idle"
        state.last_success_at = now
        state.last_updatedafter = now
        state.message = f"Incremental sync OK ({count} rows)"
        db.commit()
        logger.info("Incremental sync: %s rows", count)
        return count
    except Exception as exc:
        logger.exception("Incremental sync failed")
        state.status = "error"
        state.message = str(exc)[:2000]
        db.commit()
        raise


def list_sync_status(db: Session) -> list[SyncState]:
    """Return all sync state rows."""
    return list(db.scalars(select(SyncState)).all())

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

# Human: sync_state row keys for backfill vs incremental USGS import pipelines.
# Agent: READ/WRITTEN in get_or_create_sync_state and run_* functions; DB sync_state.key.
SYNC_BACKFILL = "backfill"
SYNC_INCREMENTAL = "incremental"


# --- Time helpers ---

# Human: Current UTC time as naive datetime (matches DB column convention).
# Agent: RETURNS datetime; no I/O.
def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --- Sync state ---

# Human: Clamp a raw percentage into the inclusive 0–100 range for API and UI display.
# Agent: READS percent float; RETURNS bounded float; no I/O.
def _clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


# Human: Derive backfill completion from processed window cursor vs configured start and now.
# Agent: READS USGS_BACKFILL_START env; READS cursor/end datetimes; RETURNS 0–100 float.
def _backfill_percent(cursor: datetime, start: datetime, end: datetime) -> float:
    total = (end - start).total_seconds()
    if total <= 0:
        return 100.0
    done = (cursor - start).total_seconds()
    return _clamp_percent((done / total) * 100.0)


# Human: Load a sync_state row by key, creating an idle default if missing.
# Agent: READS/WRITES DB sync_state; COMMITS on create; RETURNS SyncState row.
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


# --- Earthquake upsert ---

# Human: Bulk upsert parsed USGS records into earthquakes via MySQL ON DUPLICATE KEY UPDATE.
# Agent: WRITES DB earthquakes table; COMMITS per batch; RETURNS count of records processed.
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


# --- Adaptive window fetching ---

# Human: Split a datetime range into N contiguous sub-windows for recursive USGS fetching.
# Agent: READS start/end datetimes; RETURNS list of (start, end) tuples; no I/O.
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


# Human: Fetch a time window from USGS and upsert; subdivide recursively when USGS_LIMIT is hit.
# Agent: CALLS UsgsClient.fetch_window, upsert_earthquakes; READS USGS_LIMIT; RETURNS total rows upserted; failure modes: empty fetch returns 0.
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


# --- Sync orchestration ---

# Human: Historical import from USGS_BACKFILL_START through now in 30-day windows.
# Agent: READS USGS_BACKFILL_START env; WRITES sync_state and earthquakes; CALLS fetch_window_adaptive; failure modes: sets sync_state.status=error and re-raises on exception.
def run_backfill(db: Session, settings: Settings | None = None) -> None:
    """Import historical earthquakes from USGS_BACKFILL_START to now."""
    cfg = settings or get_settings()
    state = get_or_create_sync_state(db, SYNC_BACKFILL)
    if state.status == "completed":
        return

    state.status = "running"
    state.message = "Backfill in progress"
    state.progress_percent = 0.0
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
            cursor = window_end
            state.progress_percent = _backfill_percent(cursor, start, end)
            state.message = f"Backfill through {window_end.date()} ({imported} rows)"
            db.commit()

        state.status = "completed"
        state.last_success_at = _utcnow()
        state.progress_percent = 100.0
        state.message = f"Backfill complete ({imported} rows imported/updated)"
        db.commit()
        logger.info("Backfill finished: %s rows", imported)
    except Exception as exc:
        logger.exception("Backfill failed")
        state.status = "error"
        state.message = str(exc)[:2000]
        db.commit()
        raise


# Human: Fetch events updated since last incremental cursor; runs backfill first if incomplete.
# Agent: READS/WRITES sync_state; CALLS UsgsClient.fetch_window with updatedafter; WRITES earthquakes; RETURNS upsert count; failure modes: sync_state.status=error on exception.
def run_incremental(db: Session, settings: Settings | None = None) -> int:
    """Fetch events updated since last incremental sync."""
    cfg = settings or get_settings()
    state = get_or_create_sync_state(db, SYNC_INCREMENTAL)
    backfill = get_or_create_sync_state(db, SYNC_BACKFILL)

    if backfill.status != "completed":
        run_backfill(db, cfg)

    state.status = "running"
    state.message = "Incremental sync running"
    state.progress_percent = 10.0
    db.commit()

    client = UsgsClient(cfg)
    updatedafter = state.last_updatedafter or (_utcnow() - timedelta(days=30))

    try:
        state.progress_percent = 40.0
        state.message = "Incremental sync: fetching from USGS"
        db.commit()

        records = client.fetch_window(updatedafter, _utcnow(), updatedafter=updatedafter)

        state.progress_percent = 75.0
        state.message = "Incremental sync: saving to database"
        db.commit()

        count = upsert_earthquakes(db, records)
        now = _utcnow()
        state.status = "idle"
        state.last_success_at = now
        state.last_updatedafter = now
        state.progress_percent = 100.0
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


# Human: Resolve a display-ready progress percentage for one sync_state row.
# Agent: READS SyncState.status/progress_percent; RETURNS 0–100 float; failure modes: unknown keys return 0.
def resolve_progress_percent(state: SyncState) -> float:
    """Return UI progress percentage for a sync job."""
    if state.progress_percent is not None:
        return _clamp_percent(state.progress_percent)

    if state.key == SYNC_BACKFILL:
        if state.status == "completed":
            return 100.0
        return 0.0

    if state.key == SYNC_INCREMENTAL:
        if state.status in {"idle", "completed"} and state.last_success_at:
            return 100.0
        if state.status == "running":
            return 50.0
        return 0.0

    return 0.0


# Human: Return all sync_state rows for the status API.
# Agent: READS DB sync_state; RETURNS list[SyncState].
def list_sync_status(db: Session) -> list[SyncState]:
    """Return all sync state rows."""
    return list(db.scalars(select(SyncState)).all())

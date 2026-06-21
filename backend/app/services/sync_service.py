"""Database upsert and sync orchestration for USGS imports."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from typing import Iterable

from sqlalchemy import select, text
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.earthquake import Earthquake
from app.models.sync_state import SyncState
from app.services.usgs_client import ParsedEarthquake, UsgsClient, USGS_LIMIT, normalize_event_id

logger = logging.getLogger(__name__)

# Human: sync_state row keys for backfill vs incremental USGS import pipelines.
# Agent: READ/WRITTEN in get_or_create_sync_state and run_* functions; DB sync_state.key.
SYNC_BACKFILL = "backfill"
SYNC_INCREMENTAL = "incremental"
SYNC_MYSQL_LOCK_NAME = "earthquake_usgs_sync"
UPSERT_COMMIT_BATCH_SIZE = 250

# Human: Optional callback while upserting one USGS batch (processed count, total in batch).
# Agent: CALLS from upsert_earthquakes after each commit chunk; WRITES sync_state progress in backfill.
UpsertProgressFn = Callable[[int, int], None]

# Human: Optional callback after a time sub-window has been fetched and saved.
# Agent: CALLS from fetch_window_adaptive with sub-window bounds and row count.
SegmentCompleteFn = Callable[[datetime, datetime, int], None]


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


# Human: Try to acquire a MySQL advisory lock so only one sync process writes at a time.
# Agent: DB GET_LOCK; READS SYNC_MYSQL_LOCK_NAME; RETURNS True when lock acquired; failure modes: returns False when another session holds the lock.
def try_acquire_sync_lock(db: Session) -> bool:
    acquired = db.execute(
        text("SELECT GET_LOCK(:name, 0)"),
        {"name": SYNC_MYSQL_LOCK_NAME},
    ).scalar()
    return acquired == 1


# Human: Release the MySQL advisory lock after a sync cycle, including on errors.
# Agent: DB RELEASE_LOCK; READS SYNC_MYSQL_LOCK_NAME; failure modes: no-op when lock not held by this session.
def release_sync_lock(db: Session) -> None:
    db.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": SYNC_MYSQL_LOCK_NAME})


# Human: True when any sync_state row is actively running (UI guard before manual trigger).
# Agent: READS DB sync_state.status; RETURNS bool; failure modes: stale running status still blocks trigger until worker clears it.
def is_sync_running(db: Session) -> bool:
    running = db.scalars(select(SyncState).where(SyncState.status == "running")).first()
    return running is not None


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
# Agent: WRITES DB earthquakes table; COMMITS in batches; RETURNS count of records processed; skips empty event_id.
def upsert_earthquakes(
    db: Session,
    records: Iterable[ParsedEarthquake],
    *,
    on_batch: UpsertProgressFn | None = None,
) -> int:
    """Bulk upsert parsed earthquakes; returns number of rows touched."""
    record_list = list(records)
    total = len(record_list)
    count = 0
    pending = 0
    skipped = 0
    now = _utcnow()
    seen_ids: set[str] = set()

    for record in record_list:
        event_id = normalize_event_id(record.event_id)
        if not event_id:
            skipped += 1
            logger.warning(
                "Skipping USGS record with empty event_id (time=%s lat=%s lon=%s)",
                record.time_utc.isoformat(),
                record.latitude,
                record.longitude,
            )
            continue
        if event_id in seen_ids:
            logger.debug("Skipping duplicate event_id in same USGS batch: %s", event_id)
            continue
        seen_ids.add(event_id)

        stmt = insert(Earthquake).values(
            event_id=event_id,
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
        pending += 1
        if pending >= UPSERT_COMMIT_BATCH_SIZE:
            db.commit()
            pending = 0
            if on_batch:
                on_batch(count, total)

    if pending:
        db.commit()
    if on_batch and count:
        on_batch(count, total)
    if skipped:
        logger.warning("Skipped %s USGS records with empty event_id in one batch", skipped)
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
    *,
    on_segment_complete: SegmentCompleteFn | None = None,
    on_upsert_batch: UpsertProgressFn | None = None,
) -> int:
    """Fetch a time window, subdividing if USGS limit is hit."""
    records = client.fetch_window(start, end)
    if len(records) < USGS_LIMIT:
        count = upsert_earthquakes(db, records, on_batch=on_upsert_batch)
        if on_segment_complete:
            on_segment_complete(start, end, count)
        return count

    # Window saturated — split and recurse
    total = 0
    for sub_start, sub_end in _split_window(start, end, 2):
        if sub_start >= sub_end:
            continue
        total += fetch_window_adaptive(
            client,
            db,
            sub_start,
            sub_end,
            on_segment_complete=on_segment_complete,
            on_upsert_batch=on_upsert_batch,
        )
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

    client = UsgsClient(cfg)
    start = datetime.fromisoformat(f"{cfg.usgs_backfill_start}T00:00:00")
    end = _utcnow()
    # Human: Reuse last_updatedafter on the backfill row as a resume cursor after errors or restarts.
    # Agent: READS sync_state.last_updatedafter; WRITES cursor for next 30-day window loop.
    cursor = state.last_updatedafter if state.last_updatedafter and state.last_updatedafter > start else start
    imported = 0

    state.status = "running"
    state.message = f"Backfill in progress from {cursor.date()}"
    state.progress_percent = _backfill_percent(cursor, start, end)
    db.commit()

    try:
        while cursor < end:
            window_end = min(cursor + timedelta(days=30), end)
            window_rows_written = 0

            # Human: Publish live backfill progress after each sub-window and upsert batch.
            # Agent: WRITES sync_state.progress_percent/message; COMMITS without advancing resume cursor mid-window.
            def on_upsert_batch(done: int, total: int) -> None:
                ratio = (done / total) if total else 1.0
                effective = cursor + (window_end - cursor) * ratio
                state.progress_percent = _backfill_percent(effective, start, end)
                state.message = (
                    f"Backfill through {effective.date()} "
                    f"({imported + window_rows_written + done} rows, writing {done}/{total})"
                )
                db.commit()

            def on_segment_complete(_segment_start: datetime, segment_end: datetime, seg_count: int) -> None:
                nonlocal window_rows_written
                window_rows_written += seg_count
                state.progress_percent = _backfill_percent(segment_end, start, end)
                state.message = f"Backfill through {segment_end.date()} ({imported + window_rows_written} rows)"
                db.commit()

            batch = fetch_window_adaptive(
                client,
                db,
                cursor,
                window_end,
                on_segment_complete=on_segment_complete,
                on_upsert_batch=on_upsert_batch,
            )
            imported += batch
            cursor = window_end
            state.last_updatedafter = cursor
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
    if not try_acquire_sync_lock(db):
        logger.info("Sync skipped: another process holds the USGS sync lock")
        return 0

    try:
        return _run_incremental_locked(db, settings)
    finally:
        release_sync_lock(db)


# Human: Incremental/backfill pipeline after the MySQL advisory lock has been acquired.
# Agent: READS/WRITES sync_state; CALLS run_backfill, UsgsClient, upsert_earthquakes; failure modes: sync_state.status=error on exception.
def _run_incremental_locked(db: Session, settings: Settings | None = None) -> int:
    """Run incremental sync; caller must hold the MySQL sync lock."""
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


# Human: Resolve display progress; incremental stays at 0 while backfill is still incomplete.
# Agent: READS SyncState.status/progress_percent; RETURNS 0–100 float; failure modes: unknown keys return 0.
def resolve_progress_percent(state: SyncState, *, backfill_completed: bool = True) -> float:
    """Return UI progress percentage for a sync job."""
    if state.key == SYNC_INCREMENTAL and not backfill_completed:
        if state.status == "running":
            return _clamp_percent(state.progress_percent or 0.0)
        return 0.0

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

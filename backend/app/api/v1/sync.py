"""Sync status and manual trigger routes."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.errors import AppError
from app.schemas.sync import SyncStatusItem, SyncStatusResponse
from app.services.sync_service import is_sync_running, list_sync_status, resolve_progress_percent, run_incremental

# Human: Authenticated routes to inspect USGS sync state and trigger manual incremental runs.
# Agent: HTTP /sync/*; READS JWT, DB; CALLS sync_service; WRITES via background incremental sync.
router = APIRouter(prefix="/sync", tags=["sync"])


# Human: Background task wrapper that opens its own DB session for one incremental sync cycle.
# Agent: CALLS SessionLocal, run_incremental; WRITES DB via sync_service; failure modes: exceptions logged by caller, session always closed in finally.
def _background_sync() -> None:
    """Run one incremental sync cycle in background."""
    db = SessionLocal()
    try:
        run_incremental(db)
    finally:
        db.close()


# Human: Return backfill and incremental sync state rows for the admin UI.
# Agent: HTTP GET /sync/status; READS DB sync_state; CALLS list_sync_status; RETURNS SyncStatusResponse; REQUIRES auth.
@router.get("/status", response_model=SyncStatusResponse)
def sync_status(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """Return backfill and incremental sync state."""
    rows = list_sync_status(db)
    backfill_completed = any(
        row.key == SYNC_BACKFILL and row.status == "completed" for row in rows
    )
    items: list[SyncStatusItem] = []
    for row in rows:
        base = SyncStatusItem.model_validate(row)
        items.append(
            base.model_copy(
                update={
                    "progress_percent": resolve_progress_percent(
                        row,
                        backfill_completed=backfill_completed,
                    )
                }
            )
        )
    return SyncStatusResponse(items=items)


# Human: Schedule a one-off incremental sync without blocking the HTTP response.
# Agent: HTTP POST /sync/trigger; WRITES BackgroundTasks queue; RETURNS {"status": "scheduled"}; REQUIRES auth; failure modes: 409 when sync already running.
@router.post("/trigger")
def trigger_sync(
    _user: Annotated[str, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Enqueue a manual incremental sync."""
    if is_sync_running(db):
        raise AppError(
            "SYNC_ALREADY_RUNNING",
            "A sync job is already running. Please wait until it finishes.",
            status_code=409,
        )
    background_tasks.add_task(_background_sync)
    return {"status": "scheduled"}

"""Sync status and manual trigger routes."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.schemas.sync import SyncStatusItem, SyncStatusResponse
from app.services.sync_service import list_sync_status, run_incremental

router = APIRouter(prefix="/sync", tags=["sync"])


def _background_sync() -> None:
    """Run one incremental sync cycle in background."""
    db = SessionLocal()
    try:
        run_incremental(db)
    finally:
        db.close()


@router.get("/status", response_model=SyncStatusResponse)
def sync_status(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """Return backfill and incremental sync state."""
    rows = list_sync_status(db)
    return SyncStatusResponse(items=[SyncStatusItem.model_validate(r) for r in rows])


@router.post("/trigger")
def trigger_sync(
    _user: Annotated[str, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Enqueue a manual incremental sync."""
    background_tasks.add_task(_background_sync)
    return {"status": "scheduled"}

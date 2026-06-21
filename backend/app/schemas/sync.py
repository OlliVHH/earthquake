"""Sync status schemas."""

from datetime import datetime

from pydantic import BaseModel


# Human: One sync job's status mirrored from SyncState ORM for the admin dashboard.
# Agent: HTTP response element; READS SyncState row via from_attributes; failure modes: unknown status strings pass through as str.
class SyncStatusItem(BaseModel):
    """Status for one sync job key."""

    key: str
    status: str
    last_success_at: datetime | None
    last_updatedafter: datetime | None
    message: str | None
    progress_percent: float | None = None

    model_config = {"from_attributes": True}


# Human: Wrapper listing all sync job statuses (typically backfill + incremental keys).
# Agent: HTTP response shape; items built from SyncState query; READS DB sync_state table.
class SyncStatusResponse(BaseModel):
    """All sync job statuses."""

    items: list[SyncStatusItem]

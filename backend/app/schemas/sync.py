"""Sync status schemas."""

from datetime import datetime

from pydantic import BaseModel


class SyncStatusItem(BaseModel):
    """Status for one sync job key."""

    key: str
    status: str
    last_success_at: datetime | None
    last_updatedafter: datetime | None
    message: str | None

    model_config = {"from_attributes": True}


class SyncStatusResponse(BaseModel):
    """All sync job statuses."""

    items: list[SyncStatusItem]

"""Pydantic schemas for earthquake API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


# Human: Full earthquake payload for list and detail endpoints; maps from Earthquake ORM via from_attributes.
# Agent: HTTP response shape; READS ORM Earthquake; no DB writes; failure modes: validation error if ORM field missing.
class EarthquakeOut(BaseModel):
    """Single earthquake record for list/detail responses."""

    event_id: str
    time_utc: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float | None
    mag_type: str | None
    location_name: str | None
    author: str | None
    catalog: str | None
    contributor: str | None

    model_config = {"from_attributes": True}


# Human: Paginated list wrapper; limit/offset echo query params for client pagination UI.
# Agent: HTTP response shape; items are EarthquakeOut; READS query limit, offset, total count from handler.
class EarthquakeListResponse(BaseModel):
    """Paginated earthquake list."""

    items: list[EarthquakeOut]
    total: int
    limit: int
    offset: int


# Human: Minimal fields for map markers and heatmap layers to reduce payload size.
# Agent: HTTP response element; READS subset of earthquake rows; failure modes: None magnitude still valid for plotting.
class MapPoint(BaseModel):
    """Lightweight point for map/heatmap rendering."""

    event_id: str
    latitude: float
    longitude: float
    magnitude: float | None
    time_utc: datetime
    location_name: str | None


# Human: Batch of map points plus total count (may exceed len(points) when capped).
# Agent: HTTP response shape; READS filtered geo query results; WRITES nothing.
class MapPointsResponse(BaseModel):
    """Collection of map points."""

    points: list[MapPoint]
    total: int


# Human: Aggregate stats for the current filter set (count, magnitude range, time span).
# Agent: HTTP response shape; READS SQL aggregates; nullable fields when result set is empty.
class EarthquakeStatsResponse(BaseModel):
    """Aggregate statistics for current filter set."""

    count: int
    max_magnitude: float | None
    min_time: datetime | None
    max_time: datetime | None

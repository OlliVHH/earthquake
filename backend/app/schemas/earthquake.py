"""Pydantic schemas for earthquake API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


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


class EarthquakeListResponse(BaseModel):
    """Paginated earthquake list."""

    items: list[EarthquakeOut]
    total: int
    limit: int
    offset: int


class MapPoint(BaseModel):
    """Lightweight point for map/heatmap rendering."""

    event_id: str
    latitude: float
    longitude: float
    magnitude: float | None
    time_utc: datetime
    location_name: str | None


class MapPointsResponse(BaseModel):
    """Collection of map points."""

    points: list[MapPoint]
    total: int


class EarthquakeStatsResponse(BaseModel):
    """Aggregate statistics for current filter set."""

    count: int
    max_magnitude: float | None
    min_time: datetime | None
    max_time: datetime | None

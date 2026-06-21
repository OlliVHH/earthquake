"""Earthquake query routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.schemas.earthquake import (
    EarthquakeListResponse,
    EarthquakeNearbyResponse,
    EarthquakeOut,
    EarthquakeStatsResponse,
    MapPoint,
    MapPointsResponse,
)
from app.services.earthquake_query import (
    EarthquakeFilters,
    count_filtered,
    query_earthquakes,
    query_map_points,
    query_nearby_earthquakes,
    query_stats,
)
from app.services.region_presets import REGION_PRESETS

# Human: Authenticated earthquake query endpoints for list, map, stats, and presets.
# Agent: HTTP /earthquakes/*; READS JWT via get_current_user, DB via get_db; CALLS earthquake_query service.
router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])


# --- Query parameter mapping ---

# Human: Map flat HTTP query params into a single EarthquakeFilters dataclass for the service layer.
# Agent: READS route query params; RETURNS EarthquakeFilters; no DB or HTTP side effects.
def _parse_filters(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_magnitude: float | None = None,
    max_magnitude: float | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    location_query: str | None = None,
    region_preset: str | None = None,
    sort: str = "time_desc",
) -> EarthquakeFilters:
    return EarthquakeFilters(
        start_date=start_date,
        end_date=end_date,
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        min_depth=min_depth,
        max_depth=max_depth,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        location_query=location_query,
        region_preset=region_preset,
        sort=sort,
    )


# --- Route handlers ---

# Human: Expose region preset keys so the frontend can populate filter dropdowns.
# Agent: HTTP GET /earthquakes/presets; READS REGION_PRESETS; REQUIRES auth; RETURNS list of {key, label}.
@router.get("/presets")
def list_presets(_user: Annotated[str, Depends(get_current_user)]) -> list[dict[str, str]]:
    """Return available region preset keys for the UI."""
    return [{"key": p.key, "label": p.key} for p in REGION_PRESETS.values()]


# Human: Paginated earthquake list with shared filter and sort query parameters.
# Agent: HTTP GET /earthquakes; READS DB; CALLS count_filtered, query_earthquakes; RETURNS EarthquakeListResponse; REQUIRES auth.
@router.get("", response_model=EarthquakeListResponse)
def list_earthquakes(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_magnitude: float | None = None,
    max_magnitude: float | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    location_query: str | None = None,
    region_preset: str | None = None,
    sort: str = "time_desc",
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> EarthquakeListResponse:
    """Paginated, filterable earthquake list."""
    filters = _parse_filters(
        start_date, end_date, min_magnitude, max_magnitude,
        min_depth, max_depth, min_lat, max_lat, min_lon, max_lon,
        location_query, region_preset, sort,
    )
    total = count_filtered(db, filters)
    rows = query_earthquakes(db, filters, limit, offset)
    return EarthquakeListResponse(
        items=[EarthquakeOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# Human: GeoJSON-friendly map points for map and heatmap layers (higher default limit than list).
# Agent: HTTP GET /earthquakes/map; READS DB; CALLS count_filtered, query_map_points; RETURNS MapPointsResponse; REQUIRES auth.
@router.get("/map", response_model=MapPointsResponse)
def map_points(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_magnitude: float | None = None,
    max_magnitude: float | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    location_query: str | None = None,
    region_preset: str | None = None,
    sort: str = "time_desc",
    limit: int = Query(default=10000, ge=1, le=50000),
) -> MapPointsResponse:
    """Geo points for map and heatmap layers."""
    filters = _parse_filters(
        start_date, end_date, min_magnitude, max_magnitude,
        min_depth, max_depth, min_lat, max_lat, min_lon, max_lon,
        location_query, region_preset, sort,
    )
    total = count_filtered(db, filters)
    rows = query_map_points(db, filters, limit)
    points = [
        MapPoint(
            event_id=r.event_id,
            latitude=r.latitude,
            longitude=r.longitude,
            magnitude=r.magnitude,
            time_utc=r.time_utc,
            location_name=r.location_name,
        )
        for r in rows
    ]
    return MapPointsResponse(points=points, total=total)


# Human: Earthquakes within a radius of a map/table selection (all DB events, no list filters).
# Agent: HTTP GET /earthquakes/nearby; READS DB; CALLS query_nearby_earthquakes; REQUIRES auth.
@router.get("/nearby", response_model=EarthquakeNearbyResponse)
def nearby_earthquakes(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=100, ge=1, le=500),
    limit: int = Query(default=5000, ge=1, le=10000),
) -> EarthquakeNearbyResponse:
    """Return all known earthquakes within radius_km of a point."""
    rows = query_nearby_earthquakes(db, latitude, longitude, radius_km, limit=limit)
    return EarthquakeNearbyResponse(
        items=[EarthquakeOut.model_validate(r) for r in rows],
        radius_km=radius_km,
        center_latitude=latitude,
        center_longitude=longitude,
    )


# Human: Aggregate statistics (count, max magnitude, time range) for the active filter set.
# Agent: HTTP GET /earthquakes/stats; READS DB; CALLS query_stats; RETURNS EarthquakeStatsResponse; REQUIRES auth.
@router.get("/stats", response_model=EarthquakeStatsResponse)
def earthquake_stats(
    _user: Annotated[str, Depends(get_current_user)],
    db: Session = Depends(get_db),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    min_magnitude: float | None = None,
    max_magnitude: float | None = None,
    min_depth: float | None = None,
    max_depth: float | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    location_query: str | None = None,
    region_preset: str | None = None,
) -> EarthquakeStatsResponse:
    """Aggregate stats for the active filter set."""
    filters = _parse_filters(
        start_date, end_date, min_magnitude, max_magnitude,
        min_depth, max_depth, min_lat, max_lat, min_lon, max_lon,
        location_query, region_preset,
    )
    count, max_mag, min_time, max_time = query_stats(db, filters)
    return EarthquakeStatsResponse(
        count=count,
        max_magnitude=max_mag,
        min_time=min_time,
        max_time=max_time,
    )

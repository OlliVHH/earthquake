"""Shared filter parameters and SQL query building for earthquakes."""

import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.earthquake import Earthquake
from app.services.region_presets import get_region_preset


# --- Filter model ---

# Human: Normalized filter set built from API query parameters before SQL execution.
# Agent: READ by apply_filters and query_* functions; no I/O on its own.
@dataclass
class EarthquakeFilters:
    """Normalized filter set from API query parameters."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    min_magnitude: float | None = None
    max_magnitude: float | None = None
    min_depth: float | None = None
    max_depth: float | None = None
    min_lat: float | None = None
    max_lat: float | None = None
    min_lon: float | None = None
    max_lon: float | None = None
    location_query: str | None = None
    region_preset: str | None = None
    sort: str = "time_desc"


# --- SQL filter builder ---

# Human: Apply date, magnitude, depth, bbox, location, and sort constraints to a SQLAlchemy select.
# Agent: READS EarthquakeFilters and region presets; RETURNS modified Select; no DB execution.
def apply_filters(stmt: Select, filters: EarthquakeFilters) -> Select:
    """Apply earthquake filters to a SQLAlchemy select statement."""
    if filters.start_date:
        stmt = stmt.where(Earthquake.time_utc >= filters.start_date)
    if filters.end_date:
        stmt = stmt.where(Earthquake.time_utc <= filters.end_date)
    if filters.min_magnitude is not None:
        stmt = stmt.where(Earthquake.magnitude >= filters.min_magnitude)
    if filters.max_magnitude is not None:
        stmt = stmt.where(Earthquake.magnitude <= filters.max_magnitude)
    if filters.min_depth is not None:
        stmt = stmt.where(Earthquake.depth_km >= filters.min_depth)
    if filters.max_depth is not None:
        stmt = stmt.where(Earthquake.depth_km <= filters.max_depth)

    preset = get_region_preset(filters.region_preset)
    min_lat = filters.min_lat if filters.min_lat is not None else (preset.min_lat if preset else None)
    max_lat = filters.max_lat if filters.max_lat is not None else (preset.max_lat if preset else None)
    min_lon = filters.min_lon if filters.min_lon is not None else (preset.min_lon if preset else None)
    max_lon = filters.max_lon if filters.max_lon is not None else (preset.max_lon if preset else None)

    if min_lat is not None:
        stmt = stmt.where(Earthquake.latitude >= min_lat)
    if max_lat is not None:
        stmt = stmt.where(Earthquake.latitude <= max_lat)
    if min_lon is not None:
        stmt = stmt.where(Earthquake.longitude >= min_lon)
    if max_lon is not None:
        stmt = stmt.where(Earthquake.longitude <= max_lon)

    if filters.location_query:
        pattern = f"%{filters.location_query.strip()}%"
        stmt = stmt.where(Earthquake.location_name.like(pattern))

    sort_map = {
        "time_desc": Earthquake.time_utc.desc(),
        "time_asc": Earthquake.time_utc.asc(),
        "magnitude_desc": Earthquake.magnitude.desc(),
        "magnitude_asc": Earthquake.magnitude.asc(),
    }
    stmt = stmt.order_by(sort_map.get(filters.sort, Earthquake.time_utc.desc()))
    return stmt


# --- Query entrypoints ---

# Human: Count earthquakes matching the filter set (for pagination totals).
# Agent: READS DB earthquakes; CALLS apply_filters; RETURNS int count.
def count_filtered(db: Session, filters: EarthquakeFilters) -> int:
    """Count earthquakes matching filters."""
    stmt = apply_filters(select(func.count()).select_from(Earthquake), filters)
    return int(db.scalar(stmt) or 0)


# Human: Paginated full earthquake rows for the list API.
# Agent: READS DB earthquakes; CALLS apply_filters; RETURNS list[Earthquake] with limit/offset.
def query_earthquakes(
    db: Session,
    filters: EarthquakeFilters,
    limit: int,
    offset: int,
) -> list[Earthquake]:
    """Return paginated earthquake rows."""
    stmt = apply_filters(select(Earthquake), filters).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


# Human: Cap-limited rows for map rendering (same filters, no offset).
# Agent: READS DB earthquakes; CALLS apply_filters; RETURNS list[Earthquake] up to limit (default 50000).
def query_map_points(db: Session, filters: EarthquakeFilters, limit: int = 50000) -> list[Earthquake]:
    """Return lightweight rows for map rendering (capped)."""
    stmt = apply_filters(select(Earthquake), filters).limit(limit)
    return list(db.scalars(stmt).all())


# Human: Aggregate count, max magnitude, and min/max event times for the filter set.
# Agent: READS DB earthquakes via subquery; CALLS apply_filters; RETURNS tuple[int, float|None, datetime|None, datetime|None].
def query_stats(db: Session, filters: EarthquakeFilters) -> tuple[int, float | None, datetime | None, datetime | None]:
    """Return count, max magnitude, min/max time for filters."""
    base = apply_filters(select(Earthquake), filters).subquery()
    stmt = select(
        func.count(),
        func.max(base.c.magnitude),
        func.min(base.c.time_utc),
        func.max(base.c.time_utc),
    )
    row = db.execute(stmt).one()
    return int(row[0] or 0), row[1], row[2], row[3]


# --- Geo helpers ---

# Human: Great-circle distance in km between two WGS84 points.
# Agent: READS lat/lon degrees; RETURNS float km; no I/O.
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two coordinates."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(a)))


# Human: All earthquakes within radius_km of a center point (ignores dashboard filters).
# Agent: READS DB earthquakes; RETURNS list[Earthquake] sorted by time desc; uses bbox prefilter + haversine.
def query_nearby_earthquakes(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float,
    *,
    limit: int = 5000,
) -> list[Earthquake]:
    """Return earthquakes within radius_km of the given coordinate."""
    lat_delta = radius_km / 111.0
    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    lon_delta = radius_km / (111.0 * cos_lat)

    stmt = (
        select(Earthquake)
        .where(Earthquake.latitude >= latitude - lat_delta)
        .where(Earthquake.latitude <= latitude + lat_delta)
        .where(Earthquake.longitude >= longitude - lon_delta)
        .where(Earthquake.longitude <= longitude + lon_delta)
    )
    candidates = list(db.scalars(stmt).all())

    nearby: list[Earthquake] = []
    for row in candidates:
        if haversine_km(latitude, longitude, row.latitude, row.longitude) <= radius_km:
            nearby.append(row)

    nearby.sort(key=lambda row: row.time_utc, reverse=True)
    return nearby[:limit]

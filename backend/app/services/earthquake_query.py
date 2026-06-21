"""Shared filter parameters and SQL query building for earthquakes."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.earthquake import Earthquake
from app.services.region_presets import get_region_preset


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


def count_filtered(db: Session, filters: EarthquakeFilters) -> int:
    """Count earthquakes matching filters."""
    stmt = apply_filters(select(func.count()).select_from(Earthquake), filters)
    return int(db.scalar(stmt) or 0)


def query_earthquakes(
    db: Session,
    filters: EarthquakeFilters,
    limit: int,
    offset: int,
) -> list[Earthquake]:
    """Return paginated earthquake rows."""
    stmt = apply_filters(select(Earthquake), filters).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def query_map_points(db: Session, filters: EarthquakeFilters, limit: int = 50000) -> list[Earthquake]:
    """Return lightweight rows for map rendering (capped)."""
    stmt = apply_filters(select(Earthquake), filters).limit(limit)
    return list(db.scalars(stmt).all())


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

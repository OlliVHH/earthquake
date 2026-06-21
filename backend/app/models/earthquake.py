"""Earthquake ORM model."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Earthquake(Base):
    """Persisted USGS earthquake event."""

    __tablename__ = "earthquakes"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    depth_km: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    mag_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    author: Mapped[str | None] = mapped_column(String(64), nullable=True)
    catalog: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contributor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_earthquakes_lat_lon", "latitude", "longitude"),
    )

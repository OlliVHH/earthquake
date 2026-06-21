"""USGS FDSN Event API client and GeoJSON parsing."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Human: USGS query endpoint returns at most this many events per request.
# Agent: READ by fetch_window when deciding whether to subdivide time windows.
USGS_LIMIT = 20000


# --- Parsed record types ---

# Human: Normalized earthquake fields extracted from one USGS GeoJSON feature.
# Agent: READ by sync_service upsert; no I/O on its own.
@dataclass
class ParsedEarthquake:
    """Normalized earthquake record from USGS GeoJSON."""

    event_id: str
    time_utc: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float | None
    mag_type: str | None
    location_name: str | None
    updated_at: datetime | None


# --- GeoJSON parsing ---

# Human: Parse ISO8601 timestamps from USGS property strings into naive UTC datetimes.
# Agent: READS ISO8601 string; RETURNS datetime | None; failure modes: invalid format raises from fromisoformat.
def _parse_time(value: str | None) -> datetime | None:
    """Parse ISO8601 timestamp from USGS properties."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


# Human: Convert one GeoJSON Feature dict into a ParsedEarthquake, skipping malformed entries.
# Agent: READS feature dict; RETURNS ParsedEarthquake | None when coords/time/event_id missing.
def parse_geojson_feature(feature: dict[str, Any]) -> ParsedEarthquake | None:
    """Convert one GeoJSON feature to ParsedEarthquake."""
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    if len(coords) < 3:
        return None

    event_id = str(props.get("ids") or props.get("code") or feature.get("id") or "")
    if not event_id:
        return None

    time_raw = props.get("time")
    time_utc: datetime | None = None
    if isinstance(time_raw, (int, float)):
        time_utc = datetime.fromtimestamp(float(time_raw) / 1000.0, tz=UTC).replace(tzinfo=None)
    elif isinstance(time_raw, str):
        time_utc = _parse_time(time_raw)
    if time_utc is None:
        return None

    updated_raw = props.get("updated")
    updated_at: datetime | None = None
    if isinstance(updated_raw, (int, float)):
        updated_at = datetime.fromtimestamp(float(updated_raw) / 1000.0, tz=UTC).replace(tzinfo=None)
    elif isinstance(updated_raw, str):
        updated_at = _parse_time(updated_raw)

    mag = props.get("mag")
    magnitude = float(mag) if mag is not None else None

    return ParsedEarthquake(
        event_id=event_id.split(",")[0].strip(),
        time_utc=time_utc,
        latitude=float(coords[1]),
        longitude=float(coords[0]),
        depth_km=float(coords[2]),
        magnitude=magnitude,
        mag_type=props.get("magType"),
        location_name=props.get("place"),
        updated_at=updated_at,
    )


# Human: Parse a full GeoJSON FeatureCollection payload into a list of valid earthquakes.
# Agent: READS payload dict; CALLS parse_geojson_feature per feature; RETURNS list[ParsedEarthquake].
def parse_geojson_payload(payload: dict[str, Any]) -> list[ParsedEarthquake]:
    """Parse full GeoJSON FeatureCollection."""
    features = payload.get("features") or []
    results: list[ParsedEarthquake] = []
    for feature in features:
        parsed = parse_geojson_feature(feature)
        if parsed:
            results.append(parsed)
    return results


# --- HTTP client ---

# Human: HTTP client for USGS FDSN Event API queries with retry on rate limits and transport errors.
# Agent: READS USGS_BASE_URL, USGS_REQUEST_TIMEOUT_SECONDS from Settings; HTTP GET to USGS; failure modes: returns [] after retries exhausted.
class UsgsClient:
    """HTTP client for USGS earthquake queries."""

    # Human: Bind client to application settings (or explicit Settings override for tests).
    # Agent: READS Settings via get_settings when none passed; STORES self.settings.
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # Human: Fetch and parse earthquakes for a time window, or by updatedafter for incremental sync.
    # Agent: HTTP GET USGS query endpoint; READS env timeout/base URL; RETURNS list[ParsedEarthquake]; failure modes: 429 retried with backoff, HTTPError logged, empty list after 4 attempts.
    def fetch_window(
        self,
        start: datetime,
        end: datetime,
        *,
        updatedafter: datetime | None = None,
    ) -> list[ParsedEarthquake]:
        """Fetch earthquakes for a time window; returns parsed records."""
        params: dict[str, str | int] = {
            "format": "geojson",
            "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": USGS_LIMIT,
            "orderby": "time-asc",
        }
        if updatedafter:
            params.pop("starttime", None)
            params.pop("endtime", None)
            params["updatedafter"] = updatedafter.strftime("%Y-%m-%dT%H:%M:%S")

        for attempt in range(4):
            try:
                with httpx.Client(timeout=self.settings.usgs_request_timeout_seconds) as client:
                    response = client.get(self.settings.usgs_base_url, params=params)
                    if response.status_code == 429:
                        time.sleep(2 ** attempt)
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    return parse_geojson_payload(payload)
            except httpx.HTTPError:
                logger.exception("USGS request failed (attempt %s)", attempt + 1)
                time.sleep(2 ** attempt)
        return []

    # Human: Ask USGS how many events fall in a time window (used for adaptive window splitting).
    # Agent: HTTP GET USGS /count endpoint; READS env timeout; RETURNS int count; failure modes: raise_for_status on HTTP errors.
    def count_window(self, start: datetime, end: datetime) -> int:
        """Return event count for window via USGS count endpoint."""
        count_url = self.settings.usgs_base_url.replace("/query", "/count")
        params = {
            "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with httpx.Client(timeout=self.settings.usgs_request_timeout_seconds) as client:
            response = client.get(count_url, params=params)
            response.raise_for_status()
            return int(response.text.strip())

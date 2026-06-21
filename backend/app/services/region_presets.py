"""Predefined geographic bounding boxes for region presets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegionPreset:
    """Named bounding box for regional filtering."""

    key: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


REGION_PRESETS: dict[str, RegionPreset] = {
    "global": RegionPreset("global", -90.0, 90.0, -180.0, 180.0),
    "europe": RegionPreset("europe", 34.0, 72.0, -25.0, 45.0),
    "north_america": RegionPreset("north_america", 15.0, 72.0, -170.0, -50.0),
    "south_america": RegionPreset("south_america", -56.0, 15.0, -82.0, -34.0),
    "asia": RegionPreset("asia", -10.0, 55.0, 60.0, 150.0),
    "pacific_ring": RegionPreset("pacific_ring", -60.0, 60.0, 100.0, -70.0),
    "middle_east": RegionPreset("middle_east", 12.0, 42.0, 25.0, 65.0),
    "africa": RegionPreset("africa", -35.0, 38.0, -20.0, 52.0),
    "oceania": RegionPreset("oceania", -50.0, 0.0, 110.0, 180.0),
}


def get_region_preset(key: str | None) -> RegionPreset | None:
    """Return preset by key or None if unknown."""
    if not key:
        return None
    return REGION_PRESETS.get(key)

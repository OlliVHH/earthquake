"""Tests for nearby earthquake geo queries."""

# Human: Validate haversine distance helper used by the nearby earthquakes API.
# Agent: CALLS haversine_km; READS known coordinate pairs; no HTTP/DB.
from app.services.earthquake_query import haversine_km


# Human: Same point should report zero distance.
# Agent: CALLS haversine_km; RETURNS 0.0 for identical coordinates.
def test_haversine_same_point() -> None:
    assert haversine_km(48.0, 11.0, 48.0, 11.0) == 0.0


# Human: Rough Paris–London distance should be within a sensible km band.
# Agent: CALLS haversine_km; ASSERTS result between 300 and 400 km.
def test_haversine_paris_london() -> None:
    distance = haversine_km(48.8566, 2.3522, 51.5074, -0.1278)
    assert 300 < distance < 400

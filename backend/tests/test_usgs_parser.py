"""Tests for USGS GeoJSON parsing."""

from app.services.usgs_client import parse_geojson_feature, parse_geojson_payload


def test_parse_geojson_feature_epoch_ms() -> None:
    feature = {
        "id": "us7000abc1",
        "geometry": {"type": "Point", "coordinates": [-122.5, 37.8, 10.0]},
        "properties": {
            "mag": 4.5,
            "magType": "ml",
            "place": "10 km NE of Test City",
            "time": 1640995200000,
            "updated": 1640995300000,
            "ids": "us7000abc1",
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.event_id == "us7000abc1"
    assert parsed.magnitude == 4.5
    assert parsed.latitude == 37.8
    assert parsed.longitude == -122.5
    assert parsed.depth_km == 10.0


def test_parse_geojson_payload_empty() -> None:
    assert parse_geojson_payload({"features": []}) == []

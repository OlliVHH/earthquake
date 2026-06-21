"""Tests for USGS GeoJSON parsing."""

# Human: Validate USGS GeoJSON feature and payload parsing helpers.
# Agent: CALLS parse_geojson_feature, parse_geojson_payload; READS fixture dicts; no HTTP/DB; failure: assert on missing/wrong fields.
from app.services.usgs_client import parse_geojson_feature, parse_geojson_payload


# Human: Parse a single feature with epoch-ms timestamps and GeoJSON Point coordinates.
# Agent: CALLS parse_geojson_feature; READS sample feature dict; RETURNS ParsedEarthquake; failure: assert None or field mismatch.
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


# Human: Empty features array should yield an empty list, not None or errors.
# Agent: CALLS parse_geojson_payload with features=[]; RETURNS []; failure: assert non-empty result.
def test_parse_geojson_payload_empty() -> None:
    assert parse_geojson_payload({"features": []}) == []


# Human: USGS comma-padded properties.ids must resolve when feature.id is absent (root cause of empty PK inserts).
# Agent: CALLS parse_geojson_feature; READS ids=',ak0101nll17,'; RETURNS ak0101nll17.
def test_parse_geojson_feature_padded_ids_without_feature_id() -> None:
    feature = {
        "geometry": {"type": "Point", "coordinates": [-151.6587, 61.0322, 88.4]},
        "properties": {
            "mag": 1.6,
            "magType": "ml",
            "place": "Southern Alaska",
            "time": 1262304643792,
            "ids": ",ak0101nll17,",
            "net": "ak",
            "code": "0101nll17",
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.event_id == "ak0101nll17"


# Human: net+code composite is used when ids list and feature id are both missing.
# Agent: CALLS parse_geojson_feature; READS net/code; RETURNS concatenated event id.
def test_parse_geojson_feature_net_code_fallback() -> None:
    feature = {
        "geometry": {"type": "Point", "coordinates": [-122.5, 37.8, 10.0]},
        "properties": {
            "mag": 1.0,
            "time": 1640995200000,
            "net": "ci",
            "code": "14566836",
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.event_id == "ci14566836"


# Human: Truly id-less features still persist via deterministic synthetic primary keys.
# Agent: CALLS parse_geojson_feature; RETURNS synth-* event_id instead of None.
def test_parse_geojson_feature_synthetic_id_when_all_id_fields_missing() -> None:
    feature = {
        "geometry": {"type": "Point", "coordinates": [10.0, 20.0, 5.0]},
        "properties": {
            "mag": 0.5,
            "time": 1640995200000,
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.event_id.startswith("synth-")


# Human: Null coordinate components must not crash parsing (USGS occasionally omits depth/lat/lon).
# Agent: CALLS parse_geojson_feature; READS null depth; RETURNS ParsedEarthquake with depth 0.
def test_parse_geojson_feature_null_depth_defaults_to_zero() -> None:
    feature = {
        "id": "us7000nulldepth",
        "geometry": {"type": "Point", "coordinates": [10.0, 20.0, None]},
        "properties": {
            "mag": 1.2,
            "time": 1640995200000,
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.depth_km == 0.0


# Human: Features with null latitude are skipped instead of aborting the whole backfill batch.
# Agent: CALLS parse_geojson_feature; READS null latitude; RETURNS None.
def test_parse_geojson_feature_skips_null_latitude() -> None:
    feature = {
        "id": "us7000badlat",
        "geometry": {"type": "Point", "coordinates": [10.0, None, 5.0]},
        "properties": {
            "mag": 1.2,
            "time": 1640995200000,
        },
    }
    assert parse_geojson_feature(feature) is None


# Human: Whitespace-only ids with no time/coords still yield None (unparseable feature).
# Agent: CALLS parse_geojson_feature; READS invalid geometry/time; RETURNS None.
def test_parse_geojson_feature_rejects_blank_event_id() -> None:
    feature = {
        "id": "   ",
        "geometry": {"type": "Point", "coordinates": []},
        "properties": {
            "mag": 1.0,
            "time": 1640995200000,
            "ids": "   ",
        },
    }
    assert parse_geojson_feature(feature) is None


# Human: Prefer top-level GeoJSON feature id when properties.ids is empty.
# Agent: CALLS parse_geojson_feature; READS feature.id; RETURNS ParsedEarthquake with canonical id.
def test_parse_geojson_feature_uses_feature_id_when_properties_ids_empty() -> None:
    feature = {
        "id": "usp000abc1",
        "geometry": {"type": "Point", "coordinates": [-122.5, 37.8, 10.0]},
        "properties": {
            "mag": 2.1,
            "time": 1640995200000,
            "ids": "",
        },
    }
    parsed = parse_geojson_feature(feature)
    assert parsed is not None
    assert parsed.event_id == "usp000abc1"


# Human: Each GeoJSON feature becomes one parsed earthquake row candidate.
# Agent: CALLS parse_geojson_payload; RETURNS two items for two distinct feature ids.
def test_parse_geojson_payload_one_record_per_feature() -> None:
    payload = {
        "features": [
            {
                "id": "event-a",
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0, 3.0]},
                "properties": {"time": 1640995200000, "mag": 1.0},
            },
            {
                "id": "event-b",
                "geometry": {"type": "Point", "coordinates": [4.0, 5.0, 6.0]},
                "properties": {"time": 1640995300000, "mag": 2.0},
            },
        ]
    }
    parsed = parse_geojson_payload(payload)
    assert len(parsed) == 2
    assert {row.event_id for row in parsed} == {"event-a", "event-b"}

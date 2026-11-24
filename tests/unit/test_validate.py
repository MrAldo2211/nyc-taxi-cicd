"""Unit tests for data-contract validation functions."""

import pytest

from src.ingest import load_fixture_data
from src.transform import aggregate_zone_summary, build_zones_lookup, transform_trips
from src.validate import (
    DataContractError,
    validate_enriched_trips,
    validate_raw_trips_schema,
    validate_zone_summary,
    validate_zones_lookup,
)


def test_validation_passes_on_clean_fixture_outputs() -> None:
    trips_csv, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)
    validate_zones_lookup(zones_lookup)

    enriched, _ = transform_trips(trips_csv, zones_lookup)
    validate_enriched_trips(enriched)

    summary = aggregate_zone_summary(enriched)
    validate_zone_summary(summary, expected_total_trips=len(enriched))


def test_validate_raw_trips_schema_rejects_missing_columns() -> None:
    with pytest.raises(DataContractError, match="missing required columns"):
        validate_raw_trips_schema(["vendorid", "tpep_pickup_datetime"])


def test_validate_zones_lookup_rejects_duplicates_and_bad_coordinates() -> None:
    _, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)

    duplicated = [zones_lookup[0], dict(zones_lookup[0])]
    with pytest.raises(DataContractError, match="Duplicate locationid"):
        validate_zones_lookup(duplicated)

    out_of_bounds = [dict(zones_lookup[0], centroid_lat=10.0)]
    with pytest.raises(DataContractError, match="outside NYC bounds"):
        validate_zones_lookup(out_of_bounds)


def test_validate_enriched_trips_rejects_invalid_values_and_empty() -> None:
    with pytest.raises(DataContractError, match="must not be empty"):
        validate_enriched_trips([])

    trips_csv, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)
    enriched, _ = transform_trips(trips_csv, zones_lookup)

    bad_fare = [dict(enriched[0], fare_amount=-1.0)]
    with pytest.raises(DataContractError, match="negative fare_amount"):
        validate_enriched_trips(bad_fare)

    bad_distance = [dict(enriched[0], trip_distance=0.0)]
    with pytest.raises(DataContractError, match="non-positive trip_distance"):
        validate_enriched_trips(bad_distance)

    bad_hour = [dict(enriched[0], pickup_hour=25)]
    with pytest.raises(DataContractError, match="invalid pickup_hour"):
        validate_enriched_trips(bad_hour)


def test_validate_zone_summary_rejects_mismatched_trip_sum() -> None:
    trips_csv, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)
    enriched, _ = transform_trips(trips_csv, zones_lookup)
    summary = aggregate_zone_summary(enriched)

    with pytest.raises(DataContractError, match="does not match enriched trips"):
        validate_zone_summary(summary, expected_total_trips=len(enriched) + 1)

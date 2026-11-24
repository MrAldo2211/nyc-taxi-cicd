"""Unit tests for spatial centroid extraction, zone deduplication, trip cleaning, and aggregation."""

from src.ingest import load_fixture_data
from src.transform import (
    aggregate_zone_summary,
    build_zones_lookup,
    compute_multipolygon_centroid,
    transform_trips,
)


def test_compute_multipolygon_centroid() -> None:
    geom = {
        "type": "MultiPolygon",
        "coordinates": [[[[-74.0, 40.7], [-73.9, 40.7], [-73.9, 40.8], [-74.0, 40.8]]]],
    }
    lat, lon = compute_multipolygon_centroid(geom)
    assert lat == 40.75
    assert lon == -73.95


def test_build_zones_lookup_deduplicates_keeping_largest_area() -> None:
    _, raw_zones = load_fixture_data()
    lookup = build_zones_lookup(raw_zones)

    assert len(raw_zones) == 11
    assert len(lookup) == 10

    corona = next(z for z in lookup if z["locationid"] == "56")
    assert corona["zone"] == "Corona"
    assert corona["shape_area"] == 0.00045


def test_transform_trips_filters_invalid_and_enriches_zones() -> None:
    trips_csv, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)

    enriched, stats = transform_trips(trips_csv, zones_lookup)

    assert stats["raw_trips_count"] == 15
    assert stats["valid_trips_count"] == 12
    assert stats["dropped_invalid_trips_count"] == 3
    assert stats["drop_reasons"] == {
        "negative_fare_or_total": 1,
        "invalid_distance": 1,
        "invalid_duration": 1,
        "parse_error": 0,
    }

    first = enriched[0]
    assert first["pu_zone"] == "Midtown Center"
    assert first["do_zone"] == "Lenox Hill West"
    assert first["pickup_date"] == "2023-01-01"
    assert first["pickup_hour"] == 0
    assert first["trip_duration_minutes"] == 8.43
    assert first["avg_speed_mph"] == 6.9
    assert first["tip_percentage"] == 0.0

    # Verify tip percentage calculation on row 2 (fare=7.9, tip=4.0)
    second = enriched[1]
    assert second["tip_percentage"] == 50.63

    # Verify fallback handling for unknown location ID 264 and 265
    unknown_row = next(r for r in enriched if r["pulocationid"] == "264")
    assert unknown_row["pu_zone"] == "Unknown"
    assert unknown_row["pu_borough"] == "Unknown"
    assert unknown_row["pu_centroid_lat"] == ""

    # Verify fallback for 265 explicitly
    outside_csv = (
        '"vendorid","tpep_pickup_datetime","tpep_dropoff_datetime","passenger_count","trip_distance",'
        '"ratecodeid","store_and_fwd_flag","pulocationid","dolocationid","payment_type","fare_amount",'
        '"extra","mta_tax","tip_amount","tolls_amount","improvement_surcharge","total_amount",'
        '"congestion_surcharge","airport_fee"\n'
        '"2","2023-01-01T10:00:00.000","2023-01-01T10:30:00.000","1.0","10.0","1.0","N",'
        '"265","161","1","40.0","0.0","0.5","5.0","0.0","1.0","46.5","0.0","0.0"\n'
    )
    outside_enriched, _ = transform_trips(outside_csv, zones_lookup)
    assert outside_enriched[0]["pu_zone"] == "Outside of NYC"
    assert outside_enriched[0]["pu_borough"] == "N/A"


def test_aggregate_zone_summary_totals_and_sorting() -> None:
    trips_csv, raw_zones = load_fixture_data()
    zones_lookup = build_zones_lookup(raw_zones)
    enriched, _ = transform_trips(trips_csv, zones_lookup)

    summary = aggregate_zone_summary(enriched)

    assert sum(row["trip_count"] for row in summary) == len(enriched) == 12
    # JFK Airport (132) has 2 high-fare trips ($91.3 + $93.3 = $184.6) -> highest total revenue
    assert summary[0]["pulocationid"] == "132"
    assert summary[0]["pu_zone"] == "JFK Airport"
    assert summary[0]["trip_count"] == 2
    assert summary[0]["total_revenue"] == 184.6

    revenues = [row["total_revenue"] for row in summary]
    assert revenues == sorted(revenues, reverse=True)

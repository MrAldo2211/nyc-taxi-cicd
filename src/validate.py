"""Data-contract validation rules for raw schemas, zones lookup, enriched trips, and summaries."""

from __future__ import annotations

from typing import Iterable, Sequence

from src.config import (
    ENRICHED_TRIP_COLUMNS,
    NYC_LAT_MAX,
    NYC_LAT_MIN,
    NYC_LON_MAX,
    NYC_LON_MIN,
    REQUIRED_RAW_TRIP_COLUMNS,
    ZONE_SUMMARY_COLUMNS,
    ZONES_LOOKUP_COLUMNS,
)


class DataContractError(ValueError):
    """Raised when ingested or transformed records violate the pipeline data contract."""


def validate_raw_trips_schema(fieldnames: Sequence[str] | None) -> None:
    """Verify that the raw CSV header includes all required NYC Yellow Taxi columns."""
    if not fieldnames:
        raise DataContractError("Raw trips CSV has an empty or missing header.")

    present = {col.strip() for col in fieldnames if col}
    missing = [col for col in REQUIRED_RAW_TRIP_COLUMNS if col not in present]
    if missing:
        raise DataContractError(f"Raw trips CSV is missing required columns: {missing}")


def validate_zones_lookup(zones: Sequence[dict]) -> None:
    """Verify uniqueness, non-empty metadata, and valid NYC coordinate bounds for zones lookup."""
    if not zones:
        raise DataContractError("Zones lookup table must not be empty.")

    seen_ids: set[str] = set()
    for idx, row in enumerate(zones):
        missing = [col for col in ZONES_LOOKUP_COLUMNS if col not in row]
        if missing:
            raise DataContractError(f"Zones row {idx} missing columns: {missing}")

        loc_id = str(row["locationid"]).strip()
        if not loc_id:
            raise DataContractError(f"Zones row {idx} has an empty locationid.")
        if loc_id in seen_ids:
            raise DataContractError(f"Duplicate locationid detected in zones lookup: {loc_id}")
        seen_ids.add(loc_id)

        if not str(row["zone"]).strip():
            raise DataContractError(f"Zone {loc_id} has an empty zone name.")
        if not str(row["borough"]).strip():
            raise DataContractError(f"Zone {loc_id} has an empty borough.")

        lat = row.get("centroid_lat")
        lon = row.get("centroid_lon")
        if lat not in (None, "") and lon not in (None, ""):
            lat_f = float(lat)
            lon_f = float(lon)
            if not (NYC_LAT_MIN <= lat_f <= NYC_LAT_MAX):
                raise DataContractError(
                    f"Zone {loc_id} centroid_lat={lat_f} outside NYC bounds [{NYC_LAT_MIN}, {NYC_LAT_MAX}]."
                )
            if not (NYC_LON_MIN <= lon_f <= NYC_LON_MAX):
                raise DataContractError(
                    f"Zone {loc_id} centroid_lon={lon_f} outside NYC bounds [{NYC_LON_MIN}, {NYC_LON_MAX}]."
                )


def validate_enriched_trips(rows: Sequence[dict]) -> None:
    """Verify every enriched trip row satisfies schema, value, and enrichment invariants."""
    if not rows:
        raise DataContractError("Enriched trips output must not be empty.")

    for idx, row in enumerate(rows):
        missing = [col for col in ENRICHED_TRIP_COLUMNS if col not in row]
        if missing:
            raise DataContractError(f"Enriched trip row {idx} missing columns: {missing}")

        fare = float(row["fare_amount"])
        total = float(row["total_amount"])
        dist = float(row["trip_distance"])
        duration = float(row["trip_duration_minutes"])
        hour = int(row["pickup_hour"])

        if fare < 0:
            raise DataContractError(f"Enriched trip row {idx} has negative fare_amount={fare}.")
        if total < 0:
            raise DataContractError(f"Enriched trip row {idx} has negative total_amount={total}.")
        if dist <= 0:
            raise DataContractError(f"Enriched trip row {idx} has non-positive trip_distance={dist}.")
        if duration <= 0:
            raise DataContractError(
                f"Enriched trip row {idx} has non-positive trip_duration_minutes={duration}."
            )
        if not (0 <= hour <= 23):
            raise DataContractError(f"Enriched trip row {idx} has invalid pickup_hour={hour}.")
        if not str(row["pu_zone"]).strip() or not str(row["do_zone"]).strip():
            raise DataContractError(f"Enriched trip row {idx} has empty pickup/dropoff zone name.")


def validate_zone_summary(summary_rows: Sequence[dict], expected_total_trips: int) -> None:
    """Verify zone aggregation totals match the enriched trips count and revenue invariants."""
    if not summary_rows:
        raise DataContractError("Zone summary output must not be empty.")

    total_trips = 0
    for idx, row in enumerate(summary_rows):
        missing = [col for col in ZONE_SUMMARY_COLUMNS if col not in row]
        if missing:
            raise DataContractError(f"Zone summary row {idx} missing columns: {missing}")

        trip_count = int(row["trip_count"])
        total_revenue = float(row["total_revenue"])
        if trip_count <= 0:
            raise DataContractError(f"Zone summary row {idx} has non-positive trip_count={trip_count}.")
        if total_revenue < 0:
            raise DataContractError(
                f"Zone summary row {idx} has negative total_revenue={total_revenue}."
            )
        total_trips += trip_count

    if total_trips != expected_total_trips:
        raise DataContractError(
            f"Zone summary trip_count sum ({total_trips}) does not match enriched trips ({expected_total_trips})."
        )

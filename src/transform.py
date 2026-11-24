"""Data cleaning, spatial centroid extraction, zone enrichment, and aggregation transforms."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import (
    FALLBACK_ZONES,
    MAX_TRIP_DISTANCE_MILES,
    MAX_TRIP_DURATION_MINUTES,
)
from src.validate import validate_raw_trips_schema


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert numeric string/value to float safely, returning default for blank/None."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    return float(text)


def normalize_location_id(value: Any) -> str:
    """Normalize location IDs such as '161', '161.0', or ' 161 ' into canonical integer strings."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def parse_iso_datetime(value: str) -> datetime:
    """Parse Socrata ISO-8601 timestamps (with optional Z suffix) into datetime objects."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("Empty datetime value")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _extract_lon_lat_points(coordinates: Any, acc: list[tuple[float, float]]) -> None:
    """Recursively collect [lon, lat] coordinate pairs from GeoJSON coordinate nests."""
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        return
    if isinstance(coordinates[0], (int, float)) and len(coordinates) >= 2:
        acc.append((float(coordinates[0]), float(coordinates[1])))
        return
    for item in coordinates:
        _extract_lon_lat_points(item, acc)


def compute_multipolygon_centroid(the_geom: dict | None) -> tuple[float | None, float | None]:
    """Compute bounding-mean (centroid_lat, centroid_lon) from a GeoJSON Polygon/MultiPolygon."""
    if not isinstance(the_geom, dict):
        return None, None
    coords = the_geom.get("coordinates")
    if not coords:
        return None, None

    points: list[tuple[float, float]] = []
    _extract_lon_lat_points(coords, points)
    if not points:
        return None, None

    mean_lon = sum(pt[0] for pt in points) / len(points)
    mean_lat = sum(pt[1] for pt in points) / len(points)
    return round(mean_lat, 6), round(mean_lon, 6)


def build_zones_lookup(raw_zones: list[dict]) -> list[dict]:
    """Deduplicate raw NYC Taxi Zones by locationid (keeping largest shape_area) with centroids."""
    best_by_id: dict[str, dict] = {}
    for entry in raw_zones:
        loc_id = normalize_location_id(entry.get("locationid"))
        if not loc_id:
            continue

        shape_area = safe_float(entry.get("shape_area"), 0.0)
        shape_leng = safe_float(entry.get("shape_leng"), 0.0)
        zone_name = str(entry.get("zone") or "").strip() or f"Zone {loc_id}"
        borough = str(entry.get("borough") or "").strip() or "Unknown"
        centroid_lat, centroid_lon = compute_multipolygon_centroid(entry.get("the_geom"))

        candidate = {
            "locationid": loc_id,
            "zone": zone_name,
            "borough": borough,
            "shape_leng": round(shape_leng, 6),
            "shape_area": round(shape_area, 9),
            "centroid_lat": centroid_lat,
            "centroid_lon": centroid_lon,
        }

        existing = best_by_id.get(loc_id)
        if existing is None or candidate["shape_area"] > existing["shape_area"]:
            best_by_id[loc_id] = candidate

    def _sort_key(item: dict) -> tuple[int, str]:
        try:
            return (0, f"{int(item['locationid']):06d}")
        except ValueError:
            return (1, item["locationid"])

    return sorted(best_by_id.values(), key=_sort_key)


def _resolve_zone_info(loc_id: str, zones_by_id: dict[str, dict]) -> dict[str, Any]:
    """Resolve zone name, borough, and centroid for a locationid with clean fallbacks."""
    if loc_id in zones_by_id:
        match = zones_by_id[loc_id]
        return {
            "zone": match["zone"],
            "borough": match["borough"],
            "centroid_lat": match["centroid_lat"] if match["centroid_lat"] is not None else "",
            "centroid_lon": match["centroid_lon"] if match["centroid_lon"] is not None else "",
        }
    if loc_id in FALLBACK_ZONES:
        fb = FALLBACK_ZONES[loc_id]
        return {
            "zone": fb["zone"],
            "borough": fb["borough"],
            "centroid_lat": "",
            "centroid_lon": "",
        }
    return {
        "zone": "Unknown" if not loc_id else f"Zone {loc_id}",
        "borough": "Unknown",
        "centroid_lat": "",
        "centroid_lon": "",
    }


def transform_trips(
    trips_csv_text: str,
    zones_lookup: list[dict],
) -> tuple[list[dict], dict[str, Any]]:
    """Clean raw Yellow Taxi trips, filter invalid rows, and enrich with NYC Taxi Zone spatial metadata."""
    reader = csv.DictReader(io.StringIO(trips_csv_text))
    validate_raw_trips_schema(reader.fieldnames)

    zones_by_id = {str(z["locationid"]).strip(): z for z in zones_lookup}

    enriched_rows: list[dict] = []
    drop_reasons: dict[str, int] = {
        "negative_fare_or_total": 0,
        "invalid_distance": 0,
        "invalid_duration": 0,
        "parse_error": 0,
    }
    raw_count = 0

    for row in reader:
        raw_count += 1
        try:
            pickup_dt = parse_iso_datetime(row["tpep_pickup_datetime"])
            dropoff_dt = parse_iso_datetime(row["tpep_dropoff_datetime"])

            pu_id = normalize_location_id(row["pulocationid"])
            do_id = normalize_location_id(row["dolocationid"])
            if not pu_id or not do_id:
                drop_reasons["parse_error"] += 1
                continue

            trip_distance = safe_float(row["trip_distance"], 0.0)
            fare_amount = safe_float(row["fare_amount"], 0.0)
            tip_amount = safe_float(row["tip_amount"], 0.0)
            tolls_amount = safe_float(row["tolls_amount"], 0.0)
            total_amount = safe_float(row["total_amount"], 0.0)
            congestion_surcharge = safe_float(row.get("congestion_surcharge"), 0.0)
            airport_fee = safe_float(row.get("airport_fee"), 0.0)
            passenger_count = int(round(safe_float(row.get("passenger_count"), 0.0)))
        except (KeyError, ValueError, TypeError):
            drop_reasons["parse_error"] += 1
            continue

        if fare_amount < 0 or total_amount < 0:
            drop_reasons["negative_fare_or_total"] += 1
            continue

        if trip_distance <= 0 or trip_distance > MAX_TRIP_DISTANCE_MILES:
            drop_reasons["invalid_distance"] += 1
            continue

        duration_minutes = (dropoff_dt - pickup_dt).total_seconds() / 60.0
        if duration_minutes <= 0 or duration_minutes > MAX_TRIP_DURATION_MINUTES:
            drop_reasons["invalid_duration"] += 1
            continue

        avg_speed_mph = round(trip_distance / (duration_minutes / 60.0), 2)
        tip_percentage = round((tip_amount / fare_amount) * 100.0, 2) if fare_amount > 0 else 0.0

        pu_info = _resolve_zone_info(pu_id, zones_by_id)
        do_info = _resolve_zone_info(do_id, zones_by_id)

        enriched_rows.append(
            {
                "vendorid": normalize_location_id(row.get("vendorid")) or str(row.get("vendorid", "")).strip(),
                "tpep_pickup_datetime": pickup_dt.isoformat(timespec="seconds"),
                "tpep_dropoff_datetime": dropoff_dt.isoformat(timespec="seconds"),
                "pickup_date": pickup_dt.date().isoformat(),
                "pickup_hour": pickup_dt.hour,
                "passenger_count": passenger_count,
                "trip_distance": round(trip_distance, 3),
                "trip_duration_minutes": round(duration_minutes, 2),
                "avg_speed_mph": avg_speed_mph,
                "ratecodeid": normalize_location_id(row.get("ratecodeid")),
                "payment_type": normalize_location_id(row.get("payment_type")),
                "pulocationid": pu_id,
                "pu_zone": pu_info["zone"],
                "pu_borough": pu_info["borough"],
                "pu_centroid_lat": pu_info["centroid_lat"],
                "pu_centroid_lon": pu_info["centroid_lon"],
                "dolocationid": do_id,
                "do_zone": do_info["zone"],
                "do_borough": do_info["borough"],
                "do_centroid_lat": do_info["centroid_lat"],
                "do_centroid_lon": do_info["centroid_lon"],
                "fare_amount": round(fare_amount, 2),
                "tip_amount": round(tip_amount, 2),
                "tip_percentage": tip_percentage,
                "tolls_amount": round(tolls_amount, 2),
                "total_amount": round(total_amount, 2),
                "congestion_surcharge": round(congestion_surcharge, 2),
                "airport_fee": round(airport_fee, 2),
            }
        )

    stats = {
        "raw_trips_count": raw_count,
        "valid_trips_count": len(enriched_rows),
        "dropped_invalid_trips_count": raw_count - len(enriched_rows),
        "drop_reasons": drop_reasons,
    }
    return enriched_rows, stats


def aggregate_zone_summary(enriched_trips: list[dict]) -> list[dict]:
    """Aggregate trip volume, average distance/duration/fare/tip, and revenue per pickup zone."""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "pu_zone": "",
            "pu_borough": "",
            "pu_centroid_lat": "",
            "pu_centroid_lon": "",
            "trip_count": 0,
            "total_passengers": 0,
            "sum_distance": 0.0,
            "sum_duration": 0.0,
            "sum_fare": 0.0,
            "sum_tip": 0.0,
            "total_revenue": 0.0,
        }
    )

    for trip in enriched_trips:
        pu_id = str(trip["pulocationid"])
        acc = grouped[pu_id]
        acc["pu_zone"] = trip["pu_zone"]
        acc["pu_borough"] = trip["pu_borough"]
        acc["pu_centroid_lat"] = trip["pu_centroid_lat"]
        acc["pu_centroid_lon"] = trip["pu_centroid_lon"]
        acc["trip_count"] += 1
        acc["total_passengers"] += int(trip["passenger_count"])
        acc["sum_distance"] += float(trip["trip_distance"])
        acc["sum_duration"] += float(trip["trip_duration_minutes"])
        acc["sum_fare"] += float(trip["fare_amount"])
        acc["sum_tip"] += float(trip["tip_amount"])
        acc["total_revenue"] += float(trip["total_amount"])

    summary_rows: list[dict] = []
    for pu_id, acc in grouped.items():
        count = acc["trip_count"]
        summary_rows.append(
            {
                "pulocationid": pu_id,
                "pu_zone": acc["pu_zone"],
                "pu_borough": acc["pu_borough"],
                "pu_centroid_lat": acc["pu_centroid_lat"],
                "pu_centroid_lon": acc["pu_centroid_lon"],
                "trip_count": count,
                "total_passengers": acc["total_passengers"],
                "avg_trip_distance": round(acc["sum_distance"] / count, 3),
                "avg_duration_minutes": round(acc["sum_duration"] / count, 2),
                "avg_fare_amount": round(acc["sum_fare"] / count, 2),
                "avg_tip_amount": round(acc["sum_tip"] / count, 2),
                "total_revenue": round(acc["total_revenue"], 2),
            }
        )

    summary_rows.sort(
        key=lambda r: (float(r["total_revenue"]), int(r["trip_count"])),
        reverse=True,
    )
    return summary_rows


def write_csv(rows: list[dict], fieldnames: list[str], output_path: Path) -> Path:
    """Write a list of dictionaries to CSV with an explicit column order."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path

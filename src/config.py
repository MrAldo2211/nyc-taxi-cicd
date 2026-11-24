"""Centralized configuration, schema contracts, and API URL builders."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_TRIPS_PATH = PROJECT_ROOT / "data" / "sample" / "trips_sample.csv"
SAMPLE_ZONES_PATH = PROJECT_ROOT / "data" / "sample" / "zones_sample.json"

NYC_OPEN_DATA_BASE_URL = "https://data.cityofnewyork.us/resource"
DEFAULT_TAXI_DATASET_ID = os.getenv("TAXI_DATASET_ID", "4b4i-vvec")
ALTERNATIVE_2024_DATASET_ID = "rwwi-khbc"
ZONES_DATASET_ID = "8meu-9t5y"

DEFAULT_BATCH_LIMIT = int(os.getenv("TAXI_BATCH_LIMIT", "25000"))
DEFAULT_BATCH_OFFSET = int(os.getenv("TAXI_BATCH_OFFSET", "0"))
DEFAULT_ZONES_LIMIT = int(os.getenv("ZONES_LIMIT", "300"))
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))

MAX_TRIP_DISTANCE_MILES = 500.0
MAX_TRIP_DURATION_MINUTES = 1440.0

NYC_LAT_MIN = 40.4
NYC_LAT_MAX = 41.0
NYC_LON_MIN = -74.4
NYC_LON_MAX = -73.6

REQUIRED_RAW_TRIP_COLUMNS = [
    "vendorid",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "ratecodeid",
    "store_and_fwd_flag",
    "pulocationid",
    "dolocationid",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]

ZONES_LOOKUP_COLUMNS = [
    "locationid",
    "zone",
    "borough",
    "shape_leng",
    "shape_area",
    "centroid_lat",
    "centroid_lon",
]

ENRICHED_TRIP_COLUMNS = [
    "vendorid",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "pickup_date",
    "pickup_hour",
    "passenger_count",
    "trip_distance",
    "trip_duration_minutes",
    "avg_speed_mph",
    "ratecodeid",
    "payment_type",
    "pulocationid",
    "pu_zone",
    "pu_borough",
    "pu_centroid_lat",
    "pu_centroid_lon",
    "dolocationid",
    "do_zone",
    "do_borough",
    "do_centroid_lat",
    "do_centroid_lon",
    "fare_amount",
    "tip_amount",
    "tip_percentage",
    "tolls_amount",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]

ZONE_SUMMARY_COLUMNS = [
    "pulocationid",
    "pu_zone",
    "pu_borough",
    "pu_centroid_lat",
    "pu_centroid_lon",
    "trip_count",
    "total_passengers",
    "avg_trip_distance",
    "avg_duration_minutes",
    "avg_fare_amount",
    "avg_tip_amount",
    "total_revenue",
]

FALLBACK_ZONES: dict[str, dict[str, str]] = {
    "264": {"zone": "Unknown", "borough": "Unknown"},
    "265": {"zone": "Outside of NYC", "borough": "N/A"},
}


def build_trips_url(dataset_id: str = DEFAULT_TAXI_DATASET_ID, fmt: str = "csv") -> str:
    """Build NYC Open Data Socrata resource URL for Yellow Taxi trip records."""
    clean_id = dataset_id.strip()
    clean_fmt = fmt.strip().lstrip(".")
    return f"{NYC_OPEN_DATA_BASE_URL}/{clean_id}.{clean_fmt}"


def build_zones_url() -> str:
    """Build NYC Open Data Socrata resource URL for NYC Taxi Zones GeoJSON/JSON."""
    return f"{NYC_OPEN_DATA_BASE_URL}/{ZONES_DATASET_ID}.json"

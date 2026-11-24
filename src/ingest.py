"""HTTP ingestion clients with retry logic and fixture loaders for NYC Open Data."""

from __future__ import annotations

import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import (
    DEFAULT_BATCH_LIMIT,
    DEFAULT_BATCH_OFFSET,
    DEFAULT_TAXI_DATASET_ID,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_ZONES_LIMIT,
    SAMPLE_TRIPS_PATH,
    SAMPLE_ZONES_PATH,
    build_trips_url,
    build_zones_url,
)


def build_http_session(retries: int = 3, backoff_factor: float = 1.5) -> requests.Session:
    """Create a requests Session configured with retry backoff for transient API errors."""
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_taxi_trips_csv(
    dataset_id: str = DEFAULT_TAXI_DATASET_ID,
    limit: int = DEFAULT_BATCH_LIMIT,
    offset: int = DEFAULT_BATCH_OFFSET,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> str:
    """Fetch a paginated batch of NYC Yellow Taxi trips in CSV format."""
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")
    if offset < 0:
        raise ValueError(f"offset must be non-negative, got {offset}")

    own_session = session is None
    client = session or build_http_session()
    try:
        url = build_trips_url(dataset_id=dataset_id, fmt="csv")
        response = client.get(
            url,
            params={"$limit": limit, "$offset": offset},
            timeout=timeout,
        )
        response.raise_for_status()
        if not response.text.strip():
            raise ValueError(f"Empty CSV payload returned from {url} (limit={limit}, offset={offset})")
        return response.text
    finally:
        if own_session:
            client.close()


def fetch_taxi_zones_json(
    limit: int = DEFAULT_ZONES_LIMIT,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> list[dict]:
    """Fetch NYC Taxi Zone polygons and metadata in JSON format."""
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")

    own_session = session is None
    client = session or build_http_session()
    try:
        url = build_zones_url()
        response = client.get(
            url,
            params={"$limit": limit},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"Expected non-empty JSON list from {url}")
        return payload
    finally:
        if own_session:
            client.close()


def save_raw_trips_csv(csv_text: str, output_path: Path) -> Path:
    """Persist raw trips CSV text to disk using UTF-8 encoding."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(csv_text, encoding="utf-8", newline="")
    return output_path


def save_raw_zones_json(zones_data: list[dict], output_path: Path) -> Path:
    """Persist raw taxi zones JSON payload to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(zones_data, indent=2), encoding="utf-8")
    return output_path


def load_fixture_data(
    trips_path: Path = SAMPLE_TRIPS_PATH,
    zones_path: Path = SAMPLE_ZONES_PATH,
) -> tuple[str, list[dict]]:
    """Load deterministic local sample fixtures for CI testing without external API calls."""
    trips_csv_text = trips_path.read_text(encoding="utf-8")
    zones_data = json.loads(zones_path.read_text(encoding="utf-8"))
    if not isinstance(zones_data, list):
        raise ValueError(f"Expected JSON array in {zones_path}")
    return trips_csv_text, zones_data

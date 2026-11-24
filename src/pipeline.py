"""Orchestration entrypoint for NYC Yellow Taxi & Taxi Zone ingestion, transform, validation, and export."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.config import (
    DEFAULT_BATCH_LIMIT,
    DEFAULT_BATCH_OFFSET,
    DEFAULT_TAXI_DATASET_ID,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_ZONES_LIMIT,
    ENRICHED_TRIP_COLUMNS,
    PROJECT_ROOT,
    ZONE_SUMMARY_COLUMNS,
    ZONES_LOOKUP_COLUMNS,
)
from src.ingest import (
    fetch_taxi_trips_csv,
    fetch_taxi_zones_json,
    load_fixture_data,
    save_raw_trips_csv,
    save_raw_zones_json,
)
from src.transform import (
    aggregate_zone_summary,
    build_zones_lookup,
    transform_trips,
    write_csv,
)
from src.validate import (
    validate_enriched_trips,
    validate_zone_summary,
    validate_zones_lookup,
)


def run_pipeline(
    mode: str = "fixture",
    dataset_id: str = DEFAULT_TAXI_DATASET_ID,
    limit: int = DEFAULT_BATCH_LIMIT,
    offset: int = DEFAULT_BATCH_OFFSET,
    zones_limit: int = DEFAULT_ZONES_LIMIT,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    output_dir: Path | None = None,
    upload_azure: bool = False,
) -> dict[str, Any]:
    """Execute the end-to-end NYC Yellow Taxi ingestion, spatial enrichment, validation, and output pipeline."""
    now_utc = datetime.now(timezone.utc)
    run_id = now_utc.strftime("%Y%m%dT%H%M%SZ")
    partition_path = f"year={now_utc:%Y}/month={now_utc:%m}/day={now_utc:%d}/run={run_id}"

    base_out = output_dir or (PROJECT_ROOT / "data")
    raw_dir = base_out / "raw"
    processed_dir = base_out / "processed"
    metadata_dir = base_out / "metadata"

    if mode == "fixture":
        trips_csv_text, raw_zones = load_fixture_data()
        effective_limit = 0
        effective_offset = 0
    elif mode == "live":
        trips_csv_text = fetch_taxi_trips_csv(
            dataset_id=dataset_id,
            limit=limit,
            offset=offset,
            timeout=timeout,
        )
        raw_zones = fetch_taxi_zones_json(limit=zones_limit, timeout=timeout)
        effective_limit = limit
        effective_offset = offset
    else:
        raise ValueError(f"Unsupported pipeline mode '{mode}'. Use 'fixture' or 'live'.")

    raw_trips_path = save_raw_trips_csv(trips_csv_text, raw_dir / "trips_raw.csv")
    raw_zones_path = save_raw_zones_json(raw_zones, raw_dir / "zones_raw.json")

    zones_lookup = build_zones_lookup(raw_zones)
    validate_zones_lookup(zones_lookup)
    zones_lookup_path = write_csv(
        zones_lookup,
        ZONES_LOOKUP_COLUMNS,
        processed_dir / "zones_lookup.csv",
    )

    enriched_trips, trip_stats = transform_trips(trips_csv_text, zones_lookup)
    validate_enriched_trips(enriched_trips)
    enriched_trips_path = write_csv(
        enriched_trips,
        ENRICHED_TRIP_COLUMNS,
        processed_dir / "trips_enriched.csv",
    )

    zone_summary = aggregate_zone_summary(enriched_trips)
    validate_zone_summary(zone_summary, expected_total_trips=len(enriched_trips))
    zone_summary_path = write_csv(
        zone_summary,
        ZONE_SUMMARY_COLUMNS,
        processed_dir / "zone_summary.csv",
    )

    metadata: dict[str, Any] = {
        "run_id": run_id,
        "run_timestamp_utc": now_utc.isoformat(),
        "partition_path": partition_path,
        "mode": mode,
        "dataset_id": dataset_id if mode == "live" else "fixture",
        "batch_limit": effective_limit,
        "batch_offset": effective_offset,
        "raw_trips_count": trip_stats["raw_trips_count"],
        "valid_trips_count": trip_stats["valid_trips_count"],
        "dropped_invalid_trips_count": trip_stats["dropped_invalid_trips_count"],
        "drop_reasons": trip_stats["drop_reasons"],
        "raw_zones_count": len(raw_zones),
        "unique_zones_count": len(zones_lookup),
        "summary_zones_count": len(zone_summary),
        "top_5_pickup_zones": [
            {
                "pulocationid": z["pulocationid"],
                "pu_zone": z["pu_zone"],
                "pu_borough": z["pu_borough"],
                "trip_count": z["trip_count"],
                "total_revenue": z["total_revenue"],
            }
            for z in zone_summary[:5]
        ],
        "outputs": {
            "raw_trips_csv": str(raw_trips_path),
            "raw_zones_json": str(raw_zones_path),
            "zones_lookup_csv": str(zones_lookup_path),
            "trips_enriched_csv": str(enriched_trips_path),
            "zone_summary_csv": str(zone_summary_path),
        },
    }

    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = metadata_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    metadata["outputs"]["run_metadata_json"] = str(metadata_path)

    if upload_azure:
        from src.upload_blob import upload_pipeline_outputs

        uploaded_blobs = upload_pipeline_outputs(
            artifact_dir=base_out,
            partition_path=partition_path,
        )
        metadata["uploaded_blobs"] = uploaded_blobs
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return metadata


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint supporting `fixture` and `live` execution modes."""
    parser = argparse.ArgumentParser(description="NYC Yellow Taxi & Zone CI/CD Ingestion Pipeline")
    parser.add_argument(
        "mode",
        choices=["fixture", "live"],
        default="fixture",
        nargs="?",
        help="Pipeline execution mode: 'fixture' for local/CI sample data, 'live' for NYC Open Data APIs.",
    )
    parser.add_argument("--dataset-id", default=DEFAULT_TAXI_DATASET_ID, help="Socrata Taxi dataset ID (4b4i-vvec or rwwi-khbc)")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_LIMIT, help="Taxi trip rows per batch ($limit)")
    parser.add_argument("--offset", type=int, default=DEFAULT_BATCH_OFFSET, help="Taxi trip pagination offset ($offset)")
    parser.add_argument("--zones-limit", type=int, default=DEFAULT_ZONES_LIMIT, help="Taxi zone polygons limit ($limit)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="HTTP request timeout in seconds")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output base directory (default: data/)")
    parser.add_argument(
        "--upload-azure",
        action="store_true",
        help="Upload pipeline outputs to Azure Blob Storage after validation.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    summary = run_pipeline(
        mode=args.mode,
        dataset_id=args.dataset_id,
        limit=args.limit,
        offset=args.offset,
        zones_limit=args.zones_limit,
        timeout=args.timeout,
        output_dir=args.output_dir,
        upload_azure=args.upload_azure,
    )

    print(
        f"[NYC-Taxi-Pipeline] mode={summary['mode']} run_id={summary['run_id']} "
        f"raw_trips={summary['raw_trips_count']} valid_trips={summary['valid_trips_count']} "
        f"dropped={summary['dropped_invalid_trips_count']} zones={summary['unique_zones_count']}"
    )
    print("Top 5 pickup zones by total revenue:")
    for item in summary["top_5_pickup_zones"]:
        print(
            f" - {item['pu_zone']} ({item['pu_borough']}, ID {item['pulocationid']}): "
            f"{item['trip_count']} trips, ${item['total_revenue']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Integration tests for the end-to-end fixture pipeline execution."""

import csv
import json
from pathlib import Path

from src.pipeline import run_pipeline


def test_fixture_pipeline_end_to_end(tmp_path: Path) -> None:
    summary = run_pipeline(mode="fixture", output_dir=tmp_path)

    assert summary["mode"] == "fixture"
    assert summary["raw_trips_count"] == 15
    assert summary["valid_trips_count"] == 12
    assert summary["dropped_invalid_trips_count"] == 3
    assert summary["raw_zones_count"] == 11
    assert summary["unique_zones_count"] == 10

    expected_files = [
        tmp_path / "raw" / "trips_raw.csv",
        tmp_path / "raw" / "zones_raw.json",
        tmp_path / "processed" / "zones_lookup.csv",
        tmp_path / "processed" / "trips_enriched.csv",
        tmp_path / "processed" / "zone_summary.csv",
        tmp_path / "metadata" / "run_metadata.json",
    ]
    for file_path in expected_files:
        assert file_path.exists(), f"Missing pipeline artifact: {file_path}"

    with (tmp_path / "processed" / "trips_enriched.csv").open("r", encoding="utf-8") as f:
        enriched_rows = list(csv.DictReader(f))
    assert len(enriched_rows) == 12

    with (tmp_path / "processed" / "zone_summary.csv").open("r", encoding="utf-8") as f:
        summary_rows = list(csv.DictReader(f))
    assert sum(int(row["trip_count"]) for row in summary_rows) == 12

    written_metadata = json.loads((tmp_path / "metadata" / "run_metadata.json").read_text(encoding="utf-8"))
    assert written_metadata["run_id"] == summary["run_id"]
    assert written_metadata["partition_path"].startswith("year=")
    assert len(written_metadata["top_5_pickup_zones"]) == 5

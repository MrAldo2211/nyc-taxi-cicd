"""Azure Blob Storage upload and post-upload verification helpers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


CONTENT_TYPES = {
    ".csv": "text/csv",
    ".json": "application/json",
}


def build_blob_service_client(
    storage_account: str | None = None,
    connection_string: str | None = None,
) -> BlobServiceClient:
    """Authenticate to Azure Blob Storage via connection string or DefaultAzureCredential (OIDC / CLI)."""
    conn_str = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)

    account_name = storage_account or os.getenv("AZURE_STORAGE_ACCOUNT")
    if not account_name:
        raise ValueError(
            "AZURE_STORAGE_ACCOUNT environment variable (or AZURE_STORAGE_CONNECTION_STRING) is required."
        )

    account_url = f"https://{account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def build_upload_manifest(artifact_dir: Path, partition_path: str) -> list[tuple[Path, str]]:
    """Map local pipeline artifacts to partitioned and latest Azure Blob paths."""
    mappings = [
        (artifact_dir / "raw" / "trips_raw.csv", f"raw/trips/{partition_path}/trips_raw.csv"),
        (artifact_dir / "raw" / "zones_raw.json", f"raw/zones/{partition_path}/zones_raw.json"),
        (
            artifact_dir / "processed" / "zones_lookup.csv",
            f"processed/zones_lookup/{partition_path}/zones_lookup.csv",
        ),
        (
            artifact_dir / "processed" / "trips_enriched.csv",
            f"processed/trips_enriched/{partition_path}/trips_enriched.csv",
        ),
        (
            artifact_dir / "processed" / "zone_summary.csv",
            f"processed/zone_summary/{partition_path}/zone_summary.csv",
        ),
        (
            artifact_dir / "metadata" / "run_metadata.json",
            f"metadata/{partition_path}/run_metadata.json",
        ),
        (artifact_dir / "processed" / "zones_lookup.csv", "latest/zones_lookup.csv"),
        (artifact_dir / "processed" / "trips_enriched.csv", "latest/trips_enriched.csv"),
        (artifact_dir / "processed" / "zone_summary.csv", "latest/zone_summary.csv"),
        (artifact_dir / "metadata" / "run_metadata.json", "latest/run_metadata.json"),
    ]
    missing = [str(local_path) for local_path, _ in mappings if not local_path.exists()]
    if missing:
        raise FileNotFoundError(f"Expected pipeline output files are missing: {missing}")
    return mappings


def upload_pipeline_outputs(
    artifact_dir: Path,
    container_name: str | None = None,
    storage_account: str | None = None,
    connection_string: str | None = None,
    partition_path: str | None = None,
) -> list[str]:
    """Upload raw, processed, metadata, and latest blobs to Azure Blob Storage and verify existence."""
    target_container = container_name or os.getenv("AZURE_STORAGE_CONTAINER")
    if not target_container:
        raise ValueError("AZURE_STORAGE_CONTAINER environment variable is required.")

    metadata_file = artifact_dir / "metadata" / "run_metadata.json"
    if not partition_path:
        if not metadata_file.exists():
            raise FileNotFoundError(f"Cannot infer partition_path without {metadata_file}")
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        partition_path = metadata["partition_path"]

    manifest = build_upload_manifest(artifact_dir, partition_path=partition_path)
    service_client = build_blob_service_client(
        storage_account=storage_account,
        connection_string=connection_string,
    )
    container_client = service_client.get_container_client(target_container)

    uploaded_blobs: list[str] = []
    for local_path, blob_name in manifest:
        blob_client = container_client.get_blob_client(blob_name)
        content_type = CONTENT_TYPES.get(local_path.suffix.lower(), "application/octet-stream")
        with local_path.open("rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
        if not blob_client.exists():
            raise RuntimeError(f"Upload verification failed: blob '{blob_name}' does not exist.")
        uploaded_blobs.append(blob_name)

    return uploaded_blobs


def main(argv: Iterable[str] | None = None) -> int:
    """CLI entrypoint for uploading generated pipeline artifacts to Azure Blob Storage."""
    parser = argparse.ArgumentParser(description="Upload NYC Taxi pipeline outputs to Azure Blob Storage.")
    parser.add_argument("--artifact-dir", type=Path, required=True, help="Directory with raw/, processed/, metadata/")
    parser.add_argument("--storage-account", default=None, help="Azure Storage Account name")
    parser.add_argument("--container", default=None, help="Azure Blob container name")
    args = parser.parse_args(list(argv) if argv is not None else None)

    uploaded = upload_pipeline_outputs(
        artifact_dir=args.artifact_dir,
        container_name=args.container,
        storage_account=args.storage_account,
    )
    print(f"Uploaded and verified {len(uploaded)} blobs:")
    for name in uploaded:
        print(f" - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

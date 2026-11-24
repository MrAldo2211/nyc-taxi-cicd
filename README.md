# NYC Yellow Taxi & Zone CI/CD Ingestion Pipeline

Automated cloud data engineering pipeline in Python that ingests NYC Yellow Taxi Trip records and NYC Taxi Zone GeoJSON polygons, validates data contracts, enriches trips with spatial zone metadata and derived KPIs, aggregates revenue per pickup zone, and deploys results to Azure Blob Storage on a **6-hour schedule** via GitHub Actions (`*.yaml`) and OIDC.

## Architecture Overview

```text
GitHub Actions (cron: "0 */6 * * *" / workflow_dispatch / PR)
   │
   ├─► [Job 1: CI] pytest (unit + integration) + fixture pipeline validation
   │
   └─► [Job 2: CD] Live Ingestion (Python)
          ├── Trips API: https://data.cityofnewyork.us/resource/4b4i-vvec.csv ($limit=25000, $offset=...)
          │   (2024 alt: rwwi-khbc)
          ├── Zones API: https://data.cityofnewyork.us/resource/8meu-9t5y.json ($limit=300)
          ├── Clean, deduplicate zones, compute centroids, enrich & aggregate
          ├── Validate data contracts (DataContractError on schema/value violation)
          └── Azure Login (OIDC) ──► Upload & verify in Azure Blob Storage
```

## Datasets Used

1. **NYC Yellow Taxi Trip Data (CSV)**:
   `https://data.cityofnewyork.us/resource/4b4i-vvec.csv?$limit=25000&$offset=0`
   *(Alternative 2024 dataset ID: `rwwi-khbc`)*
2. **NYC Taxi Zones + Map Polygons (JSON)**:
   `https://data.cityofnewyork.us/resource/8meu-9t5y.json?$limit=300`

## Project Structure

```text
nyc-taxi-cicd/
├── .github/workflows/
│   └── ci-cd-pipeline.yaml     # CI tests + CD ingestion + 6-hour cron scheduler
├── src/
│   ├── config.py               # API URLs, schemas, thresholds, and NYC bounds
│   ├── ingest.py               # HTTP ingestion with retries + fixture loader
│   ├── transform.py            # Zone dedup, centroid math, cleaning, enrichment, summary
│   ├── validate.py             # Data-contract assertions (DataContractError)
│   ├── pipeline.py             # End-to-end CLI orchestrator (fixture | live)
│   └── upload_blob.py          # Python Azure Blob Storage uploader & verifier
├── data/
│   ├── sample/                 # Deterministic offline fixtures for CI tests
│   ├── raw/                    # Runtime raw API dumps (gitignored)
│   └── processed/              # Runtime cleaned & aggregated CSVs (gitignored)
├── tests/
│   ├── unit/                   # Unit tests for transforms and data contracts
│   └── integration/            # End-to-end fixture pipeline integration test
├── docs/
│   └── PANDUAN_RUNNING_DAN_SCREENSHOT.md
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

## Quick Local Run

```powershell
# 1. Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# 2. Run automated unit & integration tests
pytest -v

# 3. Run offline deterministic fixture pipeline
python -m src.pipeline fixture --output-dir artifacts/fixture

# 4. Run live API ingestion pipeline (NYC Taxi + Zones)
python -m src.pipeline live --limit 25000 --offset 0 --output-dir artifacts/live

# Alternative 2024 dataset:
python -m src.pipeline live --dataset-id rwwi-khbc --limit 25000 --offset 0 --output-dir artifacts/live
```

## Schedule (Every 6 Hours)

Configured in [ci-cd-pipeline.yaml](.github/workflows/ci-cd-pipeline.yaml):

```yaml
schedule:
  - cron: "0 */6 * * *"
```

Runs automatically at `00:00`, `06:00`, `12:00`, and `18:00` UTC (`07:00`, `13:00`, `19:00`, and `01:00` WIB), advancing `$offset` automatically per run number (`((run_number - 1) * batch_limit) % 5000000`) to ingest fresh taxi trip batches into Azure Blob Storage.

## Azure Blob Storage Output Layout

Each CD run uploads and verifies files in the configured container (`AZURE_STORAGE_CONTAINER`):

- `raw/trips/year=YYYY/month=MM/day=DD/run=<RUN_ID>/trips_raw.csv`
- `raw/zones/year=YYYY/month=MM/day=DD/run=<RUN_ID>/zones_raw.json`
- `processed/zones_lookup/year=YYYY/month=MM/day=DD/run=<RUN_ID>/zones_lookup.csv`
- `processed/trips_enriched/year=YYYY/month=MM/day=DD/run=<RUN_ID>/trips_enriched.csv`
- `processed/zone_summary/year=YYYY/month=MM/day=DD/run=<RUN_ID>/zone_summary.csv`
- `metadata/year=YYYY/month=MM/day=DD/run=<RUN_ID>/run_metadata.json`
- `latest/{zones_lookup.csv, trips_enriched.csv, zone_summary.csv, run_metadata.json}`

See [`docs/PANDUAN_RUNNING_DAN_SCREENSHOT.md`](docs/PANDUAN_RUNNING_DAN_SCREENSHOT.md) for the complete Git, GitHub PR, Azure OIDC setup, and screenshot checklist.

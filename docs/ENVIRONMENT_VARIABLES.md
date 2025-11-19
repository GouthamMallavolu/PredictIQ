# Environment Variables Reference

This document lists all environment variables used across the FinSightAI project and their consistent naming conventions.

## GitHub Secrets

The following secrets should be configured in GitHub (Settings → Secrets and variables → Actions):

### Azure Storage
- **`AZURE_STORAGE_CONNECTION_STRING`** - Azure Storage Account connection string
- **`AZURE_STORAGE_CONTAINER`** - Blob container name (e.g., `snapshots` or `data`)
- **`AZURE_STORAGE_BLOB_NAME`** - (Optional) Blob name, defaults to `Merged_dataset.csv`

### Azure Container Registry (ACR)
- **`ACR_LOGIN_SERVER`** - ACR login server (e.g., `finsightairegistry.azurecr.io`)
- **`ACR_USERNAME`** - ACR username
- **`ACR_PASSWORD`** - ACR password

### Kafka/Event Hubs
- **`KAFKA_BROKER`** - Kafka broker endpoint (e.g., `finsightai-eventhub.servicebus.windows.net:9093`)
- **`KAFKA_USERNAME`** - Kafka username (usually `$ConnectionString`)
- **`KAFKA_PASSWORD`** - Kafka password (Event Hub connection string)

### Alpha Vantage API
- **`ALPHA_VANTAGE_KEY`** - Alpha Vantage API key

### Other
- **`API_URL`** - API endpoint URL (for probes)
- **`AZURE_CREDENTIALS`** - Azure service principal credentials (JSON)

## Code Compatibility

The codebase supports both naming conventions for backward compatibility:

### Storage Connection String
- `STORAGE_CONNECTION` (legacy) → `AZURE_STORAGE_CONNECTION_STRING` (preferred)
- Code checks both: `os.getenv('STORAGE_CONNECTION') or os.getenv('AZURE_STORAGE_CONNECTION_STRING')`

### Storage Container
- `STORAGE_CONTAINER` (legacy) → `AZURE_STORAGE_CONTAINER` (preferred)
- `AZURE_STORAGE_CONTAINER_NAME` (used by consumer) → `AZURE_STORAGE_CONTAINER` (preferred)
- Code checks all three variants

## Workflow Files

All workflow files now use the consistent naming:
- `.github/workflows/automated-retraining.yml` - Uses `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`
- `.github/workflows/daily-data-fetch.yml` - Uses `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`
- `.github/workflows/deploy-consumer.yml` - Uses `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`
- `.github/workflows/ci-cd.yml` - Uses `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`
- `.github/workflows/automated-probes.yml` - Uses `API_URL`, `KAFKA_BROKER`, `KAFKA_USERNAME`, `KAFKA_PASSWORD`

## Python Scripts

All Python scripts support both naming conventions:
- `pipeline/train/trainers.py` - Checks both `STORAGE_CONNECTION`/`AZURE_STORAGE_CONNECTION_STRING` and `STORAGE_CONTAINER`/`AZURE_STORAGE_CONTAINER`
- `scripts/daily_data_fetch.py` - Checks both naming conventions
- `scripts/backfill_blob_data.py` - Checks both naming conventions
- `kafka_pipeline/config.py` - Checks `STORAGE_CONNECTION`/`AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER`/`AZURE_STORAGE_CONTAINER_NAME`

## Migration Guide

If you're using the legacy names (`STORAGE_CONNECTION`, `STORAGE_CONTAINER`), you can:
1. Keep using them - the code still supports them
2. Migrate to the new names - update your GitHub secrets to use `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER`

The new names are preferred and will be used consistently across all workflows.


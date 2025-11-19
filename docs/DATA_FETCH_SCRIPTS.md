# Data Fetch Scripts Documentation

This document explains how to use the data fetching scripts for Azure Blob Storage.

## Scripts Overview

1. **`scripts/backfill_blob_data.py`** - Backfills historical data for a date range
2. **`scripts/daily_data_fetch.py`** - Fetches yesterday's data (for daily cron job)
3. **`.github/workflows/daily-data-fetch.yml`** - GitHub Actions workflow for automated daily fetching

---

## 1. Backfill Script

### Purpose
Fetches historical stock data from Alpha Vantage API and uploads to Azure Blob Storage for dates Oct 31 - Nov 17, 2025.

### Usage

```bash
# Backfill default range (Oct 31 - Nov 17)
python scripts/backfill_blob_data.py

# Backfill custom date range
python scripts/backfill_blob_data.py --start-date 2025-10-31 --end-date 2025-11-17
```

### Environment Variables Required

```bash
ALPHA_VANTAGE_KEY=your_api_key
STORAGE_CONNECTION=your_azure_storage_connection_string
STORAGE_CONTAINER=data  # Optional, defaults to 'data'
```

### Features

- Fetches data for all symbols in `SYMBOLS` config
- Skips weekends (Saturday/Sunday)
- Rate limiting: 12 seconds between API calls
- Uploads data in format: `v1/date=YYYY-MM-DD/hour=HH/training_data.parquet`
- Handles API rate limits gracefully

### Important Notes

⚠️ **Alpha Vantage Free Tier Limitations:**
- 25 API calls per day
- 5 calls per minute
- The script will warn if you hit the limit

**Recommendation:** For production, use a premium API key or split the backfill across multiple days.

---

## 2. Daily Data Fetch Script

### Purpose
Fetches yesterday's stock data from Alpha Vantage API (which returns the entire day's data) and uploads it to Azure Blob Storage hour-by-hour to simulate real-time streaming. Designed to run as a daily cron job.

### Usage

```bash
# Default: Upload hour by hour with 60 second delays (simulating real-time)
python scripts/daily_data_fetch.py

# Upload all hours immediately (no delays)
python scripts/daily_data_fetch.py --no-simulate-realtime

# Custom delay between hours (in seconds)
python scripts/daily_data_fetch.py --hour-delay 30
```

### Environment Variables Required

```bash
ALPHA_VANTAGE_KEY=your_api_key
STORAGE_CONNECTION=your_azure_storage_connection_string
STORAGE_CONTAINER=data  # Optional, defaults to 'data'
```

### Features

- **Fetches complete yesterday's data** from Alpha Vantage API (one call gets entire day)
- **Simulates real-time streaming** by uploading hour-by-hour with configurable delays
- Automatically fetches yesterday's date
- Skips weekends automatically
- Rate limiting: 12 seconds between API calls for different symbols
- Logs to `logs/daily_data_fetch.log`
- Uploads data in format: `v1/date=YYYY-MM-DD/hour=HH/training_data.parquet`

### How It Works

1. **Fetches all data at once**: Makes API calls to Alpha Vantage for all symbols, getting the complete day's data
2. **Processes by hour**: Groups the data by hour (0-23)
3. **Uploads hour-by-hour**: Uploads each hour's data separately to blob storage
4. **Simulates real-time**: Waits between each hour upload (default: 60 seconds) to simulate data arriving hourly throughout the day

This approach simulates a real-time data pipeline where data arrives hourly, even though we're using historical data from Alpha Vantage.

---

## 3. GitHub Actions Daily Workflow

### Purpose
Automated daily execution of the data fetch script via GitHub Actions cron.

### Schedule

- **Runs daily at 2 AM UTC** (after US market close previous day)
- Can be manually triggered via `workflow_dispatch`

### Setup

1. **Add GitHub Secrets:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Add:
     - `ALPHA_VANTAGE_KEY` - Your Alpha Vantage API key
     - `STORAGE_CONNECTION` - Azure Storage connection string
     - `STORAGE_CONTAINER` - Container name (optional, defaults to 'data')

2. **Workflow will:**
   - Checkout code
   - Set up Python 3.10
   - Install dependencies
   - Run `scripts/daily_data_fetch.py`
   - Upload logs as artifacts

### Viewing Logs

- Go to: `Actions` → `Daily Data Fetch` → Select a run
- Download `daily-data-fetch-logs` artifact to view logs

---

## Data Format

All data is uploaded to Azure Blob Storage in the following structure:

```
v1/
  date=2025-11-17/
    hour=09/
      training_data.parquet
    hour=10/
      training_data.parquet
    ...
```

### Parquet File Schema

Each `training_data.parquet` file contains:
- `time`: Timestamp (datetime)
- `open`: Opening price (float)
- `high`: High price (float)
- `low`: Low price (float)
- `close`: Closing price (float)
- `volume`: Trading volume (int)
- `symbol`: Stock symbol (string)

---

## Running the Backfill

### Step 1: Set Environment Variables

Create/update your `.env` file:

```bash
ALPHA_VANTAGE_KEY=your_key_here
STORAGE_CONNECTION=your_connection_string_here
STORAGE_CONTAINER=data
```

### Step 2: Run Backfill Script

```bash
# This will fetch data from Oct 31 to Nov 17
python scripts/backfill_blob_data.py
```

**Note:** Due to API rate limits (25 calls/day), you may need to run this multiple times over several days, or use a premium API key.

### Step 3: Verify Data Uploaded

Use the `scripts/check_blob_storage.py` script to verify:

```bash
python scripts/check_blob_storage.py
```

---

## Troubleshooting

### Rate Limit Errors

If you see rate limit errors:
- Wait 24 hours before running again (free tier limit)
- Or upgrade to Alpha Vantage premium API
- Or split the date range across multiple runs

### Missing Data

- Check Alpha Vantage API status
- Verify API key is valid
- Check logs for specific errors
- Ensure date is not a weekend (script skips weekends)

### Blob Storage Errors

- Verify `STORAGE_CONNECTION` is correct
- Check container name matches
- Ensure Azure Storage account has write permissions

---

## Next Steps

After backfilling data:

1. **Verify data exists** in blob storage
2. **Test retraining script** to ensure it can download data:
   ```bash
   python scripts/retrain_models.py --auto-version
   ```
3. **Monitor daily workflow** to ensure it runs successfully
4. **Set up alerts** if daily fetch fails (optional)

---

## Related Files

- `scripts/backfill_blob_data.py` - Backfill script
- `scripts/daily_data_fetch.py` - Daily fetch script
- `.github/workflows/daily-data-fetch.yml` - GitHub Actions workflow
- `pipeline/train/trainers.py` - Data loading for training (uses blob storage)
- `scripts/check_blob_storage.py` - Utility to list blob storage contents


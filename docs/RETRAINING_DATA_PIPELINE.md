# Retraining Data Pipeline

This document describes how the automated retraining process loads, cleans, and processes data from Azure Blob Storage.

## Overview

The retraining pipeline performs the following steps:
1. **Load Data** from Azure Blob Storage (or local fallback)
2. **Data Cleaning** - Remove invalid records, handle missing values
3. **Feature Engineering** - Calculate technical indicators
4. **Train/Test Split** - Split data by time (80/20)
5. **Model Training** - Train LSTM, Random Forest, and Moving Average models

## Data Loading

### Blob Storage Structure

The retraining script searches for data in the following locations (in order):
1. Explicit blob name from `AZURE_STORAGE_BLOB_NAME` environment variable
2. `Merged_dataset.csv` at container root
3. `v1/Merged_dataset.csv` (in v1 folder)
4. `data/Merged_dataset.csv` (in data folder)

### Automatic CSV Merging

If `Merged_dataset.csv` is not found, the script will:
- Search for all CSV files in the container
- Load and merge up to 100 CSV files
- Combine them into a single DataFrame

This handles cases where data is stored in date-based folders (e.g., `v1/date=2022-03-01/data.csv`).

### Required Columns

The data must contain at minimum:
- `time` - Timestamp
- `symbol` - Stock symbol
- `open`, `high`, `low`, `close` - Price data
- `volume` - Trading volume

## Data Cleaning

The following cleaning steps are applied:

### 1. Data Validation
- Remove rows with invalid prices (negative or zero)
- Ensure `high >= low` and `high >= close >= low`
- Handle missing volume (fill with 0)

### 2. Time Handling
- Convert `time` column to datetime
- Sort data by time

### 3. Missing Value Handling
- Fill missing sentiment with 0.0
- Fill missing news_count with 0
- Remove rows with NaN in feature columns or target

## Feature Engineering

If features are missing, they are calculated automatically:

### Technical Indicators

1. **Returns**
   - `return` - Percentage change in close price
   - `log_return` - Logarithmic return

2. **Moving Averages**
   - `ema_10` - 10-period Exponential Moving Average
   - `ema_50` - 50-period Exponential Moving Average

3. **RSI (Relative Strength Index)**
   - `rsi` - 14-period RSI (0-100 scale)

4. **MACD (Moving Average Convergence Divergence)**
   - `macd` - Difference between 12-period and 26-period EMA

5. **Bollinger Bands**
   - `bb_high` - Upper Bollinger Band (20-period, 2 std dev)
   - `bb_low` - Lower Bollinger Band (20-period, 2 std dev)

6. **ATR (Average True Range)**
   - `atr` - 14-period ATR for volatility measurement

### Target Variable

- `close_next` - Next hour's close price (shifted by -1)
- `target` - Same as `close_next` (used for training)

### Feature Columns Used for Training

```
['open', 'high', 'low', 'close', 'volume',
 'sentiment_mean', 'news_count', 'return', 'log_return',
 'ema_10', 'ema_50', 'rsi', 'macd', 'bb_high', 'bb_low', 'atr']
```

## Per-Symbol Processing

Technical indicators are calculated **per symbol** to ensure:
- Each stock's indicators are independent
- No data leakage between different stocks
- Proper handling of multi-stock datasets

## Environment Variables

Required for blob storage access:
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Storage connection string
- `AZURE_STORAGE_CONTAINER` - Container name (e.g., `snapshots`)
- `AZURE_STORAGE_BLOB_NAME` - (Optional) Specific blob name

## Checking Blob Structure

To inspect your blob storage structure, run:

```bash
python scripts/check_blob_structure.py
```

This will list all CSV files and folders in your container, helping you understand the data organization.

## Example Workflow

```
[1/4] Training models...
  [Step 1/5] Loading training data...
  🔍 Trying to load: snapshots/Merged_dataset.csv
  ✅ Loaded 50000 records from Azure Blob Storage: Merged_dataset.csv
  ✓ Loaded 50000 raw records
  
  [Step 2/5] Data cleaning and feature engineering...
  🔧 Preparing features with data cleaning and feature engineering...
     Calculating technical indicators per symbol...
     Removed 1200 rows with missing values
  ✅ Features prepared: 48800 records with 17 features
  
  [Step 3/5] Splitting data into train/test sets...
  📊 Splitting data: 80% train, 20% test
     Training: 39040 records
     Testing: 9760 records
  
  [Step 4/5] Training LSTM model...
  [Step 5/5] Training Random Forest model...
```

## Troubleshooting

### Data Not Found
- Check that `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER` are set
- Verify the blob exists in the expected location
- Use `check_blob_structure.py` to inspect your container

### Missing Features
- The script will automatically calculate missing technical indicators
- Ensure required columns (`time`, `symbol`, `open`, `high`, `low`, `close`, `volume`) are present

### Memory Issues
- If merging many CSV files, the script limits to 100 files
- Consider consolidating data into a single `Merged_dataset.csv` file


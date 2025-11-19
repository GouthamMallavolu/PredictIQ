# Push Dockerfile Fix to GitHub

## Problem

GitHub Actions is using an **old Dockerfile** that tries to copy files that don't exist:
- `multi_stock_model_LSTM.keras` (gitignored)
- `scaler.pkl` (gitignored)
- `random_forest_model.pkl` (gitignored)
- `frontend/build/` (doesn't exist)

## Solution

The Dockerfile is **already fixed locally**. You just need to **push it to GitHub**.

## Steps to Fix

### Option 1: Push via Command Line (if you have access)

```bash
git push origin development
```

### Option 2: Push via GitHub Desktop

1. Open GitHub Desktop
2. You should see commits ready to push
3. Click **"Push origin"** button

### Option 3: Manual Upload (if push fails)

1. Go to: `https://github.com/GouthamMallavolu/PredictIQ`
2. Navigate to: `Dockerfile` (root directory)
3. Click **"Edit"** (pencil icon)
4. Replace entire contents with the fixed version (see below)
5. Click **"Commit changes"**

## Fixed Dockerfile Content

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (copy this first for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code first (changes more frequently, smaller files)
COPY api/ ./api/
COPY models/ ./models/
COPY scripts/ ./scripts/
COPY kafka_pipeline/config.py ./kafka_pipeline/
COPY kafka_pipeline/schemas.py ./kafka_pipeline/

# Model files are NOT copied here - they are loaded from Azure Blob Storage at runtime
# This keeps the Docker image small and allows model updates without rebuilding
# Models are loaded by api/predictor.py from blob storage

# Frontend build not included (doesn't exist)
# Models loaded from blob storage at runtime

# Expose port
EXPOSE 8000

# Run API (Container Apps manages health checks)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Verify After Push

1. Go to: `https://github.com/GouthamMallavolu/PredictIQ/blob/development/Dockerfile`
2. Verify it matches the fixed version above
3. Re-run the workflow in GitHub Actions
4. Build should now succeed!

## What Changed

**Removed:**
- `COPY multi_stock_model_LSTM.keras ./`
- `COPY scaler.pkl ./`
- `COPY random_forest_model.pkl ./`
- `COPY frontend/build/ ./frontend/build/`

**Kept:**
- All valid COPY commands for files that exist
- Comments explaining why models aren't copied

## After Pushing

Once pushed, the workflow will:
- ✅ Build Docker image successfully
- ✅ Skip Azure steps (if credentials not set)
- ✅ Complete successfully


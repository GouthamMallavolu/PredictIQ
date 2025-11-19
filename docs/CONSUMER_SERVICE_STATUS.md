# Kafka Consumer Service Status

## Current Situation

### ✅ What Exists:
1. **Consumer Code**: `kafka_pipeline/consumer.py` - Fully functional Kafka consumer
2. **Consumer Logic**: 
   - Listens to `team05.watch` topic
   - Processes incoming stock data
   - Updates data buffers
   - Makes predictions
   - Performs online evaluation

### ❌ What's Missing:
**The consumer is NOT running as a service** - it only runs when executed manually.

## How the Consumer Works

The consumer has a `consume_and_validate()` method that:
- Uses `for message in self.consumer:` - **This is a continuous blocking loop**
- Processes each message:
  1. Validates schema (`StockWatchEvent`)
  2. Updates data buffer for the symbol
  3. Engineers features
  4. Makes predictions (LSTM, RF, MA)
  5. Performs online evaluation
- Runs until interrupted or error

## Current Flow

```
Daily Data Fetch (Cron) → Sends to Kafka → ❌ No Consumer Running
                                    ↓
                            Messages accumulate in Kafka
                            (Not being processed)
```

## What Needs to Happen

### Option 1: Run Consumer as Separate Service (Recommended)

1. **Deploy consumer service** using `Dockerfile.consumer`
2. **Run continuously** as a background service/container
3. **Processes messages** as they arrive from daily data fetch

**Flow:**
```
Daily Data Fetch (Cron) → Sends to Kafka → Consumer Service (Running) → Processes & Predicts
```

### Option 2: Integrate into API

Run consumer in a background thread when API starts (less recommended - couples services).

## Files Created

1. **`scripts/run_consumer_service.py`** - Service wrapper for consumer
   - Handles graceful shutdown
   - Logs to `logs/consumer_service.log`
   - Runs consumer continuously

2. **`Dockerfile.consumer`** - Docker image for consumer service
   - Based on Python 3.10-slim
   - Runs `run_consumer_service.py`
   - Health check included

## How to Run Consumer Service

### Local Development:
```bash
# Set environment variables
export KAFKA_BROKER=your_broker
export KAFKA_USERNAME=$ConnectionString
export KAFKA_PASSWORD=your_password
export STORAGE_CONNECTION=your_connection_string
export STORAGE_CONTAINER=snapshots

# Run consumer service
python scripts/run_consumer_service.py
```

### Docker:
```bash
docker build -f Dockerfile.consumer -t finsightai-consumer .
docker run -d \
  -e KAFKA_BROKER=your_broker \
  -e KAFKA_USERNAME=$ConnectionString \
  -e KAFKA_PASSWORD=your_password \
  -e STORAGE_CONNECTION=your_connection_string \
  -e STORAGE_CONTAINER=snapshots \
  --name finsightai-consumer \
  finsightai-consumer
```

### Azure Container Apps:
Deploy as a separate container app that runs continuously.

## Verification

To check if consumer is processing messages:

1. **Check logs**: `logs/consumer_service.log`
2. **Check Kafka offsets**: Consumer should be committing offsets
3. **Check data buffers**: Should see data being added to buffers
4. **Check predictions**: Should see prediction logs

## Next Steps

1. ✅ Consumer code exists and works
2. ✅ Service wrapper created (`run_consumer_service.py`)
3. ✅ Dockerfile created (`Dockerfile.consumer`)
4. ⏳ **Deploy consumer service** (Azure Container Apps or similar)
5. ⏳ **Monitor consumer** to ensure it's processing messages
6. ⏳ **Verify end-to-end flow**: Daily fetch → Kafka → Consumer → Predictions

## Current End-to-End Flow

```
┌─────────────────┐
│ Daily Data Fetch│ (Cron: 2 AM UTC daily)
│  (GitHub Actions)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Alpha Vantage  │ (Fetches yesterday's data)
│      API        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Process Hourly │ (Hour 09, 10, 11, ...)
└────────┬────────┘
         │
         ├─────────────────┐
         ▼                 ▼
┌─────────────────┐  ┌──────────────┐
│ Azure Blob      │  │   Kafka      │
│   Storage       │  │ team05.watch │
└─────────────────┘  └──────┬───────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Consumer   │ ⚠️ NOT RUNNING
                    │   Service    │ (Needs deployment)
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Process &   │
                    │  Predict     │
                    └──────────────┘
```

## Summary

**Answer to your question**: The consumer code exists and CAN listen continuously, but it's **NOT currently running as a service**. You need to deploy it to process the data being sent by the daily fetch script.


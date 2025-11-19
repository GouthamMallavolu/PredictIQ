# 🚀 FinSightAI Execution Plan

## Three-Phase Deployment Strategy

---

## 📋 **Overview**

| Phase | Purpose | Data Range | Mode |
|-------|---------|------------|------|
| **Phase 1** | Store training baseline | Mar 2022 - Oct 10, 2025 | Batch upload |
| **Phase 2** | Backfill & validate | Oct 11 - Oct 30, 2025 | Batch + Predictions |
| **Phase 3** | Live production | Nov 1+ (yesterday's data) | Real-time streaming |

---

## 🎯 **Phase 1: Store Historical Data (Training Baseline)**

### **Goal:**
Upload `Merged_dataset.csv` (104K records) to Azure Blob Storage as the training baseline.

### **Command:**
```powershell
python scripts/phase1_seed_historical.py
```

### **What It Does:**
- Reads `Merged_dataset.csv`
- Filters to **Oct 10, 2025 and earlier**
- Partitions by date and hour
- Uploads as Parquet files to Azure Blob Storage
- Path: `v1/date=YYYY-MM-DD/hour=HH/training_data.parquet`

### **Expected Output:**
```
PHASE 1: SEEDING HISTORICAL DATA (TRAINING BASELINE)
📊 DATA SUMMARY:
  Total records: 104,345
  Date range: 2022-03-11 to 2025-10-10
  Symbols: ['AAPL', 'MSFT', 'NVDA', 'META', 'TSLA']
  
📦 Creating 2,847 partitioned snapshots...
  Progress: 100/2847 partitions (3.5%)
  Progress: 200/2847 partitions (7.0%)
  ...
  
✅ SUCCESS: Phase 1 Complete!
  Uploaded: 2,847 partitions
  Total records: 104,345
```

### **Verification:**
Check Azure Portal → Storage Account → Containers → `snapshots` → `v1/`
- Should see folders: `date=2022-03-11`, `date=2022-03-12`, ..., `date=2025-10-10`

### **Duration:** ~10-15 minutes (depending on upload speed)

---

## 🧪 **Phase 2: Backfill Oct 11-30 & Validate Predictions**

### **Goal:**
Fetch Oct 11-30 data from Alpha Vantage, run predictions, compare with actual prices, and append to storage.

### **Command:**
```powershell
python scripts/phase2_backfill_oct11_30.py
```

### **What It Does:**
1. **Fetch data** from Alpha Vantage for Oct 11-30, 2025
2. **Merge** stock prices + news sentiment
3. **Run predictions** using trained models (LSTM, RF, MA)
4. **Compare** predictions vs actual prices (validation metrics)
5. **Upload** validated data to Azure Blob Storage
6. Path: `v1/date=YYYY-MM-DD/hour=HH/backfill_oct.parquet`

### **Expected Output:**
```
PHASE 2: BACKFILL OCT 11-30 WITH PREDICTIONS
📅 Backfill period: 2025-10-11 to 2025-10-30
📊 Symbols: ['AAPL', 'MSFT', 'NVDA', 'META', 'TSLA']

📥 Fetching data from Alpha Vantage...
  Fetching AAPL data from 2025-10-11 to 2025-10-30...
    ✅ Fetched 320 records for AAPL
  (waiting 12s for rate limit...)
  Fetching MSFT data...
  ...
  
🔗 Merging stock and news data...
  ✅ Merged 1,600 records

🤖 Running predictions...
  AAPL: Predicted $150.25, Actual $150.50 (Error: 0.17%)
  MSFT: Predicted $420.10, Actual $419.85 (Error: 0.06%)
  ...
  
📊 VALIDATION METRICS:
  MAE: $1.23
  RMSE: $1.85
  MAPE: 0.82%
  
📤 Uploading to Azure Blob Storage...
  ✅ Uploaded 480 partitions

PHASE 2 COMPLETE - Ready for Phase 3 (Live Streaming)
```

### **Why This Phase is Critical:**
- **Validates model accuracy** on unseen data (Oct 11-30)
- **Tests end-to-end pipeline** before going live
- **Provides confidence metrics** for production deployment
- **Fills data gap** between training (Oct 10) and live (Nov 1+)

### **Duration:** ~30-45 minutes (Alpha Vantage rate limits: 5 calls/min)

---

## 🔴 **Phase 3: Live Streaming (Production Mode)**

### **Goal:**
Stream yesterday's data hour by hour, simulating real-time production.

### **Two Modes:**

#### **A. Test Mode (Run Once):**
```powershell
python scripts/phase3_live_streaming.py --once
```
- Streams yesterday's data for the current hour only
- Good for testing before going live

#### **B. Continuous Mode (Production):**
```powershell
python scripts/phase3_live_streaming.py
```
- Runs continuously
- Every hour at :00, streams yesterday's data for that hour
- Example: At 10:00 AM today, streams yesterday's 10:00 AM data

### **What It Does:**
1. **Waits** until the top of the hour
2. **Fetches** yesterday's data for that hour from Alpha Vantage
3. **Streams** to Kafka (`team05.watch` topic)
4. **Consumer** processes, makes predictions, stores in Azure
5. **Repeats** every hour

### **Expected Output (Continuous Mode):**
```
PHASE 3: LIVE STREAMING MODE
📡 Streaming yesterday's data, hour by hour
⏰ Will stream every hour at the top of the hour
Press Ctrl+C to stop

🕐 Current time: 2025-11-02 10:00:15
📤 Streaming yesterday's hour 10:00 data...
📥 Fetching data for 2025-11-01 hour 10:00...
  ✅ AAPL: 1 records
  ✅ MSFT: 1 records
  ✅ NVDA: 1 records
  ✅ META: 1 records
  ✅ TSLA: 1 records
✅ Sent 5 events to team05.watch

⏳ Waiting 59.8 minutes until next hour (11:00)
```

### **Consumer Output (Running in Parallel):**
```
SUCCESS: Consumer connected
SUCCESS: Prediction models loaded
SUCCESS: Loaded 1,680 historical records into buffer

PROCESSED: 5 messages, buffer size: 5
PREDICTION: AAPL: $150.75 (confidence: 0.82)
PREDICTION: MSFT: $420.30 (confidence: 0.79)
SNAPSHOT: Written v1/date=2025-11-01/hour=10/snapshot_000.parquet (5 records)
```

### **Duration:** Runs indefinitely (stop with Ctrl+C)

---

## 🎮 **Complete Execution Sequence**

### **Day 1: Setup & Historical Data**

1. **Update `.env` file** (see below)
2. **Run Phase 1:**
   ```powershell
   python scripts/phase1_seed_historical.py
   ```
3. **Verify in Azure Portal** (check Blob Storage)

### **Day 2: Backfill & Validation**

4. **Run Phase 2:**
   ```powershell
   python scripts/phase2_backfill_oct11_30.py
   ```
5. **Review validation metrics** (MAE, RMSE, MAPE)
6. **Adjust models if needed** (optional)

### **Day 2-3: Live Testing**

7. **Start Consumer** (Terminal 1):
   ```powershell
   python kafka_pipeline/consumer.py
   ```

8. **Test Phase 3 Once** (Terminal 2):
   ```powershell
   python scripts/phase3_live_streaming.py --once
   ```

9. **Check logs** - ensure predictions are working

10. **Start Live Streaming** (Terminal 2):
    ```powershell
    python scripts/phase3_live_streaming.py
    ```

11. **Start API** (Terminal 3):
    ```powershell
    python api/main.py
    ```

12. **Test API:**
    ```powershell
    curl http://localhost:8000/health
    curl -X POST http://localhost:8000/recommend -H "Content-Type: application/json" -d '{"user_id":"test","symbols":["AAPL","MSFT"],"model":"lstm"}'
    ```

---

## 🔧 **Required `.env` Configuration**

```bash
# Alpha Vantage API
ALPHA_VANTAGE_KEY=EL1RT5YTUGFUXF80

# Azure Event Hubs (Kafka)
KAFKA_BROKER=finsightai-eventhub.servicebus.windows.net:9093
KAFKA_USERNAME=$ConnectionString
KAFKA_PASSWORD=Endpoint=sb://finsightai-eventhub.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=YOUR_KEY

# Kafka Topics
TOPIC_WATCH=team05.watch
TOPIC_RATE=team05.rate
TOPIC_PREDICT_REQUESTS=team05.reco_requests
TOPIC_PREDICT_RESPONSES=team05.reco_responses

# Stock Symbols
SYMBOLS=AAPL,MSFT,NVDA,META,TSLA

# Azure Blob Storage
STORAGE_CONNECTION=DefaultEndpointsProtocol=https;AccountName=finsightaiteam05storage;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
STORAGE_CONTAINER=snapshots

# Consumer Group
CONSUMER_GROUP=stock-ingestor
```

---

## 📊 **Data Timeline**

```
Mar 2022 ──────────────────────────────────────────► Oct 10, 2025
                    TRAINING DATA (Phase 1)
                    104,345 records
                    Uploaded to Azure Blob Storage

Oct 11 ──────────► Oct 30, 2025
    VALIDATION DATA (Phase 2)
    ~1,600 records
    Predictions vs Actuals
    Validation metrics

Nov 1 ──────────────────────────────────────────────► Ongoing
              LIVE STREAMING (Phase 3)
              Yesterday's data, hourly
              Real-time predictions
```

---

## ✅ **Success Criteria**

### **Phase 1:**
- ✅ All 104K records uploaded to Azure
- ✅ No upload errors
- ✅ Parquet files readable in Azure Portal

### **Phase 2:**
- ✅ Oct 11-30 data fetched successfully
- ✅ Predictions generated for all symbols
- ✅ Validation metrics calculated (MAE < $2.00, MAPE < 1.5%)
- ✅ Data appended to Azure Blob Storage

### **Phase 3:**
- ✅ Hourly streaming works continuously
- ✅ Consumer processes messages without errors
- ✅ Predictions logged for each symbol
- ✅ API returns predictions successfully
- ✅ Frontend displays real-time data

---

## 🚨 **Troubleshooting**

### **Phase 1 Issues:**

**Error: "STORAGE_CONNECTION not found"**
- Fix: Check `.env` file has `STORAGE_CONNECTION` (not `STORAGE_CONN`)

**Error: "Container creation failed"**
- Fix: Container might already exist (this is OK, script continues)

### **Phase 2 Issues:**

**Error: "Alpha Vantage rate limit exceeded"**
- Fix: Script has built-in 12s delays. If still failing, increase to 15s.

**Error: "No time series data in response"**
- Fix: Alpha Vantage might not have data for that date. Check API response manually.

### **Phase 3 Issues:**

**Error: "Kafka connection timeout"**
- Fix: Check Event Hubs connection string in `.env`

**Error: "No data to stream"**
- Fix: Alpha Vantage might not have yesterday's data yet. Try 2 days ago.

---

## 📈 **Monitoring**

### **Key Metrics to Watch:**

1. **Data Ingestion:**
   - Messages/hour from producer
   - Consumer lag (should be near 0)

2. **Predictions:**
   - Prediction latency (< 100ms)
   - Confidence scores (> 0.7)

3. **Storage:**
   - Blob uploads/hour
   - Storage size growth

4. **API:**
   - Response time (< 200ms)
   - Error rate (< 1%)

---

## 🎯 **Next Steps After Phase 3**

1. **Deploy to Azure Container Apps**
2. **Set up monitoring & alerts**
3. **Implement model retraining pipeline**
4. **Add A/B testing for models**
5. **Build frontend dashboard**
6. **Document for submission**

---

**Ready to start? Begin with Phase 1!** 🚀

```powershell
python scripts/phase1_seed_historical.py
```


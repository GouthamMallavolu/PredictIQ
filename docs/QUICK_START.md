# 🚀 Quick Start Guide

## Your Three-Phase Strategy (Approved!)

---

## 📅 **Timeline & Data Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Store Historical (Training Baseline)                 │
│  ─────────────────────────────────────────────────────────────  │
│  Mar 2022 ──────────────────────────────► Oct 10, 2025         │
│  104,345 records → Azure Blob Storage                           │
│  Command: python scripts/phase1_seed_historical.py              │
│  Duration: ~15 minutes                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Backfill & Validate (Testing Period)                 │
│  ─────────────────────────────────────────────────────────────  │
│  Oct 11 ──────────────────────────────► Oct 30, 2025           │
│  Fetch from Alpha Vantage → Run Predictions → Validate         │
│  Command: python scripts/phase2_backfill_oct11_30.py            │
│  Duration: ~45 minutes (rate limits)                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: Live Streaming (Production Mode)                     │
│  ─────────────────────────────────────────────────────────────  │
│  Nov 1+ (Yesterday's data, streamed hourly)                     │
│  Every hour: Fetch yesterday's hour → Stream → Predict         │
│  Command: python scripts/phase3_live_streaming.py               │
│  Duration: Continuous (runs forever)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ **Execute Now (Step by Step)**

### **Step 1: Update `.env` File**

Replace `KAFKA_SASL_USERNAME` → `KAFKA_USERNAME`  
Replace `KAFKA_SASL_PASSWORD` → `KAFKA_PASSWORD`  
Add `SYMBOLS=AAPL,MSFT,NVDA,META,TSLA`

Your `.env` should look like:
```bash
ALPHA_VANTAGE_KEY=EL1RT5YTUGFUXF80
KAFKA_BROKER=finsightai-eventhub.servicebus.windows.net:9093
KAFKA_USERNAME=$ConnectionString
KAFKA_PASSWORD=Endpoint=sb://...
TOPIC_WATCH=team05.watch
TOPIC_RATE=team05.rate
TOPIC_PREDICT_REQUESTS=team05.reco_requests
TOPIC_PREDICT_RESPONSES=team05.reco_responses
SYMBOLS=AAPL,MSFT,NVDA,META,TSLA
STORAGE_CONNECTION=DefaultEndpointsProtocol=https;...
STORAGE_CONTAINER=snapshots
CONSUMER_GROUP=stock-ingestor
```

---

### **Step 2: Run Phase 1 (Store Historical)**

```powershell
python scripts/phase1_seed_historical.py
```

**Wait for:**
```
✅ SUCCESS: Phase 1 Complete!
  Uploaded: 2,847 partitions
  Total records: 104,345
```

**Verify:** Azure Portal → Storage Account → `snapshots` container → Should see `v1/date=...` folders

---

### **Step 3: Run Phase 2 (Backfill & Validate)**

```powershell
python scripts/phase2_backfill_oct11_30.py
```

**Wait for:**
```
✅ SUCCESS: Phase 2 Complete!
  Validation metrics: MAE=$1.23, MAPE=0.82%
  Uploaded: 480 partitions
```

---

### **Step 4: Test Live Streaming (Once)**

**Terminal 1 - Start Consumer:**
```powershell
python kafka_pipeline/consumer.py
```

**Terminal 2 - Test Streaming:**
```powershell
python scripts/phase3_live_streaming.py --once
```

**Check Terminal 1 for:**
```
PROCESSED: 5 messages
PREDICTION: AAPL: $150.75
SNAPSHOT: Written v1/date=2025-11-01/hour=10/snapshot_000.parquet
```

---

### **Step 5: Go Live! (Continuous Streaming)**

**Keep Terminal 1 running (consumer)**

**Terminal 2 - Start Live Streaming:**
```powershell
python scripts/phase3_live_streaming.py
```

**Terminal 3 - Start API:**
```powershell
python api/main.py
```

**Test API:**
```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# Or open browser: http://localhost:8000/health
```

---

## 🎯 **Why This Strategy is Perfect**

✅ **Clear Separation:**
- Training data (till Oct 10)
- Validation data (Oct 11-30) 
- Live data (Nov 1+)

✅ **Testable:**
- Phase 2 gives you validation metrics
- You can see if predictions are accurate before going live

✅ **Realistic:**
- Simulates production with yesterday's data
- 1-hour intervals match real trading hours

✅ **Gradual:**
- Build confidence at each phase
- Fix issues before moving to next phase

---

## 📊 **Expected Results**

### **Phase 1:**
- 2,847 Parquet files in Azure Blob Storage
- ~500 MB total size (compressed)

### **Phase 2:**
- ~480 additional Parquet files
- Validation metrics: MAE < $2, MAPE < 1.5%
- Confidence that models work on unseen data

### **Phase 3:**
- 5 messages/hour (one per symbol)
- Predictions within 100ms
- Continuous operation

---

## 🚨 **If Something Goes Wrong**

### **Phase 1 fails:**
- Check Azure connection string in `.env`
- Ensure `Merged_dataset.csv` exists in project root

### **Phase 2 takes too long:**
- This is normal! Alpha Vantage rate limit = 5 calls/min
- 10 symbols × 2 calls (stock + news) = 20 calls = 4 minutes per symbol
- Total: ~45 minutes for all symbols

### **Phase 3 no data:**
- Alpha Vantage might not have yesterday's data yet
- Try running at different times of day
- Or modify script to use 2 days ago

---

## 📝 **Files Created**

- `scripts/phase1_seed_historical.py` - Upload training data
- `scripts/phase2_backfill_oct11_30.py` - Backfill Oct 11-30
- `scripts/phase3_live_streaming.py` - Live hourly streaming
- `EXECUTION_PLAN.md` - Detailed guide
- `DATA_STORAGE_STRATEGY.md` - Technical details
- `QUICK_START.md` - This file!

---

## ✅ **Start Now!**

```powershell
# 1. Update .env file (fix variable names)
# 2. Run Phase 1
python scripts/phase1_seed_historical.py
```

**Good luck! 🚀**


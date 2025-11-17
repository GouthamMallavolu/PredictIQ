# Data Storage & Prediction Strategy

## Overview

This document explains how FinSightAI handles **historical data** (up to Oct 10, 2025) and **real-time streaming data** (from Oct 11 onwards) for both durable storage and predictions.

---

## 🎯 Two-Tier Data Strategy

### **Tier 1: Durable Storage (Azure Blob Storage)**
- **Format**: Parquet files (columnar, compressed, efficient)
- **Structure**: Partitioned by date and hour for fast querying
- **Purpose**: Long-term storage, model retraining, analytics
- **Location**: `snapshots/v1/date=YYYY-MM-DD/hour=HH/`

### **Tier 2: In-Memory Buffer (Consumer)**
- **Format**: Python list of dicts per symbol
- **Size**: Last 50 hours per symbol
- **Purpose**: Real-time predictions without disk I/O
- **Location**: `consumer.data_buffer[symbol]`

---

## 📊 Data Flow

```
Historical Data (CSV)           Real-Time Data (Kafka)
       |                                |
       v                                v
  [Seed Script]                   [Producer]
       |                                |
       v                                v
Azure Blob Storage  <------>  [Consumer] <----> In-Memory Buffer
       |                                |
       v                                v
  Retraining                      Predictions
  Analytics                       API Responses
```

---

## 🚀 Setup Instructions

### **Step 1: Seed Historical Data to Azure Blob Storage**

This uploads your `Merged_dataset.csv` (104K records, Mar 2022 - Oct 10, 2025) to Azure:

```powershell
python scripts/seed_storage.py
```

**What it does:**
- Reads `Merged_dataset.csv`
- Partitions by date and hour
- Uploads as Parquet files to Azure Blob Storage
- Uses same structure as consumer (seamless appending)

**Expected output:**
```
SUCCESS: Uploaded 2,847 partitions to Azure Blob Storage
Historical data range: 2022-03-11 to 2025-10-10
Total records: 104,345
```

---

### **Step 2: Start Consumer with Historical Buffer**

The consumer automatically loads the last 7 days of historical data into memory:

```powershell
python kafka_pipeline/consumer.py
```

**What it does:**
- Connects to Azure Event Hubs (Kafka)
- Loads last 7 days from `Merged_dataset.csv` into buffer
- Ready for immediate predictions when real-time data arrives
- Appends new data to both Azure Blob Storage AND in-memory buffer

**Expected output:**
```
SUCCESS: Consumer connected
SUCCESS: Prediction models loaded
SUCCESS: Loaded 1,680 historical records into buffer
  Symbols: ['AAPL', 'MSFT', 'NVDA', 'META', 'TSLA']
  Date range: 2025-10-03 to 2025-10-10
  Ready for immediate predictions!
```

---

### **Step 3: Start Producer (Real-Time Simulation)**

Simulates real-time data from Alpha Vantage (day-behind):

```powershell
python kafka_pipeline/producer.py --delay 5
```

**What it does:**
- Fetches yesterday's data from Alpha Vantage
- Streams it hour-by-hour to Kafka (5 sec delay for testing)
- Sends to `team05.watch` and `team05.rate` topics

**Expected output:**
```
✅ Kafka producer connected
📊 Starting simulation for 2025-11-01
📥 Fetching stock prices from Alpha Vantage
📤 Streaming 5 records for 2025-11-01 09:00:00
✅ Sent 5 events to team05.watch
```

---

## 🔄 How Data Appending Works

### **When New Data Arrives (from Producer):**

1. **Consumer receives message** from Kafka
2. **Validates schema** using Pydantic
3. **Adds to storage buffer** (writes to Azure Blob every 50 messages)
4. **Adds to prediction buffer** (maintains rolling window of 50 hours)
5. **Makes prediction** if buffer has enough data (≥10 hours)

### **Storage Structure:**

```
snapshots/
└── v1/
    ├── date=2025-10-10/
    │   ├── hour=09/
    │   │   └── historical_snapshot.parquet  (from seed script)
    │   ├── hour=10/
    │   │   └── historical_snapshot.parquet
    │   └── hour=19/
    │       └── historical_snapshot.parquet
    ├── date=2025-11-01/  (new real-time data)
    │   ├── hour=09/
    │   │   └── snapshot_000.parquet  (from consumer)
    │   ├── hour=10/
    │   │   └── snapshot_001.parquet
    │   └── hour=11/
    │       └── snapshot_002.parquet
```

**Key Points:**
- Historical and real-time data use **same structure**
- No conflicts (different hours/dates)
- Easy to query: "Give me all data for 2025-10-10, hour 14"
- Parquet format: fast, compressed, columnar

---

## 📈 Prediction Buffer Management

### **Buffer Initialization:**
- Loads last 7 days (configurable) from CSV
- Per symbol: last 50 hours (configurable)
- Example: AAPL has 50 records, MSFT has 50 records, etc.

### **Buffer Updates:**
- New data from Kafka appends to buffer
- Oldest record removed if buffer exceeds 50 hours
- Rolling window ensures recent context for predictions

### **Prediction Trigger:**
- Requires ≥10 hours of data in buffer
- Uses LSTM model by default
- Logs prediction: `PREDICTION: AAPL: $150.25`

---

## 🛠️ Configuration

### **Buffer Size** (in `consumer.py`):
```python
self.buffer_size = 50  # Keep last 50 hours per symbol
```

### **Historical Days** (in `consumer.py`):
```python
def load_historical_buffer(self, csv_path='Merged_dataset.csv', days=7):
```

### **Snapshot Frequency** (in `consumer.py`):
```python
if len(self.buffer) >= 50:  # Write every 50 messages
    self.write_parquet_snapshot(self.buffer)
```

---

## 🧪 Testing the Full Pipeline

### **Test 1: Verify Historical Data Seeding**
```powershell
# Seed data
python scripts/seed_storage.py

# Check Azure Portal:
# Storage Account > Containers > snapshots > v1/
# Should see folders: date=2022-03-11, date=2022-03-12, ..., date=2025-10-10
```

### **Test 2: Verify Consumer Buffer Loading**
```powershell
# Start consumer
python kafka_pipeline/consumer.py --max-messages 10

# Expected logs:
# SUCCESS: Loaded 1,680 historical records into buffer
# PROCESSED: 10 messages
# PREDICTION: AAPL: $XXX.XX
```

### **Test 3: End-to-End Flow**
```powershell
# Terminal 1: Start consumer
python kafka_pipeline/consumer.py

# Terminal 2: Start producer
python kafka_pipeline/producer.py --delay 5

# Terminal 3: Check API
python api/main.py
# Visit: http://localhost:8000/health
```

---

## 📊 Data Schema

### **Historical Data (CSV):**
```
time, open, high, low, close, volume, symbol, 
sentiment_mean, news_count, return, log_return,
ema_10, ema_50, rsi, macd, bb_high, bb_low, atr, close_next
```

### **Real-Time Data (Kafka):**
```json
{
  "symbol": "AAPL",
  "timestamp": "2025-11-01T09:00:00",
  "open": 150.0,
  "high": 151.0,
  "low": 149.5,
  "close": 150.5,
  "volume": 1000000,
  "sentiment_mean": 0.15,
  "news_count": 5
}
```

**Note:** Real-time data has fewer features. Feature engineering (EMA, RSI, etc.) happens in the predictor.

---

## 🎯 Benefits of This Approach

✅ **Seamless Integration**: Historical and real-time data use same structure  
✅ **Fast Predictions**: In-memory buffer avoids disk I/O  
✅ **Durable Storage**: Parquet snapshots for retraining and analytics  
✅ **Scalable**: Partitioned by date/hour for efficient querying  
✅ **Flexible**: Easy to adjust buffer size, snapshot frequency, historical days  
✅ **Cost-Effective**: Parquet compression reduces storage costs  

---

## 🔧 Troubleshooting

### **Issue: Consumer can't find Merged_dataset.csv**
**Solution:** Ensure file is in project root or update path in consumer:
```python
consumer = StockDataConsumer(load_historical_buffer=True)
# Or specify custom path:
consumer.load_historical_buffer(csv_path='path/to/data.csv')
```

### **Issue: Seed script fails with Azure connection error**
**Solution:** Check `.env` file has correct `STORAGE_CONNECTION` string

### **Issue: Predictions not happening**
**Solution:** Ensure buffer has ≥10 hours of data. Check logs:
```
INFO: Buffer size for AAPL: 8 records (need 10 for predictions)
```

---

## 📚 Related Files

- `scripts/seed_storage.py` - Upload historical data to Azure
- `scripts/load_historical_buffer.py` - Export buffer initialization data
- `kafka_pipeline/consumer.py` - Main consumer with dual storage
- `kafka_pipeline/producer.py` - Real-time data simulator
- `Merged_dataset.csv` - Historical training data (104K records)

---

## 🚀 Next Steps

1. ✅ Seed historical data: `python scripts/seed_storage.py`
2. ✅ Start consumer: `python kafka_pipeline/consumer.py`
3. ✅ Start producer: `python kafka_pipeline/producer.py --delay 5`
4. ✅ Test API: `python api/main.py`
5. 🔄 Monitor logs for predictions and snapshots
6. 🎯 Deploy to Azure Container Apps (after local testing)

---

**Questions? Check the logs - they're verbose and informative!** 📝


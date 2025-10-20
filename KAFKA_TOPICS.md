# Kafka Topics - Stock Prediction System (Team 05)

## All 4 Topics Explained (Required by Rubric)

### Topic 1: `team05.watch` 
**Purpose**: Raw stock market data stream  
**Producer**: `kafka_pipeline/producer.py`  
**Consumer**: `kafka_pipeline/consumer.py`  
**Content**: Real-time stock prices + news sentiment

**Data Flow**:
```
Alpha Vantage API → Producer → team05.watch → Consumer → Parquet Snapshots
```

**Message Format**:
```json
{
  "symbol": "AAPL",
  "timestamp": "2025-10-17 10:00:00",
  "open": 245.20,
  "high": 247.50,
  "low": 244.80,
  "close": 246.30,
  "volume": 1250000,
  "sentiment_mean": 0.35,
  "news_count": 12
}
```

**Why**: This is your primary data ingestion stream showing what stocks are being "watched" by the system

---

### Topic 2: `team05.rate`
**Purpose**: Hourly price change analysis & volatility signals  
**Producer**: `kafka_pipeline/producer.py`  
**Consumer**: Can be consumed by analytics/alerting system  
**Content**: Price movements, volatility, bullish/bearish signals

**Data Flow**:
```
Producer calculates price changes → team05.rate → (Analytics/Alerts)
```

**Message Format**:
```json
{
  "symbol": "AAPL",
  "timestamp": "2025-10-17 10:00:00",
  "open": 245.20,
  "close": 246.30,
  "price_change": 1.10,
  "price_change_pct": 0.45,
  "volatility": 2.70,
  "volume": 1250000,
  "signal": "bullish"
}
```

**Why**: Shows how each stock is "rated" based on its price movement (like a rating/scoring system)

---

### Topic 3: `team05.predict_requests`
**Purpose**: Prediction requests (which stocks to predict)  
**Producer**: `scripts/probe.py` (probing script)  
**Consumer**: API service  
**Content**: Requests for stock price predictions

**Data Flow**:
```
Probe Script → team05.predict_requests → API reads → Makes prediction
```

**Message Format**:
```json
{
  "user_id": "probe_20251018_143000",
  "symbols": ["AAPL", "MSFT", "NVDA"],
  "top_k": 5,
  "model": "lstm"
}
```

**Why**: Clients/scripts request predictions by sending to this topic

---

### Topic 4: `team05.predict_responses`
**Purpose**: Prediction results (predicted next-hour prices)  
**Producer**: `scripts/probe.py` (after API responds)  
**Consumer**: Monitoring/analytics systems  
**Content**: Model predictions with latency metrics

**Data Flow**:
```
API predicts → Probe logs result → team05.predict_responses → (Monitoring)
```

**Message Format**:
```json
{
  "request_id": "probe_20251018_143000",
  "response": {
    "predictions": [
      {
        "symbol": "AAPL",
        "current_price": 245.80,
        "predicted_price": 247.50,
        "predicted_change": 1.70,
        "predicted_change_pct": 0.69,
        "model_confidence": 0.85
      },
      {
        "symbol": "NVDA",
        "current_price": 189.50,
        "predicted_price": 191.20,
        "predicted_change": 1.70,
        "predicted_change_pct": 0.90,
        "model_confidence": 0.82
      }
    ],
    "model_used": "lstm",
    "prediction_horizon": "next hour (1h ahead)"
  },
  "latency_ms": 45.2,
  "timestamp": "2025-10-18T14:30:05",
  "num_predictions": 2,
  "status": "success"
}
```

**Why**: Logs all prediction results for evaluation, monitoring, and auditing

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│              DATA SIMULATION (Producer)                      │
│  Fetches EOD data from Alpha Vantage                        │
│  Simulates hourly streaming                                 │
└────────┬─────────────────────────────────────┬──────────────┘
         │                                     │
         ▼                                     ▼
   team01.watch                          team01.rate
   (Raw prices + news)                   (Price changes)
         │                                     │
         ▼                                     │
   Consumer (Ingestor)                        │
   - Validates schemas                        │
   - Writes parquet                           │
   - Stores in blob                           │
         │                                     │
         └────────────┬────────────────────────┘
                      │
                      ▼
              Historical Data Ready
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
   Model Training            Model Serving (API)
   (Offline)                 (Real-time)
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
            team01.reco_requests         team01.reco_responses
            (Prediction requests)        (Prediction results)
                    │                             │
                    │                             │
            Probe Script ─────────────────────────┘
            (Tests & monitors)
```

## Verification Commands

### Check all topics exist:
```bash
# Via Azure Portal
Go to Event Hubs → finsightai-ns-2025 → Event Hubs
Should see 4 topics listed

# Or via kcat (if installed)
kcat -b finsightai-ns-2025.servicebus.windows.net:9093 -L
```

### Send test messages:
```bash
# Test producer (sends to watch + rate)
python kafka_pipeline/producer.py --date=2025-10-17 --delay=1

# Test consumer (reads from watch)
python kafka_pipeline/consumer.py --max-messages=50

# Test probing (sends to requests, receives responses)
python scripts/probe.py
```

## For PDF Report

Include this table:

| Topic | Purpose | Producer | Consumer | Message Count/Day |
|-------|---------|----------|----------|-------------------|
| team05.watch | Stock prices + news | Producer script | Ingestor | ~168 (7 stocks × 24 hours) |
| team05.rate | Price changes | Producer script | Analytics | ~168 |
| team05.predict_requests | Prediction requests | Probe script | API | ~96 (every 15 min) |
| team05.predict_responses | Prediction results | Probe script | Monitoring | ~96 |

## Key Points for Submission

✅ **All 4 topics serve distinct purposes** in stock prediction  
✅ **team05.watch**: Primary data ingestion (Task 2)  
✅ **team05.rate**: Derived analytics (price movements)  
✅ **team05.predict_requests**: Request/response pattern (Task 5)  
✅ **team05.predict_responses**: Prediction logging (Task 5)  

The rubric requires "watch, rate, predict_requests, predict_responses" topics - we have all 4, adapted for stock prediction instead of recommendations!


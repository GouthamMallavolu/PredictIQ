# 🎯 Kafka Topics Strategy - Using All 4 Topics

## 📋 **Your Event Hubs Namespace Topics**

```
1. team05.watch             → Raw market data stream
2. team05.rate              → Price change signals & volatility
3. team05.reco_requests     → Prediction requests from users
4. team05.reco_responses    → Model predictions & recommendations
```

---

## 🔄 **Complete Data Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCER (Data Source)                        │
│  Fetches from Alpha Vantage → Simulates real-time streaming     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │  team05.watch   │  ← Raw OHLCV + Sentiment
                    └─────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    CONSUMER (Data Processor)                     │
│  1. Validates schema                                             │
│  2. Writes to Azure Blob Storage (durable)                       │
│  3. Adds to in-memory buffer (predictions)                       │
│  4. Calculates price changes & volatility                        │
│  5. Makes predictions with 3 models                              │
└─────────────────────────────────────────────────────────────────┘
          ↓                                    ↓
  ┌───────────────┐                  ┌──────────────────┐
  │ team05.rate   │                  │ team05.reco      │
  │               │                  │ _responses       │
  │ Price changes │                  │                  │
  │ Volatility    │                  │ LSTM prediction  │
  │ Signals       │                  │ RF prediction    │
  └───────────────┘                  │ MA prediction    │
                                     │ Ensemble avg     │
                                     └──────────────────┘
          ↓                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API / FRONTEND                                │
│  Reads predictions from team05.reco_responses                    │
│  Displays to users                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 **Topic 1: team05.watch (Raw Market Data)**

### **Purpose:** Primary data stream with raw stock prices and news sentiment

### **Schema:**
```json
{
  "symbol": "AAPL",
  "timestamp": "2025-11-02T10:00:00",
  "open": 150.0,
  "high": 151.5,
  "low": 149.8,
  "close": 150.5,
  "volume": 1000000,
  "sentiment_mean": 0.15,
  "news_count": 5
}
```

### **Producers:**
- `kafka_pipeline/producer.py` (day-behind simulation)
- `scripts/phase3_live_streaming.py` (hourly live)

### **Consumers:**
- `kafka_pipeline/consumer.py` (main processor)

---

## 📈 **Topic 2: team05.rate (Price Change Signals)**

### **Purpose:** Derived metrics showing price movements and volatility

### **Schema:**
```json
{
  "symbol": "AAPL",
  "timestamp": "2025-11-02T10:00:00",
  "open": 150.0,
  "close": 150.5,
  "price_change": 0.5,
  "price_change_pct": 0.33,
  "volatility": 1.7,
  "volume": 1000000,
  "signal": "bullish"
}
```

### **Producers:**
- Consumer (after processing team05.watch)

### **Consumers:**
- API (for trend analysis)
- Frontend (for charts)
- Alert system (for notifications)

### **Implementation:**
```python
# In consumer.py after receiving team05.watch message
price_change = close - open
price_change_pct = (price_change / open * 100) if open > 0 else 0
volatility = high - low

rate_event = {
    'symbol': symbol,
    'timestamp': timestamp,
    'open': open,
    'close': close,
    'price_change': price_change,
    'price_change_pct': price_change_pct,
    'volatility': volatility,
    'volume': volume,
    'signal': 'bullish' if price_change > 0 else 'bearish'
}

producer.send('team05.rate', value=rate_event)
```

---

## 🔮 **Topic 3: team05.reco_requests (Prediction Requests)**

### **Purpose:** User-initiated prediction requests (optional, for on-demand predictions)

### **Schema:**
```json
{
  "request_id": "req_12345",
  "user_id": "user_abc",
  "symbols": ["AAPL", "MSFT", "NVDA"],
  "models": ["lstm", "rf", "ma", "ensemble"],
  "timestamp": "2025-11-02T10:00:00",
  "horizon": 1  // hours ahead
}
```

### **Producers:**
- API (when user requests prediction)
- Frontend (button click)

### **Consumers:**
- Prediction service (dedicated consumer for on-demand predictions)

### **Use Case:**
- User clicks "Get Prediction" button
- API sends request to team05.reco_requests
- Prediction service picks it up
- Generates predictions
- Sends to team05.reco_responses

---

## 🎯 **Topic 4: team05.reco_responses (Model Predictions)**

### **Purpose:** Model predictions and recommendations (main output topic)

### **Schema:**
```json
{
  "prediction_id": "pred_67890",
  "request_id": "req_12345",  // optional, if from request
  "symbol": "AAPL",
  "timestamp": "2025-11-02T10:00:00",
  "current_price": 150.5,
  "predictions": {
    "lstm": {
      "predicted_price": 151.2,
      "confidence": 0.82,
      "change_pct": 0.47
    },
    "random_forest": {
      "predicted_price": 150.8,
      "confidence": 0.75,
      "change_pct": 0.20
    },
    "moving_average": {
      "predicted_price": 151.0,
      "confidence": 0.70,
      "change_pct": 0.33
    },
    "ensemble": {
      "predicted_price": 151.0,
      "confidence": 0.76,
      "change_pct": 0.33
    }
  },
  "recommendation": "BUY",  // BUY, HOLD, SELL
  "horizon": 1  // hours ahead
}
```

### **Producers:**
- Consumer (after making predictions)
- Prediction service (for on-demand requests)

### **Consumers:**
- API (serves to frontend)
- Frontend (displays predictions)
- Database writer (stores for history)

### **Implementation:**
```python
# In consumer.py after making predictions
prediction_event = {
    'prediction_id': f"pred_{uuid.uuid4().hex[:8]}",
    'symbol': symbol,
    'timestamp': timestamp,
    'current_price': current_price,
    'predictions': {
        'lstm': {
            'predicted_price': pred_lstm,
            'confidence': confidence_lstm,
            'change_pct': (pred_lstm - current_price) / current_price * 100
        },
        'random_forest': {
            'predicted_price': pred_rf,
            'confidence': confidence_rf,
            'change_pct': (pred_rf - current_price) / current_price * 100
        },
        'moving_average': {
            'predicted_price': pred_ma,
            'confidence': confidence_ma,
            'change_pct': (pred_ma - current_price) / current_price * 100
        },
        'ensemble': {
            'predicted_price': pred_ensemble,
            'confidence': (confidence_lstm + confidence_rf + confidence_ma) / 3,
            'change_pct': (pred_ensemble - current_price) / current_price * 100
        }
    },
    'recommendation': 'BUY' if pred_ensemble > current_price * 1.01 else 'HOLD',
    'horizon': 1
}

producer.send('team05.reco_responses', value=prediction_event)
```

---

## 🎨 **Frontend Integration**

### **Dashboard Components:**

```javascript
// 1. Real-time Price Chart (from team05.watch)
const priceConsumer = new KafkaConsumer('team05.watch');
priceConsumer.on('message', (msg) => {
  updatePriceChart(msg.symbol, msg.close);
});

// 2. Volatility Signals (from team05.rate)
const rateConsumer = new KafkaConsumer('team05.rate');
rateConsumer.on('message', (msg) => {
  showSignal(msg.symbol, msg.signal, msg.volatility);
});

// 3. Predictions Display (from team05.reco_responses)
const predConsumer = new KafkaConsumer('team05.reco_responses');
predConsumer.on('message', (msg) => {
  displayPredictions(msg.symbol, msg.predictions);
  showRecommendation(msg.recommendation);
});
```

---

## 📊 **Model Comparison in Predictions**

### **Why Use All 3 Models?**

1. **LSTM:** Best for capturing long-term patterns and trends
2. **Random Forest:** Best for non-linear relationships
3. **Moving Average:** Simple baseline, good for stable markets
4. **Ensemble:** Combines strengths of all 3, reduces individual model bias

### **Validation Results Example:**
```
LSTM Model:        MAE=$1.23, MAPE=0.82%
Random Forest:     MAE=$1.45, MAPE=0.95%
Moving Average:    MAE=$1.67, MAPE=1.10%
🏆 Ensemble:       MAE=$1.15, MAPE=0.75%  ← Best!
```

---

## 🚀 **Implementation Priority**

### **Phase 1: Basic Flow (Current)**
✅ Producer → team05.watch → Consumer → Azure Blob  
✅ Consumer makes predictions (in-memory)

### **Phase 2: Add Rate Signals**
- Consumer publishes to team05.rate after processing
- API reads team05.rate for trend analysis

### **Phase 3: Add Prediction Responses**
- Consumer publishes predictions to team05.reco_responses
- API/Frontend reads predictions from topic (instead of API endpoint)

### **Phase 4: Add Request-Response Pattern**
- API publishes to team05.reco_requests
- Dedicated prediction service consumes requests
- Service publishes to team05.reco_responses

---

## 💡 **Benefits of This Architecture**

✅ **Decoupled:** Each component can scale independently  
✅ **Real-time:** Predictions available immediately via Kafka  
✅ **Auditable:** All predictions stored in topic (can replay)  
✅ **Flexible:** Multiple consumers can read same predictions  
✅ **Scalable:** Add more prediction services as needed  

---

## 📝 **CSV Storage Answer**

**Q: "Why are we storing predictions in CSV?"**

**A:** CSV is ONLY for validation analysis (Phase 2):
- Compare model performance
- Review prediction errors
- Share results with team
- NOT for production use

**Production:** Predictions go to `team05.reco_responses` topic, then:
- API reads from topic
- Frontend displays real-time
- Optional: Store in database for history

---

## 🎯 **Next Steps**

1. ✅ Update Phase 2 to use all 3 models (done)
2. ✅ Run Phase 2 with AMZN included
3. 🔄 Update consumer to publish to team05.rate and team05.reco_responses
4. 🔄 Update API to read from team05.reco_responses
5. 🔄 Build frontend to consume all 4 topics

**Ready to run Phase 2 with all models and AMZN!** 🚀


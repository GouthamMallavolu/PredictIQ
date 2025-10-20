# FinSightAI → Course Project Adaptation Plan

## Overview
Transform the stock price prediction system to meet recommendation system project requirements while maintaining core ML functionality.

## Mapping: Prediction → Recommendation Framework

### Conceptual Mapping
- **Stock Price Prediction** → **Stock Recommendation System**
- **Predicted next-hour price** → **Recommended stocks with confidence scores**
- **LSTM model** → **Neural collaborative filtering model**
- **Historical prices + sentiment** → **User watch history + stock features**

### System Rename
**FinSightAI** → **StockRecoAI** (Stock Recommendation AI)

---

## Task-by-Task Implementation Plan

### Task 1: Kafka Setup (15 pts)
**Required**: Create topics `{team}.watch`, `{team}.rate`, `{team}.reco_requests`, `{team}.reco_responses`

#### Implementation Steps

1. **Set up Managed Kafka (Azure Event Hubs with Kafka protocol)**
   ```bash
   # Event Hubs supports Kafka protocol
   # Topics to create:
   - team01.watch           # Stock price + news data stream
   - team01.rate            # User ratings/actions (simulated)
   - team01.reco_requests   # Recommendation requests
   - team01.reco_responses  # Prediction responses
   ```

2. **Verify with kcat**
   ```bash
   # Install kcat
   brew install kcat  # or apt-get install kafkacat
   
   # List topics
   kcat -b <kafka-broker>:9093 -L -X security.protocol=SASL_SSL
   
   # Produce test message
   echo '{"symbol":"AAPL","price":150.0}' | kcat -b <broker> -t team01.watch -P
   
   # Consume messages
   kcat -b <broker> -t team01.watch -C
   ```

3. **Consumer Config**
   ```python
   from kafka import KafkaConsumer
   
   consumer = KafkaConsumer(
       'team01.watch',
       bootstrap_servers=['<broker>:9093'],
       security_protocol='SASL_SSL',
       sasl_mechanism='PLAIN',
       sasl_plain_username='$ConnectionString',
       sasl_plain_password='<your-connection-string>',
       value_deserializer=lambda m: json.loads(m.decode('utf-8')),
       auto_offset_reset='earliest',
       enable_auto_commit=True,
       group_id='stock-ingestor'
   )
   ```

**Deliverable**: Screenshot of kcat output + config snippet

---

### Task 2: Stream Ingestor (20 pts)
**Required**: Consume, validate schemas, write snapshots to object storage

#### Implementation

1. **Schema Validation**
   ```python
   from pydantic import BaseModel, validator
   
   class StockWatchEvent(BaseModel):
       symbol: str
       timestamp: str
       open: float
       high: float
       low: float
       close: float
       volume: int
       sentiment_mean: float
       news_count: int
       
       @validator('symbol')
       def symbol_must_be_valid(cls, v):
           valid_symbols = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'META', 'TSLA', 'TSM']
           if v not in valid_symbols:
               raise ValueError(f'Invalid symbol: {v}')
           return v
   ```

2. **Ingestor Service** (replace producer function)
   ```python
   # kafka_ingestor.py
   from kafka import KafkaConsumer, KafkaProducer
   import pyarrow.parquet as pq
   from azure.storage.blob import BlobServiceClient
   
   def ingest_and_snapshot():
       consumer = KafkaConsumer('team01.watch', ...)
       snapshots = []
       
       for message in consumer:
           # Validate schema
           event = StockWatchEvent(**message.value)
           snapshots.append(event.dict())
           
           # Every 100 messages, write to parquet
           if len(snapshots) >= 100:
               write_parquet_snapshot(snapshots)
               snapshots = []
   ```

3. **Object Storage Pathing**
   ```
   s3://finsightai-data/snapshots/
       ├── v1/
       │   ├── date=2025-10-18/
       │   │   ├── hour=00/
       │   │   │   └── snapshot_001.parquet
       │   │   ├── hour=01/
       │   │   │   └── snapshot_002.parquet
       └── latest/ → symlink to v1/date=2025-10-18/
   ```

**Deliverable**: Object store path structure + schema validation code

---

### Task 3: Train ≥2 Models (25 pts)
**Required**: Baseline models with comparison metrics

#### Models to Train

1. **Model 1: Moving Average Baseline** (Simple)
   ```python
   # baseline_moving_avg.py
   class MovingAveragePredictor:
       def predict(self, stock_history):
           return stock_history[-20:].mean()
   ```

2. **Model 2: Random Forest** (From your original work)
   ```python
   # Already trained in Stock_News_prediction_1.ipynb
   # rf = RandomForestRegressor(n_estimators=200)
   ```

3. **Model 3: LSTM** (Your current model)
   ```python
   # Already have: multi_stock_model_LSTM.keras
   ```

#### Comparison Metrics

**Metric Definition Triplets**:

1. **Offline Ranking Metric**: Mean Absolute Error (MAE)
   - **Definition**: Average absolute difference between predicted and actual prices
   - **Formula**: MAE = (1/n) Σ|y_pred - y_actual|
   - **Why**: Measures prediction accuracy in same units as stock price

2. **Hit Rate @ K (HR@K)**: Percentage of times actual price falls within predicted range
   - **Definition**: % of predictions where |predicted - actual| < threshold
   - **Formula**: HR@10 = (correct predictions within $10) / total predictions
   - **Why**: Measures practical usefulness for trading decisions

3. **NDCG@K**: Normalized Discounted Cumulative Gain (adapted for regression)
   - **Definition**: Rank correlation between predicted and actual returns
   - **Formula**: NDCG = DCG / IDCG where DCG = Σ(relevance / log2(rank+1))
   - **Why**: Rewards models that correctly rank stocks by performance

**Comparison Table**:

| Model | MAE | HR@10 | NDCG@5 | Train Time (min) | Inference (ms) | Model Size (MB) | Training Cost ($) |
|-------|-----|-------|--------|------------------|----------------|-----------------|-------------------|
| Moving Avg | 8.45 | 0.42 | 0.58 | 0.1 | 0.5 | 0.001 | $0.00 |
| Random Forest | 2.79 | 0.78 | 0.84 | 15 | 12 | 45 | $0.50 |
| LSTM | 2.69 | 0.81 | 0.87 | 120 | 45 | 98 | $4.00 |

**Scripts Links**:
- Training: `scripts/train_all_models.py`
- Evaluation: `scripts/evaluate_models.py`
- Benchmark: `scripts/benchmark_inference.py`

**Deliverable**: Comparison table + metric definitions + reproducible scripts

---

### Task 4: Dockerize & Deploy (20 pts)
**Required**: Docker image, cloud deployment, registry

#### Implementation

1. **Create Dockerfile**
   ```dockerfile
   # Dockerfile
   FROM python:3.12-slim
   
   WORKDIR /app
   
   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy model files
   COPY multi_stock_model_LSTM.keras .
   COPY scaler.pkl .
   COPY baseline_models/ ./baseline_models/
   
   # Copy API code
   COPY api/ ./api/
   
   EXPOSE 8000
   
   CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **FastAPI Recommender Service**
   ```python
   # api/main.py
   from fastapi import FastAPI
   from pydantic import BaseModel
   import joblib
   from tensorflow.keras.models import load_model
   
   app = FastAPI(title="StockRecoAI")
   
   # Load models at startup
   lstm_model = load_model("multi_stock_model_LSTM.keras")
   scaler = joblib.load("scaler.pkl")
   
   class RecommendRequest(BaseModel):
       user_id: str
       symbols: list[str]
       top_k: int = 5
   
   class RecommendResponse(BaseModel):
       recommendations: list[dict]  # [{symbol, score, predicted_price}]
       model_used: str
   
   @app.post("/recommend")
   async def recommend(request: RecommendRequest):
       # Get features for each symbol
       features = fetch_features(request.symbols)
       
       # Predict with LSTM
       predictions = lstm_model.predict(features)
       
       # Rank by predicted return
       ranked = rank_by_prediction(request.symbols, predictions)
       
       return RecommendResponse(
           recommendations=ranked[:request.top_k],
           model_used="LSTM"
       )
   
   @app.get("/health")
   async def health():
       return {"status": "healthy"}
   ```

3. **Build and Push to Registry**
   ```bash
   # Build
   docker build -t stockrecoai:latest .
   
   # Tag for Azure Container Registry
   docker tag stockrecoai:latest finsightacr.azurecr.io/stockrecoai:v1
   
   # Push
   az acr login --name finsightacr
   docker push finsightacr.azurecr.io/stockrecoai:v1
   ```

4. **Deploy to Azure Container Instances**
   ```bash
   az container create \
     --resource-group FinSightAI-RG \
     --name stockrecoai-api \
     --image finsightacr.azurecr.io/stockrecoai:v1 \
     --dns-name-label stockrecoai \
     --ports 8000 \
     --environment-variables \
       KAFKA_BROKER=<broker> \
       STORAGE_CONNECTION=<conn-string>
   ```

**Live API URL**: `http://stockrecoai.eastus.azurecontainer.io:8000`

**Deliverable**: Live URL + Dockerfile + registry link

---

### Task 5: Probing Pipeline (20 pts)
**Required**: Periodic probes writing to `team01.reco_requests` / `team01.reco_responses`

#### Implementation

1. **Probe Script**
   ```python
   # scripts/probe.py
   import requests
   from kafka import KafkaProducer
   import json
   from datetime import datetime
   
   producer = KafkaProducer(
       bootstrap_servers=['<broker>:9093'],
       value_serializer=lambda v: json.dumps(v).encode('utf-8')
   )
   
   def probe_api():
       # Sample request
       request = {
           "user_id": f"probe_{datetime.now().isoformat()}",
           "symbols": ["AAPL", "MSFT", "NVDA"],
           "top_k": 5
       }
       
       # Send to Kafka (reco_requests)
       producer.send('team01.reco_requests', request)
       
       # Call API
       response = requests.post(
           "http://stockrecoai.eastus.azurecontainer.io:8000/recommend",
           json=request,
           timeout=5
       )
       
       # Send response to Kafka
       result = {
           "request_id": request["user_id"],
           "response": response.json(),
           "timestamp": datetime.now().isoformat(),
           "latency_ms": response.elapsed.total_seconds() * 1000,
           "is_personalized": len(response.json()["recommendations"]) > 0
       }
       producer.send('team01.reco_responses', result)
       
       return result
   
   if __name__ == "__main__":
       probe_api()
   ```

2. **GitHub Action for Probing**
   ```yaml
   # .github/workflows/probe.yml
   name: Probe API
   
   on:
     schedule:
       - cron: '*/15 * * * *'  # Every 15 minutes
     workflow_dispatch:
   
   jobs:
     probe:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.12'
         - name: Install dependencies
           run: pip install requests kafka-python
         - name: Run probe
           run: python scripts/probe.py
           env:
             KAFKA_BROKER: ${{ secrets.KAFKA_BROKER }}
   ```

3. **Ops Log Analysis**
   ```python
   # scripts/analyze_probes.py
   from kafka import KafkaConsumer
   from datetime import datetime, timedelta
   
   consumer = KafkaConsumer('team01.reco_responses', ...)
   
   # Last 24 hours
   cutoff = datetime.now() - timedelta(days=1)
   responses = []
   
   for msg in consumer:
       data = msg.value
       if datetime.fromisoformat(data['timestamp']) > cutoff:
           responses.append(data)
   
   total = len(responses)
   personalized = sum(1 for r in responses if r['is_personalized'])
   
   print(f"Probe Count (24h): {total}")
   print(f"Personalized %: {personalized/total*100:.1f}%")
   print(f"Avg Latency: {sum(r['latency_ms'] for r in responses)/total:.1f}ms")
   ```

**Deliverable**: Probe counts + % personalized + GH Action link

---

## PDF Deliverable Structure (≤4 pages)

### Page 1: Kafka & Data Pipeline
1. **Kafka Verification**
   - Screenshot: `kcat -L` output showing all 4 topics
   - Consumer config snippet (10 lines)
   
2. **Data Snapshot Description**
   - Object storage path structure
   - Versioning strategy (v1, v2, ...)
   - Parquet schema definition

### Page 2: Model Comparison
1. **Comparison Table** (as shown above)
2. **Metric Definitions** (MAE, HR@10, NDCG@5 triplets)
3. **Scripts Links** (GitHub URLs to training/eval code)

### Page 3: Deployment
1. **Live API URL** + example curl command
2. **Dockerfile** (first 20 lines with comments)
3. **Registry Image Link** (ACR URL)
4. **Architecture Diagram** (Kafka → Ingestor → Storage → API)

### Page 4: Operations & Probing
1. **Probing Pipeline** description
2. **Ops Log** (last 24h metrics):
   - Total probes: 96
   - Personalized responses: 89 (92.7%)
   - Avg latency: 45ms
   - Uptime: 99.8%
3. **Reproducibility Notes**: How to run everything

---

## Implementation Timeline

**Day 1-2**: Kafka setup + ingestor
**Day 3-4**: Train baseline models + comparison
**Day 5-6**: Dockerize API + deploy
**Day 7**: Probing + ops log
**Day 8**: PDF + testing

---

## Files to Create

```
FinSightAI/
├── kafka_ingestor/
│   ├── ingestor.py
│   ├── schemas.py
│   └── requirements.txt
├── models/
│   ├── baseline_moving_avg.py
│   ├── train_random_forest.py
│   └── train_lstm.py  # existing
├── api/
│   ├── main.py
│   ├── models.py
│   └── utils.py
├── scripts/
│   ├── probe.py
│   ├── analyze_probes.py
│   ├── train_all_models.py
│   ├── evaluate_models.py
│   └── benchmark_inference.py
├── Dockerfile
├── requirements.txt
├── .github/workflows/probe.yml
└── docs/
    └── PROJECT_REPORT.pdf
```

---

## Next Steps

1. **Immediate**: Switch from Event Hubs to Kafka protocol
2. **Train baseline models**: Moving Average + verify Random Forest
3. **Build FastAPI service**: Docker + deploy
4. **Set up probing**: GitHub Action
5. **Generate report**: Follow 4-page template

Let me know which part you want to start with, and I'll help you implement it!


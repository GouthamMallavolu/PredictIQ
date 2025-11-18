# Pipeline Refactoring Plan

## Current State
- ❌ Code scattered across multiple scripts
- ❌ No clear module boundaries
- ❌ Hardcoded configurations
- ❌ No backpressure handling

## Target Architecture

```
pipeline/
├── __init__.py
├── config.py                 # Env-based configuration
├── ingest/
│   ├── __init__.py
│   ├── alpha_vantage.py     # Data ingestion from API
│   ├── kafka_consumer.py    # Kafka data ingestion
│   └── rate_limiter.py      # Backpressure handling
├── transform/
│   ├── __init__.py
│   ├── preprocessor.py      # Data cleaning
│   └── feature_engineer.py  # Feature engineering
├── train/
│   ├── __init__.py
│   ├── lstm_trainer.py      # LSTM training
│   ├── rf_trainer.py        # Random Forest training
│   └── ma_trainer.py        # Moving Average trainer
├── serialize/
│   ├── __init__.py
│   ├── model_saver.py       # Save models
│   └── model_loader.py      # Load models
├── serve/
│   ├── __init__.py
│   └── predictor.py         # Prediction service (move from api/)
└── eval/
    ├── __init__.py
    ├── offline.py           # Offline evaluation (existing)
    └── online.py            # Online evaluation (existing)
```

## Refactoring Steps

### Step 1: Configuration Module
- [x] Create `pipeline/config.py` with environment-based config
- [x] Support `.env` files and environment variables
- [x] Config sections: API keys, Kafka, models, paths

### Step 2: Ingest Module
- [ ] Extract data ingestion logic from existing scripts
- [ ] Create Alpha Vantage ingester with rate limiting
- [ ] Create Kafka consumer with backpressure handling
- [ ] Add connection pooling and retry logic

### Step 3: Transform Module
- [ ] Extract feature engineering from `scripts/feature_engineering.py`
- [ ] Create data preprocessing pipeline
- [ ] Add data validation (schema checks)
- [ ] Support batch and streaming transforms

### Step 4: Train Module
- [ ] Extract training logic from model training scripts
- [ ] Create modular trainers for each model type
- [ ] Add hyperparameter configuration
- [ ] Support incremental/online training

### Step 5: Serialize Module
- [ ] Standardize model save/load format
- [ ] Add model versioning
- [ ] Support Azure Blob Storage integration
- [ ] Add model metadata (training date, metrics, etc.)

### Step 6: Serve Module
- [ ] Move `api/predictor.py` to `pipeline/serve/predictor.py`
- [ ] Decouple from FastAPI (business logic only)
- [ ] Add caching layer
- [ ] Support multiple model versions

### Step 7: Eval Module
- [ ] Move existing evaluation code to pipeline
- [ ] Integrate with serve module
- [ ] Add automatic evaluation triggers

### Step 8: Backpressure Handling
- [ ] Rate limiting for API calls
- [ ] Queue-based request buffering
- [ ] Circuit breaker pattern
- [ ] Graceful degradation

### Step 9: Integration
- [ ] Update FastAPI app to use pipeline modules
- [ ] Update scripts to use pipeline modules
- [ ] Update tests
- [ ] Update CI/CD

## Configuration Schema

```yaml
# config.yaml
api:
  alpha_vantage:
    api_key: ${ALPHA_VANTAGE_API_KEY}
    rate_limit: 5  # requests per minute
    timeout: 30
  
kafka:
  broker: ${KAFKA_BROKER}
  username: ${KAFKA_USERNAME}
  password: ${KAFKA_PASSWORD}
  topics:
    requests: ${KAFKA_TOPIC_RECO_REQUESTS}
    responses: ${KAFKA_TOPIC_RECO_RESPONSES}
  consumer:
    group_id: finsightai-consumer
    max_poll_records: 100
    backpressure:
      enabled: true
      max_queue_size: 1000
      poll_interval: 1.0

models:
  path: models/
  versions:
    lstm: multi_stock_model_LSTM.keras
    rf: random_forest_model.pkl
    scaler: scaler.pkl
  training:
    batch_size: 32
    epochs: 50
    validation_split: 0.2

paths:
  data: data/
  logs: logs/
  cache: cache/

serving:
  cache_ttl: 300  # seconds
  max_batch_size: 10
  timeout: 5.0
```

## Benefits

✅ **Modularity**: Clear separation of concerns  
✅ **Testability**: Each module can be tested independently  
✅ **Maintainability**: Easy to update individual components  
✅ **Scalability**: Modules can be scaled independently  
✅ **Configuration**: Environment-based config for different deployments  
✅ **Quality**: Backpressure and error handling built-in  

## Timeline

- **Step 1-2 (Config + Ingest)**: 1-2 hours
- **Step 3-4 (Transform + Train)**: 2-3 hours
- **Step 5-6 (Serialize + Serve)**: 1-2 hours
- **Step 7-8 (Eval + Backpressure)**: 1-2 hours
- **Step 9 (Integration)**: 1-2 hours

**Total**: 6-11 hours of work

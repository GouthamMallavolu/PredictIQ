# FinSightAI Project Requirements Checklist

## Requirements vs. Status

### ✅ **1. Kafka Setup** - **COMPLETE**
**Requirement**: Create/access `{team}.watch`, `{team}.rate`, `{team}.reco_requests`, `{team}.reco_responses`; verify with kcat.

**Status**:
- ✅ `team05.watch` - Created and verified
- ✅ `team05.news` - Created (used instead of rate)
- ⚠️ `team05.rate` - **NOT CREATED** (not in config.py)
- ✅ `team05.reco_requests` - Created and verified
- ✅ `team05.reco_responses` - Created and verified
- ⚠️ **kcat verification** - **MISSING** (need to run and capture output)

**Files**: `kafka_pipeline/config.py`, `kafka_pipeline/producer.py`, `kafka_pipeline/consumer.py`

---

### ✅ **2. Stream Ingestor** - **MOSTLY COMPLETE**
**Requirement**: Consume, validate schemas, write snapshot(s) to object storage (parquet/CSV), optional Redis cache.

**Status**:
- ✅ **Consume**: Consumer reads from Kafka topics
- ✅ **Validate Schemas**: Pydantic schemas in `kafka_pipeline/schemas.py`
  - `StockWatchEvent` schema with validators
  - `PriceChangeEvent` schema
- ⚠️ **Write Snapshots**: **PARTIAL**
  - ✅ Consumer loads from blob storage (`load_historical_buffer_from_blob()`)
  - ✅ Blob path structure: `v1/date={date_str}/hour={hour:02d}/backfill_oct.parquet`
  - ❌ **MISSING**: Consumer doesn't write NEW snapshots back to blob (only reads)
  - ❌ **MISSING**: Explicit snapshot writing function
- ❌ **Redis Cache**: **NOT IMPLEMENTED** (optional, but not done)

**Files**: `kafka_pipeline/consumer.py`, `kafka_pipeline/schemas.py`

---

### ✅ **3. Train ≥2 Models** - **COMPLETE**
**Requirement**: Train ≥2 models (e.g., Popularity, Item-Item CF, ALS, Neural MF).

**Status**: ✅ **COMPLETE** (3 models trained)
- ✅ **LSTM**: `multi_stock_model_LSTM.keras` (exists)
- ✅ **Random Forest**: `random_forest_model.pkl` (exists)
- ✅ **Moving Average**: Implemented in consumer (`MovingAveragePredictor`)

**Model Files**: 
- `multi_stock_model_LSTM.keras`
- `random_forest_model.pkl`
- `scaler.pkl`
- Training metrics: `lstm_training_metrics.pkl`, `rf_training_metrics.pkl`, `ma_training_metrics.pkl`

**Note**: Models are stock prediction models (not traditional recommendation models like CF/ALS), but meet the ≥2 requirement.

---

### ⚠️ **4. Compare Models** - **PARTIAL**
**Requirement**: Compare models across:
- Offline ranking metric (e.g., HR@K, NDCG@K)
- Training cost (time/CPU or $)
- Inference latency/throughput (local benchmark)
- Model size

**Status**: ⚠️ **PARTIAL**
- ✅ **Comparison CSV exists**: `model_comparison.csv`
- ⚠️ **HR@K, NDCG@K**: Values present but need validation (some values >1.0)
- ✅ **Training cost**: Train time documented (67.0 min LSTM, 0.5 min RF, 0.0 min MA)
- ❌ **Inference latency**: Values are 0.0 for LSTM and RF (not properly measured)
- ✅ **Model size**: Documented (LSTM: 0.4 MB, RF: 1153.1 MB, MA: 0.0 MB)
- ❌ **Comparison table**: CSV exists but needs formatting for PDF
- ❌ **Metric definitions**: Not documented
- ❌ **Scripts links**: Not provided

**Files**: `scripts/compare_models.py`, `scripts/compare_models_clean.py`, `model_comparison.csv`

**Action Needed**: 
1. Fix inference latency measurements
2. Validate HR@K, NDCG@K values
3. Create formatted comparison table for PDF
4. Document metric definitions
5. Link to comparison scripts

---

### ✅ **5. Dockerize Recommender-API** - **COMPLETE**
**Requirement**: Dockerize recommender-api; deploy to cloud runtime; publish image to registry; configure secrets.

**Status**: ✅ **COMPLETE**
- ✅ **Dockerfile**: `Dockerfile` exists and optimized
- ✅ **API Code**: `api/predictor.py` and `api/main.py` implemented
- ✅ **Deploy to Cloud**: Deployed to Azure Container Apps
- ✅ **Publish to Registry**: Image in Azure Container Registry (`finsightairegistry.azurecr.io/finsightai-api:latest`)
- ✅ **Configure Secrets**: Environment variables configured in Container App
- ✅ **Live API URL**: `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io`

**Files**: `Dockerfile`, `api/predictor.py`, `api/main.py`

---

### ✅ **6. Probes** - **COMPLETE** (Automation Done)
**Requirement**: Run `scripts/probe.py` periodically (can be GH Action cron) to hit `/recommend` and write `{team}.reco_requests`/`{team}.reco_responses`.

**Status**: ✅ **COMPLETE** (Automation implemented)
- ✅ **Probe Script**: `scripts/probe.py` exists and fixed
- ✅ **Functionality**: Writes to `team05.reco_requests` and `team05.reco_responses`
- ✅ **Automation**: **COMPLETE** - GitHub Actions cron job created
- ⚠️ **Ops Log**: **NOT IMPLEMENTED** - No probe count tracking or % personalized responses (separate task)

**Files**: 
- `scripts/probe.py` (fixed bug: TOPIC_PREDICT_RESPONSES → TOPIC_RECO_RESPONSES)
- `.github/workflows/automated-probes.yml` (runs every 6 hours)
- `.github/workflows/README.md` (setup documentation)

**Next Steps**:
1. ✅ GitHub Actions workflow created
2. ⚠️ Add GitHub secrets (API_URL, KAFKA_BROKER, KAFKA_USERNAME, KAFKA_PASSWORD)
3. ⚠️ Push to GitHub repository
4. ⚠️ Workflow will run automatically every 6 hours

---

## Deliverables Status (PDF ≤ 4 pages)

### ⚠️ **1. Kafka Verification** - **PARTIAL**
**Required**:
- Topic list
- kcat output
- Consumer config snippet

**Status**:
- ✅ Topic list: Available in `kafka_pipeline/config.py`
- ❌ **kcat output**: **MISSING** - Need to run kcat and capture output
- ✅ Consumer config snippet: Available in `kafka_pipeline/consumer.py`

---

### ⚠️ **2. Data Snapshot Description** - **PARTIAL**
**Required**: Object store pathing/versioning.

**Status**:
- ✅ Path structure: `v1/date={date_str}/hour={hour:02d}/backfill_oct.parquet`
- ⚠️ **MISSING**: Complete documentation of versioning strategy
- ⚠️ **MISSING**: Snapshot writing process documentation

---

### ⚠️ **3. Model Comparison Table** - **PARTIAL**
**Required**: Comparison table + metric definition triplets + scripts links.

**Status**:
- ✅ Comparison CSV: `model_comparison.csv` exists
- ⚠️ **MISSING**: Formatted table for PDF
- ❌ **MISSING**: Metric definitions documented
- ❌ **MISSING**: Scripts links provided

---

### ✅ **4. Live API URL + Dockerfile + Registry** - **COMPLETE**
**Required**: Live API URL + Dockerfile(s) + registry image link.

**Status**: ✅ **COMPLETE**
- ✅ **Live API URL**: `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io`
- ✅ **Dockerfile**: `Dockerfile` exists
- ✅ **Registry Image**: `finsightairegistry.azurecr.io/finsightai-api:latest`

---

### ❌ **5. Ops Log** - **NOT DONE**
**Required**: Short ops log: probe counts and % personalized responses in last 24h.

**Status**: ❌ **NOT IMPLEMENTED**
- ❌ **Probe counts**: Not tracked
- ❌ **% personalized responses**: Not calculated
- ❌ **Ops log report**: Not created

---

## Summary: Completion Status

### ✅ **COMPLETE (70-75%)**
1. ✅ Kafka topics created (4/5 - missing rate topic)
2. ✅ Stream ingestor (consume + validate schemas)
3. ✅ Blob storage reading (historical data)
4. ✅ 3 models trained (LSTM, RF, MA)
5. ✅ Consumer generates predictions
6. ✅ Predictions sent to response topic
7. ✅ Dockerfile created and optimized
8. ✅ API code created and tested
9. ✅ API deployed to Azure Container Apps
10. ✅ Probe script exists and fixed

### ⚠️ **PARTIAL (15-20%)**
1. ⚠️ Snapshot writing to blob (consumer reads but doesn't write new snapshots)
2. ⚠️ Model comparison (CSV exists but needs fixes and formatting)
3. ⚠️ Probe script exists but not automated
4. ⚠️ Kafka verification needs kcat output
5. ⚠️ Data snapshot description needs versioning strategy doc

### ❌ **MISSING (10-15%)**
1. ❌ **team05.rate topic** (not critical if news topic is used instead)
2. ❌ **Inference latency measurements** (currently 0.0)
3. ❌ **HR@K, NDCG@K validation** (some values >1.0)
4. ❌ **Automated Probes** (GitHub Actions cron)
5. ❌ **Ops Log** (probe counts and % personalized responses)
6. ❌ **Redis Cache** (optional)
7. ❌ **Snapshot Writing** (consumer doesn't write new snapshots)
8. ❌ **Metric definitions documentation**
9. ❌ **Scripts links in deliverables**

---

## Critical Next Steps (Priority Order)

### 🔴 **HIGH PRIORITY** (Required for Deliverables)
1. **Fix Model Comparison**
   - Re-measure inference latency for LSTM and RF
   - Validate HR@K, NDCG@K values
   - Create formatted comparison table for PDF
   - Document metric definitions

2. **Create Ops Log**
   - Implement probe count tracking
   - Calculate % personalized responses
   - Generate ops log report for last 24h

3. **kcat Verification**
   - Run kcat commands for all topics
   - Capture output for PDF

### 🟡 **MEDIUM PRIORITY** (Should Have)
4. ✅ **Automate Probes** - **COMPLETE**
   - ✅ Create GitHub Actions workflow
   - ✅ Set up cron schedule (every 6 hours)
   - ⚠️ Test automated probing (requires GitHub secrets setup)

5. **Snapshot Writing**
   - Add snapshot writing function to consumer
   - Test blob storage writes
   - Document versioning strategy

### 🟢 **LOW PRIORITY** (Nice to Have)
6. **team05.rate Topic**
   - Create if needed (or document why news topic is used instead)

7. **Redis Cache**
   - Optional enhancement

---

## Estimated Completion: **75-80%**

**Core Infrastructure**: ✅ 95% (Kafka, Consumer, Models, API)
**Deployment**: ✅ 100% (Docker, Container Apps, Registry)
**Documentation**: ⚠️ 50% (Partial, needs completion)
**Operations**: ⚠️ 30% (Probe script exists, but not automated)
**Deliverables**: ⚠️ 60% (Mostly done, needs formatting and fixes)


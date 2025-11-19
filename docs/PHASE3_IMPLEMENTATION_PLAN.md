# Phase 3: Availability & MLOps - Implementation Plan

## Overview

**Goals**: Live monitoring; scheduled retraining; safe model switches; online A/B; full traceability

**Availability Requirement**: ≥70% available during 72h before + 144h after submission (216h total)

**Model Updates**: ≥2 model updates within a 7-day window

---

## Tasks Breakdown

### 1. Containerization ✅ (Partially Complete)
**Status**: Basic Dockerfile exists, needs multi-stage optimization

**Current**:
- Single-stage Dockerfile
- Large image size (includes all dependencies)

**Required**:
- Multi-stage Dockerfile (builder + runtime)
- Small production image
- Optimized layer caching

**Action Items**:
- [ ] Create multi-stage Dockerfile
- [ ] Separate build dependencies from runtime
- [ ] Optimize image size (target <500MB if possible)
- [ ] Test build and push to ACR

---

### 2. Automated Retraining
**Status**: Not started

**Components Needed**:

#### A. Scheduler
- GitHub Actions cron job (already have probes, add retraining)
- Run daily or every 12 hours

#### B. Model Registry
- Structure: `model_registry/v{major}.{minor}/`
  - `model.keras` or `model.pkl`
  - `metadata.json` (timestamp, metrics, git_sha, etc.)
- Storage: Azure Blob Storage (already configured)

#### C. Hot-Swap Mechanism
- Option 1: `/switch?model=v1.2` endpoint
- Option 2: Environment variable + rolling deploy
- Option 3: Config file reload

**Action Items**:
- [ ] Create retraining script (`scripts/retrain_models.py`)
- [ ] Create model registry structure in blob storage
- [ ] Implement version management
- [ ] Add hot-swap endpoint to API
- [ ] Create GitHub Actions retraining workflow
- [ ] Test end-to-end retraining flow

---

### 3. Monitoring
**Status**: Not started

**Components Needed**:

#### A. Metrics Endpoint
- `/metrics` endpoint (Prometheus format)
- Metrics to export:
  - `http_requests_total{method, status}`
  - `http_request_duration_seconds{quantile="0.95"}`
  - `model_predictions_total{model, status}`
  - `model_errors_total{model, error_type}`
  - `api_uptime_seconds`

#### B. Grafana Dashboard
- Use Azure Monitor / Prometheus
- Visualizations:
  - P95 latency timeseries
  - Error rate (%)
  - Uptime (%)
  - Request rate
  - Model performance

#### C. Alerts
- P95 latency > 1000ms
- Error rate > 5%
- Uptime < 95%

#### D. Runbook
- Alert response procedures
- Escalation paths
- Common issues & fixes

**Action Items**:
- [ ] Add `/metrics` endpoint to FastAPI
- [ ] Integrate Prometheus client
- [ ] Set up metrics collection
- [ ] Create Grafana dashboard
- [ ] Configure alert rules
- [ ] Write runbook document

---

### 4. A/B Testing
**Status**: Not started

**Design**:
- Split logic: `user_id % 2` (50/50 split)
- Model A: LSTM (control)
- Model B: Random Forest (variant)
- Metrics: Prediction accuracy, latency, error rate

**Statistical Test**:
- Two-proportion z-test for success rates
- Bootstrap confidence intervals
- Significance level: α = 0.05

**Action Items**:
- [ ] Add A/B split logic to API
- [ ] Log model variant per request
- [ ] Collect metrics for each variant
- [ ] Implement statistical tests
- [ ] Create analysis script
- [ ] Generate A/B report with visualization

---

### 5. Provenance Tracking
**Status**: Not started

**Required Fields per Prediction**:
- `request_id`: Unique identifier
- `model_version`: e.g., "v1.2"
- `data_snapshot_id`: Blob storage snapshot ID
- `pipeline_git_sha`: Git commit SHA
- `container_image_digest`: Docker image hash
- `timestamp`: Request time
- `user_id`: User identifier
- `input_symbols`: Input data
- `predictions`: Output predictions
- `latency_ms`: Processing time

**Storage**:
- Kafka topic: `team05.provenance`
- Format: JSON with all fields
- Retention: 7 days minimum

**Action Items**:
- [ ] Add provenance logging to API
- [ ] Capture all required fields
- [ ] Log to Kafka
- [ ] Create trace viewer script
- [ ] Generate example trace
- [ ] Document provenance format

---

### 6. Availability Tracking
**Status**: Partially done (health endpoint exists)

**Metrics Needed**:
- Total uptime (seconds)
- Total downtime (seconds)
- Availability % = (uptime / (uptime + downtime)) * 100

**Monitoring Window**:
- 72h before submission
- 144h after submission
- Total: 216 hours

**Action Items**:
- [ ] Set up uptime monitoring (Azure Monitor or external)
- [ ] Log all health check results
- [ ] Calculate availability percentage
- [ ] Document any downtime incidents
- [ ] Generate availability report

---

## Implementation Schedule

### Phase 3A: Core Infrastructure (2-3 hours)
1. Multi-stage Dockerfile
2. Metrics endpoint
3. Provenance logging

### Phase 3B: Automation (2-3 hours)
4. Automated retraining
5. Model registry
6. Hot-swap mechanism

### Phase 3C: Monitoring & Testing (2-3 hours)
7. Grafana dashboard
8. Alert rules
9. A/B testing implementation

### Phase 3D: Documentation (1-2 hours)
10. Availability calculation
11. Provenance traces
12. A/B results
13. Final PDF deliverable

**Total Estimated Time**: 7-11 hours

---

## Deliverables Checklist

### PDF Document (≤ 4 pages)

#### Page 1: Docker & Deploy
- [ ] Multi-stage Dockerfile explanation
- [ ] Image size comparison
- [ ] Deployment process outline
- [ ] Links to Docker files and workflows

#### Page 2: Automated Retraining
- [ ] Scheduler configuration
- [ ] Model registry structure
- [ ] Evidence of ≥2 model updates
- [ ] Hot-swap mechanism explanation

#### Page 3: Monitoring & A/B Testing
- [ ] Monitoring screenshot (Grafana dashboard)
- [ ] Alert rules configuration
- [ ] Dashboard link
- [ ] A/B design explanation
- [ ] Statistical test results
- [ ] KPI timeseries screenshot

#### Page 4: Provenance & Availability
- [ ] Provenance format explanation
- [ ] Concrete trace example
- [ ] Availability calculation
- [ ] Uptime evidence

---

## Success Criteria

✅ API availability ≥70% over 216-hour window  
✅ At least 2 model updates with evidence  
✅ /metrics endpoint working  
✅ Grafana dashboard deployed  
✅ Alert rules configured  
✅ A/B test with statistical significance  
✅ Full provenance traces available  
✅ Multi-stage Docker with small images  
✅ All deliverables in PDF ≤4 pages  

---

## Next Steps

1. Start with multi-stage Dockerfile (quick win)
2. Add /metrics endpoint (foundation for monitoring)
3. Implement provenance logging (trace everything)
4. Set up automated retraining
5. Create Grafana dashboard
6. Implement A/B testing
7. Calculate availability
8. Generate deliverables PDF

**Let's begin!**

# 1-Day Implementation Plan: All 3 Phases

## Overview
Complete implementation plan for Phase 1 (Probing), Phase 2 (Robust Pipeline), and Phase 3 (Availability & MLOps).

**Timeline**: 8-10 hours
**Priority**: Critical deliverables first

---

## âœ… Phase 1: Probing Using GitHub (COMPLETE)

**Status**: âœ… Already implemented
- scripts/probe.py exists
- .github/workflows/automated-probes.yml exists
- Probes write to 	eam05.reco_requests and 	eam05.reco_responses

**Action**: Verify probes are generating records

---

## Phase 2: Robust Modular Pipeline (4-5 hours)

### Task 1: Online Evaluation - KPI Computation (1 hour)
**File**: scripts/online_eval.py
- Read from 	eam05.reco_responses Kafka topic
- Define proxy success: status == 'success' AND num_predictions > 0
- Compute KPIs:
  - Proxy success rate
  - P50/P95/P99 latency
  - Error rate
  - Total probes
- Export results to JSON/CSV

**Deliverable**: Online metric spec & results from 	eam05.reco_responses

---

### Task 2: Offline Evaluation - Enhance Existing (30 min)
**File**: scripts/compare_models.py (enhance)
- âœ… Chronological split: Already done (	rain_test_split_by_time)
- âœ… Ranking metrics: Already done (HR@K, NDCG@K)
- Add: Subpopulation analysis by symbol
- Add: Leakage prevention documentation

**Deliverable**: Offline evaluation spec & results + code links

---

### Task 3: Modular Pipeline Structure (1.5 hours)
**Create**: pipeline/ directory structure
`
pipeline/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ config.py          # Environment-based config
â”œâ”€â”€ ingest.py          # Wrapper for producer
â”œâ”€â”€ transform.py        # Wrapper for feature_engineering
â”œâ”€â”€ train.py           # Wrapper for train_all_models
â”œâ”€â”€ serialize.py       # Model serialization
â”œâ”€â”€ serve.py           # API serving
â”œâ”€â”€ eval.py            # Offline + online evaluation
â””â”€â”€ drift_detector.py  # Drift detection
`

**Deliverable**: Clear module structure (ingest â†’ transform â†’ train â†’ serialize â†’ serve â†’ eval)

---

### Task 4: Quality Gates (1.5 hours)

**4a. Unit Tests** (30 min)
- 	ests/test_pipeline.py - Pipeline module tests
- 	ests/test_schemas.py - Schema validation tests
- 	ests/test_eval.py - Evaluation tests
- Target: â‰¥70% coverage for non-ML code

**4b. Schema Validation** (30 min)
- âœ… Pydantic schemas exist (kafka_pipeline/schemas.py)
- Add: Pandera validation (optional enhancement)
- Document: Schema validation approach

**4c. Drift Detection** (30 min)
- pipeline/drift_detector.py
- Kolmogorov-Smirnov test for distribution drift
- Detect drift on stock price distributions
- Generate drift chart/table

**4d. Backpressure Handling** (30 min)
- Monitor consumer lag
- Rate limiting in consumer
- Queue size monitoring
- Error handling for overload

**Deliverable**: 
- Test report (coverage screenshot)
- Data quality: schemas, drift checks, drift chart

---

### Task 5: CI/CD Workflow (1 hour)
**File**: .github/workflows/ci-cd.yml
- Run tests/lint/coverage (â‰¥70% threshold)
- Build Docker image
- Push to Azure Container Registry
- Deploy to Azure Container Apps
- Block deployment on test failures

**Deliverable**: CI/CD workflow files + link to successful runs + secrets strategy

---

## Phase 3: Availability & MLOps (3-4 hours)

### Task 1: Multi-Stage Dockerfile (30 min)
**File**: Dockerfile.multistage
- Stage 1: Builder (install dependencies)
- Stage 2: Runtime (copy from builder)
- Smaller image size
- Models loaded from blob storage at runtime

**Deliverable**: Final multi-stage Dockerfile

---

### Task 2: Monitoring Endpoint (1 hour)
**File**: pi/main.py (enhance)
- Add /metrics endpoint (Prometheus format)
- Track: p95 latency, error rate, uptime
- Export metrics: equest_count, equest_latency, error_count
- Add prometheus-client to requirements.txt

**Deliverable**: /metrics endpoint + monitoring setup

---

### Task 3: Automated Retraining (1 hour)
**File**: .github/workflows/retrain-models.yml
- Schedule: Weekly cron (after Oct 31st)
- Train models using scripts/train_all_models.py
- Register models to blob storage: model_registry/vX.Y/
- Store metadata: version, git_sha, training_date
- Trigger hot-swap via API endpoint or env var update

**Deliverable**: Scheduler/job configuration + evidence of â‰¥2 model updates

---

### Task 4: Hot-Swap Mechanism (30 min)
**File**: pi/main.py (add endpoint)
- Add /admin/reload-models?version=X.Y endpoint
- Load models from blob storage registry
- Reload without restarting API
- Update MODEL_VERSION env var

**Deliverable**: Hot-swap implementation

---

### Task 5: A/B Testing (1 hour)
**File**: pi/main.py (enhance /recommend)
- Split: user_id % 2 â†’ Group A (LSTM) vs Group B (RandomForest)
- Log A/B assignment to Kafka
- Track performance per group

**File**: scripts/ab_test_analysis.py
- Two-proportion z-test
- Bootstrap confidence intervals
- Show decision (which group performs better)

**Deliverable**: A/B design + statistical test + results + screenshot

---

### Task 6: Provenance Tracking (30 min)
**File**: pi/main.py (enhance response)
- Add to each prediction:
  - equest_id (UUID)
  - model_version (from env)
  - data_snapshot_id (date-based)
  - pipeline_git_sha (from git)
  - container_image_digest (from env)
- Log provenance to Kafka
- Show trace example

**Deliverable**: Provenance explanation + concrete trace example

---

### Task 7: Availability Monitoring (30 min)
**File**: scripts/availability_monitor.py
- Continuous health check monitoring
- Calculate availability % over 72h/144h windows
- Track uptime
- Alert on <70% availability

**Deliverable**: Availability calculation over required window

---

## File Creation Checklist

### Phase 2 Files:
- [ ] scripts/online_eval.py
- [ ] pipeline/__init__.py
- [ ] pipeline/config.py
- [ ] pipeline/ingest.py
- [ ] pipeline/transform.py
- [ ] pipeline/train.py
- [ ] pipeline/serialize.py
- [ ] pipeline/serve.py
- [ ] pipeline/eval.py
- [ ] pipeline/drift_detector.py
- [ ] 	ests/test_pipeline.py
- [ ] 	ests/test_schemas.py
- [ ] 	ests/test_eval.py
- [ ] .github/workflows/ci-cd.yml

### Phase 3 Files:
- [ ] Dockerfile.multistage
- [ ] .github/workflows/retrain-models.yml
- [ ] scripts/ab_test_analysis.py
- [ ] scripts/availability_monitor.py
- [ ] pi/model_registry.py (for model versioning)

### Enhancements:
- [ ] pi/main.py - Add /metrics, A/B testing, provenance
- [ ] scripts/compare_models.py - Add subpopulation analysis
- [ ] equirements.txt - Add prometheus-client

---

## Deliverables Summary (PDF â‰¤ 4 pages)

### Page 1: Offline Evaluation
- Spec: Chronological split, ranking metrics, subpopulation analysis
- Results: Model comparison table
- Code links: scripts/compare_models.py

### Page 2: Online Evaluation
- Spec: Proxy success definition, KPI computation
- Results: KPIs from 	eam05.reco_responses
- Code links: scripts/online_eval.py

### Page 3: Data Quality & CI/CD
- Schemas: Pydantic validation approach
- Drift checks: Drift detection results + chart
- CI/CD: Workflow files + successful run link
- Test report: Coverage screenshot (â‰¥70%)

### Page 4: MLOps & Availability
- Model updates: â‰¥2 updates in 7-day window
- Monitoring: /metrics endpoint + Grafana setup
- A/B testing: Design + results + decision
- Provenance: Trace example
- Availability: â‰¥70% over 72h before + 144h after

---

## Execution Order (Priority)

1. **Hour 1**: Online evaluation (scripts/online_eval.py)
2. **Hour 2**: Modular structure (pipeline/ directory)
3. **Hour 3**: Quality gates (tests + drift detection)
4. **Hour 4**: CI/CD workflow
5. **Hour 5**: Multi-stage Dockerfile + monitoring endpoint
6. **Hour 6**: Automated retraining + hot-swap
7. **Hour 7**: A/B testing + provenance
8. **Hour 8**: Availability monitoring + documentation

---

## Quick Start Commands

`ash
# 1. Generate probe records (if needed)
python scripts/probe.py  # Run multiple times

# 2. Test online evaluation
python scripts/online_eval.py

# 3. Run offline evaluation
python scripts/compare_models.py

# 4. Run tests
pytest tests/ --cov=pipeline --cov-report=term-missing

# 5. Check drift
python -c "from pipeline.drift_detector import detect_distribution_drift; ..."

# 6. Test A/B
python scripts/ab_test_analysis.py

# 7. Monitor availability
python scripts/availability_monitor.py
`

---

## Critical Success Factors

1. âœ… **Probe records exist** - Verify Kafka topics have data
2. âœ… **Online KPIs computed** - Must have results from 	eam05.reco_responses
3. âœ… **Tests pass** - â‰¥70% coverage for non-ML code
4. âœ… **CI/CD works** - Workflow runs successfully
5. âœ… **Monitoring works** - /metrics endpoint accessible
6. âœ… **A/B test results** - Statistical analysis complete
7. âœ… **Provenance logged** - Trace example available
8. âœ… **Availability â‰¥70%** - Monitor and document

---

## Notes

- **Data simulation**: Use Oct 1-31 data shifted forward for post-Oct-31 testing
- **Model updates**: Schedule retraining after Oct 31st (cron:   2 * * 0 = Sundays 2 AM UTC)
- **Secrets**: Document GitHub secrets strategy (API_URL, KAFKA_BROKER, etc.)
- **Documentation**: Keep code comments clear, add docstrings

---

**Total Estimated Time**: 8-10 hours
**Critical Path**: Online eval â†’ Tests â†’ CI/CD â†’ Monitoring â†’ A/B â†’ Provenance

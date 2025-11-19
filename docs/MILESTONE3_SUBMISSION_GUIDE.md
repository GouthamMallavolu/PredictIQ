# Milestone 3 Submission Guide
**Complete checklist for screenshots and evidence**

## Required Deliverables Checklist

### 1. Docker & Deploy Outline (15 pts)
**Screenshots Needed:**
- [ ] Multi-stage Dockerfile (show both stages)
- [ ] Docker image size comparison (before/after optimization)
- [ ] Azure Container App deployment configuration
- [ ] GitHub Actions CI/CD workflow runs

**Where to Find:**
- Dockerfile: `Dockerfile` (root directory)
- GitHub Actions: https://github.com/[YOUR_REPO]/actions/workflows/ci-cd.yml
- Azure Portal: https://portal.azure.com → Container Apps → finsightai-api → Deployment

**Scripts to Run:**
```bash
# Generate Docker image info
docker images finsightai-api --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

---

### 2. Automated Retraining + Hot-Swap (25 pts)
**Screenshots Needed:**
- [ ] GitHub Actions retraining workflow (≥2 successful runs)
- [ ] Model registry structure (`model_registry/vX.Y/`)
- [ ] Retraining history log entries
- [ ] Hot-swap endpoint or environment variable configuration

**Where to Find:**
- GitHub Actions: https://github.com/[YOUR_REPO]/actions/workflows/automated-retraining.yml
- Model Registry: `model_registry/` directory
- Retraining Log: `logs/retraining_history.jsonl`

**Scripts to Run:**
```bash
# Generate retraining evidence report
python scripts/generate_retraining_evidence.py
```

---

### 3. Monitoring (25 pts)
**Screenshots Needed:**
- [ ] `/metrics` endpoint output (Prometheus format)
- [ ] Grafana dashboard (or equivalent)
- [ ] Alert rules configuration
- [ ] p95 latency, error rate, uptime metrics

**Where to Find:**
- Metrics Endpoint: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/metrics
- Health Endpoint: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health
- Grafana: [Your Grafana URL] (if configured)

**Scripts to Run:**
```bash
# Generate monitoring report
python scripts/generate_monitoring_report.py
```

---

### 4. A/B Testing (25 pts)
**Screenshots Needed:**
- [ ] A/B test design document
- [ ] Statistical test results (two-proportion z-test or bootstrap)
- [ ] KPI timeseries or report screenshot
- [ ] Decision/recommendation

**Where to Find:**
- A/B Metrics: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/ab-test-metrics
- Analysis Script: `python scripts/analyze_ab_test.py`
- Results Log: `logs/ab_test_results.jsonl`

**Scripts to Run:**
```bash
# Generate A/B test report
python scripts/generate_ab_report.py
```

---

### 5. Provenance (10 pts)
**Screenshots Needed:**
- [ ] Provenance trace example (JSON)
- [ ] Explanation of trace fields
- [ ] Kafka topic or log file showing traces

**Where to Find:**
- Provenance Logs: `logs/provenance_*.jsonl` or Kafka topic `team05.provenance`
- API Code: `api/provenance.py`

**Scripts to Run:**
```bash
# Generate provenance trace example
python scripts/generate_provenance_example.py
```

---

### 6. Availability (10 pts)
**Screenshots Needed:**
- [ ] Availability calculation (≥70% over 72h before + 144h after)
- [ ] Uptime metrics from monitoring
- [ ] Health check logs

**Where to Find:**
- Uptime Metric: `api_uptime_seconds` from `/metrics`
- Health Logs: Container App logs or UptimeRobot (if configured)

**Scripts to Run:**
```bash
# Calculate availability
python scripts/calculate_availability.py
```

---

## Quick Screenshot Checklist

### GitHub Actions Screenshots
1. Go to: https://github.com/[YOUR_REPO]/actions
2. Screenshot: Workflow runs showing:
   - CI/CD pipeline (ci-cd.yml) - at least 1 successful run
   - Automated retraining (automated-retraining.yml) - at least 2 successful runs
   - Automated probes (automated-probes.yml) - multiple runs

### Azure Portal Screenshots
1. Go to: https://portal.azure.com
2. Navigate to: Resource Groups → [Your RG] → Container Apps → finsightai-api
3. Screenshot:
   - Overview page (showing uptime/status)
   - Revisions (showing deployments)
   - Logs (showing health checks)

### API Endpoint Screenshots
1. Metrics: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/metrics
2. Health: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health
3. A/B Metrics: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/ab-test-metrics

### Local Files Screenshots
1. Model Registry: `model_registry/v1.2/` directory structure
2. Retraining History: `logs/retraining_history.jsonl` (last 2 entries)
3. A/B Test Results: `logs/ab_test_results.jsonl` (if exists)
4. Provenance Traces: `logs/provenance_*.jsonl` (sample trace)

---

## Next Steps
1. Run all generation scripts (below)
2. Take screenshots using browser dev tools or Azure Portal
3. Compile into PDF (≤4 pages)
4. Include links to GitHub Actions runs and Azure resources


# Milestone 3 Screenshot Guide
**Where to take screenshots from deployed infrastructure**

## 1. Docker & Deploy (15 pts)

### Screenshot 1: Multi-stage Dockerfile
- **Location:** Local file OR GitHub Repository
- **Local Path:** `Dockerfile` (root directory)
- **GitHub URL:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/Dockerfile`
- **What to show:** Both stages (builder and runtime) clearly visible

**Exact Lines to Highlight:**

**Stage 1: Builder (Lines 6-28)**
```dockerfile
# ============================================================================= 
# Stage 1: Builder
# ============================================================================= 
FROM python:3.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
```

**Stage 2: Runtime (Lines 30-58)**
```dockerfile
# ============================================================================= 
# Stage 2: Runtime
# ============================================================================= 
FROM python:3.10-slim

WORKDIR /app

# Install only runtime dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (changes more frequently, so copy after dependencies)   
COPY api/ ./api/
COPY models/ ./models/
COPY scripts/ ./scripts/
COPY pipeline/ ./pipeline/
COPY kafka_pipeline/config.py ./kafka_pipeline/
COPY kafka_pipeline/schemas.py ./kafka_pipeline/
COPY evaluation/ ./evaluation/
COPY quality/ ./quality/

# Create directories for logs and cache
RUN mkdir -p logs cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check (managed by Azure Container Apps, but useful for local testing)  
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \       
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Points to Highlight:**
- Line 8: `FROM python:3.10-slim as builder` - Stage 1 declaration
- Line 30: `FROM python:3.10-slim` - Stage 2 declaration (fresh base)
- Line 55: `COPY --from=builder /opt/venv /opt/venv` - Copying from Stage 1 (multi-stage optimization)

### Screenshot 2: GitHub Actions CI/CD Workflow Run
- **Location:** GitHub Actions
- **URL:** `https://github.com/[YOUR_REPO]/actions/workflows/ci-cd.yml`
- **What to show:** 
  - Successful workflow run
  - Build step showing Docker image build
  - Deploy step showing Azure Container App deployment

### Screenshot 3: Azure Container App Deployment
- **Location:** Azure Portal
- **URL:** `https://portal.azure.com` → Your Resource Group → Container Apps → `finsightai-api` → Revisions
- **What to show:**
  - Active revision
  - Image details (showing multi-stage build result)
  - Deployment history

---

## 2. Automated Retraining (25 pts)

### Screenshot 1: GitHub Actions Retraining Workflow (≥2 runs)
- **Location:** GitHub Actions
- **URL:** `https://github.com/[YOUR_REPO]/actions/workflows/automated-retraining.yml`
- **What to show:**
  - At least 2 successful workflow runs
  - Workflow run details showing:
    - Scheduled trigger (cron) OR manual trigger
    - Model version increment
    - Artifact uploads

### Screenshot 2: Model Registry Structure
- **Location:** GitHub Repository (or Azure Blob Storage if configured)
- **URL:** `https://github.com/[YOUR_REPO]/tree/[BRANCH]/model_registry`
- **What to show:**
  - At least 2 version folders (e.g., `v1.1/`, `v1.2/`)
  - Each folder containing: model files + metadata.json

### Screenshot 3: Retraining History Log
- **Location:** GitHub Repository
- **URL:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/logs/retraining_history.jsonl`
- **What to show:**
  - Last 2-3 entries showing successful retraining
  - Timestamps and version numbers

### Screenshot 4: Hot-Swap Configuration
- **Location:** Azure Portal OR GitHub Actions workflow
- **Option A (Azure):** Container App → Configuration → Environment Variables
- **Option B (GitHub):** `.github/workflows/ci-cd.yml` showing MODEL_VERSION env var
- **What to show:** Environment variable for model version selection

---

## 3. Monitoring (25 pts)

### Screenshot 1: Prometheus Metrics Endpoint
- **Location:** Browser (API endpoint)
- **URL:** `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/metrics`
- **What to show:**
  - Full `/metrics` endpoint output
  - Highlight these metrics:
    - `http_requests_total`
    - `http_request_duration_seconds` (with p95 quantile)
    - `api_uptime_seconds`
    - `api_health_status`
    - `model_predictions_total`

### Screenshot 2: Health Endpoint
- **Location:** Browser (API endpoint)
- **URL:** `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health`
- **What to show:** JSON response showing status, uptime, models_ready

### Screenshot 3: Grafana Dashboard (if configured)
- **Location:** Grafana (if you set it up)
- **What to show:**
  - Dashboard with metrics from `/metrics` endpoint
  - Panels showing: p95 latency, error rate, uptime

### Screenshot 4: Alert Rules
- **Location:** Grafana OR Prometheus config
- **What to show:** Alert rule definitions (see `docs/MONITORING_SETUP.md`)

---

## 4. A/B Testing (25 pts)

### Screenshot 1: A/B Test Design (Code)
- **Location:** GitHub Repository
- **URL:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/api/ab_testing.py`
- **What to show:**
  - `get_ab_variant()` function showing 50/50 split logic
  - Assignment based on user_id hash

### Screenshot 2: A/B Metrics Endpoint
- **Location:** Browser (API endpoint)
- **URL:** `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/ab-test-metrics`
- **What to show:** JSON response with A/B test metrics

### Screenshot 3: Statistical Analysis Results
- **Location:** Run script and screenshot output
- **Command:** `python scripts/analyze_ab_test.py`
- **What to show:**
  - Two-proportion z-test results
  - Bootstrap confidence intervals
  - Recommendation/decision

### Screenshot 4: A/B Test Results Log (if available)
- **Location:** GitHub Repository
- **URL:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/logs/ab_test_results.jsonl`
- **What to show:** Sample entries showing variant assignments

---

## 5. Provenance (10 pts)

### Screenshot 1: Provenance Code Implementation
- **Location:** GitHub Repository
- **URL:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/api/provenance.py`
- **What to show:**
  - `log_provenance()` function
  - Fields: request_id, model_version, pipeline_git_sha, container_image_digest, data_snapshot_id

### Screenshot 2: Example Provenance Trace
- **Location:** Browser (API response) OR Log file
- **Option A:** Send a test request, check response logs
- **Option B:** `https://github.com/[YOUR_REPO]/blob/[BRANCH]/logs/provenance_*.jsonl`
- **What to show:**
  - Complete JSON trace with all required fields
  - Highlight: request_id, model_version, git_sha, container_digest

---

## 6. Availability (10 pts)

### Screenshot 1: Uptime Calculation
- **Location:** Calculate from metrics
- **Method:** Use `api_uptime_seconds` from `/metrics` endpoint
- **Formula:** `(uptime_seconds / total_window_seconds) * 100`
- **Window:** 72h before + 144h after submission = 216h total
- **Requirement:** ≥70% availability

### Screenshot 2: Health Check Logs
- **Location:** Azure Portal
- **URL:** `https://portal.azure.com` → Container Apps → `finsightai-api` → Logs
- **What to show:**
  - Health check logs over the required window
  - Uptime percentage calculation

### Screenshot 3: Monitoring Dashboard (if available)
- **Location:** Grafana OR Azure Monitor
- **What to show:** Uptime graph over the required time window

---

## Quick Checklist

### GitHub Actions Screenshots Needed:
- [ ] CI/CD workflow run (ci-cd.yml)
- [ ] Retraining workflow runs (≥2) (automated-retraining.yml)
- [ ] Workflow showing scheduled triggers

### Azure Portal Screenshots Needed:
- [ ] Container App overview (showing status/uptime)
- [ ] Revisions page (showing deployments)
- [ ] Configuration page (showing environment variables)

### API Endpoint Screenshots Needed:
- [ ] `/metrics` endpoint (full output)
- [ ] `/health` endpoint (JSON response)
- [ ] `/ab-test-metrics` endpoint (JSON response)

### Code Repository Screenshots Needed:
- [ ] Dockerfile (multi-stage)
- [ ] `api/ab_testing.py` (A/B split logic)
- [ ] `api/provenance.py` (provenance logging)
- [ ] Model registry structure (≥2 versions)

---

## Tips for Screenshots

1. **Use browser zoom:** Set to 80-90% to fit more content
2. **Full-page screenshots:** Use browser extensions or dev tools
3. **Annotate:** Add arrows/text to highlight key parts
4. **Combine related screenshots:** Use image editing to combine multiple views
5. **Include timestamps:** Show when screenshots were taken

---

## Direct Links (Replace [YOUR_REPO] and [BRANCH])

- **GitHub Actions:** `https://github.com/[YOUR_REPO]/actions`
- **CI/CD Workflow:** `https://github.com/[YOUR_REPO]/actions/workflows/ci-cd.yml`
- **Retraining Workflow:** `https://github.com/[YOUR_REPO]/actions/workflows/automated-retraining.yml`
- **API Metrics:** `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/metrics`
- **API Health:** `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health`
- **Azure Portal:** `https://portal.azure.com`


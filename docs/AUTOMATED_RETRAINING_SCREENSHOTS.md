# Automated Retraining Screenshots Guide

**Section**: Automated retraining: schedule + publish model_registry/vX.Y + hot-swap  
**Points**: 25  
**Requirement**: ≥2 model updates within 7 days

---

## ✅ What You Have

1. **GitHub Actions Workflow**: `.github/workflows/automated-retraining.yml`
   - Scheduled: 2x daily (2 AM and 2 PM UTC)
   - Manual trigger: `workflow_dispatch`
   
2. **Model Registry**: `model_registry/`
   - v1.0 ✅
   - v1.1 ✅
   - v1.2 ✅ (≥2 updates ✓)

3. **Retraining History**: `logs/retraining_history.jsonl`
   - 3 successful retraining entries

---

## 📸 Screenshots Needed

### Screenshot 1: GitHub Actions Retraining Workflow Configuration

**Location**: GitHub Repository  
**URL**: `https://github.com/GouthamMallavolu/PredictIQ/blob/main/.github/workflows/automated-retraining.yml`

**What to Capture**:
- Show the workflow file with cron schedule visible:
  ```yaml
  schedule:
    - cron: '0 2 * * *'   # 2 AM UTC daily
    - cron: '0 14 * * *'  # 2 PM UTC daily
  workflow_dispatch:  # Allow manual trigger
  ```
- Highlight the schedule configuration
- Show the retraining script call

---

### Screenshot 2: GitHub Actions Retraining Workflow Runs (≥2)

**Location**: GitHub Actions  
**URL**: `https://github.com/GouthamMallavolu/PredictIQ/actions/workflows/automated-retraining.yml`

**What to Capture**:
- Show at least 2 successful workflow runs
- Show timestamps (should be within 7 days)
- Show green checkmarks (✅)
- Show "Automated Model Retraining" workflow name

**Click into a workflow run** to show:
- Workflow trigger (scheduled/manual)
- "Run retraining script" step (success)
- "Upload model artifacts" step (success)
- Artifact name: `retrained-models-{run_id}`

---

### Screenshot 3: Model Registry Structure

**Location**: GitHub Repository  
**URL**: `https://github.com/GouthamMallavolu/PredictIQ/tree/main/model_registry`

**What to Capture**:
- Show folder structure with at least 2 version folders (v1.0, v1.1, v1.2)
- Show that each contains model files + metadata.json

---

### Screenshot 4: Model Registry Metadata

**Location**: GitHub Repository  
**URL**: `https://github.com/GouthamMallavolu/PredictIQ/blob/main/model_registry/v1.2/metadata.json`

**What to Capture**:
- Show metadata.json content showing version, timestamp, git_sha
- Take 2 screenshots: One for v1.1, one for v1.2

---

### Screenshot 5: Retraining History Log

**Location**: GitHub Repository  
**URL**: `https://github.com/GouthamMallavolu/PredictIQ/blob/main/logs/retraining_history.jsonl`

**What to Capture**:
- Show last 2-3 entries
- Highlight timestamps showing they're within 7 days
- Show `"success": true` for both entries

---

### Screenshot 6: Hot-Swap Implementation

**Option A: Environment Variable (Azure Portal)**
- Go to: Azure Portal → Container Apps → `finsightai-api` → Configuration
- Show `MODEL_VERSION` environment variable

**Option B: Code Implementation**
- Show `api/predictor.py` reading `MODEL_VERSION` env var

---

## 📋 Quick Checklist

- [ ] Workflow file showing cron schedule
- [ ] At least 2 successful workflow runs
- [ ] Model registry showing ≥2 versions
- [ ] Metadata.json for each version
- [ ] Retraining history log
- [ ] Hot-swap mechanism (env var or code)

---

## 🎯 Evidence Requirements

1. ✅ **Scheduler configured** (cron schedule)
2. ✅ **≥2 model updates** (you have 3!)
3. ✅ **Model registry structure** (vX.Y folders)
4. ✅ **Hot-swap mechanism** (env var or endpoint)


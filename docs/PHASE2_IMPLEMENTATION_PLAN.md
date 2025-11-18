# Phase 2: Robust Modular Pipeline - Implementation Plan

## Overview
Implement offline+online evaluation, schema & drift checks, and CI/CD pipeline.

## Step-by-Step Plan

### Step 1: Offline Evaluation ✅
- [x] Chronological split
- [x] Ranking metrics (NDCG, MAP)
- [x] Subpopulation analysis
- [ ] Avoid leakage (ensure no future data)

### Step 2: Online Evaluation ✅
- [x] Define proxy success metrics
- [x] Compute KPIs from Kafka logs
- [ ] Test with real probe data

### Step 3: Refactor Pipeline
- [ ] Create modular structure: ingest → transform → train → serialize → serve → eval
- [ ] Environment-based configuration
- [ ] Clear module boundaries

### Step 4: Quality Gates
- [ ] Unit tests (≥70% coverage for non-ML glue)
- [ ] Schema validation (Pandera)
- [ ] Drift detection (user/symbol distributions)
- [ ] Backpressure handling

### Step 5: CI/CD
- [ ] GitHub Actions: tests/lint/coverage
- [ ] Build/push images
- [ ] Deploy to Azure Container Apps
- [ ] Secrets strategy

### Step 6: Deliverables
- [ ] Offline evaluation spec & results
- [ ] Online metric spec & results
- [ ] Data quality: schemas, drift checks, charts
- [ ] CI/CD workflow files + successful runs
- [ ] Test report (coverage ≥70%)

## Implementation Order

1. **Start with Offline Evaluation** (foundation)
2. **Online Evaluation** (uses Kafka data)
3. **Pipeline Refactoring** (structure)
4. **Quality Gates** (validation)
5. **CI/CD** (automation)
6. **Documentation** (deliverables)


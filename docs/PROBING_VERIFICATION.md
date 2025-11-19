# Probing Verification Guide

## Overview

This guide helps you verify that the probing setup is working correctly before relying on it for production.

## Requirements Checklist

### 1. Kafka Topics ✅
- [ ] `team05.reco_requests` exists
- [ ] `team05.reco_responses` exists
- [ ] Topics are accessible from your environment

**Verification:**
```bash
python scripts/test_probing_setup.py
```

### 2. API Endpoint ✅
- [ ] API is deployed and accessible
- [ ] `/recommend` endpoint works
- [ ] `/health` endpoint returns 200

**Verification:**
```bash
# Test health
curl $API_URL/health

# Test recommend
curl -X POST $API_URL/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","symbols":["AAPL"],"model":"lstm"}'
```

### 3. Probe Script ✅
- [ ] `scripts/probe.py` exists
- [ ] Can write to Kafka topics
- [ ] Can call API endpoint

**Verification:**
```bash
python scripts/probe.py
```

### 4. GitHub Actions Workflow ✅
- [ ] `.github/workflows/automated-probes.yml` exists
- [ ] Secrets are configured:
  - `API_URL`
  - `KAFKA_BROKER`
  - `KAFKA_USERNAME`
  - `KAFKA_PASSWORD`
- [ ] Workflow can be triggered manually

**Verification:**
1. Go to GitHub → Actions → Automated API Probes
2. Click "Run workflow"
3. Verify it runs successfully

## Step-by-Step Verification

### Step 1: Run Test Script
```bash
python scripts/test_probing_setup.py
```

This will test:
- API endpoint accessibility
- Kafka connection
- Kafka topics existence
- Probe script functionality
- API /recommend endpoint

### Step 2: Run Single Probe
```bash
python scripts/probe.py
```

Expected output:
```
Sending probe request: probe_YYYYMMDD_HHMMSS
[OK] Request sent to team05.reco_requests
[OK] Response sent to team05.reco_responses (latency: XXXms)
```

### Step 3: Verify Probe Records
```bash
python scripts/verify_probe_records.py --hours 1
```

Expected output:
```
PROBE RECORDS SUMMARY
============================================================

Requests (team05.reco_requests):
   Total records: 1
   Sample request IDs:
     - probe_YYYYMMDD_HHMMSS

Responses (team05.reco_responses):
   Total records: 1
   Successful: 1
   Errors: 0
   Avg latency: XXXms
```

### Step 4: Test GitHub Actions Workflow
1. Go to: `https://github.com/GouthamMallavolu/PredictIQ/actions`
2. Select "Automated API Probes" workflow
3. Click "Run workflow" → "Run workflow" (manual trigger)
4. Wait for completion
5. Verify logs show successful probe

### Step 5: Simulate Historical Probes (Optional)
```bash
python scripts/simulate_probes_nov1_5.py
```

This creates probe records for Nov 1-5, 2024 during market hours.

## Troubleshooting

### API Not Accessible
- Check API is running: `curl $API_URL/health`
- Verify API_URL environment variable
- Check firewall/network settings

### Kafka Connection Failed
- Verify KAFKA_BROKER, KAFKA_USERNAME, KAFKA_PASSWORD
- Check network connectivity to Kafka broker
- Verify credentials are correct

### Topics Not Found
- Create topics manually if needed
- Verify topic names match exactly: `team05.reco_requests`, `team05.reco_responses`
- Check permissions for creating topics

### Probe Script Fails
- Check all environment variables are set
- Verify Python dependencies installed: `pip install requests kafka-python`
- Check API is responding before probe runs

### GitHub Actions Fails
- Verify all secrets are set in GitHub
- Check workflow file syntax is valid
- Review workflow logs for specific errors

## Expected Probe Flow

```
1. Probe script runs (manual or scheduled)
   ↓
2. Creates request payload
   ↓
3. Sends to team05.reco_requests (Kafka)
   ↓
4. Calls API /recommend endpoint
   ↓
5. Receives API response
   ↓
6. Sends response to team05.reco_responses (Kafka)
   ↓
7. Logs success/failure
```

## Verification Commands

```bash
# 1. Test setup
python scripts/test_probing_setup.py

# 2. Run single probe
python scripts/probe.py

# 3. Verify records
python scripts/verify_probe_records.py

# 4. Run batch probes (for testing)
python scripts/batch_probe_simulation.py --count 10

# 5. Simulate historical probes
python scripts/simulate_probes_nov1_5.py
```

## Success Criteria

✅ All test_probing_setup.py tests pass
✅ Single probe runs successfully
✅ Probe records appear in Kafka topics
✅ GitHub Actions workflow runs successfully
✅ Probe records can be verified with verify_probe_records.py

## Next Steps

Once probing is verified:
1. ✅ Probes write to Kafka topics
2. ✅ GitHub Actions runs probes automatically
3. ✅ Probe records can be analyzed for online evaluation
4. ✅ Ready for Phase 2: Online evaluation KPI computation


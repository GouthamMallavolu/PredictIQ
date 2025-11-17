# Probing Quick Start

## What is Probing?

Probing is the automated testing of your API that:
1. Sends requests to `/recommend` endpoint
2. Logs requests to `team05.reco_requests` Kafka topic
3. Logs responses to `team05.reco_responses` Kafka topic
4. Runs automatically via GitHub Actions during market hours

## Quick Verification (5 minutes)

### Step 1: Test Setup
```bash
python scripts/test_probing_setup.py
```

This verifies:
- ✅ API is accessible
- ✅ Kafka connection works
- ✅ Topics exist
- ✅ Probe script works

### Step 2: Run Single Probe
```bash
python scripts/probe.py
```

Expected: Success message with latency

### Step 3: Verify Records
```bash
python scripts/verify_probe_records.py --hours 1
```

Expected: Shows 1+ probe records

## GitHub Actions Setup

### Required Secrets
Add these in GitHub: Settings → Secrets → Actions

1. `API_URL` - Your API endpoint (e.g., `https://finsightai-api.xxx.azurecontainerapps.io`)
2. `KAFKA_BROKER` - Kafka broker address
3. `KAFKA_USERNAME` - Kafka username (usually `$ConnectionString`)
4. `KAFKA_PASSWORD` - Kafka connection string

### Workflow Schedule
The workflow runs automatically:
- **When**: During US stock market hours (9:30 AM - 4:00 PM ET)
- **Frequency**: Every hour (9 times per trading day)
- **Days**: Monday-Friday only

### Manual Trigger
You can also trigger manually:
1. Go to Actions → Automated API Probes
2. Click "Run workflow"
3. Select branch and click "Run workflow"

## Files Created

- `scripts/probe.py` - Main probe script
- `scripts/test_probing_setup.py` - Verification script
- `scripts/verify_probe_records.py` - Check probe records
- `scripts/simulate_probes_nov1_5.py` - Simulate historical probes
- `.github/workflows/automated-probes.yml` - GitHub Actions workflow

## Troubleshooting

### "API not accessible"
- Check API is running: `curl $API_URL/health`
- Verify API_URL secret is correct

### "Kafka connection failed"
- Check KAFKA_BROKER, KAFKA_USERNAME, KAFKA_PASSWORD secrets
- Verify network connectivity

### "Topics not found"
- Topics should be: `team05.reco_requests` and `team05.reco_responses`
- Create them if they don't exist

### "GitHub Actions fails"
- Check all secrets are set
- Review workflow logs for errors

## Next Steps

Once probing works:
1. ✅ Verify probe records in Kafka
2. ✅ Check GitHub Actions runs successfully
3. ✅ Move to Phase 2: Online evaluation KPI computation


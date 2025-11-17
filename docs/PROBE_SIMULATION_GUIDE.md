# Probe Simulation Guide

## Overview

This guide explains how to simulate probe records for Nov 1-5, 2024 during stock market hours, and how the GitHub Actions automated probing works.

---

## Scripts

### 1. `scripts/simulate_probes_nov1_5.py`

**Purpose**: Simulate historical probe records for Nov 1-5, 2024

**Features**:
- Generates probes for trading days only (Nov 1, 4, 5)
- Market hours: 9:30 AM - 4:00 PM ET (14:30 - 21:00 UTC)
- 1-hour gaps: 7 probes per trading day
- Total: 21 probes (3 days × 7 probes)

**Usage**:
```bash
python scripts/simulate_probes_nov1_5.py
```

**What it does**:
1. Creates probe requests to `team05.reco_requests`
2. Calls API and logs responses to `team05.reco_responses`
3. Uses historical timestamps (Nov 1-5, 2024) for simulation
4. Flags records with `simulated: true`

**Output**:
- Probe records in Kafka topics
- Console output showing progress

---

### 2. `scripts/batch_probe_simulation.py`

**Purpose**: Quick batch probes for testing

**Usage**:
```bash
# Default: 20 probes with 5-second intervals
python scripts/batch_probe_simulation.py

# Custom count and interval
python scripts/batch_probe_simulation.py --count 50 --interval 3
```

**Use cases**:
- Generate probe records quickly for testing
- Test API under load
- Generate data for online evaluation

---

### 3. `scripts/verify_probe_records.py`

**Purpose**: Verify probe records exist in Kafka

**Usage**:
```bash
# Check last 24 hours (default)
python scripts/verify_probe_records.py

# Check last 7 days
python scripts/verify_probe_records.py --hours 168
```

**Output**:
- Total request records
- Total response records
- Success/error counts
- Latency statistics
- Date range analysis

---

## GitHub Actions Automated Probing

### Workflow: `.github/workflows/automated-probes.yml`

**Schedule**: Runs during US stock market hours (Monday-Friday)
- 9:30 AM - 4:00 PM ET
- Cron schedule: Every hour during trading hours
- Total: 9 runs per trading day

**Cron Schedule** (UTC):
```
30 13 * * 1-5  # 1:30 PM UTC (9:30 AM ET) - Market open
0 14 * * 1-5   # 2:00 PM UTC (10:00 AM ET)
0 15 * * 1-5   # 3:00 PM UTC (11:00 AM ET)
0 16 * * 1-5   # 4:00 PM UTC (12:00 PM ET)
0 17 * * 1-5   # 5:00 PM UTC (1:00 PM ET)
0 18 * * 1-5   # 6:00 PM UTC (2:00 PM ET)
0 19 * * 1-5   # 7:00 PM UTC (3:00 PM ET)
0 20 * * 1-5   # 8:00 PM UTC (4:00 PM ET)
0 21 * * 1-5   # 9:00 PM UTC (5:00 PM ET) - Market close
```

**Required GitHub Secrets**:
- `API_URL` - API endpoint URL
- `KAFKA_BROKER` - Kafka broker address
- `KAFKA_USERNAME` - Kafka username
- `KAFKA_PASSWORD` - Kafka password

**Manual Trigger**: Can be triggered manually via GitHub Actions UI

---

## Simulation Details

### Market Hours Calculation

**US Stock Market Hours**: 9:30 AM - 4:00 PM ET

**UTC Conversion** (November 2024, EST = UTC-5):
- 9:30 AM ET = 14:30 UTC
- 4:00 PM ET = 21:00 UTC

**Probe Times** (UTC):
- 14:30 (9:30 AM ET) - Market open
- 15:30 (10:30 AM ET)
- 16:30 (11:30 AM ET)
- 17:30 (12:30 PM ET)
- 18:30 (1:30 PM ET)
- 19:30 (2:30 PM ET)
- 20:30 (3:30 PM ET)
- 21:00 (4:00 PM ET) - Market close (not included in hourly probes)

**Total Probes per Day**: 7 (hourly from 14:30 to 20:30 UTC)

---

## Nov 1-5, 2024 Trading Days

- **Nov 1 (Friday)**: ✅ Trading day - 7 probes
- **Nov 2 (Saturday)**: ❌ Non-trading day - Skipped
- **Nov 3 (Sunday)**: ❌ Non-trading day - Skipped
- **Nov 4 (Monday)**: ✅ Trading day - 7 probes
- **Nov 5 (Tuesday)**: ✅ Trading day - 7 probes

**Total Simulated Probes**: 21 (3 trading days × 7 probes)

---

## Quick Start

### Step 1: Simulate Historical Probes
```bash
python scripts/simulate_probes_nov1_5.py
```

### Step 2: Verify Records
```bash
python scripts/verify_probe_records.py --hours 168
```

### Step 3: Check GitHub Actions
1. Go to GitHub repository
2. Navigate to **Actions** tab
3. Check **Automated API Probes** workflow
4. Verify it's running on schedule

---

## Expected Output

### Simulation Script Output:
```
🚀 Starting Probe Simulation for Nov 1-5, 2024
============================================================

📅 Friday, November 01, 2024 (Trading Day)
📊 Simulating probe: probe_20241101_143000 at 2024-11-01 14:30:00 UTC
  ✅ Request sent to team05.reco_requests
  ✅ Response sent to team05.reco_responses (latency: 245.32ms)
...

============================================================
✅ Simulation Complete!
   Total probes: 21
   Successful: 21
   Failed: 0
```

### Verification Script Output:
```
🔍 Verifying Probe Records in Kafka
============================================================

📥 Reading from team05.reco_requests...
📥 Reading from team05.reco_responses...

============================================================
📊 PROBE RECORDS SUMMARY
============================================================

📨 Requests (team05.reco_requests):
   Total records: 21
   Sample request IDs:
     - probe_20241101_143000
     - probe_20241101_153000
     ...

📬 Responses (team05.reco_responses):
   Total records: 21
   Successful: 21
   Errors: 0
   Avg latency: 234.56ms
   Min latency: 189.23ms
   Max latency: 312.45ms

   ⚠️  Simulated records: 21

📅 Date Range:
   Earliest: 2024-11-01 14:30:00
   Latest: 2024-11-05 20:30:00
   Span: 102.0 hours

============================================================
✅ Probe records verified successfully!
```

---

## Notes

- **Simulated Records**: Records created by simulation script are flagged with `simulated: true`
- **Historical Timestamps**: Simulation uses Nov 1-5, 2024 timestamps for historical analysis
- **API Calls**: Simulation makes real API calls but logs with historical timestamps
- **Data Availability**: Since we only have data until Oct 31, simulation uses existing API responses but with shifted timestamps

---

## Troubleshooting

### No probe records found
- Check Kafka connection: Verify `KAFKA_BROKER`, `KAFKA_USERNAME`, `KAFKA_PASSWORD` in `.env`
- Check API is running: Verify `API_URL` is accessible
- Run simulation again: `python scripts/simulate_probes_nov1_5.py`

### GitHub Actions not running
- Check secrets are set: Go to Settings → Secrets → Actions
- Verify cron schedule: Check workflow file for correct cron syntax
- Manual trigger: Use "Run workflow" button to test

### API errors during simulation
- Check API health: `curl $API_URL/health`
- Verify API has models loaded
- Check API logs for errors

---

## Next Steps

After generating probe records:
1. ✅ Run online evaluation: `python scripts/online_eval.py` (to be created)
2. ✅ Analyze probe data for KPIs
3. ✅ Document results for deliverables


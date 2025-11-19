# Implementation Guide: Automated Probes Setup

## Step-by-Step Instructions

### Prerequisites
- GitHub repository (your FinSightAI project)
- GitHub account with repository access
- Azure Event Hubs connection string
- Deployed API URL

---

## Step 1: Get Required Values

Before setting up GitHub secrets, gather these values:

### 1.1 API URL
Your deployed API URL:
```
https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io
```

**How to verify:**
```bash
# Test the API
curl https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health
```

### 1.2 Kafka Connection Details

**From Azure Portal:**
1. Go to **Azure Portal** → **Event Hubs namespaces**
2. Select your Event Hub namespace (e.g., `finsightai-eventhub`)
3. Go to **Shared access policies** → **RootManageSharedAccessKey**
4. Copy the **Connection string-primary key**

**Values needed:**
- **KAFKA_BROKER**: `{namespace}.servicebus.windows.net:9093`
  - Example: `finsightai-eventhub.servicebus.windows.net:9093`
  
- **KAFKA_USERNAME**: `$ConnectionString` (usually this value)

- **KAFKA_PASSWORD**: Full connection string
  - Format: `Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...`

**Or check your local environment:**
```bash
# On Windows PowerShell
$env:KAFKA_BROKER
$env:KAFKA_USERNAME
$env:KAFKA_PASSWORD
```

---

## Step 2: Add GitHub Secrets

### 2.1 Navigate to Repository Settings

1. Go to your GitHub repository: `https://github.com/{username}/{repo-name}`
2. Click **Settings** (top right)
3. In the left sidebar, click **Secrets and variables** → **Actions**

### 2.2 Add Each Secret

Click **New repository secret** for each of the following:

#### Secret 1: API_URL
- **Name**: `API_URL`
- **Value**: `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io`
- Click **Add secret**

#### Secret 2: KAFKA_BROKER
- **Name**: `KAFKA_BROKER`
- **Value**: `finsightai-eventhub.servicebus.windows.net:9093`
- Click **Add secret**

#### Secret 3: KAFKA_USERNAME
- **Name**: `KAFKA_USERNAME`
- **Value**: `$ConnectionString`
- Click **Add secret**

#### Secret 4: KAFKA_PASSWORD
- **Name**: `KAFKA_PASSWORD`
- **Value**: Your full Event Hub connection string
  - Example: `Endpoint=sb://finsightai-eventhub.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=...`
- Click **Add secret**

### 2.3 Verify Secrets

You should see 4 secrets listed:
- ✅ `API_URL`
- ✅ `KAFKA_BROKER`
- ✅ `KAFKA_USERNAME`
- ✅ `KAFKA_PASSWORD`

---

## Step 3: Push Workflow to GitHub

### 3.1 Check Current Status

```bash
# Navigate to project directory
cd C:\Users\jhans\Desktop\FinSightAI

# Check if workflow file exists
ls .github\workflows\automated-probes.yml
```

### 3.2 Commit and Push

```bash
# Check git status
git status

# Add the workflow file
git add .github/workflows/automated-probes.yml
git add .github/workflows/README.md

# Commit
git commit -m "Add automated probes workflow for stock market hours"

# Push to GitHub
git push origin main
# (or git push origin master if your default branch is master)
```

**Alternative: Using GitHub Desktop or VS Code**
1. Stage the `.github/workflows/automated-probes.yml` file
2. Commit with message: "Add automated probes workflow"
3. Push to GitHub

---

## Step 4: Verify Workflow is Active

### 4.1 Check GitHub Actions

1. Go to your GitHub repository
2. Click the **Actions** tab (top navigation)
3. You should see **"Automated API Probes"** workflow listed
4. The workflow should show as "Active" (it will run on the next scheduled time)

### 4.2 Manual Test Run

**To test immediately without waiting for schedule:**

1. Go to **Actions** tab
2. Click **"Automated API Probes"** workflow
3. Click **"Run workflow"** button (top right)
4. Select branch: `main` (or `master`)
5. Click **"Run workflow"**

### 4.3 Monitor Execution

1. Click on the workflow run to see details
2. Click on **"probe-api"** job
3. Expand each step to see logs:
   - ✅ Checkout code
   - ✅ Set up Python
   - ✅ Install dependencies
   - ✅ Run probe script (should show probe results)
   - ✅ Probe summary

**Expected output:**
```
Sending probe request: probe_20240101_143000
Probe successful:
   Latency: 245.32ms
   Results: 3
   Model used: lstm
   AAPL: $150.25 -> $152.30 (+1.36%) [LSTM]
   MSFT: $380.50 -> $382.15 (+0.43%) [LSTM]
   NVDA: $450.00 -> $448.20 (-0.40%) [LSTM]
```

---

## Step 5: Verify Kafka Topics

### 5.1 Check Kafka Topics

After the workflow runs, verify data was written to Kafka:

**Option 1: Using Azure Portal**
1. Go to **Azure Portal** → **Event Hubs**
2. Select your Event Hub namespace
3. Check topics: `team05.reco_requests` and `team05.reco_responses`
4. View messages/metrics

**Option 2: Using kafka-python script**

Create a test script to read from topics:

```python
# test_kafka_read.py
from kafka import KafkaConsumer
import json
import os

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'finsightai-eventhub.servicebus.windows.net:9093')
SASL_USERNAME = os.getenv('KAFKA_USERNAME', '$ConnectionString')
SASL_PASSWORD = os.getenv('KAFKA_PASSWORD')

consumer = KafkaConsumer(
    'team05.reco_responses',
    bootstrap_servers=[KAFKA_BROKER],
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username=SASL_USERNAME,
    sasl_plain_password=SASL_PASSWORD,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    consumer_timeout_ms=5000
)

print("Reading from team05.reco_responses...")
for message in consumer:
    print(f"Received: {message.value}")
```

Run it:
```bash
python test_kafka_read.py
```

---

## Step 6: Schedule Verification

### 6.1 Check Next Run Time

The workflow will run automatically:
- **Every hour during market hours** (9:30 AM - 4:00 PM ET)
- **Monday through Friday only**
- **First run**: Next Monday at 13:30 UTC (9:30 AM EDT / 8:30 AM EST)

### 6.2 View Schedule

GitHub Actions shows the next scheduled run time:
1. Go to **Actions** tab
2. Click **"Automated API Probes"** workflow
3. Look for **"Scheduled"** badge showing next run time

---

## Troubleshooting

### Issue: Workflow fails with "Secret not found"

**Solution:**
- Verify all 4 secrets are added in **Settings** → **Secrets and variables** → **Actions**
- Check secret names match exactly: `API_URL`, `KAFKA_BROKER`, `KAFKA_USERNAME`, `KAFKA_PASSWORD`
- Secrets are case-sensitive!

### Issue: "API timeout" or "Connection refused"

**Solution:**
- Verify `API_URL` secret is correct
- Test API manually: `curl https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health`
- Check if API is running in Azure Container Apps

### Issue: "Kafka connection error"

**Solution:**
- Verify `KAFKA_BROKER` format: `{namespace}.servicebus.windows.net:9093`
- Check `KAFKA_USERNAME` is `$ConnectionString`
- Verify `KAFKA_PASSWORD` is the full connection string (not just the key)
- Test Kafka connection locally first

### Issue: "Workflow not running on schedule"

**Solution:**
- GitHub Actions schedules can be delayed by up to 15 minutes
- Ensure workflow file is in `.github/workflows/` directory
- Check that cron syntax is correct (no syntax errors)
- Verify you're on the correct branch (usually `main` or `master`)

### Issue: "Import errors" or "Module not found"

**Solution:**
- Dependencies are installed in the workflow: `requests` and `kafka-python`
- If you need additional dependencies, add them to the `pip install` step in the workflow

---

## Quick Reference

### Workflow File Location
```
.github/workflows/automated-probes.yml
```

### Required Secrets
- `API_URL`
- `KAFKA_BROKER`
- `KAFKA_USERNAME`
- `KAFKA_PASSWORD`

### Schedule
- **Frequency**: Every hour during market hours
- **Days**: Monday-Friday
- **Times**: 13:30, 14:00, 15:00, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00 UTC

### Manual Trigger
- Go to **Actions** → **Automated API Probes** → **Run workflow**

---

## Next Steps

After implementation:
1. ✅ Monitor first few runs to ensure they succeed
2. ✅ Check Kafka topics for probe data
3. ✅ Set up alerts/notifications for failed runs (optional)
4. ✅ Review probe data periodically to ensure API is healthy

---

## Support

If you encounter issues:
1. Check workflow logs in GitHub Actions
2. Verify all secrets are correct
3. Test API and Kafka connections locally first
4. Review the troubleshooting section above


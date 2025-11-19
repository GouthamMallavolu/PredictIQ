# How to Run GitHub Actions Cron Job

## Quick Answer

The cron job runs **automatically** during market hours, but you can also **trigger it manually** for testing.

---

## Option 1: Manual Trigger (Test Immediately)

### Step-by-Step:

1. **Push workflow to GitHub** (if not already pushed)
   ```bash
   git push origin development
   ```

2. **Go to GitHub Actions**
   - Open: `https://github.com/GouthamMallavolu/PredictIQ/actions`
   - Or: Repository → **Actions** tab (top menu)

3. **Select Workflow**
   - Click on **"Automated API Probes"** workflow

4. **Trigger Manually**
   - Click **"Run workflow"** button (top right, next to "Filter" dropdown)
   - Select branch: `development` (or `main`)
   - Click **"Run workflow"** button

5. **Monitor Execution**
   - You'll see a new workflow run appear
   - Click on it to see logs in real-time
   - Wait for completion (usually 1-2 minutes)

### Expected Output:
```
✓ Checkout code
✓ Set up Python
✓ Install dependencies
✓ Run probe script
  - Sending probe request: probe_YYYYMMDD_HHMMSS
  - [OK] Request sent to team05.reco_requests
  - [OK] Response sent to team05.reco_responses
✓ Probe summary
```

---

## Option 2: Automatic Schedule (No Action Needed)

The workflow runs **automatically** based on the cron schedule:

### Schedule Details:
- **When**: US Stock Market Hours (9:30 AM - 4:00 PM ET)
- **Frequency**: Every hour during trading hours
- **Days**: Monday-Friday only
- **Total**: 9 probes per trading day

### Cron Schedule (UTC):
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

### How to Verify It's Running:
1. Go to: `https://github.com/GouthamMallavolu/PredictIQ/actions`
2. Look for **"Automated API Probes"** runs
3. Check timestamps match market hours
4. Verify runs are completing successfully

---

## Prerequisites

Before the cron job works, ensure:

### 1. Workflow File is in GitHub
- File exists: `.github/workflows/automated-probes.yml`
- Pushed to repository: `git push origin development`

### 2. GitHub Secrets are Configured
Go to: `https://github.com/GouthamMallavolu/PredictIQ/settings/secrets/actions`

Required secrets:
- ✅ `API_URL` - Your API endpoint
- ✅ `KAFKA_BROKER` - Kafka broker address
- ✅ `KAFKA_USERNAME` - Kafka username
- ✅ `KAFKA_PASSWORD` - Kafka password

### 3. Workflow is Enabled
- GitHub Actions must be enabled for the repository
- Workflow file must be in `.github/workflows/` directory
- File must have valid YAML syntax

---

## Troubleshooting

### "Workflow not showing in Actions"
- **Fix**: Push the workflow file to GitHub
  ```bash
  git add .github/workflows/automated-probes.yml
  git commit -m "Add automated probes workflow"
  git push origin development
  ```

### "Run workflow button not visible"
- **Fix**: Make sure you're on the workflow page, not the Actions overview
- Navigate to: Actions → Automated API Probes → Click on workflow name

### "Workflow fails with 'secrets not found'"
- **Fix**: Add missing secrets in GitHub Settings → Secrets → Actions
- See: `docs/GITHUB_SECRETS_QUICK_SETUP.md`

### "Cron job not running automatically"
- **Check**: GitHub Actions may be disabled for free accounts
- **Check**: Verify cron syntax is correct
- **Check**: Wait for the scheduled time (cron runs at specific times)
- **Alternative**: Use manual trigger for testing

### "Workflow runs but probe fails"
- **Check**: API_URL secret is correct
- **Check**: API is accessible from GitHub Actions (public URL)
- **Check**: Kafka credentials are correct
- **Check**: Review workflow logs for specific errors

---

## Testing the Workflow

### Quick Test:
1. **Manual Trigger**: Use "Run workflow" button
2. **Check Logs**: Verify probe script runs successfully
3. **Verify Kafka**: Check that records appear in topics
4. **Check API**: Verify API receives and responds to requests

### Verify Probe Records:
After workflow runs, verify records were created:
```bash
python scripts/verify_probe_records.py --hours 1
```

---

## Schedule Notes

- **GitHub Actions Cron**: Uses UTC timezone
- **Market Hours**: 9:30 AM - 4:00 PM ET = 14:30 - 21:00 UTC (during EST)
- **Daylight Saving**: Schedule covers both EST and EDT
- **Weekends**: Cron only runs Mon-Fri (1-5)

---

## Quick Commands

```bash
# Push workflow to GitHub
git push origin development

# Test probe locally first
python scripts/probe.py

# Verify setup
python scripts/test_probing_setup.py

# Check probe records
python scripts/verify_probe_records.py
```

---

## Next Steps

Once cron job is running:
1. ✅ Monitor workflow runs in GitHub Actions
2. ✅ Verify probe records in Kafka
3. ✅ Move to Phase 2: Online evaluation KPI computation


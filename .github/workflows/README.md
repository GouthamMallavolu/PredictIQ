# GitHub Actions Workflows

## Automated API Probes

The `automated-probes.yml` workflow runs the probe script periodically to test the API and log requests/responses to Kafka.

### Schedule
- **Frequency**: Every hour during US stock market trading hours
- **Market Hours**: 9:30 AM - 4:00 PM Eastern Time (ET)
- **UTC Schedule**: Runs at 13:30, 14:00, 15:00, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00 UTC (Monday-Friday)
- **Runs Per Day**: 9 times per day during market hours
- **Days**: Monday through Friday only (excludes weekends)
- **Manual Trigger**: Can be triggered manually via GitHub Actions UI at any time

### Required GitHub Secrets

Before the workflow can run, you need to configure the following secrets in your GitHub repository:

1. Go to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

2. Add these secrets:

   | Secret Name | Description | Example Value |
   |------------|-------------|---------------|
   | `API_URL` | The deployed API URL | `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io` |
   | `KAFKA_BROKER` | Kafka broker address | `finsightai-eventhub.servicebus.windows.net:9093` |
   | `KAFKA_USERNAME` | Kafka SASL username | `$ConnectionString` |
   | `KAFKA_PASSWORD` | Kafka connection string | `Endpoint=sb://...` (full connection string) |

### How to Get Values

#### API_URL
- From Azure Portal → Container Apps → finsightai-api → Application URL
- Or from the deployed API: `https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io`

#### KAFKA_BROKER
- From Azure Portal → Event Hubs namespace → Connection strings
- Format: `{namespace}.servicebus.windows.net:9093`

#### KAFKA_USERNAME
- Usually: `$ConnectionString`

#### KAFKA_PASSWORD
- From Azure Portal → Event Hubs namespace → Shared access policies → RootManageSharedAccessKey → Connection string-primary key
- Full connection string format: `Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...`

### Testing the Workflow

1. **Manual Test**: Go to **Actions** → **Automated API Probes** → **Run workflow**
2. **Check Logs**: View the workflow run logs to see probe results
3. **Verify Kafka**: Check Kafka topics `team05.reco_requests` and `team05.reco_responses` for probe data

### Workflow Output

The workflow will:
- Send a probe request to the API with test symbols (AAPL, MSFT, NVDA)
- Log the request to `team05.reco_requests` topic
- Log the response to `team05.reco_responses` topic
- Include latency metrics and prediction results

### Troubleshooting

- **Workflow fails**: Check that all secrets are configured correctly
- **API timeout**: Verify API_URL is correct and API is running
- **Kafka connection error**: Verify KAFKA_BROKER, KAFKA_USERNAME, and KAFKA_PASSWORD are correct
- **Import errors**: Ensure all dependencies are listed in the workflow's `pip install` step


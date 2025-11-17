# Quick Setup: GitHub Secrets

## Azure Credentials Already Generated

✅ Azure Service Principal created successfully!
✅ Credentials saved to: `azure_credentials.json`

## Add to GitHub Secrets

### Step 1: Open GitHub Secrets Page
Go to: `https://github.com/GouthamMallavolu/PredictIQ/settings/secrets/actions`

Or navigate manually:
1. Go to your repository: `https://github.com/GouthamMallavolu/PredictIQ`
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)

### Step 2: Add AZURE_CREDENTIALS Secret
1. Click **New repository secret**
2. **Name**: `AZURE_CREDENTIALS`
3. **Value**: Copy the entire JSON from `azure_credentials.json`
4. Click **Add secret**

### Step 3: Verify Other Secrets
Make sure these secrets are also configured:
- `API_URL` - Your API endpoint URL
- `KAFKA_BROKER` - Kafka broker address
- `KAFKA_USERNAME` - Kafka username
- `KAFKA_PASSWORD` - Kafka password
- `STORAGE_CONNECTION` - Azure Storage connection string

### Step 4: Clean Up
After adding to GitHub:
```powershell
Remove-Item azure_credentials.json
```

## Test the Workflow

After adding secrets:
1. Go to **Actions** tab
2. Select **Deploy to Azure** workflow
3. Click **Run workflow** (manual trigger)
4. Verify it runs successfully

## Troubleshooting

### Secret not found error
- Double-check the secret name is exactly `AZURE_CREDENTIALS`
- Ensure you copied the entire JSON (including all brackets)

### Authentication failed
- Verify the JSON format is correct
- Check that the service principal still exists
- Regenerate if needed: `.\scripts\setup_azure_credentials.ps1`

### Permission denied
- Ensure the service principal has Contributor role
- Check subscription permissions


# Add Azure Credentials to GitHub Secrets

## Quick Steps

### Step 1: Get Your Credentials

If you have `azure_credentials.json` locally:
```powershell
Get-Content azure_credentials.json
```

Or regenerate if needed:
```powershell
.\scripts\setup_azure_credentials.ps1
```

### Step 2: Add to GitHub

1. **Go to GitHub Secrets Page**
   - Open: `https://github.com/GouthamMallavolu/PredictIQ/settings/secrets/actions`
   - Or: Repository → **Settings** → **Secrets and variables** → **Actions**

2. **Click "New repository secret"**

3. **Enter Details**
   - **Name**: `AZURE_CREDENTIALS`
   - **Value**: Copy the **entire JSON** from `azure_credentials.json`
   - Example format:
     ```json
     {"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"...",...}
     ```

4. **Click "Add secret"**

### Step 3: Verify

After adding, the workflow should work. The error you saw means the secret wasn't found.

**Note**: The workflow uses `continue-on-error: true`, so it will skip Azure steps if credentials are missing, but you'll still see the error in logs.

## Current Status

The workflow is configured to:
- ✅ Always build Docker image
- ⚠️ Skip Azure steps if credentials missing (with error message)
- ✅ Complete successfully either way

## After Adding Secret

Once `AZURE_CREDENTIALS` is added:
- ✅ Azure login will work
- ✅ Docker image will be pushed to ACR
- ✅ Container App will be updated

## Quick Copy Command

If you have the file locally:
```powershell
# View credentials (copy the output)
Get-Content azure_credentials.json

# Then paste into GitHub Secrets
```

## Security Reminder

After adding to GitHub:
```powershell
# Delete local file for security
Remove-Item azure_credentials.json
```


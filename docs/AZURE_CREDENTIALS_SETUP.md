# Azure Credentials Setup for GitHub Actions

## Overview

The `azure-deploy.yml` workflow requires Azure credentials to build and push Docker images to Azure Container Registry and deploy to Azure Container Apps.

## Error Message

If you see this error:
```
Error: Login failed with Error: Using auth-type: SERVICE_PRINCIPAL. Not all values are present. 
Ensure 'client-id' and 'tenant-id' are supplied.
```

This means the `AZURE_CREDENTIALS` secret is not configured or is incorrectly formatted.

## Solution: Set Up Azure Service Principal

### Step 1: Create Azure Service Principal

Run this Azure CLI command (requires Azure CLI installed and logged in):

```bash
az ad sp create-for-rbac --name "github-actions-finsightai" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --sdk-auth
```

Replace `{subscription-id}` with your Azure subscription ID.

**Output format:**
```json
{
  "clientId": "xxxx-xxxx-xxxx-xxxx",
  "clientSecret": "xxxx-xxxx-xxxx-xxxx",
  "subscriptionId": "xxxx-xxxx-xxxx-xxxx",
  "tenantId": "xxxx-xxxx-xxxx-xxxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### Step 2: Add Secret to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AZURE_CREDENTIALS`
5. Value: Paste the **entire JSON output** from Step 1
6. Click **Add secret**

### Step 3: Verify Secret Format

The secret should be a JSON string with these required fields:
- `clientId`
- `clientSecret`
- `subscriptionId`
- `tenantId`

## Alternative: Skip Azure Deployment

If you don't need automatic deployment, the workflow will:
- Still build the Docker image
- Skip Azure login and deployment
- Show a message that credentials are not configured

## Manual Deployment

If you prefer manual deployment:

1. Build image locally:
   ```bash
   docker build -t finsightai-api:latest .
   ```

2. Push to ACR manually:
   ```bash
   az acr login --name finsightairegistry
   docker tag finsightai-api:latest finsightairegistry.azurecr.io/finsightai-api:latest
   docker push finsightairegistry.azurecr.io/finsightai-api:latest
   ```

3. Update Container App:
   ```bash
   az containerapp update \
     --name finsightai-api \
     --resource-group FinSightAI-RG \
     --image finsightairegistry.azurecr.io/finsightai-api:latest
   ```

## Troubleshooting

### Error: "Not all values are present"
- Check that the JSON secret contains all required fields
- Ensure there are no extra quotes or formatting issues
- Copy the entire JSON output from `az ad sp create-for-rbac`

### Error: "Authentication failed"
- Verify the service principal still exists: `az ad sp list --display-name "github-actions-finsightai"`
- Check if the secret expired (service principal secrets can expire)
- Regenerate if needed: `az ad sp credential reset --name "github-actions-finsightai"`

### Error: "Insufficient permissions"
- Ensure the service principal has Contributor role
- Check resource group permissions
- Verify ACR access: `az acr show --name finsightairegistry`

## Security Notes

- Never commit Azure credentials to the repository
- Use GitHub Secrets for all sensitive values
- Rotate service principal secrets regularly
- Use least-privilege access (only grant necessary permissions)


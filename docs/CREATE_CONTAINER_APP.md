# Create Azure Container App

## Issue

The workflow is trying to update a Container App that doesn't exist yet:
```
ERROR: The containerapp 'finsightai-api' does not exist
```

## Solution: Create the Container App First

### Option 1: Create via Azure Portal (Easiest)

1. Go to Azure Portal: `https://portal.azure.com`
2. Search for "Container Apps"
3. Click **"Create"** or **"Create Container App"**
4. Fill in details:
   - **Name**: `finsightai-api`
   - **Resource Group**: `FinSightAI-RG` (or create new)
   - **Environment**: Create new or use existing
   - **Image**: `finsightairegistry.azurecr.io/finsightai-api:latest`
   - **Registry**: `finsightairegistry.azurecr.io`
   - **Port**: `8000`
5. Click **"Create"**

### Option 2: Create via Azure CLI

```bash
# Login to Azure
az login

# Create Container App
az containerapp create \
  --name finsightai-api \
  --resource-group FinSightAI-RG \
  --image finsightairegistry.azurecr.io/finsightai-api:latest \
  --registry-server finsightairegistry.azurecr.io \
  --target-port 8000 \
  --ingress external \
  --cpu 2.0 \
  --memory 4.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars \
    KAFKA_BROKER="$KAFKA_BROKER" \
    STORAGE_CONNECTION="$STORAGE_CONNECTION" \
    AZURE_STORAGE_CONTAINER_NAME="snapshots"
```

### Option 3: Update Workflow to Create (Advanced)

The workflow now checks if the app exists. You can add a create step if needed.

## Required Environment Variables

When creating the Container App, set these environment variables:

- `KAFKA_BROKER` - Kafka broker address
- `KAFKA_USERNAME` - Kafka username (usually `$ConnectionString`)
- `KAFKA_PASSWORD` - Kafka password/connection string
- `STORAGE_CONNECTION` - Azure Storage connection string
- `AZURE_STORAGE_CONTAINER_NAME` - Container name (e.g., `snapshots`)
- `ALPHA_VANTAGE_KEY` - Alpha Vantage API key (if needed)

## Verify Container App

After creating:
```bash
az containerapp show \
  --name finsightai-api \
  --resource-group FinSightAI-RG
```

## Workflow Behavior

After creating the Container App:
- ✅ Workflow will detect it exists
- ✅ Will update it with new image
- ✅ Deployment will succeed

## Current Status

The workflow now:
- ✅ Builds Docker image (always works)
- ✅ Checks if Container App exists
- ✅ Updates if exists, shows message if doesn't
- ✅ Completes successfully either way

Once you create the Container App, the workflow will automatically update it on each push!


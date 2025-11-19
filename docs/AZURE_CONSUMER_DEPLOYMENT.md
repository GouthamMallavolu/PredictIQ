# Azure Consumer Service Deployment Guide

This guide explains how to deploy the Kafka consumer service to Azure Container Apps.

## Overview

The consumer service:
- Listens continuously to Kafka topic `team05.watch`
- Processes incoming stock data
- Updates data buffers
- Makes predictions
- Performs online evaluation

## Prerequisites

1. **Azure CLI** installed and configured
2. **Docker** installed
3. **Azure resources**:
   - Resource Group: `finsightai-resourcegroup`
   - Container Registry: `finsightairegistry`
   - Container Apps Environment: `finsightai-containerenv`
4. **GitHub Secrets** configured (for automated deployment)

## Deployment Methods

### Method 1: Automated via GitHub Actions (Recommended)

The consumer will be automatically built and deployed when:
- You push changes to `main` or `development` branch
- Files changed: `Dockerfile.consumer`, `scripts/run_consumer_service.py`, `kafka_pipeline/consumer.py`
- Or manually trigger: `Deploy Consumer to Azure` workflow

**Workflow**: `.github/workflows/deploy-consumer.yml`

**Required GitHub Secrets:**
- `AZURE_CREDENTIALS` - Azure service principal credentials
- `ACR_LOGIN_SERVER` - Container registry server (e.g., `finsightairegistry.azurecr.io`)
- `ACR_USERNAME` - Container registry username
- `ACR_PASSWORD` - Container registry password
- `KAFKA_BROKER` - Kafka broker address
- `KAFKA_USERNAME` - Kafka username
- `KAFKA_PASSWORD` - Kafka password
- `STORAGE_CONNECTION` - Azure Storage connection string
- `STORAGE_CONTAINER` - Storage container name

### Method 2: Manual Deployment Script (PowerShell)

```powershell
# Run the deployment script
.\scripts\azure-deploy-consumer.ps1

# Or with custom parameters
.\scripts\azure-deploy-consumer.ps1 `
    -ResourceGroup "finsightai-resourcegroup" `
    -ContainerAppName "finsightai-consumer" `
    -AcrName "finsightairegistry"
```

### Method 3: Manual Deployment Script (Bash)

```bash
# Make script executable
chmod +x scripts/azure-deploy-consumer.sh

# Run the deployment script
./scripts/azure-deploy-consumer.sh
```

### Method 4: Azure CLI Commands (Manual)

```bash
# 1. Build Docker image
docker build -f Dockerfile.consumer -t finsightai-consumer:latest .

# 2. Tag for ACR
docker tag finsightai-consumer:latest finsightairegistry.azurecr.io/finsightai-consumer:latest

# 3. Login to ACR
az acr login --name finsightairegistry

# 4. Push to ACR
docker push finsightairegistry.azurecr.io/finsightai-consumer:latest

# 5. Create Container App (first time)
az containerapp create \
  --name finsightai-consumer \
  --resource-group finsightai-resourcegroup \
  --image finsightairegistry.azurecr.io/finsightai-consumer:latest \
  --environment finsightai-containerenv \
  --registry-server finsightairegistry.azurecr.io \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 1 \
  --env-vars \
    KAFKA_BROKER="your_kafka_broker" \
    KAFKA_USERNAME="$ConnectionString" \
    KAFKA_PASSWORD="your_kafka_password" \
    STORAGE_CONNECTION="your_storage_connection" \
    STORAGE_CONTAINER="snapshots" \
    CONSUMER_GROUP="finsight-consumer-group"

# 6. Update Container App (subsequent deployments)
az containerapp update \
  --name finsightai-consumer \
  --resource-group finsightai-resourcegroup \
  --image finsightairegistry.azurecr.io/finsightai-consumer:latest
```

## Container App Configuration

### Resource Allocation
- **CPU**: 1.0 cores
- **Memory**: 2.0 Gi
- **Min Replicas**: 1 (always running)
- **Max Replicas**: 1 (single instance for Kafka consumer)

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `KAFKA_BROKER` | Kafka broker address | `finsightai-eventhub.servicebus.windows.net:9093` |
| `KAFKA_USERNAME` | Kafka username | `$ConnectionString` |
| `KAFKA_PASSWORD` | Kafka password | `Endpoint=sb://...` |
| `STORAGE_CONNECTION` | Azure Storage connection string | `DefaultEndpointsProtocol=https;...` |
| `STORAGE_CONTAINER` | Storage container name | `snapshots` |
| `CONSUMER_GROUP` | Kafka consumer group | `finsight-consumer-group` |

## Verification

### Check Container App Status

```bash
az containerapp show \
  --name finsightai-consumer \
  --resource-group finsightai-resourcegroup \
  --query "properties.runningStatus"
```

### View Logs

```bash
# Stream logs
az containerapp logs show \
  --name finsightai-consumer \
  --resource-group finsightai-resourcegroup \
  --follow

# Get recent logs
az containerapp logs show \
  --name finsightai-consumer \
  --resource-group finsightai-resourcegroup \
  --tail 100
```

### Check Consumer is Processing

Look for these log messages:
- `✓ Kafka producer connected to ...`
- `Consumer initialized successfully`
- `Starting to consume messages...`
- `PREDICTION for {symbol} at {timestamp}: ...`
- `ONLINE EVAL for {symbol}: ...`

## Troubleshooting

### Consumer Not Starting

1. **Check logs**:
   ```bash
   az containerapp logs show --name finsightai-consumer --resource-group finsightai-resourcegroup --tail 50
   ```

2. **Verify environment variables**:
   ```bash
   az containerapp show --name finsightai-consumer --resource-group finsightai-resourcegroup --query "properties.template.containers[0].env"
   ```

3. **Check Kafka connectivity**:
   - Verify `KAFKA_BROKER`, `KAFKA_USERNAME`, `KAFKA_PASSWORD` are correct
   - Check if Kafka topic `team05.watch` exists

### Consumer Not Processing Messages

1. **Check consumer group**:
   - Ensure `CONSUMER_GROUP` is set correctly
   - Check Kafka offsets: Consumer should be committing offsets

2. **Verify topic subscription**:
   - Consumer subscribes to `team05.watch` topic
   - Check if messages are being sent to this topic

3. **Check data buffers**:
   - Look for logs showing data being added to buffers
   - Verify historical data is loaded from blob storage

### Container App Crashes

1. **Check resource limits**:
   - Increase CPU/memory if needed
   - Check if container is running out of memory

2. **Check health**:
   ```bash
   az containerapp show --name finsightai-consumer --resource-group finsightai-resourcegroup --query "properties.healthState"
   ```

3. **Restart container app**:
   ```bash
   az containerapp revision restart \
     --name finsightai-consumer \
     --resource-group finsightai-resourcegroup
   ```

## Monitoring

### Azure Portal

1. Go to: **Container Apps** → **finsightai-consumer**
2. View:
   - **Overview**: Status, replicas, metrics
   - **Logs**: Real-time log streaming
   - **Revisions**: Deployment history
   - **Metrics**: CPU, memory, requests

### Logs Location

- **Container logs**: `logs/consumer_service.log` (inside container)
- **Azure logs**: Available via Azure Portal or CLI

## Scaling

The consumer is configured with:
- **Min replicas**: 1 (always running)
- **Max replicas**: 1 (single instance)

**Note**: Kafka consumers typically run as single instances per consumer group. If you need to scale, use multiple consumer groups or partition the workload.

## Cost Optimization

- **CPU**: 1.0 core (minimum for ML model inference)
- **Memory**: 2.0 Gi (sufficient for models and buffers)
- **Always-on**: Consumer needs to run continuously to process messages

## Next Steps

After deployment:

1. ✅ **Verify consumer is running**: Check Azure Portal
2. ✅ **Check logs**: Ensure consumer is connecting to Kafka
3. ✅ **Test data flow**: Trigger daily data fetch and verify consumer processes messages
4. ✅ **Monitor performance**: Watch logs for predictions and evaluations

## Related Files

- `Dockerfile.consumer` - Docker image definition
- `scripts/run_consumer_service.py` - Consumer service entry point
- `kafka_pipeline/consumer.py` - Consumer logic
- `.github/workflows/deploy-consumer.yml` - Automated deployment workflow
- `scripts/azure-deploy-consumer.sh` - Manual deployment script (Bash)
- `scripts/azure-deploy-consumer.ps1` - Manual deployment script (PowerShell)


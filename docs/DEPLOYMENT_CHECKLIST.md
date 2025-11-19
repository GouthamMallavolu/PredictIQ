# Deployment Checklist - FinSightAI API

## ✅ Pre-Deployment Checklist

### Code & Files
- [x] API code created (`api/main.py`, `api/predictor.py`)
- [x] API tested locally - ALL TESTS PASS
- [x] Probe script fixed and tested
- [x] Dockerfile updated with correct paths
- [x] All dependencies in `requirements.txt`

### Docker Build
- [ ] Test Docker build locally:
  ```bash
  docker build -t finsightai-api:latest .
  ```
- [ ] Test Docker container locally:
  ```bash
  docker run -p 8000:8000 \
    -e KAFKA_BROKER=your-broker \
    -e KAFKA_PASSWORD=your-password \
    -e STORAGE_CONNECTION=your-connection-string \
    finsightai-api:latest
  ```
- [ ] Verify health endpoint in container:
  ```bash
  curl http://localhost:8000/health
  ```

### Azure Deployment
- [ ] Create Azure Container Registry (ACR) or use existing
- [ ] Login to ACR:
  ```bash
  az acr login --name <registry-name>
  ```
- [ ] Tag and push image:
  ```bash
  docker tag finsightai-api:latest <registry>.azurecr.io/finsightai-api:latest
  docker push <registry>.azurecr.io/finsightai-api:latest
  ```
- [ ] Create Azure Container App or update existing
- [ ] Configure environment variables:
  - `KAFKA_BROKER`
  - `KAFKA_PASSWORD`
  - `STORAGE_CONNECTION`
  - `AZURE_STORAGE_CONTAINER_NAME`
  - `ALPHA_VANTAGE_KEY` (if needed)
- [ ] Set up secrets in Azure Container Apps
- [ ] Configure ingress (public access)
- [ ] Get live API URL

### Post-Deployment Verification
- [ ] Test live API health endpoint
- [ ] Test live API `/recommend` endpoint
- [ ] Update `API_URL` in probe script
- [ ] Test probe script against live API
- [ ] Verify Kafka topics receive probe messages

### Environment Variables Needed
```bash
KAFKA_BROKER=finsightai-eventhub.servicebus.windows.net:9093
KAFKA_USERNAME=$ConnectionString
KAFKA_PASSWORD=<connection-string>
STORAGE_CONNECTION=<azure-storage-connection-string>
AZURE_STORAGE_CONTAINER_NAME=snapshots
ALPHA_VANTAGE_KEY=<optional>
```

### Next Steps After Deployment
1. Update probe script with live API URL
2. Set up GitHub Actions for automated probing
3. Create model comparison documentation
4. Set up monitoring and ops log


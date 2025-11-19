# FinSightAI - Real-Time Stock Price Prediction

Multi-model stock price prediction system with real-time data streaming and Azure deployment.

## System Architecture

```
Alpha Vantage API → Producer → Event Hubs (Kafka) → Consumer → Blob Storage
                                      ↓
                                  FastAPI ← LSTM/RF/MA Models
                                      ↓
                                React Dashboard
```

## Features

- **Real-time Data Streaming**: Simulates live market data with hourly updates
- **Multi-Model Predictions**: LSTM, Random Forest, and Moving Average models
- **News Sentiment Analysis**: Integrates news sentiment for enhanced predictions
- **Azure-Native**: Event Hubs, Blob Storage, Container Apps
- **Auto-scaling**: Serverless container deployment
- **Docker-optimized**: Layer caching for fast builds

## Quick Start

### Local Development

1. **Setup Environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

2. **Configure Environment Variables**

Create `.env` file:
```env
# Azure Event Hubs (Kafka)
KAFKA_BROKER=your-eventhub.servicebus.windows.net:9093
SASL_PASSWORD=your-connection-string

# Azure Blob Storage
STORAGE_CONNECTION=your-storage-connection-string
STORAGE_CONTAINER=snapshots

# Alpha Vantage API
ALPHA_VANTAGE_KEY=your-api-key

# Topics
TOPIC_WATCH=team05.watch
TOPIC_RATE=team05.rate
TOPIC_PREDICT_REQUESTS=team05.reco_requests
TOPIC_PREDICT_RESPONSES=team05.reco_responses
```

3. **Run Components**

**Terminal 1 - Producer (Data Streaming)**
```bash
python kafka_pipeline/producer.py --delay 5
```

**Terminal 2 - Consumer (Ingestion + Storage)**
```bash
python kafka_pipeline/consumer.py
```

**Terminal 3 - API Server**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 4 - Probe (Testing)**
```bash
python scripts/probe.py --interval 60
```

### Docker Deployment

1. **Build Image**
```bash
docker build -t finsightai:latest .
```

2. **Run Container**
```bash
docker run -p 8000:8000 --env-file .env finsightai:latest
```

## Azure Deployment

### Prerequisites

- Azure CLI installed and logged in
- Subscription with credits available

### Provision Resources

```bash
# Set variables
RESOURCE_GROUP="rg-finsightai-prod"
LOCATION="eastus"
EVENTHUB_NAMESPACE="eh-finsight-prod"
STORAGE_ACCOUNT="stfinsightprod"
CONTAINER_REGISTRY="acrfinsightprod"
CONTAINER_APP_ENV="env-finsight-prod"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Event Hubs namespace
az eventhubs namespace create \
  --resource-group $RESOURCE_GROUP \
  --name $EVENTHUB_NAMESPACE \
  --location $LOCATION \
  --sku Standard

# Create Event Hub topics
az eventhubs eventhub create --resource-group $RESOURCE_GROUP \
  --namespace-name $EVENTHUB_NAMESPACE --name team05.watch --partition-count 4

az eventhubs eventhub create --resource-group $RESOURCE_GROUP \
  --namespace-name $EVENTHUB_NAMESPACE --name team05.rate --partition-count 2

# Create Blob Storage
az storage account create \
  --resource-group $RESOURCE_GROUP \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS

az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name snapshots

# Create Container Registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_REGISTRY \
  --sku Basic \
  --admin-enabled true

# Build and push image
az acr build \
  --registry $CONTAINER_REGISTRY \
  --image finsightai:latest \
  --file Dockerfile .

# Create Container Apps environment
az containerapp env create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_ENV \
  --location $LOCATION

# Deploy API
az containerapp create \
  --resource-group $RESOURCE_GROUP \
  --name api-finsight \
  --environment $CONTAINER_APP_ENV \
  --image $CONTAINER_REGISTRY.azurecr.io/finsightai:latest \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --cpu 1 --memory 2Gi \
  --min-replicas 1 --max-replicas 3 \
  --ingress external --target-port 8000 \
  --secrets \
    kafka-conn="$KAFKA_CONNECTION_STRING" \
    storage-conn="$STORAGE_CONNECTION_STRING" \
    alpha-key="$ALPHA_VANTAGE_KEY" \
  --env-vars \
    KAFKA_BROKER=$EVENTHUB_NAMESPACE.servicebus.windows.net:9093 \
    SASL_PASSWORD=secretref:kafka-conn \
    STORAGE_CONNECTION=secretref:storage-conn \
    ALPHA_VANTAGE_KEY=secretref:alpha-key
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Get Model Metrics
```bash
GET /models
```

### Get Predictions
```bash
POST /recommend
{
  "user_id": "user123",
  "symbols": ["AAPL", "MSFT", "NVDA"],
  "model": "lstm"
}
```

## Project Structure

```
FinSightAI/
├── api/
│   ├── main.py           # FastAPI application
│   └── predictor.py      # ML model inference
├── kafka_pipeline/
│   ├── config.py         # Centralized configuration
│   ├── schemas.py        # Pydantic schemas
│   ├── producer.py       # Data streaming
│   └── consumer.py       # Ingestion + predictions
├── models/
│   └── baseline_ma.py    # Moving Average model
├── scripts/
│   ├── train_all_models.py   # Model training
│   ├── compare_models.py     # Model evaluation
│   └── probe.py              # API testing
├── frontend/              # React dashboard (if built)
├── Dockerfile
├── requirements.txt
└── README.md
```

## Models

- **LSTM**: Deep learning for time-series prediction
- **Random Forest**: Ensemble model for feature-based prediction
- **Moving Average**: Baseline model for comparison

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `KAFKA_BROKER` | Event Hubs endpoint | Yes |
| `SASL_PASSWORD` | Event Hubs connection string | Yes |
| `STORAGE_CONNECTION` | Blob Storage connection string | Yes |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage API key | Yes |
| `TOPIC_WATCH` | Stock price topic | Yes |
| `TOPIC_RATE` | Rating topic | Yes |
| `STORAGE_CONTAINER` | Blob container name | No (default: snapshots) |
| `CONSUMER_GROUP` | Kafka consumer group | No (default: stock-ingestor) |

## Development Notes

- **Model Files**: Large `.pkl` and `.keras` files stored in Azure Blob (not in git)
- **Data Files**: CSV files stored in Blob Storage
- **Secrets**: Use `.env` locally, Azure secrets in production
- **Docker Optimization**: Layers ordered for maximum cache reuse

## License

MIT
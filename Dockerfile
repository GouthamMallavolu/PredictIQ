FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (copy this first for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code first (changes more frequently, smaller files)
COPY api/ ./api/
COPY models/ ./models/
COPY scripts/ ./scripts/
COPY kafka_pipeline/config.py ./kafka_pipeline/
COPY kafka_pipeline/schemas.py ./kafka_pipeline/

# Model files are NOT copied here - they are loaded from Azure Blob Storage at runtime
# This keeps the Docker image small and allows model updates without rebuilding
# Models are loaded by api/predictor.py from blob storage

# Frontend build not included (doesn't exist)
# Models loaded from blob storage at runtime

# Expose port
EXPOSE 8000

# Run API (Container Apps manages health checks)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model files (using the correctly named files)
COPY multi_stock_model_LSTM.keras ./
COPY scaler.pkl ./
COPY random_forest_model.pkl ./

# Copy application code
COPY api/ ./api/
COPY models/ ./models/
COPY kafka_pipeline/config.py ./kafka_pipeline/
COPY kafka_pipeline/schemas.py ./kafka_pipeline/

# Copy React frontend build
COPY frontend/build/ ./frontend/build/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run unified API + Frontend
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

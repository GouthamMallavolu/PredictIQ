FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model files
COPY multi_stock_model_LSTM.keras .
COPY scaler.pkl .
COPY random_forest_model.pkl .

# Copy application code
COPY api/ ./api/
COPY models/ ./models/
COPY kafka_pipeline/config.py ./
COPY kafka_pipeline/schemas.py ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Multi-Stage Dockerfile for FinSightAI
# Stage 1: Builder - Install dependencies and compile
# Stage 2: Runtime - Minimal production image

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.10-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.10-slim

WORKDIR /app

# Install only runtime dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (changes more frequently, so copy after dependencies)
COPY api/ ./api/
COPY models/ ./models/
COPY scripts/ ./scripts/
COPY pipeline/ ./pipeline/
COPY kafka_pipeline/config.py ./kafka_pipeline/
COPY kafka_pipeline/schemas.py ./kafka_pipeline/
COPY evaluation/ ./evaluation/
COPY quality/ ./quality/

# Create directories for logs and cache
RUN mkdir -p logs cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check (managed by Azure Container Apps, but useful for local testing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

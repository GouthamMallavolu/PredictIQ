# Monitoring Setup Guide

## Overview

This guide covers setting up monitoring for FinSightAI API including:
- Prometheus metrics collection
- Grafana dashboards
- Alert rules
- Availability tracking

---

## 1. Prometheus Metrics

### Available Metrics

The API exposes metrics at `/metrics` endpoint in Prometheus format:

```
# HTTP Request Metrics
http_requests_total{method, endpoint, status}
http_request_duration_seconds{method, endpoint}

# Model Prediction Metrics
model_predictions_total{model, status}
model_errors_total{model, error_type}

# API Health Metrics
api_uptime_seconds
api_health_status
```

### Accessing Metrics

```bash
# Local
curl http://localhost:8000/metrics

# Production
curl https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/metrics
```

---

## 2. Grafana Dashboard Setup

### Option A: Azure Monitor + Grafana

1. **Enable Application Insights** (if not already enabled):
   ```bash
   az monitor app-insights component create \
     --app finsightai-insights \
     --location eastus \
     --resource-group finsightai-resourcegroup \
     --application-type web
   ```

2. **Connect Grafana to Azure Monitor**:
   - Add Azure Monitor data source in Grafana
   - Use managed identity or service principal for authentication

3. **Import dashboard template** (see JSON below)

### Option B: Prometheus + Grafana (Self-hosted)

1. **Deploy Prometheus**:
   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s
   
   scrape_configs:
     - job_name: 'finsightai-api'
       static_configs:
         - targets: ['finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io:8000']
       metrics_path: '/metrics'
   ```

2. **Deploy Grafana**:
   ```bash
   docker run -d \
     -p 3000:3000 \
     --name grafana \
     grafana/grafana-oss
   ```

3. **Add Prometheus data source** in Grafana (http://prometheus:9090)

---

## 3. Grafana Dashboard JSON

Create a new dashboard and import this configuration:

```json
{
  "dashboard": {
    "title": "FinSightAI API Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }],
        "type": "graph"
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "{{endpoint}}"
        }],
        "type": "graph",
        "alert": {
          "name": "High P95 Latency",
          "conditions": [{
            "evaluator": { "params": [1.0], "type": "gt" },
            "operator": { "type": "and" },
            "query": { "params": ["A", "5m", "now"] },
            "reducer": { "params": [], "type": "avg" },
            "type": "query"
          }]
        }
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
          "legendFormat": "Error Rate"
        }],
        "type": "gauge",
        "alert": {
          "name": "High Error Rate",
          "conditions": [{
            "evaluator": { "params": [0.05], "type": "gt" }
          }]
        }
      },
      {
        "title": "API Uptime",
        "targets": [{
          "expr": "api_uptime_seconds / 3600",
          "legendFormat": "Uptime (hours)"
        }],
        "type": "stat"
      },
      {
        "title": "Model Prediction Success Rate",
        "targets": [{
          "expr": "rate(model_predictions_total{status=\"success\"}[5m]) / rate(model_predictions_total[5m])",
          "legendFormat": "{{model}}"
        }],
        "type": "graph"
      }
    ],
    "refresh": "30s",
    "time": {
      "from": "now-6h",
      "to": "now"
    }
  }
}
```

---

## 4. Alert Rules

### Critical Alerts

#### High Error Rate
```yaml
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
for: 5m
labels:
  severity: critical
annotations:
  summary: "High error rate detected"
  description: "Error rate is {{ $value | humanizePercentage }}"
```

#### High P95 Latency
```yaml
alert: HighLatency
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
for: 5m
labels:
  severity: warning
annotations:
  summary: "High P95 latency"
  description: "P95 latency is {{ $value }}s"
```

#### API Down
```yaml
alert: APIDown
expr: up{job="finsightai-api"} == 0
for: 2m
labels:
  severity: critical
annotations:
  summary: "API is down"
  description: "FinSightAI API has been down for more than 2 minutes"
```

#### Low Uptime
```yaml
alert: LowUptime
expr: api_health_status == 0
for: 5m
labels:
  severity: warning
annotations:
  summary: "API health check failing"
  description: "API is reporting unhealthy status"
```

---

## 5. Availability Tracking

### Azure Container Apps Built-in Monitoring

Azure Container Apps provides built-in availability monitoring:

1. **View Metrics** in Azure Portal:
   - Go to Container App > Monitoring > Metrics
   - Select metrics: Requests, Response Time, CPU, Memory

2. **Configure Alerts**:
   ```bash
   # Create alert rule for availability
   az monitor metrics alert create \
     --name finsightai-availability-alert \
     --resource-group finsightai-resourcegroup \
     --scopes /subscriptions/{subscription-id}/resourceGroups/finsightai-resourcegroup/providers/Microsoft.App/containerApps/finsightai-api \
     --condition "avg Percentage CPU > 80" \
     --window-size 5m \
     --evaluation-frequency 1m
   ```

3. **View Logs**:
   ```bash
   az containerapp logs show \
     --name finsightai-api \
     --resource-group finsightai-resourcegroup \
     --follow
   ```

### External Uptime Monitoring

For independent availability tracking, use external services:

1. **UptimeRobot** (free tier):
   - Monitor: https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health
   - Check interval: 5 minutes
   - Alert on: 2 consecutive failures

2. **Pingdom** or **StatusCake**

3. **Custom Script**:
   ```python
   # scripts/check_availability.py
   import requests
   import time
   from datetime import datetime
   
   API_URL = "https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io/health"
   
   while True:
       try:
           response = requests.get(API_URL, timeout=10)
           status = "UP" if response.status_code == 200 else "DOWN"
           print(f"{datetime.now()}: {status} (status={response.status_code})")
       except Exception as e:
           print(f"{datetime.now()}: DOWN (error={e})")
       
       time.sleep(300)  # Check every 5 minutes
   ```

---

## 6. Availability Calculation

### Required Window
- **72 hours before submission**
- **144 hours after submission**
- **Total: 216 hours** (9 days)

### Calculation Formula

```
Availability % = (Total Uptime / Total Time) * 100

Where:
- Total Time = 216 hours = 777,600 seconds
- Total Uptime = Total Time - Total Downtime
- Requirement: ≥ 70%
```

### Example

If API is down for:
- 2 hours on Day 1
- 1 hour on Day 5
- Total downtime: 3 hours

```
Availability = ((216 - 3) / 216) * 100 = 98.6% ✅
```

### Tracking Script

```python
# scripts/calculate_availability.py
import json
from datetime import datetime, timedelta

def calculate_availability(start_date, end_date, downtime_minutes):
    """
    Calculate availability percentage.
    
    Args:
        start_date: Start of monitoring window
        end_date: End of monitoring window
        downtime_minutes: Total downtime in minutes
    
    Returns:
        Availability percentage
    """
    total_time = (end_date - start_date).total_seconds() / 60  # minutes
    uptime = total_time - downtime_minutes
    availability = (uptime / total_time) * 100
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_time_minutes": total_time,
        "uptime_minutes": uptime,
        "downtime_minutes": downtime_minutes,
        "availability_percent": round(availability, 2),
        "requirement_met": availability >= 70.0
    }

# Example usage
start = datetime(2024, 11, 11)  # 72h before submission
end = datetime(2024, 11, 20)    # 144h after submission
downtime = 180  # 3 hours in minutes

result = calculate_availability(start, end, downtime)
print(json.dumps(result, indent=2))
```

---

## 7. Runbook

### Common Issues

#### Issue 1: High Error Rate

**Symptoms**: Error rate > 5%

**Diagnosis**:
1. Check logs: `az containerapp logs show --name finsightai-api --resource-group finsightai-resourcegroup`
2. Check health endpoint: `curl https://finsightai-api.../health`
3. Check model loading status

**Resolution**:
1. If models not loaded: Restart container app
2. If persistent: Roll back to previous container image
3. Check resource limits (CPU/memory)

#### Issue 2: High Latency

**Symptoms**: P95 latency > 1000ms

**Diagnosis**:
1. Check CPU/memory usage in Azure Portal
2. Check model file sizes
3. Check concurrent request count

**Resolution**:
1. Scale up: Increase CPU/memory allocation
2. Scale out: Increase replica count
3. Optimize: Add caching for model predictions

#### Issue 3: API Down

**Symptoms**: Health checks failing

**Diagnosis**:
1. Check container app status in Azure Portal
2. Check recent deployments
3. Check resource quotas

**Resolution**:
1. Restart container app
2. Roll back to last known good deployment
3. Check Azure status page for outages

---

## 8. Testing Monitoring Setup

### Test Metrics Endpoint
```bash
curl https://finsightai-api.../metrics
# Should return Prometheus format metrics
```

### Test Alerts
```bash
# Generate high load to trigger alerts
for i in {1..100}; do
  curl https://finsightai-api.../recommend \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test'$i'","symbols":["AAPL"],"model":"lstm"}' &
done
```

### Test Availability Tracking
```bash
# Monitor health endpoint
watch -n 5 'curl -s https://finsightai-api.../health | jq'
```

---

## Summary

✅ **Metrics**: Prometheus format at `/metrics`  
✅ **Dashboard**: Grafana with 5 key panels  
✅ **Alerts**: 4 critical/warning rules  
✅ **Availability**: 70% target over 216-hour window  
✅ **Runbook**: Common issues and resolutions

# FinSightAI Monitoring Setup Guide

This guide details how to set up monitoring for the FinSightAI API using Azure Monitor for Containers.

## Prerequisites

1.  An active Azure Subscription.
2.  The FinSightAI application deployed to Azure Container Apps.
3.  Azure CLI installed and configured.

## Step 1: Enable Monitoring in Your Container App Environment

Azure Container Apps can be integrated with Log Analytics workspaces to enable monitoring.

1.  **Navigate to your Container App Environment** in the Azure Portal.
2.  Under **Settings**, click on **Log Analytics workspace**.
3.  **Select an existing workspace** or **create a new one**. This workspace will store all the logs and metrics from your container apps.

## Step 2: Enable Prometheus Metrics Collection

The `prometheus-fastapi-instrumentator` library exposes a `/metrics` endpoint on our API. We need to configure our Azure Container App to scrape this endpoint.

1.  **Navigate to your `finsightai-api` Container App** in the Azure Portal.
2.  Under **Settings**, go to the **Dapr** section.
3.  **Enable Dapr** if it's not already enabled.
4.  In the Dapr configuration, you will need to add annotations to your component to tell Dapr to scrape the metrics.

Alternatively, and more simply if Dapr is not a core part of your application, you can configure **Azure Monitor Prometheus Scraping**.

1. Go to your **Log Analytics Workspace**.
2. Under **Settings**, select **Container insights**.
3. In the **Monitoring configuration** section, you can configure the collection of Prometheus metrics. You will need to create a config map that tells Azure Monitor where to scrape metrics from.

Here is a sample `ama-metrics-settings-configmap.yaml` you would apply to your cluster:

```yaml
kind: ConfigMap
apiVersion: v1.data:
  schema-version: v1
  config-version: ver1
  prometheus-config: |-
    scrape_configs:
    - job_name: 'finsightai-api'
      scrape_interval: 30s
      metrics_path: /metrics
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_app]
        action: keep
        regex: finsightai-api
```

## Step 3: Create a Dashboard

Once metrics are flowing into your Log Analytics workspace, you can visualize them.

1.  Go to **Azure Monitor** and click on **Workbooks**.
2.  Create a **New Workbook**.
3.  Add a new query and set the data source to your Log Analytics workspace.

### Key Queries (PromQL)

*   **P95 Latency (for `/recommend` endpoint):**
    ```promql
    histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{handler="/recommend"}[5m])) by (le))
    ```

*   **Error Rate (5xx errors):**
    ```promql
    sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
    ```

*   **Uptime/Availability (based on successful health checks):**
    *This is simpler to monitor via Azure's built-in availability tests or by tracking successful responses vs. total responses.*
    ```promql
    sum(rate(http_requests_total{handler="/health", status_code="200"}[5m])) > 0
    ```
    *A more robust uptime can be calculated by dividing successful requests by total requests.*

## Step 4: Configure Alerts

1.  In **Azure Monitor**, go to **Alerts** and create a **New alert rule**.
2.  Set the **scope** to your Log Analytics workspace.
3.  For the **condition**, use a custom log search query.

### Sample Alert Rules

*   **High P95 Latency:**
    *   **Query:** `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{handler="/recommend"}[5m])) by (le)) > 0.5`
    *   **Logic:** Fire an alert if the 95th percentile latency for the `/recommend` endpoint is greater than 500ms.
    *   **Frequency:** Evaluate every 5 minutes.

*   **High Error Rate:**
    *   **Query:** `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5`
    *   **Logic:** Fire an alert if the error rate exceeds 5% over a 5-minute period.
    *   **Frequency:** Evaluate every 5 minutes.

By following these steps, you will have a robust monitoring and alerting system for your FinSightAI API.

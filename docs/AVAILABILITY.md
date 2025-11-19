# FinSightAI API Availability

This document defines the availability metric for the FinSightAI prediction API and the service level objective (SLO).

## Availability Definition

Availability is a measure of the API's success in responding to valid client requests. It is calculated as the ratio of successful requests to total valid requests over a specific time window.

**Formula:**
\[
\text{Availability} = \frac{\text{Successful Requests}}{\text{Total Valid Requests}} \times 100\%
\]

-   **Successful Requests**: Any API call to the `/recommend` endpoint that returns an HTTP `200 OK` status code.
-   **Total Valid Requests**: All non-malformed requests sent to the `/recommend` endpoint. This excludes requests that return `4xx` client errors (e.g., `400 Bad Request`, `422 Unprocessable Entity`), as these are not service failures. It includes all `200 OK` and `5xx` server error responses.

## Service Level Objective (SLO)

The target availability for the FinSightAI API is **≥ 70%** over a rolling 28-day window.

This SLO acknowledges that in a machine learning context, occasional prediction failures for complex inputs are possible and that transient infrastructure issues can occur. The 70% target ensures a generally reliable service while being realistic for a complex, multi-component system.

## Monitoring

Availability is actively monitored using the "API Availability (%)" chart on the Azure Monitor dashboard. This chart uses the following KQL query to calculate the metric based on data scraped from the `/metrics` endpoint:

```kql
// API Availability (%)
PrometheusMetrics
| where Name == "http_requests_total"
| extend http_status_code = tostring(parse_json(Labels).status)
| summarize total_requests = sum(Value) by bin(TimeGenerated, 5m), http_status_code
| summarize successful_requests = sumif(total_requests, http_status_code !startswith "5"), all_requests = sum(total_requests) by TimeGenerated
| extend availability_rate = todouble(successful_requests) / all_requests * 100
| project TimeGenerated, availability_rate
| render timechart
```

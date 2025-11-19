# FinSightAI API Alerting Runbook

This document outlines the procedures to follow when an alert is triggered for the FinSightAI API.

## Alerting Policies

| Alert Name          | Severity | Description                                           | Threshold                                 | Action                                                           |
| ------------------- | -------- | ----------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------- |
| **High P95 Latency**  | Warning  | The 95th percentile request latency is too high.      | > 500ms for 5 minutes                     | Investigate performance bottlenecks (CPU, memory, model loading). |
| **High Error Rate**   | Critical | The percentage of server-side errors (5xx) is high. | > 5% over 5 minutes                       | Check application logs for exceptions. Consider rollback.        |
| **API Unhealthy**     | Critical | The `/health` endpoint is failing or unreachable.   | Health check fails for 2 consecutive mins | Restart the container app. Check for deployment issues.          |

---

## Triage and Investigation Steps

### Initial Triage (All Alerts)

1.  **Acknowledge the Alert:** Acknowledge the alert in your monitoring tool (e.g., Azure Monitor Alerts, PagerDuty) to notify the team you are investigating.
2.  **Check the Monitoring Dashboard:** Open the FinSightAI Grafana or Azure Monitor dashboard to get a visual overview of the system's state. Look for correlations:
    *   Did latency spike at the same time as the error rate?
    *   Is there a surge in request volume?
    *   Are CPU or memory resources saturated?
3.  **Check Application Logs:**
    *   Navigate to your `finsightai-api` Container App in the Azure Portal.
    *   Go to **Monitoring -> Log stream**.
    *   Look for any obvious error messages, stack traces, or exceptions that occurred around the time of the alert.

---

## Specific Alert Playbooks

### Playbook: High P95 Latency

**Symptoms:**
*   Alert fires for `High P95 Latency`.
*   Users may report that the API is slow.
*   The latency graph on the dashboard shows a sustained spike.

**Potential Causes:**
*   High CPU or memory utilization.
*   A slow downstream dependency (though this API has few).
*   A recent deployment introduced a performance regression.
*   Inefficient model loading or prediction logic.
*   A large influx of traffic.

**Investigation & Remediation:**
1.  **Check Resource Utilization:** In the Azure Portal for the Container App, view the **Metrics** for CPU and Memory Usage. If they are near 100%, this is the likely cause.
    *   **Remediation:** Scale the Container App. You can increase the CPU/memory allocated to the existing replica or increase the number of replicas (scale-out).
2.  **Review Recent Deployments:** Check the deployment history in GitHub Actions. If the issue started immediately after a new deployment, the new code is the likely cause.
    *   **Remediation:** Consider rolling back to the previous stable deployment. The `FinSightAI CI/CD` workflow can be manually triggered with a specific commit SHA to redeploy an older version.
3.  **Analyze Logs for Slow Operations:** Look for logs that indicate long processing times for specific symbols or models.
    *   **Remediation:** If a specific model is causing slowness, this may require deeper code-level analysis and optimization.

### Playbook: High Error Rate

**Symptoms:**
*   Alert fires for `High Error Rate`.
*   The API may be returning `500 Internal Server Error` responses.
*   The error rate graph on the dashboard is elevated.

**Potential Causes:**
*   A bug in the code that is causing unhandled exceptions.
*   Invalid or corrupt model files.
*   Failure to connect to external services (like Kafka for provenance logging, though this should be fault-tolerant).
*   Resource exhaustion (CPU, memory, or disk space).

**Investigation & Remediation:**
1.  **Analyze Application Logs:** This is the most critical step. Look for Python stack traces in the **Log stream**. The error message will pinpoint the exact line of code that is failing.
2.  **Common Log Errors & Fixes:**
    *   `ModuleNotFoundError`, `ImportError`: A dependency might be missing. Check `requirements.txt` and the CI/CD workflow.
    *   `FileNotFoundError`: The application might be trying to load a model file that doesn't exist. This could happen after a bad retraining run. Verify the contents of the `model-registry` in Azure Blob Storage.
    *   `ValueError`, `TypeError`: These often point to data-related issues. A model might be receiving input in an unexpected format.
3.  **Rollback:** If the cause is a recent deployment, the quickest path to recovery is to roll back to the previous version.
4.  **Check Model Registry:** If errors seem related to model loading, inspect the Azure Blob Storage container for the `model-registry`. Ensure the latest version's files are present and not corrupted.

---
## Escalation

If you are unable to resolve the issue within 30 minutes, escalate to the project lead. Provide a summary of the alert, the investigation steps you have taken, and links to relevant logs or dashboard views.

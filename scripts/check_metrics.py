"""Quick script to check metrics endpoint"""
import requests

api_url = "https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io"
response = requests.get(f"{api_url}/metrics", timeout=10)

custom_metrics = [
    'http_requests_total',
    'http_request_duration_seconds',
    'api_uptime_seconds',
    'api_health_status',
    'model_predictions_total'
]

print("\nCustom FinSightAI Metrics:")
for metric in custom_metrics:
    found = metric in response.text
    status = "FOUND" if found else "NOT FOUND"
    print(f"  {metric}: {status}")

# Show uptime value
uptime_lines = [l for l in response.text.split('\n') if 'api_uptime_seconds' in l and not l.startswith('#')]
if uptime_lines:
    print(f"\nUptime value:")
    print(f"  {uptime_lines[0]}")

# Show request count
request_lines = [l for l in response.text.split('\n') if 'http_requests_total{' in l]
if request_lines:
    print(f"\nRequest counts (sample):")
    for line in request_lines[:5]:
        print(f"  {line[:100]}")



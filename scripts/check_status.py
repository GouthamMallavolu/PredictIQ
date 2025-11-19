"""Quick status check"""
import requests

api_url = "https://finsightai-api.orangegrass-19668bba.eastus.azurecontainerapps.io"
try:
    r = requests.get(f"{api_url}/health", timeout=10)
    data = r.json()
    print(f"Status: {data['status']}")
    print(f"Models Ready: {data.get('models_ready', False)}")
    print(f"Uptime: {data.get('uptime', 'N/A')}")
    print(f"Models Loaded: {data.get('models_loaded', {})}")
except Exception as e:
    print(f"Error: {e}")


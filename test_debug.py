import requests
import json
import time

# Wait for server to start
time.sleep(3)

# Test the recommendation endpoint
query = "Quiero veruna película animada tipo Shrek con mis hijos"
user_id = "test_user_001"

url = f"http://localhost:8000/api/v1/recommendations"
params = {
    "query": query,
    "user_id": user_id
}

try:
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

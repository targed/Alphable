import os
import requests
import json

# IMPORTANT: Replace this with your actual key from Woogles settings or set WOOGLES_API_KEY environment variable
API_KEY = os.environ.get("WOOGLES_API_KEY", "YOUR_API_KEY_HERE")

if API_KEY == "YOUR_API_KEY_HERE":
    print("WARNING: You are using the placeholder API_KEY. Please replace it with your real key.")

user = "BasicBot"
# Based on documentation, the metadata service handles game history
api_url = 'https://woogles.io/api/game_service.GameMetadataService/GetRecentGames'

headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "username": user,
    "num_games": 500,
    "offset": 0
}

print(f"Attempting authenticated POST request to {api_url}...")

try:
    response = requests.post(api_url, headers=headers, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")

    if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
        data = response.json()
        # Protobuf-to-JSON usually keeps the snake_case names defined in .proto
        games = data.get('game_info', [])
        print(f"Success! Found {len(games)} games.")
        with open('woogles.json', 'w') as f:
            json.dump(data, f)
    else:
        print(f"\n--- ERROR: Unexpected Response ---")
        print(f"Status: {response.status_code}")
        print(f"Response Body: {response.text[:500]}")

except Exception as e:
    print(f"An error occurred: {e}")

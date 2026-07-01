import requests

# Trigger the local server endpoint to start an outbound call.
response = requests.post(
    "http://127.0.0.1:5050/call",
)

print(response.json())
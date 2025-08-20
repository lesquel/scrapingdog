import requests

url = "https://api.scrapingdog.com/linkedin/"
params = {
    "api_key": "68a52eba6cd6f18dcca57bd2",
    "type": "company",
    "linkId": "amazon"
}
response = requests.get(url, params=params)
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Request failed with status code: {response.status_code}")
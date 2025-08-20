import requests

api_key = '5eaa61a6e562fc52fe763tr516e4653'
profileId = 'sama'


params = {
    'api_key': api_key,
    'profileId': profileId
}

response = requests.get('https://api.scrapingdog.com/x/profile', params=params)

if response.status_code == 200:
    # Parse the JSON response using response.json()
    response_data = response.json()

    # Now you can work with the response_data as a Python dictionary
    print(response_data)
else:
    print(f'Request failed with status code: {response.status_code}')
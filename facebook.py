import requests

access_token = "TU_ACCESS_TOKEN"
page_id = "cocacola"  # ID o username de la página
url = f"https://graph.facebook.com/v17.0/{page_id}?fields=name,about,followers_count,posts{{message,created_time,shares,likes.summary(true),comments.summary(true)}}&access_token={access_token}"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {response.status_code} - {response.text}")

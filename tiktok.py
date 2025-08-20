import requests
from bs4 import BeautifulSoup
import pandas as pd

l=[]
obj={}

params={
  'api_key': '68a52eba6cd6f18dcca57bd2',
  'url': 'https://www.tiktok.com/@kimkardashian?lang=en',
  'dynamic': 'true',
  'wait': '10000',
  }

response = requests.get("https://api.scrapingdog.com/scrape", params=params)


print("status code is ",response.status_code)

soup = BeautifulSoup(response.text, 'html.parser')

try:
    obj["username"]=soup.find("h1").text
except:
    obj["username"]=None

try:
    obj["profile"]=soup.find("img",{"class":"css-1zpj2q-ImgAvatar"}).get('src')
except:
    obj["profile"]=None


try:
    obj["following"]=soup.find("strong",{"title":'Following'}).text
except:
    obj["following"]=None

try:
    obj["followers"]=soup.find("strong",{"title":'Followers'}).text
except:
    obj["followers"]=None

try:
    obj["Bio"]=soup.find("h2",{"data-e2e":'user-bio'}).text
except:
    obj["Bio"]=None

try:
    obj["website"]=soup.find("a",{"data-e2e":"user-link"}).get('href')
except:
    obj["website"]=None

l.append(obj)
print(l)
df = pd.DataFrame(l)
df.to_csv('tiktok.csv', index=False, encoding='utf-8')
import requests

# URL for the request
url = "https://www.instagram.com/api/v1/users/web_profile_info/?username=erimoreirac"
o={}
post={}
allpost=[]
insta_arr=[]
# Headers for the request
headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "x-ig-app-id": "936619743392459",
}

# Make the GET request
response = requests.get(url, headers=headers)

# Print the response
if response.status_code == 200:
    allData = response.json()['data']['user']
    o['biography']=allData['biography']
    o['link_in_bio']=allData['bio_links']
    o['followers']=allData['edge_followed_by']['count']
    o['following']=allData['edge_follow']['count']
    o['num_posts']=allData['edge_owner_to_timeline_media']['count']
    o['profile_pic_url']=allData['profile_pic_url_hd']
    o['verified']=allData['is_verified']
    allPosts=allData['edge_owner_to_timeline_media']['edges']

    for i in range(0,len(allPosts)):
        if(allPosts[i]['node']['is_video']==True):
            post['display_url']=allPosts[i]['node']['display_url']
            post['video_view_count']=allPosts[i]['node']['video_view_count']
            post['video_url']=allPosts[i]['node']['video_url']
            post['num_comments']=allPosts[i]['node']['edge_media_to_comment']['count']
            post['num_likes']=allPosts[i]['node']['edge_liked_by']['count']
        else:
            post['display_url']=allPosts[i]['node']['display_url']
            post['num_comments']=allPosts[i]['node']['edge_media_to_comment']['count']
            post['num_likes']=allPosts[i]['node']['edge_liked_by']['count']

        allpost.append(post)
        post={}


    insta_arr.append(o)
    insta_arr.append(allpost)
    print(insta_arr)
else:
    print(f"Error: {response.status_code} - {response.text}")
import requests
import json
import os
from datetime import datetime
from googleapiclient.discovery import build

# --- API KEYS (These stay 'hidden' for safety) ---
TWITCH_ID = os.environ.get('TWITCH_ID')
TWITCH_SECRET = os.environ.get('TWITCH_SECRET')
YT_KEY = os.environ.get('YT_KEY')

def get_twitch():
    print("Fetching Twitch...")
    try:
        auth = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={TWITCH_ID}&client_secret={TWITCH_SECRET}&grant_type=client_credentials").json()
        headers = {'Client-ID': TWITCH_ID, 'Authorization': f'Bearer {auth["access_token"]}'}
        # Category ID 509658 = Just Chatting
        res = requests.get("https://api.twitch.tv/helix/clips?game_id=509658&first=50", headers=headers).json()
        
        return [{
            "title": c['title'],
            "streamer": c['broadcaster_name'],
            "views": c['view_count'],
            "platform": "Twitch",
            "url": c['url']
        } for c in res.get('data', [])]
    except Exception as e:
        print(f"Twitch Error: {e}")
        return []

def get_youtube():
    print("Fetching YouTube (Strict Filter)...")
    try:
        youtube = build('youtube', 'v3', developerKey=YT_KEY)
        request = youtube.search().list(
            q="streamer clips", 
            part="snippet", 
            type="video", 
            videoDuration="short", 
            maxResults=50, 
            order="viewCount",
            videoCategoryId="20" # Gaming
        )
        res = request.execute()
        
        video_ids = [item['id']['videoId'] for item in res['items']]
        stats = youtube.videos().list(id=",".join(video_ids), part="statistics,liveStreamingDetails").execute()
        
        yt_clips = []
        for i, item in enumerate(stats['items']):
            # Filter out full VODs
            if 'liveStreamingDetails' not in item:
                yt_clips.append({
                    "title": item['snippet']['title'],
                    "streamer": item['snippet']['channelTitle'],
                    "views": int(item['statistics']['viewCount']),
                    "platform": "YouTube",
                    "url": f"https://youtube.com/watch?v={item['id']}"
                })
        return yt_clips
    except Exception as e:
        print(f"YouTube Error: {e}")
        return []

def update_site():
    all_data = get_twitch() + get_youtube()
    all_data.sort(key=lambda x: x['views'], reverse=True)
    
    final_list = []
    for i, item in enumerate(all_data[:100], 1):
        item['rank'] = i
        final_list.append(item)

    output = {
        "last_updated": datetime.now().strftime("%B %d, %Y"),
        "clips": final_list
    }

    # This creates the data.json file automatically!
    with open('data.json', 'w') as f:
        json.dump(output, f, indent=4)
    print("Success! data.json created.")

if __name__ == "__main__":
    update_site()

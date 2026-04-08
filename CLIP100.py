import requests
import json
import os
from datetime import datetime, timedelta

# --- KEYS come from GitHub Secrets, never hardcoded ---
TWITCH_ID     = os.environ.get('TWITCH_ID')
TWITCH_SECRET = os.environ.get('TWITCH_SECRET')
YT_KEY        = os.environ.get('YT_KEY')

def get_twitch_token():
    r = requests.post(
        'https://id.twitch.tv/oauth2/token',
        params={
            'client_id': TWITCH_ID,
            'client_secret': TWITCH_SECRET,
            'grant_type': 'client_credentials'
        }
    )
    return r.json().get('access_token')

def get_twitch_clips(token):
    print("Fetching Twitch clips (all categories)...")
    headers = {
        'Client-ID': TWITCH_ID,
        'Authorization': f'Bearer {token}'
    }
    # Last 7 days, no game filter = ALL categories
    started_at = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'
    clips = []
    cursor = None

    # Pull up to 100 clips across all categories
    for _ in range(2):
        params = {
            'started_at': started_at,
            'first': 50
        }
        if cursor:
            params['after'] = cursor

        r = requests.get(
            'https://api.twitch.tv/helix/clips',
            headers=headers,
            params=params
        )
        data = r.json()
        batch = data.get('data', [])
        if not batch:
            break

        for c in batch:
            clips.append({
                'title':    c['title'],
                'streamer': c['broadcaster_name'],
                'views':    c['view_count'],
                'peak':     round(c['view_count'] * 0.22),
                'platform': 'Twitch',
                'category': 'Gaming',
                'url':      c['url']
            })

        cursor = data.get('pagination', {}).get('cursor')
        if not cursor:
            break

    print(f"  Got {len(clips)} Twitch clips")
    return clips

def get_youtube_clips():
    print("Fetching YouTube stream clips...")
    if not YT_KEY:
        print("  No YouTube key, skipping")
        return []

    clips = []
    # Search specifically for stream highlight/clip content
    search_terms = ['twitch clip', 'stream highlight', 'streamer moments']

    for term in search_terms:
        try:
            # Search for videos
            search_r = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'key':            YT_KEY,
                    'q':              term,
                    'part':           'snippet',
                    'type':           'video',
                    'videoDuration':  'short',
                    'maxResults':     15,
                    'order':          'viewCount',
                    'publishedAfter': (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
                }
            )
            items = search_r.json().get('items', [])
            if not items:
                continue

            video_ids = [i['id']['videoId'] for i in items]

            # Get real view counts
            stats_r = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                params={
                    'key':  YT_KEY,
                    'id':   ','.join(video_ids),
                    'part': 'snippet,statistics'
                }
            )
            for v in stats_r.json().get('items', []):
                view_count = int(v['statistics'].get('viewCount', 0))
                clips.append({
                    'title':    v['snippet']['title'],
                    'streamer': v['snippet']['channelTitle'],
                    'views':    view_count,
                    'peak':     round(view_count * 0.18),
                    'platform': 'YouTube',
                    'category': 'Gaming',
                    'url':      f"https://youtube.com/watch?v={v['id']}"
                })
        except Exception as e:
            print(f"  YouTube error for '{term}': {e}")

    print(f"  Got {len(clips)} YouTube clips")
    return clips

def build_chart():
    token = get_twitch_token()
    if not token:
        print("ERROR: Could not get Twitch token. Check TWITCH_ID and TWITCH_SECRET.")
        return

    all_clips = get_twitch_clips(token) + get_youtube_clips()

    if not all_clips:
        print("ERROR: No clips found from any platform.")
        return

    # Sort by views highest to lowest
    all_clips.sort(key=lambda x: x['views'], reverse=True)

    # Assign ranks 1-100
    ranked = []
    for i, clip in enumerate(all_clips[:100], 1):
        clip['rank'] = i
        clip['prev'] = None  # Could track previous rank in future
        ranked.append(clip)

    output = {
        'last_updated': datetime.utcnow().strftime('%B %d, %Y'),
        'clips': ranked,
        'streams': []  # Placeholder for streams tab - add later
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS: data.json created with {len(ranked)} clips.")

if __name__ == '__main__':
    build_chart()

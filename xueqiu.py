import os
import requests
from bs4 import BeautifulSoup
from wechatpy import WeChatClient
from wechatpy.client.api import WeChatMessage
import time

# Configuration from Environment Variables
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
USER_IDS = os.environ.get("USER_IDS", "").split(";")
TEMPLATE_ID = os.environ.get("TEMPLATE_ID_XUEQIU")
XUEQIU_USER_ID = "2292705444"
LAST_ID_FILE = "xueqiu_last_id.txt"

def format_text(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text()

def get_latest_posts():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'https://xueqiu.com/u/{XUEQIU_USER_ID}'
    }
    
    # Get cookies
    try:
        session.get('https://xueqiu.com/', headers=headers, timeout=10)
        time.sleep(1)
        session.get(f'https://xueqiu.com/u/{XUEQIU_USER_ID}', headers=headers, timeout=10)
        time.sleep(1)
    except Exception as e:
        print(f"Error getting cookies: {e}")
        return []

    api_url = f'https://xueqiu.com/v4/statuses/user_timeline.json?user_id={XUEQIU_USER_ID}&page=1&type=0&count=20'
    try:
        response = session.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Error fetching timeline: {response.status_code}")
            return []
        return response.json().get('statuses', [])
    except Exception as e:
        print(f"Error calling API: {e}")
        return []

def send_wechat_notification(content, post_time):
    if not content or not APP_ID or not APP_SECRET or not TEMPLATE_ID:
        print("Missing WeChat configuration, skipping push.")
        return

    client = WeChatClient(APP_ID, APP_SECRET)
    wm = WeChatMessage(client)
    
    # Split content into 20-character chunks for WeChat template limits
    chunk_size = 20
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
    
    data = {
        "name": {"value": "雪球-2292705444"},
        "time": {"value": post_time},
    }
    
    # Fill note1 to note5
    for i in range(5):
        val = chunks[i] if i < len(chunks) else ""
        data[f"note{i+1}"] = {"value": val}

    for user_id in USER_IDS:
        if user_id:
            try:
                res = wm.send_template(user_id, TEMPLATE_ID, data)
                print(f"Push to {user_id}: {res}")
            except Exception as e:
                print(f"Error pushing to {user_id}: {e}")

def main():
    # Read last processed ID
    last_id = 0
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r") as f:
            try:
                last_id = int(f.read().strip())
            except ValueError:
                pass

    statuses = get_latest_posts()
    if not statuses:
        print("No posts found or error occurred.")
        return

    # Filter new posts and sort by ID ascending (chronological)
    new_posts = [s for s in statuses if s.get('id', 0) > last_id]
    new_posts.sort(key=lambda x: x.get('id', 0))

    if not new_posts:
        print("No new posts.")
        return

    for post in new_posts:
        post_id = post.get('id')
        text = format_text(post.get('text'))
        
        # Handle retweets/quotes
        retweet = post.get('retweeted_status')
        if retweet:
            rt_user = retweet.get('user', {}).get('screen_name', 'Unknown')
            rt_text = format_text(retweet.get('text'))
            text = f"{text} // 转发 @{rt_user}: {rt_text}"
        
        # Format time (created_at is typically ms timestamp)
        created_at = post.get('created_at', 0)
        post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at/1000))
        
        print(f"Processing new post {post_id}...")
        send_wechat_notification(text, post_time)
        
        # Update last_id immediately after sending each post to be safe
        last_id = post_id
        with open(LAST_ID_FILE, "w") as f:
            f.write(str(last_id))

if __name__ == "__main__":
    main()

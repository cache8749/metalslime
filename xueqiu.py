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
# Xueqiu sits behind an Aliyun WAF JS challenge: plain requests only ever get the
# `acw_tc` cookie, never `xq_a_token`, so the JSON API returns an HTML challenge page.
# Supply a logged-in browser Cookie header here (copy from DevTools → Network → any
# xueqiu.com request → Request Headers → Cookie). The cookie expires periodically and
# must be refreshed. Without it the legacy unauthenticated handshake is attempted as a
# best-effort fallback (will usually be blocked by the WAF).
XUEQIU_COOKIE = os.environ.get("XUEQIU_COOKIE", "").strip()
XUEQIU_USER_ID = "2292705444"
LAST_ID_FILE = "xueqiu_last_id.txt"

# WeChat template messages truncate each {{var.DATA}} field at ~20 chars with "...".
# Split content across N fields concatenated in the template to extend the cap.
CONTENT_CHUNK_SIZE = 19
CONTENT_CHUNK_COUNT = 10

def format_text(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    # Xueqiu renders emoji as <img alt="[狗头]" ...>; replace with the alt/title so it survives get_text()
    for img in soup.find_all('img'):
        label = img.get('alt') or img.get('title') or ''
        img.replace_with(label)
    return soup.get_text()

def _looks_like_waf(text):
    # The Aliyun WAF challenge page is HTML, not JSON; these markers identify it.
    head = text[:2048]
    return any(marker in head for marker in ('renderData', '_waf_', 'aliyun_waf'))

def get_latest_posts():
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'https://xueqiu.com/u/{XUEQIU_USER_ID}'
    }

    if XUEQIU_COOKIE:
        # A logged-in cookie carries xq_a_token and gets us straight past the WAF.
        headers['Cookie'] = XUEQIU_COOKIE
    else:
        # Best-effort legacy handshake (usually blocked by the WAF now).
        try:
            session.get('https://xueqiu.com/', headers=headers, timeout=10)
            time.sleep(1)
            session.get(f'https://xueqiu.com/u/{XUEQIU_USER_ID}', headers=headers, timeout=10)
            time.sleep(1)
        except Exception as e:
            print(f"Error getting cookies: {e}")
            return []

    api_url = f'https://xueqiu.com/v4/statuses/user_timeline.json?user_id={XUEQIU_USER_ID}&page=1&count=20'
    try:
        response = session.get(api_url, headers=headers, timeout=10)
    except Exception as e:
        print(f"Error calling API: {e}")
        return []

    if response.status_code != 200:
        print(f"Error fetching timeline: {response.status_code}")
        return []

    if 'application/json' not in response.headers.get('content-type', '') or _looks_like_waf(response.text):
        if XUEQIU_COOKIE:
            print("Blocked by Xueqiu WAF despite cookie — the XUEQIU_COOKIE has likely "
                  "expired. Log into xueqiu.com and refresh the cookie.")
        else:
            print("Blocked by Xueqiu WAF (no XUEQIU_COOKIE set). Set XUEQIU_COOKIE to a "
                  "logged-in browser Cookie header so the request can pass the challenge.")
        return []

    try:
        return response.json().get('statuses', [])
    except ValueError as e:
        print(f"Error parsing API response as JSON: {e}")
        return []

def chunk_content(text):
    capacity = CONTENT_CHUNK_SIZE * CONTENT_CHUNK_COUNT
    truncated = len(text) > capacity
    if truncated:
        text = text[:capacity - 1] + "…"
    return [text[i * CONTENT_CHUNK_SIZE:(i + 1) * CONTENT_CHUNK_SIZE]
            for i in range(CONTENT_CHUNK_COUNT)]

def send_wechat_notification(content, post_time, screen_name):
    if not content or not APP_ID or not APP_SECRET or not TEMPLATE_ID:
        print("Missing WeChat configuration, skipping push.")
        return

    client = WeChatClient(APP_ID, APP_SECRET)
    wm = WeChatMessage(client)

    data = {
        "name": {"value": screen_name},
        "time": {"value": post_time},
    }
    for i, chunk in enumerate(chunk_content(content), start=1):
        data[f"content{i}"] = {"value": chunk}

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

    def extract_body(p):
        # Xueqiu returns the body in different fields depending on post type:
        # short status uses `text`; long-form 长文 uses `description` + `title`.
        for key in ('description', 'text'):
            body = format_text(p.get(key))
            if body and body.strip() and body.strip() != '查看全文':
                return body.strip()
        return format_text(p.get('title')).strip()

    for post in new_posts:
        post_id = post.get('id')
        text = extract_body(post)

        # Handle retweets/quotes
        retweet = post.get('retweeted_status')
        if retweet:
            rt_user = retweet.get('user', {}).get('screen_name', 'Unknown')
            rt_text = extract_body(retweet)
            text = f"{text} // 转发 @{rt_user}: {rt_text}"

        if not text:
            text = "(无内容)"
        
        # Format time (created_at is typically ms timestamp)
        created_at = post.get('created_at', 0)
        post_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created_at/1000))
        
        screen_name = (post.get('user') or {}).get('screen_name') or f"雪球-{XUEQIU_USER_ID}"

        print(f"Processing new post {post_id}...")
        send_wechat_notification(text, post_time, screen_name)
        
        # Update last_id immediately after sending each post to be safe
        last_id = post_id
        with open(LAST_ID_FILE, "w") as f:
            f.write(str(last_id))

if __name__ == "__main__":
    main()

# Xueqiu Post Monitor

Automated script to monitor a specific Xueqiu user and push new posts to WeChat.

## Setup

1. **GitHub Secrets**:
   - `APP_ID`: Your WeChat Test Account AppID.
   - `APP_SECRET`: Your WeChat Test Account AppSecret.
   - `USER_IDS`: WeChat OpenIDs (separated by `;`).
   - `TEMPLATE_ID_XUEQIU`: The Template ID for Xueqiu notifications.
   - `XUEQIU_COOKIE`: A logged-in Cookie header for xueqiu.com (see below). Required —
     Xueqiu now sits behind an Aliyun WAF JS challenge that blocks unauthenticated requests.

   **Getting `XUEQIU_COOKIE`**: Log into xueqiu.com in a browser, open DevTools →
   Network, click any request to `xueqiu.com`, and copy the full `Cookie` value from its
   Request Headers (it must include `xq_a_token`). Paste it as the secret. The cookie
   expires periodically (days–weeks); when pushes stop and the Action logs
   "the XUEQIU_COOKIE has likely expired", refresh the secret with a new cookie.

2. **WeChat Template**:
   Follow the instructions in `XUEQIU_TEMPLATE.md` to set up your template.

## Workflow
The scraper runs every 5 minutes via GitHub Actions. It maintains state in `xueqiu_last_id.txt`.

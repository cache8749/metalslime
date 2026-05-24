# Xueqiu Post Monitor

Automated script to monitor a specific Xueqiu user and push new posts to WeChat.

## Setup

1. **GitHub Secrets**:
   - `APP_ID`: Your WeChat Test Account AppID.
   - `APP_SECRET`: Your WeChat Test Account AppSecret.
   - `USER_IDS`: WeChat OpenIDs (separated by `;`).
   - `TEMPLATE_ID_XUEQIU`: The Template ID for Xueqiu notifications.

2. **WeChat Template**:
   Follow the instructions in `XUEQIU_TEMPLATE.md` to set up your template.

## Workflow
The scraper runs every 5 minutes via GitHub Actions. It maintains state in `xueqiu_last_id.txt`.

#!/usr/bin/env python3
"""
Check webhook status for the bot
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found in .env")
    exit(1)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"

try:
    response = requests.get(url)
    data = response.json()

    if data.get('ok'):
        webhook_info = data.get('result', {})
        webhook_url = webhook_info.get('url', '')
        pending_updates = webhook_info.get('pending_update_count', 0)

        print("🔍 Webhook Status:")
        print(f"URL: {webhook_url}")
        print(f"Pending updates: {pending_updates}")

        if webhook_url:
            print("⚠️  Webhook is SET - this may be why bot is still responding")
            print("💡 To remove webhook, you can use /deleteWebhook")
        else:
            print("✅ No webhook set - bot should not be responding")
    else:
        print(f"❌ Error: {data.get('description', 'Unknown error')}")

except Exception as e:
    print(f"❌ Request failed: {e}")

import sys
import os
sys.path.append(os.path.dirname(__file__))
from send_telegram import send_telegram_message

print("🧪 Testing Telegram Link...")
result = send_telegram_message("🤖 Hello from Pahang Hotel Intelligence! If you receive this, your Telegram Bot is successfully linked.")

if result:
    print("\n✅ SUCCESS! Your Telegram Bot is working.")
else:
    print("\n❌ FAILED. Please check configs/secrets.yaml and ensure your Token and Chat ID are correct.")

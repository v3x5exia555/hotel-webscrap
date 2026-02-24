import sys
import os
sys.path.append(os.path.dirname(__file__))
from send_whatsapp import send_message

print("🧪 Testing WhatsApp Link...")
result = send_message("Hello from Pahang Hotel Intelligence! 🟢 If you receive this, your terminal is successfully linked.")

if result:
    print("\n✅ SUCCESS! You are linked.")
else:
    print("\n❌ FAILED. Please check configs/secrets.yaml and ensure your Phone number (+60...) and API Key are correct.")

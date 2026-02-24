import sys
import yaml
import requests
import os

def send_telegram_message(message):
    secrets_path = os.path.join(os.path.dirname(__file__), "../configs/secrets.yaml")
    if not os.path.exists(secrets_path):
        print(f"Error: {secrets_path} not found.")
        return False
    
    with open(secrets_path, "r") as f:
        config = yaml.safe_load(f)
    
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")
    
    if not token or not chat_id or "YOUR_" in str(token) or "YOUR_" in str(chat_id):
        print("Error: Telegram credentials not configured in configs/secrets.yaml")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("Telegram message sent successfully!")
            return True
        else:
            print(f"Failed to send Telegram message. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 send_telegram.py 'your message'")
    else:
        msg = " ".join(sys.argv[1:])
        send_telegram_message(msg)

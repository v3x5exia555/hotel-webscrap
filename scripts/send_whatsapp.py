import sys
import yaml
import requests
import os

def send_message(message):
    secrets_path = os.path.join(os.path.dirname(__file__), "../configs/secrets.yaml")
    if not os.path.exists(secrets_path):
        print(f"Error: {secrets_path} not found.")
        return False
    
    with open(secrets_path, "r") as f:
        config = yaml.safe_load(f)
    
    phone = config.get("whatsapp_phone")
    api_key = config.get("whatsapp_api_key")
    
    if not phone or not api_key or "YOUR_" in str(phone) or "YOUR_" in str(api_key):
        print("Error: WhatsApp credentials not configured in configs/secrets.yaml")
        return False

    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={requests.utils.quote(message)}&apikey={api_key}"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            print("Message sent successfully!")
            return True
        else:
            print(f"Failed to send message. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 send_whatsapp.py 'your message'")
    else:
        msg = " ".join(sys.argv[1:])
        send_message(msg)

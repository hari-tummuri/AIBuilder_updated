import threading
import time
# import requests
import socket
from datetime import datetime
from itassist.utils.sync_utils import sync_json_to_mysql
from django.core.management import call_command


def check_internet_connection():
    try:
        # requests.get("https://www.google.com", timeout=5)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False
    
sync_lock = threading.Lock()

def background_sync_runner():
    print("🔁 sync_loop running...")
    while True:
        if check_internet_connection():
            with sync_lock:
                print(f"🌐 Internet available at {datetime.now()}, starting sync...")
                try:
                    call_command('sync_conversations_to_azure')
                    # sync_json_to_mysql()
                except Exception as e:
                    print(f"⚠️ Sync failed: {e}")
            time.sleep(600)  # 10 minutes
        else:
            print(f"❌ No internet at {datetime.now()}, retrying in 5 seconds...")
            time.sleep(5)

def start_background_sync():
    print("🧵 Sync thread started")
    thread = threading.Thread(target=background_sync_runner, daemon=True)
    thread.start()
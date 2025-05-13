from django.apps import AppConfig
from threading import Thread
import os
import sys
from itassist.services.sync_runner import start_background_sync

thread_started = False


class ItassistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itassist'

    def ready(self):
        
        # global thread_started

        # if thread_started:
        #     return
        
        # if os.environ.get('RUN_MAIN') != 'true':
        #     return
        # print("✅ AppConfig.ready() called")
        # start_background_sync()
        # thread_started = True

        global thread_started

        if thread_started:
            return

        print("✅ AppConfig.ready() called")
        # Use process ID check to avoid reloader process (specific to Uvicorn with --reload)
        if os.environ.get("RUN_MAIN") == "true" or (
            "uvicorn" in sys.argv[0].lower() and os.getppid() != os.getpid()
        ):
            print("🧵 Starting sync thread...")
            start_background_sync()
            thread_started = True
        else:
            print("🚫 Not the main server process, skipping thread.")


         # Prevent duplicate thread starts (especially in dev mode)
        # if os.environ.get('RUN_MAIN') == 'true':
        #     # Check if thread is already running (optional safeguard)
        #     if not hasattr(self, 'sync_thread_started'):
        #         self.sync_thread_started = True
        #         thread = Thread(target=background_sync_runner, daemon=True)
        #         thread.start()
            
            
# api\itassist\services\sync_runner.py
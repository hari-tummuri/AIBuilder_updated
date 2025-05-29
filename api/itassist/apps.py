from django.apps import AppConfig
from threading import Thread
import os
import sys
from itassist.services.sync_runner import start_background_sync
import subprocess
import atexit
import platform
import re
import psutil
# from .views import stop_ollama_model
import json
from core.settings import MODELS_FILE

ollama_process = None
thread_started = False


def stop_ollama_by_port(port=11434):
        from .views import stop_ollama_model

        with open(MODELS_FILE, "r") as file:
            data = json.load(file)

        current_model = data.get('current_model')
        stop_ollama_model(current_model)
        
        if platform.system() == "Windows":
            try:
                # Run netstat and find the PID using the port
                result = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
                lines = result.strip().split('\n')
                for line in lines:
                    if "LISTENING" in line or "ESTABLISHED" in line:
                        parts = re.split(r'\s+', line.strip())
                        pid = parts[-1]
                        print(f"🔍 Found process on port {port} with PID: {pid}")
                        subprocess.run(["taskkill", "/PID", pid, "/F"], check=True)
                        print("✅ Ollama process forcefully terminated.")
                        return
                print("ℹ️ No process found listening on the port.")
            except Exception as e:
                print(f"❌ Failed to stop Ollama by port: {e}")
        else:
            print("⚠️ stop_ollama_by_port() currently supports only Windows.")


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
        

        global thread_started, ollama_process

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

            # 🔁 Start Ollama in a specific directory
            ollama_dir = os.path.abspath("./Ollama") 
            # 🔁 Start Ollama using relative path
            executable_path = os.path.join(ollama_dir, 'ollama.exe')
            print(f"🚀 Starting Ollama from: {ollama_dir}")
            
            try:
                ollama_process = subprocess.Popen(
                    [executable_path, "serve"],
                    cwd=ollama_dir,
                    # stdout=subprocess.PIPE,
                    # stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, 
                )
                print("✅ Ollama started.")
            except Exception as e:
                print(f"❌ Failed to start Ollama: {e}")

            atexit.register(lambda: stop_ollama_by_port(port=11434))

        else:
            print("🚫 Not the main server process, skipping thread.")


         # Prevent duplicate thread starts (especially in dev mode)
        # if os.environ.get('RUN_MAIN') == 'true':
        #     # Check if thread is already running (optional safeguard)
        #     if not hasattr(self, 'sync_thread_started'):
        #         self.sync_thread_started = True
        #         thread = Thread(target=background_sync_runner, daemon=True)
        #         thread.start()
            
    
    # def stop_ollama(self):
    #     global ollama_process
    #     if ollama_process and ollama_process.poll() is None:
    #         try:
    #             print(f"🛑 Attempting to stop Ollama (PID: {ollama_process.pid}) gracefully...")
    #             ollama_process.terminate()
    #             try:
    #                 ollama_process.wait(timeout=5)
    #                 print("✅ Ollama stopped gracefully.")
    #             except subprocess.TimeoutExpired:
    #                 print("⚠️ Graceful stop timed out. Forcing termination...")
    #                 if platform.system() == "Windows":
    #                     try:
    #                         subprocess.run(["taskkill", "/PID", str(ollama_process.pid), "/F"], check=True)
    #                         print("✅ Ollama forcefully terminated using taskkill.")
    #                     except Exception as e:
    #                         print(f"❌ taskkill failed: {e}")
    #                 else:
    #                     try:
    #                         ollama_process.kill()
    #                         print("✅ Ollama forcefully killed.")
    #                     except Exception as e:
    #                         print(f"❌ Kill failed: {e}")

    #         except Exception as e:
    #             print(f"❌ Unexpected error when stopping Ollama: {e}")
    #     else:
    #         print("ℹ️ Ollama process is not running or already stopped.")
            
# api\itassist\services\sync_runner.py
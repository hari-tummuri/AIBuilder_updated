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

# Function to stop Ollama by port
# This function is designed to work on Windows systems using netstat and taskkill.
## It checks if the Ollama model is running on the specified port and attempts to stop it.
def stop_ollama_by_port(port=11434):
        from .views import stop_ollama_model

        if not os.path.exists(MODELS_FILE):
            print(f"❌ Model file not found at {MODELS_FILE}")
            return

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
                        if pid.isdigit():
                            print(f"Found process on port {port} with PID: {pid}")
                            subprocess.run(["taskkill", "/PID", pid, "/F"], check=True)
                            print("Ollama process forcefully terminated.")
                            return
                print("No process found listening on the port.")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ netstat or taskkill failed: {e}")

            except Exception as e:
                print(f"❌ Failed to stop Ollama by port: {e}")
        else:
            print("⚠️ stop_ollama_by_port() currently supports only Windows.")


class ItassistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itassist'

    

    # def ready(self):
        
    #     # global thread_started

    #     # if thread_started:
    #     #     return
        
    #     # if os.environ.get('RUN_MAIN') != 'true':
    #     #     return
    #     # print("✅ AppConfig.ready() called")
    #     # start_background_sync()
    #     # thread_started = True
        
    #     from .services.vectordb_service import load_documents
    #     global thread_started, ollama_process

    #     if thread_started:
    #         return

    #     print("✅ AppConfig.ready() called")
    #     # Use process ID check to avoid reloader process (specific to Uvicorn with --reload)
    #     if os.environ.get("RUN_MAIN") == "true" or (
    #         "uvicorn" in sys.argv[0].lower() and os.getppid() != os.getpid()
    #     ):
    #         print("✅ Conditions passed: Starting sync and Ollama...")
    #         start_background_sync()
    #         thread_started = True

    #         print("Loading documents into ChromaDB...")
    #         load_documents()
    #         print("Finished loading documents.")
            
    #         # 🔁 Start Ollama in a specific directory
    #         ollama_dir = os.path.abspath("./Ollama") 
    #         # 🔁 Start Ollama using relative path
    #         executable_path = os.path.join(ollama_dir, 'ollama.exe')
    #         print(f"🚀 Starting Ollama from: {ollama_dir}")
            
    #         try:
    #             ollama_process = subprocess.Popen(
    #                 [executable_path, "serve"],
    #                 cwd=ollama_dir,
    #                 # stdout=subprocess.PIPE,
    #                 # stderr=subprocess.PIPE,
    #                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, 
    #             )
    #             print("✅ Ollama started.")
    #         except Exception as e:
    #             print(f"❌ Failed to start Ollama: {e}")
    #         # 🔁 Determine runtime base directory (handles dev vs PyInstaller frozen mode)
    #         # if getattr(sys, 'frozen', False):
    #         #     base_dir = sys._MEIPASS  # PyInstaller temp dir
    #         # else:
    #         #     base_dir = os.path.dirname(os.path.abspath(__file__))

    #         # # ✅ Resolve path to Ollama executable
    #         # ollama_dir = os.path.join(base_dir, 'Ollama')
    #         # executable_path = os.path.join(ollama_dir, 'ollama.exe')
    #         # print(f"🚀 Starting Ollama from: {executable_path}")

    #         # try:
    #         #     ollama_process = subprocess.Popen(
    #         #         [executable_path, "serve"],
    #         #         cwd=ollama_dir,
    #         #         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    #         #     )
    #         #     print("✅ Ollama started.")
    #         # except Exception as e:
    #         #     print(f"❌ Failed to start Ollama: {e}")

            

    #         atexit.register(lambda: stop_ollama_by_port(port=11434))

    #     else:
    #         print("🚫 Not the main server process, skipping thread.")
    

    #This method is called when the Django app is ready.
    # It initializes the background sync thread and starts the Ollama service.
    # It also loads documents into the ChromaDB vector database.
    def ready(self):
        from .services.vectordb_service import load_documents
        global thread_started, ollama_process

        if thread_started:
            return

        print("✅ AppConfig.ready() called (no condition check)")

        # 🧵 Start background sync thread
        print("🧵 Starting sync thread...")
        start_background_sync()
        thread_started = True

        # 📄 Load documents into ChromaDB
        print("📄 Loading documents into ChromaDB...")
        load_documents()
        print("✅ Finished loading documents.")

        # 🚀 Start Ollama
        ollama_dir = os.path.abspath("./Ollama")
        executable_path = os.path.join(ollama_dir, 'ollama.exe')
        print(f"🚀 Starting Ollama from: {executable_path}")

        try:
            ollama_process = subprocess.Popen(
                [executable_path, "serve"],
                cwd=ollama_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            print("✅ Ollama started.")
        except Exception as e:
            print(f"❌ Failed to start Ollama: {e}")

        # 🔁 Ensure Ollama stops on exit
        atexit.register(lambda: stop_ollama_by_port(port=11434))


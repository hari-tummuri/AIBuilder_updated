# import sys
# import subprocess

# def main():
#     # Use the same command you use in dev, without --reload (which is for dev only)
#     cmd = [
#         sys.executable,
#         "-m", "uvicorn",
#         "core.asgi:application",
#         "--host", "0.0.0.0",
#         "--port", "8000",
#     ]
#     # Run the uvicorn server (blocking call)
#     subprocess.run(cmd)

# if __name__ == "__main__":
#     main()

# import uvicorn

# if __name__ == "__main__":
#     print("Starting backend via uvicorn.run...")
#     uvicorn.run("core.asgi:application", host="0.0.0.0", port=8000)


# import sys
# import os

# # Ensure your project root is in the Python path
# project_root = os.path.dirname(os.path.abspath(__file__))
# sys.path.insert(0, project_root)

# # Import Django settings module before running uvicorn
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')  # Adjust 'core.settings' accordingly

# import uvicorn

# if __name__ == "__main__":
#     print("Starting backend via uvicorn.run...")
#     uvicorn.run("core.asgi:application", host="0.0.0.0", port=8000)

import sys
import os

# 1. Ensure Python can find your “core” package (and any other local modules)
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle → core/ is unpacked into sys._MEIPASS
    BASE_DIR = sys._MEIPASS
else:
    # Running normally (dev mode)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Insert that unpacked folder at the front of sys.path so “import core” works
sys.path.insert(0, BASE_DIR)

# 2. Now you can set Django’s settings and launch UVicorn
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import uvicorn  # noqa: E402

print("Starting backend via uvicorn.run…")
uvicorn.run("core.asgi:application", host="0.0.0.0", port=8000)

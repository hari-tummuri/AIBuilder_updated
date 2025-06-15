import os
import shutil
import sys

def get_data_path(folder_name):
    """Returns a safe writable path for userdata or chroma_db."""
    if getattr(sys, 'frozen', False):
        # .exe mode
        base_path = sys._MEIPASS
        source_path = os.path.join(base_path, folder_name)
        target_base = os.path.join(os.path.expanduser("~"), "AIBuilderAppData", "MyApp")
        target_path = os.path.join(target_base, folder_name)

        if not os.path.exists(target_path):
            shutil.copytree(source_path, target_path)

        return target_path
    else:
        # Dev mode
        return os.path.abspath(folder_name)

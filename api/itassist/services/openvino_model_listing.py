import os
import glob

def get_hf_cache_dir():
    return os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))

def get_directory_size_in_bytes(directory):
    total = 0
    for root, _, files in os.walk(directory):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total

def list_openvino_downloaded_models():
    hf_cache = get_hf_cache_dir()
    models_root = os.path.join(hf_cache, "hub")
    models = []

    print(f"list_openvino_downloaded_models function called")
    if not os.path.isdir(models_root):
        return models

    for model_folder in os.listdir(models_root):
        if not model_folder.startswith("models--OpenVINO--"):
            continue

        repo_id = model_folder.replace("models--", "").replace("--", "/")
        snapshots_path = os.path.join(models_root, model_folder, "snapshots")

        if not os.path.isdir(snapshots_path):
            continue

        for snapshot in os.listdir(snapshots_path):
            snapshot_dir = os.path.join(snapshots_path, snapshot)

            # Skip if any partial files exist
            part_files = glob.glob(os.path.join(snapshot_dir, "**", "*.part"), recursive=True)
            if part_files:
                continue

            all_files = glob.glob(os.path.join(snapshot_dir, "**", "*.*"), recursive=True)
            if not all_files:
                continue

            total_size_bytes = get_directory_size_in_bytes(snapshot_dir)
            total_size_gb = round(total_size_bytes / (1024 ** 3), 3)

            models.append({
                "model_id": repo_id,
                "snapshot": snapshot,
                "file_count": len(all_files),
                "size_gb": total_size_gb,
                "path": snapshot_dir
            })

    return models

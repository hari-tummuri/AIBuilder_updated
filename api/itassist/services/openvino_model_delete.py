import os
import shutil

def get_cache_dir(repo_id):
    hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    repo_folder = f"models--{repo_id.replace('/', '--')}"
    return os.path.join(hf_home, "hub", repo_folder)

def openvino_delete_model(repo_id):
    try:
        base_dir = get_cache_dir(repo_id)
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
            return {"status": "deleted", "model": repo_id}
        else:
            return {"status": "not_found", "message": "Model not found in cache."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

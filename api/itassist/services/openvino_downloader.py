# # services/hf_async_downloader.py

# import os
# import json
# import time
# import asyncio
# import aiohttp
# from huggingface_hub import list_repo_files, hf_hub_url
# from asgiref.sync import sync_to_async

# HF_CACHE_DIR = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
# cancel_flags = {}
# cancel_lock = asyncio.Lock()

# async def error_stream(message):
#     yield json.dumps({"status": "error", "message": message}) + "\n"

# def get_cache_dir(repo_id):
#     repo_folder = f"models--{repo_id.replace('/', '--')}"
#     return os.path.join(HF_CACHE_DIR, "hub", repo_folder, "snapshots", "manual")

# async def download_hf_model_stream(model_id: str, download_id: str):
#     """
#     Async generator: yields JSON lines about download progress.
#     """
#     yield json.dumps({"status": "starting", "model": model_id}) + "\n"

#     # 1. List files (sync call wrapped)
#     try:
#         files = await sync_to_async(list_repo_files)(model_id)
#     except Exception as e:
#         yield json.dumps({"status": "error", "error": f"Cannot list files: {e}"}) + "\n"
#         async with cancel_lock:
#             cancel_flags.pop(download_id, None)
#         return

#     output_dir = get_cache_dir(model_id)
#     os.makedirs(output_dir, exist_ok=True)

#     # 2. Check fully downloaded
#     all_exist = True
#     for fn in files:
#         if not os.path.exists(os.path.join(output_dir, fn)):
#             all_exist = False
#             break
#     if all_exist:
#         yield json.dumps({"status": "exists", "message": "Model is already fully downloaded."}) + "\n"
#         async with cancel_lock:
#             cancel_flags.pop(download_id, None)
#         return

#     # 3. Download each file
#     for filename in files:
#         # cancellation check
#         async with cancel_lock:
#             if cancel_flags.get(download_id):
#                 yield json.dumps({"status": "cancelled", "file": filename}) + "\n"
#                 # clean up partials
#                 for root, _, fs in os.walk(output_dir):
#                     for f in fs:
#                         if f.endswith(".part"):
#                             try: os.remove(os.path.join(root, f))
#                             except: pass
#                 cancel_flags.pop(download_id, None)
#                 return

#         url = hf_hub_url(repo_id=model_id, filename=filename)
#         final_path = os.path.join(output_dir, filename)
#         temp_path = final_path + ".part"

#         # skip if fully exists
#         if os.path.exists(final_path):
#             yield json.dumps({"file": filename, "status": "skipped", "reason": "already exists"}) + "\n"
#             continue

#         # start download via aiohttp
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(url) as resp:
#                     if resp.status != 200:
#                         raise Exception(f"HTTP {resp.status}")
#                     total = int(resp.headers.get("content-length", 0))
#                     downloaded = 0
#                     start = time.time()
#                     last_emit = 0

#                     os.makedirs(os.path.dirname(final_path), exist_ok=True)
#                     # open temp file in sync mode
#                     with open(temp_path, "wb") as f:
#                         async for chunk in resp.content.iter_chunked(8192):
#                             # cancel?
#                             async with cancel_lock:
#                                 if cancel_flags.get(download_id):
#                                     try:
#                                         f.close()
#                                         os.remove(temp_path)
#                                     except:
#                                         pass
#                                     yield json.dumps({"file": filename, "status": "cancelled"}) + "\n"
#                                     # cleanup partials
#                                     for root, _, fs in os.walk(output_dir):
#                                         for pf in fs:
#                                             if pf.endswith(".part"):
#                                                 try: os.remove(os.path.join(root, pf))
#                                                 except: pass
#                                     cancel_flags.pop(download_id, None)
#                                     return
#                             # write chunk
#                             if chunk:
#                                 f.write(chunk)
#                                 downloaded += len(chunk)

#                             now = time.time()
#                             if now - last_emit >= 1:
#                                 percent = (downloaded / total * 100) if total else 0
#                                 speed = downloaded / (now - start + 1e-6)
#                                 yield json.dumps({
#                                     "file": filename,
#                                     "status": "downloading",
#                                     "downloaded": downloaded,
#                                     "total": total,
#                                     "progress": f"{percent:.2f}%",
#                                     "speed_bps": int(speed)
#                                 }) + "\n"
#                                 last_emit = now

#             # rename when done; verify full size
#             try:
#                 size = os.path.getsize(temp_path)
#                 if total and size < total:
#                     # incomplete; remove and error
#                     os.remove(temp_path)
#                     yield json.dumps({"file": filename, "status": "error", "error": "Incomplete download"}) + "\n"
#                     # proceed to next or abort? Here we abort:
#                     async with cancel_lock:
#                         cancel_flags.pop(download_id, None)
#                     return
#                 os.rename(temp_path, final_path)
#             except Exception as e:
#                 if os.path.exists(temp_path):
#                     os.remove(temp_path)
#                 yield json.dumps({"file": filename, "status": "error", "error": str(e)}) + "\n"
#                 async with cancel_lock:
#                     cancel_flags.pop(download_id, None)
#                 return

#             yield json.dumps({"file": filename, "status": "done"}) + "\n"

#         except Exception as e:
#             # cleanup partial
#             if os.path.exists(temp_path):
#                 try: os.remove(temp_path)
#                 except: pass
#             yield json.dumps({"file": filename, "status": "error", "error": str(e)}) + "\n"
#             async with cancel_lock:
#                 cancel_flags.pop(download_id, None)
#             return

#     # all files done
#     yield json.dumps({"status": "completed", "model": model_id}) + "\n"
#     async with cancel_lock:
#         cancel_flags.pop(download_id, None)


import os
import json
import time
import asyncio
import aiohttp
from huggingface_hub import list_repo_files, hf_hub_url
from asgiref.sync import sync_to_async

HF_CACHE_DIR = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
cancel_flags = {}
cancel_lock = asyncio.Lock()

async def error_stream(message):
    yield json.dumps({"status": "error", "message": message}) + "\n"

def get_cache_dir(repo_id):
    repo_folder = f"models--{repo_id.replace('/', '--')}"
    return os.path.join(HF_CACHE_DIR, "hub", repo_folder, "snapshots", "manual")

async def download_hf_model_stream(model_id: str, download_id: str):
    yield json.dumps({"status": "starting", "model": model_id}) + "\n"

    try:
        files = await sync_to_async(list_repo_files)(model_id)
    except Exception as e:
        yield json.dumps({"status": "error", "error": f"Cannot list files: {e}"}) + "\n"
        async with cancel_lock:
            cancel_flags.pop(download_id, None)
        return

    output_dir = get_cache_dir(model_id)
    os.makedirs(output_dir, exist_ok=True)

    all_exist = all(os.path.exists(os.path.join(output_dir, fn)) for fn in files)
    if all_exist:
        yield json.dumps({"status": "exists", "message": "Model is already fully downloaded."}) + "\n"
        async with cancel_lock:
            cancel_flags.pop(download_id, None)
        return

    for filename in files:
        async with cancel_lock:
            if cancel_flags.get(download_id):
                yield json.dumps({"status": "cancelled", "file": filename}) + "\n"
                cancel_flags.pop(download_id, None)
                return

        url = hf_hub_url(repo_id=model_id, filename=filename)
        final_path = os.path.join(output_dir, filename)
        temp_path = final_path + ".part"

        if os.path.exists(final_path):
            yield json.dumps({"file": filename, "status": "skipped", "reason": "already exists"}) + "\n"
            continue

        resume_bytes = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
        headers = {"Range": f"bytes={resume_bytes}-"} if resume_bytes > 0 else {}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resume_bytes > 0:
                        if resp.status != 206:
                            yield json.dumps({
                                "file": filename,
                                "status": "warn",
                                "message": "Server did not support Range request. Restarting full download."
                            }) + "\n"
                            os.remove(temp_path)
                            resume_bytes = 0
                            headers = {}
                            async with session.get(url) as resp:
                                if resp.status != 200:
                                    raise Exception(f"HTTP {resp.status}")
                                total = int(resp.headers.get("content-length", 0))
                                downloaded = 0
                        else:
                            content_range = resp.headers.get("Content-Range")
                            if not content_range:
                                raise Exception("Missing Content-Range on 206 response")
                            total = int(content_range.split("/")[1])
                            downloaded = resume_bytes
                    else:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}")
                        total = int(resp.headers.get("content-length", 0))
                        downloaded = 0

                    start = time.time()
                    last_emit = 0

                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    with open(temp_path, "ab") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            async with cancel_lock:
                                if cancel_flags.get(download_id):
                                    yield json.dumps({"file": filename, "status": "cancelled"}) + "\n"
                                    cancel_flags.pop(download_id, None)
                                    return

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                            now = time.time()
                            if now - last_emit >= 1:
                                percent = (downloaded / total * 100) if total else 0
                                speed = downloaded / (now - start + 1e-6)
                                yield json.dumps({
                                    "file": filename,
                                    "status": "downloading",
                                    "downloaded": downloaded,
                                    "total": total,
                                    "progress": f"{percent:.2f}%",
                                    "speed_bps": int(speed)
                                }) + "\n"
                                last_emit = now

            # Final integrity check
            if os.path.getsize(temp_path) < total:
                yield json.dumps({"file": filename, "status": "incomplete", "downloaded": downloaded, "expected": total}) + "\n"
                continue

            os.rename(temp_path, final_path)
            yield json.dumps({"file": filename, "status": "done"}) + "\n"

        except Exception as e:
            yield json.dumps({"file": filename, "status": "error", "error": str(e)}) + "\n"
            async with cancel_lock:
                cancel_flags.pop(download_id, None)
            return

    yield json.dumps({"status": "completed", "model": model_id}) + "\n"
    async with cancel_lock:
        cancel_flags.pop(download_id, None)


# async def download_hf_model_stream(model_id: str, download_id: str):
#     yield json.dumps({"status": "starting", "model": model_id}) + "\n"

#     try:
#         files = await sync_to_async(list_repo_files)(model_id)
#     except Exception as e:
#         yield json.dumps({"status": "error", "error": f"Cannot list files: {e}"}) + "\n"
#         async with cancel_lock:
#             cancel_flags.pop(download_id, None)
#         return

#     output_dir = get_cache_dir(model_id)
#     os.makedirs(output_dir, exist_ok=True)

#     all_exist = True
#     for fn in files:
#         if not os.path.exists(os.path.join(output_dir, fn)):
#             all_exist = False
#             break
#     if all_exist:
#         yield json.dumps({"status": "exists", "message": "Model is already fully downloaded."}) + "\n"
#         async with cancel_lock:
#             cancel_flags.pop(download_id, None)
#         return

#     for filename in files:
#         async with cancel_lock:
#             if cancel_flags.get(download_id):
#                 yield json.dumps({"status": "cancelled", "file": filename}) + "\n"
#                 cancel_flags.pop(download_id, None)
#                 return

#         url = hf_hub_url(repo_id=model_id, filename=filename)
#         final_path = os.path.join(output_dir, filename)
#         temp_path = final_path + ".part"

#         if os.path.exists(final_path):
#             yield json.dumps({"file": filename, "status": "skipped", "reason": "already exists"}) + "\n"
#             continue

#         resume_bytes = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
#         headers = {"Range": f"bytes={resume_bytes}-"} if resume_bytes > 0 else {}

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(url, headers=headers) as resp:
#                     if resp.status not in [200, 206]:
#                         raise Exception(f"HTTP {resp.status}")
#                     total = int(resp.headers.get("content-length", 0)) + resume_bytes
#                     downloaded = resume_bytes
#                     start = time.time()
#                     last_emit = 0

#                     os.makedirs(os.path.dirname(final_path), exist_ok=True)
#                     with open(temp_path, "ab") as f:
#                         async for chunk in resp.content.iter_chunked(8192):
#                             async with cancel_lock:
#                                 if cancel_flags.get(download_id):
#                                     yield json.dumps({"file": filename, "status": "cancelled"}) + "\n"
#                                     cancel_flags.pop(download_id, None)
#                                     return

#                             if chunk:
#                                 f.write(chunk)
#                                 downloaded += len(chunk)

#                             now = time.time()
#                             if now - last_emit >= 1:
#                                 percent = (downloaded / total * 100) if total else 0
#                                 speed = downloaded / (now - start + 1e-6)
#                                 yield json.dumps({
#                                     "file": filename,
#                                     "status": "downloading",
#                                     "downloaded": downloaded,
#                                     "total": total,
#                                     "progress": f"{percent:.2f}%",
#                                     "speed_bps": int(speed)
#                                 }) + "\n"
#                                 last_emit = now

#             if os.path.getsize(temp_path) < total:
#                 yield json.dumps({"file": filename, "status": "incomplete", "downloaded": downloaded, "expected": total}) + "\n"
#                 continue
#             os.rename(temp_path, final_path)
#             yield json.dumps({"file": filename, "status": "done"}) + "\n"

#         except Exception as e:
#             yield json.dumps({"file": filename, "status": "error", "error": str(e)}) + "\n"
#             async with cancel_lock:
#                 cancel_flags.pop(download_id, None)
#             return

#     yield json.dumps({"status": "completed", "model": model_id}) + "\n"
#     async with cancel_lock:
#         cancel_flags.pop(download_id, None)

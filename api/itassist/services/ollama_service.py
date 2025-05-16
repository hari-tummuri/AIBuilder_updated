import subprocess
import json
import os

import re
from django.http import StreamingHttpResponse

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def stream_ollama_pull_output(model_name):
    relative_dir = r"./../Ollama/" 
    working_dir = os.path.abspath(relative_dir)
    # Step 1: Navigate to the correct folder (ollama directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # from services -> core
    ollama_dir = os.path.join(base_dir, 'ollama')
    command = f'./ollama pull {model_name}' if os.name != 'nt' else f'ollama.exe pull {model_name}'

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=working_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'
    )

    for line in iter(process.stdout.readline, ''):
        cleaned = strip_ansi_codes(line.strip())
        yield cleaned + "\n"

    process.stdout.close()
    process.wait()






# def get_ollama_list_json():
#     try:
#         # Run the command
#         result = subprocess.run(['ollama', 'list'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#         lines = result.stdout.strip().split('\n')

#         # Skip the header and parse each line
#         headers = lines[0].split()
#         models = []
#         for line in lines[1:]:
#             parts = line.split()
#             model = {
#                 "repository": parts[0],
#                 "tag": parts[1],
#                 "size": parts[2] + ' ' + parts[3],  # e.g., '4.2 GB'
#                 "created": ' '.join(parts[4:])      # e.g., '2 days ago'
#             }
#             models.append(model)

#         return models
#     except subprocess.CalledProcessError as e:
#         return {"error": e.stderr}



# def pull_ollama_model(model_name):
#     relative_dir = r"./../Ollama/" 
#     try:
#         working_dir = os.path.abspath(relative_dir)
#         ollama_executable = os.path.join(working_dir, "ollama.exe")

#         if not os.path.isfile(ollama_executable):
#             return {"status": "error", "message": f"Ollama executable not found at {ollama_executable}"}

#         # Build command string
#         command = f'"{ollama_executable}" pull {model_name}'

#         result = subprocess.run(
#             command,
#             cwd=working_dir,
#             shell=True,  # Needed on Windows for .exe and PATH resolution
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             encoding="utf-8",  # ✅ Use UTF-8 instead of relying on system default
#             errors="replace"   # ✅ Replace undecodable characters instead of crashing
#         )

#         output = result.stdout.strip()
#         if "success" in output.lower():
#             return {"status": "success", "message": output}
#         else:
#             return {"status": "error", "message": output or result.stderr.strip()}

#     except Exception as e:
#         return {"status": "error", "message": str(e)}
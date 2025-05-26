from django.shortcuts import render
import json
import os
import uuid
import socket
import threading
import time
import requests
from datetime import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from itassist.services import conversation
from .utils.sync_utils import sync_json_to_mysql
from core.settings import CONV_JSON_FILE, DOCUMENT_ROOT, AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME, DOWNLOAD_FOLDER,MODELS_FILE, USER_DATA_ROOT, DEFAULT_FILE, SELECTED_FILE
from django.http import FileResponse
from .services.azure_blob_service import upload_file_to_blob, delete_blob_from_url
from .serializers import SharedBlobSerializer
from .models import SharedBlob
from .services.sync_runner import check_internet_connection
from .services.ollama_service import get_downloaded_models, delete_model
from .services.vectordb_service import simulate_vdb_upload
from .services.hyper_params_service import get_hyperparameters, compare_structure
from .services.system_info_service import get_system_info
from django.http import StreamingHttpResponse,JsonResponse,HttpResponse,HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str
import asyncio
import httpx

# Create your views here.

#For Creating a new conversation
# This function creates a new conversation and saves it to a JSON file.
# It generates a unique conversation ID based on the hostname and the current date and time.
# It also initializes the conversation with a default name and an empty message list.
@api_view(['POST'])
def create_conversation(request):
    print("Creating new conversation...")
    conversations = conversation.load_conversations()
    conv_id = conversation.get_next_conversation_id(conversations)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_convo = {
        "conv_id": conv_id,
        "Name": "New Conversation",
        "Date": created_at,
        "messages": []
    }

    conversations.append(new_convo)
    conversation.save_conversations(conversations)

    return Response(new_convo, status=status.HTTP_201_CREATED)

# This function deletes a conversation based on the provided conversation ID.
# It checks if the conversation exists in the JSON file and removes it if found.
@api_view(['DELETE'])
def delete_conversation(request, conv_id):
    conversations = conversation.load_conversations()

    # Check if it exists
    updated_conversations = [conv for conv in conversations if conv["conv_id"] != conv_id]
    if len(updated_conversations) == len(conversations):
        return Response(
            {"detail": f"Conversation with ID '{conv_id}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    conversation.save_conversations(updated_conversations)
    return Response(
        {"detail": f"Conversation '{conv_id}' deleted successfully."},
        status=status.HTTP_204_NO_CONTENT
    )


# This function retrieves all conversations from the JSON file.
# It returns the list of conversations in the response.
@api_view(['GET'])
def get_all_conversations(request):
    conversations = conversation.load_conversations()
    return Response(conversations, status=status.HTTP_200_OK)



# This function updates the conversation data based on the provided conversation ID.
# It allows updating the conversation name and messages.    
# It checks if the conversation exists and updates it accordingly.
# If the conversation is not found, it returns a 404 error.
@api_view(["PUT"])
def update_conversation(request, conv_id):
    result, stat = conversation.update_conversation_data(conv_id, request.data)
    return Response(result, status=stat)


# This function adds a new user message to the specified conversation.
# It generates a unique message ID based on the existing messages in the conversation.
# It also checks if the conversation exists and adds the message to it.
# If the conversation is not found, it returns a 404 error.
# If the message content is empty, it returns a 400 error.
@api_view(["POST"])
def add_user_message_to_conversation(request, conv_id):
    message_text = request.data.get("message")
    result, status = conversation.add_user_message(conv_id, message_text)
    return Response(result, status=status)


# This function retrieves the details of a specific conversation based on its ID.
# It returns the conversation details if found, or an error message if not found.
# It also includes the messages associated with the conversation.
@api_view(["GET"])
def get_conversation_detail_view(request, conv_id):
    result, status_code = conversation.get_conversation_by_id(conv_id)
    return Response(result, status=status_code)


# This function synchronizes data from a SQL Server database to a MySQL database.
# It uses the sync_json_to_mysql function from the sync_utils module to perform the synchronization.
@api_view(["GET"])
def sync_data_sql_server(request):
    try:
        sync_json_to_mysql()
        return Response({"message": "Data synced successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def list_files(request):
    file_list = []
    for root, dirs, files in os.walk(DOCUMENT_ROOT):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), start=DOCUMENT_ROOT)
            file_list.append(os.path.join(DOCUMENT_ROOT, rel_path).replace("\\", "/"))  # Normalize Windows paths
    return Response({"files": file_list})


@api_view(["GET"])
def download_file(request):
    filepath = request.GET.get("filepath")
    if not filepath:
        return Response({"error": "Filepath is required."}, status=400)

    full_path = os.path.abspath(filepath)

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=os.path.basename(full_path))


# This function checks if the internet connection is available.
# If the connection is available, it uploads a file to Azure Blob Storage.
# It requires the sender's email, receiver's email, and file path as input.
# It also validates the input data and handles exceptions accordingly.
# If the upload is successful, it saves the blob information to the database.
# If the internet connection is not available, it returns a 503 error.
@api_view(['POST'])
def share_document(request):
    print("Sharing document...")
    if check_internet_connection():
        sender_email = request.data.get('sender_email')
        receiver_email = request.data.get('receiver_email')
        file_path = request.data.get('file_path')

        if not all([sender_email, receiver_email, file_path]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blob_info = upload_file_to_blob(sender_email, file_path)

            data = {
                "sender_email": sender_email,
                "receiver_email": receiver_email,
                "file_name": blob_info["file_name"],
                "blob_url": blob_info["blob_url"],
            }

            serializer = SharedBlobSerializer(data=data, context={'using': 'azure'})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except FileNotFoundError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'error': 'No internet connection'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    

# This function retrieves the list of notifications (shared blobs) for a specific email address.
# It filters the blobs based on the receiver's email and returns the list in the response.
# It also checks for internet connectivity before attempting to retrieve the data.
# If the internet connection is not available, it returns a 503 error.
@api_view(['GET'])
def list_noti_by_email(request, email):
    if check_internet_connection():
        # email = request.GET.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blobs = SharedBlob.objects.using('azure').filter(receiver_email=email)
            serializer = SharedBlobSerializer(blobs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'error': 'No internet connection to display notifications'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    

@api_view(['POST'])
def download_blob_to_local(request):
    print("Downloading blob to local...")
    if not check_internet_connection():
        return Response({'error': 'No internet connection'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    blob_url = request.data.get('blob_url')
    filename = request.data.get('filename')

    if not blob_url or not filename:
        return Response({'error': 'Both blob_url and filename are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        response = requests.get(blob_url, stream=True)
        if response.status_code != 200:
            return Response({'error': 'Failed to download file from blob URL.'}, status=response.status_code)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"File downloaded to {file_path}")
        print("deleting file in Blob storage")

        #delete the blob from Azure Blob Storage
        delete_blob_from_url(blob_url)

        # Delete related DB record from the 'azure' database
        deleted, _ = SharedBlob.objects.using('azure').filter(blob_url=blob_url).delete()
        if deleted:
            print(f"🗃️ Successfully deleted {deleted} record(s) from DB.")
        else:
            print("⚠️ No matching record found in DB to delete.")

        return Response({'message': 'File downloaded successfully', 'local_path': file_path}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
def list_downloaded_ollama_models(request):
    try:
        models_data = get_downloaded_models()
        return Response(models_data, status=status.HTTP_200_OK)

    except requests.exceptions.ConnectionError:
        return Response(
            {"error": "Ollama API is not running on http://localhost:11434"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except requests.exceptions.RequestException as e:
        return Response(
            {"error": "Failed to fetch models from Ollama", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": "Unexpected error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@api_view(['POST'])  # Use POST since some clients have issues with DELETE + body
def delete_ollama_model(request):
    model_name = request.data.get('model')

    if not model_name:
        return Response({"error": "Model name is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = delete_model(model_name)
        return Response(result, status=status.HTTP_200_OK)

    except requests.exceptions.ConnectionError:
        return Response({"error": "Ollama API is not running"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    except requests.exceptions.HTTPError as e:
        return Response({"error": f"Failed to delete model: {e.response.text}"}, status=e.response.status_code)

    except Exception as e:
        return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


cancel_flags = {}
cancel_lock = asyncio.Lock()


@csrf_exempt
async def download_ollama_model(request: HttpRequest):
    # Parse JSON body
    try:
        # body_bytes = await request.body
        body_bytes = request.body 
        body_unicode = body_bytes.decode('utf-8')
        data = json.loads(body_bytes.decode('utf-8'))
        model_name = data.get('model')
    except Exception:
        return StreamingHttpResponse((line async for line in error_stream("Invalid JSON")), status=400)

    if not model_name:
        return StreamingHttpResponse((line async for line in error_stream("Model name is required")), status=400)

    download_id = str(uuid.uuid4())

    async with cancel_lock:
        cancel_flags[download_id] = False

    async def stream():
        latest_data = None
        last_sent_time = 0
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", "http://localhost:11434/api/pull", json={"name": model_name}) as res:
                    async for line in res.aiter_lines():
                        async with cancel_lock:
                            if cancel_flags.get(download_id):
                                yield json.dumps({"status": "cancelled"}) + '\n'
                                break

                        if line:
                            try:
                                data = json.loads(line)
                                if 'total' in data and 'completed' in data and data['total']:
                                    percent = (data['completed'] / data['total']) * 100
                                    data['percent'] = f"{percent:.2f}%"
                                latest_data = json.dumps(data) + '\n'
                            except json.JSONDecodeError:
                                latest_data = line + '\n'

                        now = asyncio.get_event_loop().time()
                        if latest_data and (now - last_sent_time >= 1):
                            yield latest_data
                            last_sent_time = now
                            latest_data = None
                        await asyncio.sleep(0)

                    if latest_data:
                        yield latest_data
        finally:
            async with cancel_lock:
                cancel_flags.pop(download_id, None)

    headers = {"X-Download-ID": download_id}
    response = StreamingHttpResponse(stream(), content_type="application/json")
    response['X-Download-ID'] = download_id
    # return StreamingHttpResponse(stream(), media_type="application/json", headers=headers)
    return response


# Optional: a helper async generator to send error messages
async def error_stream(message):
    yield json.dumps({"error": message}) + "\n"


@csrf_exempt
async def cancel_download(request):
    try:
        body_bytes = request.body
        data = json.loads(body_bytes.decode('utf-8'))
        download_id = data.get("download_id")

        if not download_id:
            return JsonResponse({"error": "Missing download_id"}, status=400)

        async with cancel_lock:
            if download_id in cancel_flags:
                cancel_flags[download_id] = True
                return JsonResponse({"status": "cancelled", "download_id": download_id})
            else:
                return JsonResponse({"error": "Download ID not found or already completed"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@api_view(['GET'])
def get_system_info_view(request):
    try:
        system_info = get_system_info()
        return Response(system_info, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# retrieves hyperparameters from a JSON file
# This function reads the hyperparameters from a JSON file and returns them in the response.
# If the file is not found, it returns a 404 error.
@api_view(['GET'])
def get_hyperparams_view(request):
    try:
        hyperparams = get_hyperparameters()
        return Response(hyperparams, status=status.HTTP_200_OK)
    except FileNotFoundError:
        return Response({"error": "No hyperparameter file found."}, status=status.HTTP_404_NOT_FOUND)
    except json.JSONDecodeError:
        return Response({"error": "Invalid JSON in hyperparameter file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# This function saves the selected hyperparameters to a JSON file.
# It first validates the input data against a template structure.
# If the structure is valid, it saves the data to the file.
# If the structure is invalid, it returns a 400 error.
@api_view(['POST'])
def save_selected_hyper_params(request):
    # DEFAULT_FILE = os.path.join(USER_DATA_ROOT, 'default_hyper_params.json')
    try:
        input_data = request.data
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

    # Load template structure
    try:
        with open(DEFAULT_FILE, 'r') as f:
            template = json.load(f)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load template file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Validate structure
    if not compare_structure(template, input_data):
        return JsonResponse({"error": "Input JSON structure does not match the default template exactly."},
                            status=status.HTTP_400_BAD_REQUEST)

    # Save to selected_hyper_params.json
    try:
        with open(SELECTED_FILE, 'w') as f:
            json.dump(input_data, f, indent=4)
    except Exception as e:
        return JsonResponse({"error": f"Failed to save selected hyperparameters: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JsonResponse({"message": "Selected hyperparameters saved successfully."}, status=status.HTTP_200_OK)

# This function restores the default hyperparameters by deleting the user-specific file.
# If the file does not exist, it returns a message indicating that the default hyperparameters are already in use.
# If the file is deleted successfully, it returns a success message.
@api_view(['DELETE'])
def restore_default_hyper_params(request):
    if os.path.exists(SELECTED_FILE):
        try:
            os.remove(SELECTED_FILE)
            return JsonResponse({"message": "Restored to default hyperparameters."}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({"error": f"Failed to delete file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return JsonResponse({"message": "No customized hyperparameters found, already using defaults."}, status=status.HTTP_200_OK)

# Simulate VDB upload
# This function simulates the upload of a file to a VDB (vector Database).
@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_document(request):
    file = request.FILES.get("file")

    if not file:
        return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

    # === Simulate VDB upload ===
    try:
        # TODO: Replace this block with real VDB integration
        simulate_vdb_upload(file)
    except Exception as e:
        return Response({"error": f"Failed to upload to VDB: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # === Save file locally ===
    try:
        # Target "others" folder inside documents root
        target_dir = os.path.join(DOCUMENT_ROOT, "others")
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, file.name)

        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return Response({"message": "Uploaded successfully."}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": f"Failed to save file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#previous code


# cancel_flags = {}
# cancel_lock = threading.Lock()

# @api_view(['POST'])
# def download_ollama_model(request):
#     model_name = request.data.get('model')
#     if not model_name:
#         return HttpResponse("Model name required", status=400)

#     download_id = str(uuid.uuid4())

#     with cancel_lock:
#         cancel_flags[download_id] = False

#     try:
#         ollama_response = requests.post(
#             'http://localhost:11434/api/pull',
#             json={'name': model_name},
#             stream=True
#         )

#         def event_stream():
#             latest_data = None
#             last_sent = 0

#             for line in ollama_response.iter_lines():
#                 with cancel_lock:
#                     if cancel_flags.get(download_id):
#                         yield f"data: {json.dumps({'status': 'cancelled'})}\n\n"
#                         break

#                 if line:
#                     try:
#                         data = json.loads(line.decode('utf-8'))
#                         if 'total' in data and 'completed' in data:
#                             percent = (data['completed'] / data['total']) * 100
#                             data['percent'] = f"{percent:.2f}%"
#                         latest_data = json.dumps(data)
#                     except Exception:
#                         latest_data = line.decode('utf-8')

#                 now = time.time()
#                 if latest_data and (now - last_sent >= 1):
#                     yield f"data: {latest_data}\n\n"
#                     last_sent = now
#                     latest_data = None

#             if latest_data:
#                 yield f"data: {latest_data}\n\n"

#             with cancel_lock:
#                 cancel_flags.pop(download_id, None)

#         response = HttpResponse(event_stream(), content_type='text/event-stream')
#         response['X-Download-ID'] = download_id
#         response['Cache-Control'] = 'no-cache'
#         response['X-Accel-Buffering'] = 'no'   # For nginx proxy
#         response['Content-Encoding'] = 'none' # Disable compression to prevent buffering
#         return response

#     except requests.exceptions.ConnectionError:
#         return HttpResponse("Ollama is not running", status=500)

#below id working with gunicorn

# @api_view(['POST'])
# def download_ollama_model(request):
#     model_name = request.data.get('model')

#     if not model_name:
#         # return StreamingHttpResponse("Model name is required.\n", status=400)
#         return JsonResponse({"error": "Model name is required"}, status=status.HTTP_400_BAD_REQUEST)
    
#     # Generate unique ID for this download
#     download_id = str(uuid.uuid4())

#     # Create cancel flag
#     with cancel_lock:
#         cancel_flags[download_id] = False

#     try:
#         ollama_response = requests.post(
#             'http://localhost:11434/api/pull',
#             json={'name': model_name},
#             stream=True
#         )

#         def stream_generator():
#             latest_data = None
#             last_sent_time = 0
#             for line in ollama_response.iter_lines():
#                 # Check if cancellation was requested
#                 with cancel_lock:
#                     if cancel_flags.get(download_id):
#                         yield json.dumps({"status": "cancelled"}) + '\n'
#                         break

#                 if line:
#                     try:
#                         data = json.loads(line.decode('utf-8'))
#                         # Calculate percent if possible
#                         if 'total' in data and 'completed' in data and data['total']:
#                             percent = (data['completed'] / data['total']) * 100
#                             data['percent'] = f"{percent:.2f}%"
#                         latest_data = json.dumps(data) + '\n'
#                     except json.JSONDecodeError:
#                         latest_data = line.decode('utf-8') + '\n'

#                 # Check if 1 second elapsed since last send
#                 now = time.time()
#                 if latest_data and (now - last_sent_time >= 1):
#                     yield latest_data
#                     last_sent_time = now
#                     latest_data = None

#             # After stream ends, send last buffered data if any
#             if latest_data:
#                 yield latest_data

#             # Cleanup after stream ends
#             with cancel_lock:
#                 cancel_flags.pop(download_id, None)

#         # Return download ID in headers
#         response = StreamingHttpResponse(stream_generator(), content_type='application/json')
#         response['X-Download-ID'] = download_id
#         return response

#     except requests.exceptions.ConnectionError:
#         # return StreamingHttpResponse("Ollama is not running on localhost:11434\n", status=500)
#         return JsonResponse({"error": "Ollama is not running"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# @api_view(['POST'])
# def cancel_download(request):
#     download_id = request.data.get('download_id')
#     if not download_id:
#         return Response({'error': 'Missing download_id'}, status=status.HTTP_400_BAD_REQUEST)

#     with cancel_lock:
#         if download_id in cancel_flags:
#             cancel_flags[download_id] = True
#             return Response({'status': 'cancellation requested'})
#         else:
#             return Response({'error': 'Invalid or expired download_id'}, status=status.HTTP_400_BAD_REQUEST)
from django.shortcuts import render
import json
import os
import socket
import requests
from datetime import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from itassist.services import conversation
from .utils.sync_utils import sync_json_to_mysql
from core.settings import CONV_JSON_FILE, DOCUMENT_ROOT, AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME, DOWNLOAD_FOLDER
from django.http import FileResponse
from .services.azure_blob_service import upload_file_to_blob, delete_blob_from_url
from .serializers import SharedBlobSerializer
from .models import SharedBlob
from .services.sync_runner import check_internet_connection


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
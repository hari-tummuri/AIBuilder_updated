from azure.storage.blob import BlobServiceClient
import os
from urllib.parse import urlparse, unquote

from core.settings import CONV_JSON_FILE, DOCUMENT_ROOT, AZURE_CONNECTION_STRING, AZURE_CONTAINER_NAME

def upload_file_to_blob(sender_email, file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("File path does not exist")

    file_name = os.path.basename(file_path)
    blob_name = f"{sender_email}_{file_name}"

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=blob_name)

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    blob_url = blob_client.url

    return {
        "file_name": file_name,
        "blob_url": blob_url
    }


def delete_blob_from_url(blob_url: str):

    decoded_url = unquote(blob_url)
                          
    # 2. Parse the URL and extract container and blob name
    parsed_url = urlparse(decoded_url)
    path_parts = parsed_url.path.lstrip('/').split('/')  # Split the path into parts

    if len(path_parts) < 2:
        print("❌ Invalid URL: It must contain both container name and blob name.")
        return
    
    # Container is the first part of the URL path, blob is the second part
    container_name = path_parts[0]
    blob_name = '/'.join(path_parts[1:])  # Join the remaining parts if the blob name has slashes

    # 3. Init service and delete the blob
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    # 4. Delete the blob
    try:
        blob_client.delete_blob()
        print(f"✅ Blob '{blob_name}' in container '{container_name}' deleted successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to delete blob: {e}")
        return False
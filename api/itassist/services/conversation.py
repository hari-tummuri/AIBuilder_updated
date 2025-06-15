import socket
import os
import json
from datetime import datetime
from rest_framework import status
from core.settings import CONV_JSON_FILE
# from .answer import modelResponse
from .ollama_service import modelResponse


# JSON_FILE = r"./userdata/conversations.json"

def delete_conv_history():
    try:
        with open(CONV_JSON_FILE, "w") as file:
            file.truncate(0)
        print(f"Contents of '{CONV_JSON_FILE}' have been cleared.")
        return True
    except Exception as e:
        print(f"An error occurred while clearing the file: {e}")
        return False


# This function retrieves the hostname of the machine.
def get_hostname():
    return socket.gethostname()


# This function loads conversations from a JSON file.
# If the file does not exist or is empty, it returns an empty list.
def load_conversations():
    """
    Loads conversations from the CONV_JSON_FILE.
    Returns an empty list if the file doesn't exist or is malformed.
    """
    if not os.path.exists(CONV_JSON_FILE):
        return []

    try:
        with open(CONV_JSON_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
        

# This function saves conversations to a JSON file.
# It ensures that the directory exists before attempting to write to the file.
def save_conversations(conversations):
    """
    Saves conversation data to CONV_JSON_FILE.
    Ensures the target directory exists.
    """
    try:
        os.makedirs(os.path.dirname(CONV_JSON_FILE), exist_ok=True)
        with open(CONV_JSON_FILE, "w") as file:
            json.dump(conversations, file, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to save conversations: {e}")


# This function generates a new conversation ID based on the hostname and existing conversation IDs.
def get_next_conversation_id(conversations):
    # hostname = get_hostname()
    # prefix = f"{hostname}-"
    # matching = [c for c in conversations if c["conv_id"].startswith(prefix)]
    # if not matching:
    #     return f"{prefix}1"
    # last_id = max(int(c["conv_id"].split("-")[-1]) for c in matching)
    # return f"{prefix}{last_id + 1}"
    hostname = get_hostname()
    prefix = f"{hostname}-"

    # Get all existing conversation IDs for this hostname
    existing_ids = [conv["conv_id"] for conv in conversations if conv["conv_id"].startswith(prefix)]

    # Extract numeric parts
    numbers = [int(conv_id.split("-")[-1]) for conv_id in existing_ids]

    next_id = max(numbers) + 1 if numbers else 1
    return f"{prefix}{next_id}"


# This function retrieves a conversation by its ID.
# It returns the conversation if found, or an error message if not found.
def update_conversation_data(conv_id, data):
    """
    Updates a conversation by ID in the conversations file.

    Args:
        conv_id (str): ID of the conversation to update.
        data (dict): Data containing optional 'Name' and 'messages' fields.

    Returns:
        tuple: (response dictionary, HTTP status code)
    """
    if not os.path.exists(CONV_JSON_FILE):
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except json.JSONDecodeError:
        return {"error": "Conversation file is corrupted."}, status.HTTP_500_INTERNAL_SERVER_ERROR

    for conv in conversations:
        if conv.get("conv_id") == conv_id:
            if "Name" in data:
                conv["Name"] = data["Name"]

            if "messages" in data:
                for update in data["messages"]:
                    msg_id = update.get("id")
                    new_msg = update.get("message")

                    if msg_id and new_msg:
                        for message in conv.get("messages", []):
                            if message.get("id") == msg_id and message.get("from_field") == "User":
                                message["message"] = new_msg
                                break

            try:
                with open(CONV_JSON_FILE, "w") as file:
                    json.dump(conversations, file, indent=4)
            except Exception as e:
                return {"error": f"Failed to write file: {str(e)}"}, status.HTTP_500_INTERNAL_SERVER_ERROR

            return {"message": "Conversation updated successfully.", "new_conv_name" : data["Name"]}, status.HTTP_202_ACCEPTED

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND

# This function adds a new user message to the specified conversation.
# It generates a unique message ID based on the existing messages in the conversation.
def add_user_message(conv_id, message_text, collection_name):
    """
    Adds a new user message to the conversation identified by conv_id.
    Generates a unique message ID and appends the message.
    Also adds a system response message via modelResponse and add_system_message.

    Returns:
        Tuple: (updated conversation dict or error dict, HTTP status code)
    """
    if not message_text:
        return {"error": "Message content is required."}, status.HTTP_400_BAD_REQUEST

    if not os.path.exists(CONV_JSON_FILE):
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except json.JSONDecodeError:
        return {"error": "Conversation file is corrupted."}, status.HTTP_500_INTERNAL_SERVER_ERROR

    for conv in conversations:
        if conv.get("conv_id") == conv_id:
            existing_ids = [
                msg.get("id", "")
                for msg in conv.get("messages", [])
                if isinstance(msg.get("id", ""), str)
            ]
            numbers = [
                int(msg_id.split("-")[-1])
                for msg_id in existing_ids
                if msg_id.startswith(f"{conv_id}-") and msg_id.split("-")[-1].isdigit()
            ]
            next_num = max(numbers, default=0) + 1

            new_id = f"{conv_id}-{next_num}"
            new_message = {
                "id": new_id,
                "from_field": "User",
                "message": message_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            }
            conv.setdefault("messages", []).append(new_message)

            try:
                with open(CONV_JSON_FILE, "w") as file:
                    json.dump(conversations, file, indent=4)
            except Exception as e:
                return {"error": f"Failed to write conversations: {str(e)}"}, status.HTTP_500_INTERNAL_SERVER_ERROR

            # Call your modelResponse and add_system_message functions
            response = modelResponse(message_text, conv_id, collection_name)
            ai_message = response.get("message")
            references = response.get("references")
            add_system_message(conv_id, ai_message, references)

            # Reload updated conversations to return fresh data
            try:
                with open(CONV_JSON_FILE, "r") as file:
                    updated_conversations = json.load(file)
            except Exception:
                updated_conversations = conversations  # fallback if reload fails

            updated_conv = next((c for c in updated_conversations if c.get("conv_id") == conv_id), None)

            return updated_conv, status.HTTP_201_CREATED

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND


# This function adds a system message to the specified conversation.
# It generates a unique message ID based on the existing messages in the conversation.
def add_system_message(conv_id, message_text, references):
    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except FileNotFoundError:
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    for conv in conversations:
        if conv["conv_id"] == conv_id:
            if not message_text:
                return {"error": "Message content is required."}, status.HTTP_400_BAD_REQUEST

            # Use string-based IDs like "conv_id-1", "conv_id-2"
            existing_ids = [msg.get("id", "") for msg in conv["messages"] if isinstance(msg.get("id", ""), str)]
            numbers = [
                int(msg_id.split("-")[-1])
                for msg_id in existing_ids
                if msg_id.startswith(f"{conv_id}-") and msg_id.split("-")[-1].isdigit()
            ]
            next_num = max(numbers, default=0) + 1

            print(f"references ----- {references}")
            new_message = {
                "id": f"{conv_id}-{next_num}",
                "from_field": "System",
                "message": message_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "references": references
            }

            conv["messages"].append(new_message)

            with open(CONV_JSON_FILE, "w") as file:
                json.dump(conversations, file, indent=4)

            return {"message": "System message added successfully."}, status.HTTP_201_CREATED

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND


def get_conversation_by_id(conv_id):
    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except FileNotFoundError:
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND
    except json.JSONDecodeError:
        return {"error": "Conversation file is not valid JSON."}, status.HTTP_500_INTERNAL_SERVER_ERROR

    conv = next((c for c in conversations if c.get("conv_id") == conv_id), None)
    if conv:
        return conv, status.HTTP_200_OK

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND
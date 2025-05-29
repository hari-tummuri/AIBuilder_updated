import socket
import os
import json
from datetime import datetime
from rest_framework import status
from core.settings import CONV_JSON_FILE
# from .answer import modelResponse
from .ollama_service import modelResponse


# JSON_FILE = r"./userdata/conversations.json"

# This function retrieves the hostname of the machine.
def get_hostname():
    return socket.gethostname()


# This function loads conversations from a JSON file.
# If the file does not exist or is empty, it returns an empty list.
def load_conversations():
    if not os.path.exists(CONV_JSON_FILE):
        return []
    with open(CONV_JSON_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []
        except FileNotFoundError:
            return "file not found"
        

# This function saves conversations to a JSON file.
# It ensures that the directory exists before attempting to write to the file.
def save_conversations(conversations):
    # Ensure directory exists
    os.makedirs(os.path.dirname(CONV_JSON_FILE), exist_ok=True)

    with open(CONV_JSON_FILE, "w") as file:
        json.dump(conversations, file, indent=4)


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
    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except FileNotFoundError:
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    for conv in conversations:
        if conv["conv_id"] == conv_id:
            # Update Name if provided
            if "Name" in data:
                conv["Name"] = data["Name"]

            # Update messages if provided
            if "messages" in data:
                updates = data["messages"]
                for update in updates:
                    msg_id = update.get("id")
                    new_msg = update.get("message")

                    if msg_id is not None and new_msg is not None:
                        for message in conv["messages"]:
                            if message.get("id") == msg_id and message.get("from_field") == "User":
                                message["message"] = new_msg
                                break

            with open(CONV_JSON_FILE, "w") as file:
                json.dump(conversations, file, indent=4)

            return {"message": "Conversation updated successfully."}, status.HTTP_202_ACCEPTED

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND


# This function adds a new user message to the specified conversation.
# It generates a unique message ID based on the existing messages in the conversation.
def add_user_message(conv_id, message_text):
    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except FileNotFoundError:
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    for conv in conversations:
        if conv["conv_id"] == conv_id:
            if not message_text:
                return {"error": "Message content is required."}, status.HTTP_400_BAD_REQUEST

            # Determine next message number
            existing_ids = [msg.get("id", "") for msg in conv["messages"] if isinstance(msg.get("id", ""), str)]
            numbers = [int(msg_id.split("-")[-1]) for msg_id in existing_ids if msg_id.startswith(conv_id + "-")]
            next_num = max(numbers, default=0) + 1

            # Construct new ID
            new_id = f"{conv_id}-{next_num}"

            new_message = {
                "id": new_id,
                "from_field": "User",
                "message": message_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            }

            conv["messages"].append(new_message)

            with open(CONV_JSON_FILE, "w") as file:
                json.dump(conversations, file, indent=4)

            # Add static system message using your existing helper
            add_system_message(conv_id, modelResponse(message_text, conv_id))

            # Reload conversation to include both messages before returning
            with open(CONV_JSON_FILE, "r") as file:
                updated_conversations = json.load(file)

            # Return the updated conversation object
            updated_conv = next((c for c in updated_conversations if c["conv_id"] == conv_id), None)
            return updated_conv, status.HTTP_201_CREATED

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND


# This function adds a system message to the specified conversation.
# It generates a unique message ID based on the existing messages in the conversation.
def add_system_message(conv_id, message_text):
    try:
        with open(CONV_JSON_FILE, "r") as file:
            conversations = json.load(file)
    except FileNotFoundError:
        return {"error": "Conversation file not found."}, status.HTTP_404_NOT_FOUND

    for conv in conversations:
        if conv["conv_id"] == conv_id:
            if not message_text:
                return {"error": "Message content is required."}, status.HTTP_404_NOT_FOUND

            #Use string-based IDs like "conv_id-1", "conv_id-2" instead of just integers
            existing_ids = [msg.get("id", "") for msg in conv["messages"] if isinstance(msg.get("id", ""), str)]
            numbers = [int(msg_id.split("-")[-1]) for msg_id in existing_ids if msg_id.startswith(conv_id + "-")]
            next_num = max(numbers, default=0) + 1

            new_message = {
                "id": f"{conv_id}-{next_num}",
                "from_field": "System",
                "message": message_text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
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

    for conv in conversations:
        if conv["conv_id"] == conv_id:
            return conv, status.HTTP_200_OK

    return {"error": "Conversation not found."}, status.HTTP_404_NOT_FOUND
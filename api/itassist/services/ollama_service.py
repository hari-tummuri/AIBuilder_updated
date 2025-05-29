import requests
from core.settings import CONV_JSON_FILE, MODELS_FILE
import json
from .hyper_params_service import get_hyperparameters
# from .conversation import get_conversation_by_id

def bytes_to_gib(size_bytes):
    if size_bytes is None:
        return None
    gib = size_bytes / (1024 ** 3)
    return round(gib, 2) 

def is_embedding_model(model_name: str) -> bool:
    embedding_keywords = ['embed', 'embedding', 'bge', 'minilm']
    return any(keyword in model_name.lower() for keyword in embedding_keywords)

def get_downloaded_models(ollama_url="http://localhost:11434/api/tags") -> dict:
    """
    Fetch list of downloaded Ollama models with their type.
    Raises requests.exceptions.RequestException if the API call fails.
    """
    response = requests.get(ollama_url, timeout=3)
    response.raise_for_status()
    data = response.json()

    models = []
    for model in data.get("models", []):
        size_bytes = model.get("size", None)
        models.append({
            "name": model.get("name"),
            "digest": model.get("digest"),
            "size": bytes_to_gib(size_bytes),
            "type": "embedding" if is_embedding_model(model.get("name", "")) else "language"
        })

    return {"models": models}


def delete_model(model_name: str, ollama_url="http://localhost:11434/api/delete") -> dict:
    """
    Send a delete request to Ollama API to delete a downloaded model.
    Returns the API response JSON.
    Raises requests.exceptions.RequestException on failure.
    """
    payload = {"name": model_name}
    response = requests.request("DELETE", ollama_url, json=payload, timeout=5)
    response.raise_for_status()
    # return response.json()
    try:
        return response.json()  # try parse JSON response
    except ValueError:
        # No JSON returned, return status code or message
        return {"message": "Model deleted successfully or no content returned.", "status_code": response.status_code}
    

def modelResponse(question, conv_id):
    # return "Response from LLM"
    from .conversation import get_conversation_by_id
    hyper_params = get_hyperparameters()
    system_prompt = hyper_params['parameters']['system_prompt']

    with open(MODELS_FILE, "r") as file:
        data = json.load(file)

    current_model = data.get('current_model')

    conv_details, staus = get_conversation_by_id(conv_id)  # Ensure conversation exists
    message_context = get_updated_messages(conv_details)
    
    # Convert message_context to OpenAI-like chat format
    chat_messages = [{"role": "system", "content": system_prompt+"dont mention that context is provided. just follow the instruction"}]

    for msg in message_context:
        chat_messages.append({
            "role": msg["from_field"],  # already 'user' or 'assistant'
            "content": msg["message"]
        })

     # Append the current user question as the last input
    chat_messages.append({"role": "user", "content": question})

    response = requests.post(
            'http://localhost:11434/api/chat',
            json={
                "model": current_model,
                "messages":chat_messages,
                "stream": False
            }
        )
    data = response.json()
    return data['message']['content']

def update_from_field(messages: list) -> list:
    """
    Converts 'from_field' values to lowercase:
    - 'System' becomes 'assistant'
    - 'User' becomes 'user'
    
    Args:
        messages (list): A list of message dictionaries.
    
    Returns:
        list: Updated list with modified 'from_field' values.
    """
    for msg in messages:
        if msg.get('from_field') == 'System':
            msg['from_field'] = 'assistant'
        elif msg.get('from_field') == 'User':
            msg['from_field'] = 'user'
    return messages

def get_updated_messages(data: dict) -> list:
    """
    Extracts and updates the 'messages' list from the input data.
    Returns an empty list if 'messages' is missing or empty.
    """
    messages = data.get('messages', [])
    if isinstance(messages, list) and messages:
        return update_from_field(messages)
    return []
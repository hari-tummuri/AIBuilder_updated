import requests
from core.settings import CONV_JSON_FILE, MODELS_FILE
import json
import os
from .hyper_params_service import get_hyperparameters
from .vectordb_service import query_vector_db
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
    
def rephrase_query(query, chat_messages, current_model):
    new_sys_prompt = "rephrase the question accoring to the given context...and give only the rephrased question..no extra information needed.."
    chat_messages[0] = {"role":"system", "content": new_sys_prompt}
    chat_messages.append({"role":"user", "content": query})
    print("rephrasing question...")
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

    

def modelResponse(question, conv_id, collection_name):
    # return "Response from LLM"
    from .conversation import get_conversation_by_id
    hyper_params = get_hyperparameters()
    system_prompt = hyper_params['parameters']['system_prompt']

    if not os.path.exists(MODELS_FILE):
        raise FileNotFoundError(f"Model file not found at {MODELS_FILE}")

    with open(MODELS_FILE, "r") as file:
        data = json.load(file)

    current_model = data.get('current_model')

    if not current_model:
        raise ValueError("No model is currently selected in models.json")

    conv_details, staus = get_conversation_by_id(conv_id)  # Ensure conversation exists
    message_context = get_updated_messages(conv_details)
    
    # Convert message_context to OpenAI-like chat format
    chat_messages = [{"role": "system", "content": "Answer the small talks like greetings, acknowledgements and wishes from your knowledge "+system_prompt+"while generating response dont mention that context is provided and give more priority to the previous messages.give some more infomation by applying common sense based on the context provided. just follow the instruction and give the response in 30 words."}]

    for msg in message_context:
        chat_messages.append({
            "role": msg["from_field"],  # already 'user' or 'assistant'
            "content": msg["message"]
        })
    

    db_context, references = query_vector_db(question, collection_name)

    # Append the current user question as the last input
    chat_messages.append({"role": "user", "content": f"Context : {db_context}..Query: {question}"})

    print("Generatig the response...")
    try:
        response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    "model": current_model,
                    "messages":chat_messages,
                    "stream": False
                }
            )
        response.raise_for_status()

    except requests.RequestException as e:
        raise Exception(f"Failed to contact Ollama: {str(e)}")
    except Exception:
        raise Exception("Some uknown error from ollama...might be model does not exist in local machine")
    data = response.json()

    if "message" not in data or "content" not in data["message"]:
        raise ValueError("Invalid response structure from Ollama")
    
    return {'message' : data['message']['content'], 'references': references}
    # return data['message']['content']


async def modelResponseStream(question, conv_id, collection_name):
    import httpx
    from .conversation import get_conversation_by_id, add_system_message
    hyper_params = get_hyperparameters()
    system_prompt = hyper_params['parameters']['system_prompt']
    temparature = hyper_params['parameters']['llm']['temperature']
    max_tokens = hyper_params['parameters']['llm']['max_tokens']

    if not os.path.exists(MODELS_FILE):
        yield "[ERROR] Model config not found."
        return
    
    with open(MODELS_FILE, "r") as file:
        data = json.load(file)

    current_model = data.get('current_model')
    if not current_model:
        yield "[ERROR] No model selected."
        return
    
    conv_details, _ = get_conversation_by_id(conv_id)
    message_context = get_updated_messages(conv_details)

    # Convert message_context to OpenAI-like chat format
    chat_messages = [{"role": "system", "content": "Answer the small talks like greetings, acknowledgements and wishes from your knowledge "+system_prompt+"while generating response dont mention that context is provided and give more priority to the previous messages.give some more infomation by applying common sense based on the context provided."}]

    for msg in message_context:
        chat_messages.append({
            "role": msg["from_field"],  # already 'user' or 'assistant'
            "content": msg["message"]
        })

    db_context, references = query_vector_db(question, collection_name)

    # Append the current user question as the last input
    chat_messages.append({
        "role": "user",
        "content": f"Context : {db_context}..Query: {question}"
    })
    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", "http://localhost:11434/api/chat", json={
            "model": current_model,
            "messages": chat_messages,
            "stream": True,
            "temperature": temparature,
            "max_tokens" : max_tokens
        }) as response:
            full_response = ""
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    line = line[6:]

                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        full_response += content
                        # yield content
                        yield json.dumps({
                            "from_field": "System",
                            "message": content,
                            "references": references
                        }) + "\n"
                except:
                    continue
    # After stream ends, save full_response to your JSON
    add_system_message(conv_id, full_response, references)


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




import requests

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
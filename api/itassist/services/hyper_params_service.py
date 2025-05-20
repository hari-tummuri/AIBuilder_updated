import json
import os
from django.conf import settings
from core.settings import USER_DATA_ROOT


# This function retrieves hyperparameters from a JSON file.
# It first checks for a user-specific file and falls back to a default file if not found.
# The function returns the loaded hyperparameters as a dictionary.
def get_hyperparameters():
    # base_path = os.path.join(settings.BASE_DIR, 'hyperparams')
    selected_path = os.path.join(USER_DATA_ROOT, 'selected_hyper_params.json')
    default_path = os.path.join(USER_DATA_ROOT, 'default_hyper_params.json')

    if os.path.exists(selected_path):
        source = 'selected_hyper_params.json'
        target_path = selected_path
    else:
        source = 'default_hyper_parameters.json'
        target_path = default_path

    # target_path = selected_path if os.path.exists(selected_path) else default_path

    with open(target_path, 'r') as f:
        data = json.load(f)

    return {
        "source": source,
        "parameters": data
    }

# This function validates the structure of the hyperparameters against a template.
# It checks if the keys and their types match the expected structure.
# If the structure is valid, it returns True; otherwise, it returns False.
def compare_structure(template, data):
    """Recursively compare keys and structure of two dicts."""
    if not isinstance(template, dict) or not isinstance(data, dict):
        # Both should be dicts at each level
        return False
    if set(template.keys()) != set(data.keys()):
        return False
    for key in template:
        if isinstance(template[key], dict):
            if not compare_structure(template[key], data[key]):
                return False
        else:
            # For leaf nodes, just ensure key exists, don't check type/values here
            if key not in data:
                return False
    return True



def save_selected_hyperparameters(data: dict) -> dict:
    # base_path = os.path.join(settings.BASE_DIR, 'hyperparams')
    os.makedirs(USER_DATA_ROOT, exist_ok=True)
    selected_path = os.path.join(USER_DATA_ROOT, 'selected_hyper_params.json')

    # Optional: validate keys here if needed
    with open(selected_path, 'w') as f:
        json.dump(data, f, indent=2)

    return {
        "message": "Hyperparameters updated successfully",
        "file": "selected_hyper_params.json"
    }
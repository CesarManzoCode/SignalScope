import json
from pathlib import Path
from typing import Any, Dict


CONFIG_PATH = Path(__file__).parent / "user_config.json"


def load_user_config() -> Dict[str, Any]:
    """
    Load user configuration from JSON file.

    Returns:
        dict: Parsed user configuration.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("user_config.json not found in config directory")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in user_config.json")
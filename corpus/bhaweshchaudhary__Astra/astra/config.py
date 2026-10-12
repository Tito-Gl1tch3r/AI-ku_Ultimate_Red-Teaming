import json
import logging
import os
from typing import Dict

def load_config(config_path: str = None) -> Dict:
    """Load configuration from file."""
    default_config = {
        "api_token": "",
        "whoisxml_api_key": "",
        "default_ports": "22,80,443,8080,8443",
        "default_timeout": 1.0
    }

    # Set default config path if none provided
    if config_path is None:
        config_path = os.path.expanduser("~/.astra/config.json")
    else:
        config_path = os.path.expanduser(config_path)

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            default_config.update(config)
            logging.debug(f"Loaded config from {config_path}")
    except FileNotFoundError:
        logging.debug(f"Config file {config_path} not found.")
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing config file {config_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error loading config {config_path}: {e}")

    return default_config
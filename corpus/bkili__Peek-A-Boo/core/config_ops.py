import os
from pathlib import Path
from core.utils.formatter import printc
from core.state import reload_global_config
from ruamel.yaml import YAML

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.preserve_quotes = True

DEFAULT_CONFIG_PATH = Path(os.getenv("PB_CONFIG_PATH", "config.yaml"))
DEFAULT_CONFIG = {}
_cached_config = None  # Internal cache


def load_global_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Read YAML config from file."""
    if not path.exists():
        with path.open("w") as f:
            yaml.dump(DEFAULT_CONFIG, f)
        printc(
            f"[!] Configuration file not found. Created default at {path}", level="info"
        )

    try:
        with path.open("r") as file:
            config = yaml.load(file)
            return config if isinstance(config, dict) else {}
    except Exception as e:
        printc(f"[!] Error parsing YAML config: {e}", level="error")
        return {}


def get_global_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Return cached config after first load."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_global_config(path)
    return _cached_config


def add_alias_to_config(alias, command):
    config = get_global_config()

    if "ALIASES" not in config or not isinstance(config["ALIASES"], dict):
        config["ALIASES"] = {}

    config["ALIASES"][alias] = command

    with DEFAULT_CONFIG_PATH.open("w") as file:
        yaml.dump(config, file)

    reload_global_config(DEFAULT_CONFIG_PATH)

    printc(f"[+] Alias '{alias}: {command}' added to config.", level="success")

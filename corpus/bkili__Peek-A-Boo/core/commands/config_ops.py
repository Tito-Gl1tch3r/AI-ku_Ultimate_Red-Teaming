# core/commands/config_ops.py
import json
from pathlib import Path
from core.registry import register_command
from core.state import get_current_module
from core.utils.formatter import printc


@register_command("save")
def handle_save(args, shared_data):
    mod = get_current_module()
    try:
        if args and args[0] == "config" and len(args) > 1:
            filepath = Path("configs") / args[1]
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(mod.options, f, indent=4)
            printc(f"Configuration saved to {filepath}", level="success")
        else:
            printc("Usage: save config <filename>", level="warn")
    except Exception:
        printc("No module selected. Use a module before saving config.", level="error")
        return


@register_command("load")
def handle_load(args, shared_data):
    try:
        if not args:
            printc("Usage: load <config|module> <value>", level="warn")
            return

        if args[0] == "config" and len(args) > 1:
            module = get_current_module()
            if not module:
                printc(
                    "No module selected. Use a module before loading config.",
                    level="warn",
                )
                return
            filepath = Path("configs") / args[1]
            filepath = filepath.expanduser()
            if not filepath.exists():
                printc("File not found.", level="error")
                return
            with open(filepath, "r") as f:
                config = json.load(f)
            for k, v in config.items():
                module.set_option(k, str(v))
            printc(f"Configuration loaded from {filepath}", level="success")
    except Exception:
        return

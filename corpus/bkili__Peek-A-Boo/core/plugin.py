# core/plugin.py

import importlib.util
import os
from core.utils.formatter import printc
from core.base_plugin import Plugin as BasePlugin
from core.registry import register_command  # noqa: F401

PLUGINS_DIR = "plugins"

loaded_plugins = {}


def load_plugins(plugin_names, cli_context):
    if plugin_names is None:
        return {}
    for name in plugin_names:
        plugin_path = os.path.join(PLUGINS_DIR, name, "plugin.py")
        if not os.path.exists(plugin_path):
            printc(f"[!] Plugin '{name}' not found at {plugin_path}", level="warn")
            continue

        spec = importlib.util.spec_from_file_location(f"{name}_plugin", plugin_path)
        if spec is None:
            printc(f"[!] Failed to load spec for plugin '{name}'", level="error")
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            printc(f"[!] Error loading plugin '{name}': {e}", level="error")
            continue

        if not hasattr(module, "Plugin"):
            printc(
                f"[!] Plugin '{name}' does not define a 'Plugin' class", level="error"
            )
            continue

        plugin_class = module.Plugin
        if not issubclass(plugin_class, BasePlugin):
            printc(
                f"[!] Plugin '{name}' does not inherit from base Plugin class",
                level="error",
            )
            continue

        try:
            instance = plugin_class()
            instance.on_load(cli_context)

            commands = instance.register_commands()
            for cmd_name, handler in commands.items():
                cli_context.setdefault("commands", {})[cmd_name] = handler

            loaded_plugins[name] = instance
            printc(f"[✓] Loaded plugin: {name}", level="success")
        except Exception as e:
            printc(f"[!] Plugin '{name}' failed to initialize: {e}", level="error")
    return loaded_plugins

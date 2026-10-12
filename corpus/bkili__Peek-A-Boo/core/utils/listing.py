import os
import importlib
import logging

EXCLUDED_MODULES = {"__init__", "base"}
EXCLUDED_PLUGINS = {}
EXCLUDED_EXPLOITS = {}


def list_modules():
    modules_dir = os.path.join(os.path.dirname(__file__), "..", "..", "modules")
    modules_dir = os.path.abspath(modules_dir)

    if not os.path.exists(modules_dir):
        logging.warning(f"Modules directory not found: {modules_dir}")
        return []

    return [
        f[:-3]
        for f in os.listdir(modules_dir)
        if f.endswith(".py")
        and not f.startswith("_")
        and f[:-3] not in EXCLUDED_MODULES
    ]


def list_plugins():
    plugins_dir = os.path.join(os.path.dirname(__file__), "..", "..", "plugins")
    plugins_dir = os.path.abspath(plugins_dir)

    if not os.path.exists(plugins_dir):
        logging.warning(f"Plugins directory not found: {plugins_dir}")
        return []

    return [
        f[:-3]
        for f in os.listdir(plugins_dir)
        if f.endswith(".py")
        and not f.startswith("_")
        and f[:-3] not in EXCLUDED_PLUGINS
    ]


def list_exploits():
    exploits_dir = os.path.join(os.path.dirname(__file__), "..", "..", "exploits")
    exploits_dir = os.path.abspath(exploits_dir)

    if not os.path.exists(exploits_dir):
        logging.warning(f"Exploits directory not found: {exploits_dir}")
        return []

    return [
        f[:-3]
        for f in os.listdir(exploits_dir)
        if f.endswith(".py")
        and not f.startswith("_")
        and f[:-3] not in EXCLUDED_EXPLOITS
    ]


def list_modules_by_category():
    categorized = {}
    for module_name in list_modules():
        try:
            module = importlib.import_module(f"modules.{module_name}")
            instance = module.Module()
            category = getattr(instance, "category", "uncategorized")
            categorized.setdefault(category, []).append(module_name)
        except Exception as e:
            logging.warning(f"Failed to categorize module '{module_name}': {e}")
    return categorized


def list_plugins_by_category():
    categorized = {}
    for plugin_name in list_plugins():
        try:
            plugin = importlib.import_module(f"plugins.{plugin_name}")
            instance = plugin.Module()
            category = getattr(instance, "category", "uncategorized")
            categorized.setdefault(category, []).append(plugin_name)
        except Exception as e:
            logging.warning(f"Failed to categorize plugin '{plugin_name}': {e}")
    return categorized


def list_exploits_by_category():
    categorized = {}
    for exploit_name in list_exploits():
        try:
            exploit = importlib.import_module(f"exploits.{exploit_name}")
            instance = exploit.Module()
            category = getattr(instance, "category", "uncategorized")
            categorized.setdefault(category, []).append(exploit_name)
        except Exception as e:
            logging.warning(f"Failed to categorize exploit '{exploit_name}': {e}")
    return categorized

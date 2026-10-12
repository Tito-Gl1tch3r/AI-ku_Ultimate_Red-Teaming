# core/commands/module_ops.py
import importlib
from importlib.util import spec_from_file_location, module_from_spec
import os
from core.registry import register_command
from core.state import set_current_module
from core.utils.formatter import printc
from core.utils.listing import list_plugins, list_exploits


@register_command("use")
def handle_use(args, shared_data):
    if not args:
        printc("Usage: use <module_name>", level="warn")
        return
    module_name = args[0]
    try:
        if module_name in list_plugins():
            path = os.path.join("plugins", module_name + ".py")
            spec = spec_from_file_location(module_name, path)
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)
            instance = mod.Module()

        elif module_name in list_exploits():
            path = os.path.join("exploits", module_name + ".py")
            spec = spec_from_file_location(module_name, path)
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)
            instance = mod.Module()
        else:
            module = importlib.import_module(f"modules.{module_name}")
            instance = module.Module()
        set_current_module(instance)
        shared_data["CURRENT_MODULE"] = instance
        printc(f"[+] Module selected: {module_name}", level="success")
    except Exception as e:
        shared_data["CURRENT_MODULE"] = None
        printc(f"[!] Failed to import module '{module_name}': {e}", level="error")


@register_command("info")
def handle_info(args, shared_data):
    from core.state import get_current_module

    mod = get_current_module()
    if args:
        module_name = args[0]
        try:
            if module_name in list_plugins():
                path = os.path.join("plugins", module_name + ".py")
                spec = spec_from_file_location(module_name, path)
                mod_file = module_from_spec(spec)
                spec.loader.exec_module(mod_file)
                temp = mod_file.Module()
            else:
                module = importlib.import_module(f"modules.{module_name}")
                temp = module.Module()
            mod = temp
        except Exception as e:
            printc(f"Error loading module: {e}", level="error")
            return
    if mod:
        printc(f"Module: {mod.name}", level="headline")
        print(f"Description: {mod.description}")
        print(f"Author: {getattr(mod, 'author', '-')}")
        print(f"Email: {getattr(mod, 'author_email', '-')}")
        print(f"Website: {getattr(mod, 'url', '-')}")
        print(f"License: {getattr(mod, 'license', '-')}")
        print(f"Version: {getattr(mod, 'version', '-')}")
    else:
        printc("No module selected.", level="warn")


@register_command("run")
def handle_run(args, shared_data):
    from core.state import get_current_module

    mod = get_current_module()
    if not mod:
        printc("No module selected.", level="error")
        return

    if hasattr(mod, "requires"):
        for dep in mod.requires():
            try:
                dep_mod = importlib.import_module(f"modules.{dep}").Module()
                for k, v in mod.options.items():
                    if k in dep_mod.options:
                        dep_mod.set_option(k, v)
                printc(f"[core] Running dependency: {dep}", level="debug")
                dep_mod.run(shared_data)
            except Exception as e:
                printc(f"[core] Failed to run dependency {dep}: {e}", level="error")
    mod.run(shared_data)


@register_command("reload")
def handle_reload(args, shared_data):
    from core.state import get_current_module

    mod = get_current_module()
    if mod and hasattr(mod, "options_reload"):
        mod.options_reload()
        printc(f"[{mod.name}] Options reloaded to default.", level="info")
    else:
        printc("No module found: reload not supported.", level="warn")

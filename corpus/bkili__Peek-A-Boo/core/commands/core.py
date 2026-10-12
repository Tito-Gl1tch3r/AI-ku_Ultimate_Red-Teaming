# core/commands/core.py
from core.registry import register_command
from core.utils.formatter import printc
from core.config_ops import add_alias_to_config
import sys
import os


@register_command("exit")
def handle_exit(args, shared_data):
    printc("Exiting...", level="warn")
    sys.exit()


@register_command("help")
def handle_help(args, shared_data):
    from core.registry import COMMAND_HANDLERS

    printc("Available commands:", level="info")
    for cmd in sorted(COMMAND_HANDLERS):
        print(f"  - {cmd}")


@register_command("clear")
def handle_clear(args, shared_data):
    os.system("cls" if os.name == "nt" else "clear")


@register_command("history")
def handle_history(args, shared_data):
    from core.cli import HISTORY_PATH

    path = HISTORY_PATH
    if not os.path.exists(path):
        printc("No command history found.", level="warn")
        return

    try:
        with open(path, "r") as file:
            history = file.read().strip()
            if history:
                printc("Command History:", level="selection")
                for line in history.splitlines():
                    printc(f"{line}", level="info")
            else:
                printc("No command history found.", level="warn")
    except Exception as e:
        printc(f"[!] Failed to read history: {e}", level="error")


@register_command("debug")
def handle_debug(args, shared_data):
    for arg in args:
        print(f"Debug argument: {arg}")


@register_command("alias")
def handle_alias(args, shared_data):
    if not args:
        printc("Usage: alias <alias_name> = <command>", level="warn")

    elif len(args) == 1:
        printc("Usage: alias <alias_name> = <command>", level="warn")

    else:
        input_str = " ".join(args)
        if "=" not in input_str:
            printc("Usage: alias <alias_name> = <command>", level="warn")
            return
        alias_name, command_str = map(str.strip, input_str.split("=", 1))

        if not alias_name or not command_str:
            printc("Usage: alias <alias_name> = <command>", level="warn")
            printc("Both alias name and command must be provided.", level="error")
            return

        add_alias_to_config(alias_name, command_str)
        printc(
            f"[*] Alias registered: {alias_name} => {command_str}", level="selection"
        )

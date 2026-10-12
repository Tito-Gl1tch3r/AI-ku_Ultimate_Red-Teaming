# core/commands/display.py
from core.registry import register_command
from core.utils.formatter import printc
from core.utils.listing import (
    list_modules_by_category,
    list_plugins_by_category,
    list_modules,
    list_exploits_by_category,
)
from core.state import get_current_module


@register_command("show")
def handle_show(args, shared_data):
    mod = get_current_module()
    if not mod:
        printc("No module selected.", level="error")
        return
    if not args:
        printc("Usage: show <options|summary>", level="warn")
        return
    sub = args[0]
    if sub == "options":
        print(f"{'Option':<20} {'Value':<35} {'Required':<10}")
        print(f"{'-' * 20} {'-' * 35} {'-' * 10}")
        for k, v in mod.options.items():
            req = "yes" if k in mod.required_options else ""
            print(f"{k:<20} {v:<35} {req:<10}")
    elif sub == "summary":
        summary = shared_data.get("last_summary")
        if summary:
            mod.print_summary(summary)
        else:
            printc("No summary available.", level="warn")


@register_command("list")
def handle_list(args, shared_data):
    def print_categorized(title, data):
        printc(title, level="headline")
        for category, items in data.items():
            printc(f"[{category}]", level="module")
            for item in items:
                current = get_current_module()
                prefix = "[*]" if current and current.name == item else "[-]"
                level = "selection" if prefix == "[*]" else "dim"
                printc(f"  {prefix} {item}", level=level)
            print()

    if not args or args[0] == "all":
        print_categorized("Available modules:", list_modules_by_category())
        print_categorized("Available exploits:", list_exploits_by_category())
        print_categorized("Available plugins:", list_plugins_by_category())
    elif args[0] in ("modules", "module"):
        print_categorized("Available modules:", list_modules_by_category())
    elif args[0] in ("plugins", "plugin"):
        print_categorized("Available plugins:", list_plugins_by_category())
    elif args[0] in ("exploits", "exploit"):
        print_categorized("Available exploits:", list_exploits_by_category())


@register_command("search")
def handle_search(args, shared_data):
    if not args:
        printc("Usage: search <keyword>", level="warn")
        return
    keyword = args[0].lower()
    matches = [m for m in list_modules() if keyword in m.lower()]
    for m in matches:
        printc(f"  - {m}", level="info")

    mod = get_current_module()
    if mod:
        for key in mod.options:
            if keyword in key.lower():
                printc(f"  [option] {key}", level="success")

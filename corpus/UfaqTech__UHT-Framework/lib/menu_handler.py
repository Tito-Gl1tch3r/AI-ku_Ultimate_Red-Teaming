import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.align import Align

console = Console()

# ───────────────────────────────────────────────
# Banner
# ───────────────────────────────────────────────
def display_banner(version, os_type=None):
    """
    Displays the UHT banner with ASCII art, version, and system info.
    """
    banner_ascii = """
██╗   ██╗██╗  ██╗████████╗
██║   ██║██║  ██║╚══██╔══╝
██║   ██║███████║   ██║   
██║   ██║██╔══██║   ██║   
╚██████╔╝██║  ██║   ██║   
 ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
"""

    banner_text = Text.from_markup(
        f"[bold bright_green]{banner_ascii}[/]\n"
        f"[bold yellow]UfaqTech Hacking Toolkit[/]\n\n"
        f"[bold cyan]Version:[/] {version}\n"
        f"[bold magenta]OS Detected:[/] {os_type if os_type else 'Unknown'}\n"
    )

    header_panel = Panel(
        Align.center(banner_text),
        border_style="bright_green",
        title="[bold blue]UHT[/]",
        padding=(1, 2),
    )
    console.print(header_panel)


# ───────────────────────────────────────────────
# Footer
# ───────────────────────────────────────────────
def display_footer(os_type, installed, total, version):
    """Displays a footer with system info and status."""
    footer_text = (
        f"[bold cyan]OS:[/] {os_type}   "
        f"[bold magenta]Installed:[/] {installed}/{total}   "
        f"[bold yellow]Version:[/] {version}"
    )
    footer_panel = Panel(
        Align.center(footer_text),
        border_style="bright_black",
        padding=(0, 1),
    )
    console.print(footer_panel)


# ───────────────────────────────────────────────
# OS Filter Menu
# ───────────────────────────────────────────────
def display_filter_menu():
    """Displays a menu to let the user choose an OS filter."""
    table = Table(
        title="[bold yellow]Select OS Filter[/]",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    table.add_column("Option", style="bold cyan", justify="center", no_wrap=True)
    table.add_column("OS", style="bold yellow", justify="left")

    table.add_row("1", "All Tools")
    table.add_row("2", "Linux")
    table.add_row("3", "Windows")
    table.add_row("4", "Termux")
    table.add_row("[bold red]0[/]", "[bold red]Exit[/]")

    console.print(Panel(Align.center(table), border_style="bright_black"))
    return console.input("\n[bold cyan]Enter your choice: [/]").strip().lower()


# ───────────────────────────────────────────────
# Main Menu
# ───────────────────────────────────────────────
def display_main_menu(categories, manager, os_filter, uht_version, total_filtered_tools):
    """
    Displays the main menu with tool categories and returns the user's choice.
    """
    installed_count = len(manager.get_installed_tools_names())

    table = Table(
        title=f"[bold yellow]Main Menu ({os_filter.capitalize()})[/]",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    table.add_column("Option", style="bold cyan", justify="center", no_wrap=True)
    table.add_column("Description", style="bold yellow", justify="left")
    table.add_column("Tools", style="bold magenta", justify="center", no_wrap=True)

    # OS Filter Option
    table.add_row("f", "Change OS Filter", "")

    # Installed Tools
    table.add_row("installed", "View Installed Tools", f"{installed_count}")

    # Categories
    for i, category in enumerate(categories, 1):
        tools_in_cat = len(manager.get_filtered_tools_data(os_filter)[i - 1]["tools"])
        table.add_row(str(i), category, str(tools_in_cat))

    # Update options
    table.add_row("update", "Check for Updates / New Tools", "")
    table.add_row("self-update", "Update UHT Framework", "")

    # Exit
    table.add_row("[bold red]0[/]", "[bold red]Exit[/]", "")

    console.print(Panel(Align.center(table), border_style="bright_black"))

    # Footer always under menu
    display_footer(manager.os_type, installed_count, total_filtered_tools, uht_version)

    return console.input("\n[bold cyan]Enter your choice: [/]").strip().lower()


# ───────────────────────────────────────────────
# All Tools Menu
# ───────────────────────────────────────────────
def display_all_tools_menu(manager, installed_only=False):
    """Displays all tools in one flat list (installed or all)."""
    clear_screen()

    if installed_only:
        title = "[bold yellow]Installed Tools[/]"
        all_tools_flat = manager.get_installed_tools_data()
    else:
        title = "[bold yellow]All Tools[/]"
        all_tools_flat = manager.get_all_tools_flattened()

    table = Table(title=title, box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Option", style="bold cyan")
    table.add_column("Tool Name", style="bold magenta")
    table.add_column("Category", style="bold yellow")
    table.add_column("Status", style="bold green")

    installed_tools = manager.get_installed_tools_names()

    for i, tool in enumerate(all_tools_flat, 1):
        status = "[green]Installed[/]" if tool["name"] in installed_tools else "[red]Not Installed[/]"
        table.add_row(str(i), tool["name"], tool["category"], status)

    table.add_row("b", "Back to Main Menu", "", "")
    table.add_row("0", "Exit", "", "")

    console.print(Panel(table, title_align="center"))
    return console.input("\n[bold cyan]Enter your choice: [/]").strip().lower()


# ───────────────────────────────────────────────
# Tool Menu
# ───────────────────────────────────────────────
def display_tool_menu(selected_category_name, category_tools, installed_tools_names):
    """Displays tools for a given category."""
    clear_screen()

    table = Table(
        title=f"[bold blue]{selected_category_name} Tools[/]",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    table.add_column("No.", style="bold cyan")
    table.add_column("Tool Name", style="bold magenta")
    table.add_column("Status", style="bold yellow")

    for i, tool in enumerate(category_tools, 1):
        status = "[green]Installed[/]" if tool["name"] in installed_tools_names else "[red]Not Installed[/]"
        table.add_row(str(i), tool["name"], status)

    table.add_row("b", "Back", "")
    table.add_row("0", "[bold red]Exit[/]", "")

    console.print(Panel(table))
    return console.input("\n[bold cyan]Enter your choice: [/]").strip().lower()


# ───────────────────────────────────────────────
# Tool Options Menu
# ───────────────────────────────────────────────
def display_tool_options(tool_name):
    """Displays install/run options for a tool."""
    clear_screen()

    table = Table(
        title=f"[bold blue]Actions for {tool_name}[/]",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    table.add_column("Option", style="bold cyan")
    table.add_column("Action", style="bold magenta")

    table.add_row("1", "Install / Update")
    table.add_row("2", "Run")
    table.add_row("b", "Back to previous menu")
    table.add_row("0", "Exit")

    console.print(Panel(table))
    return console.input("\n[bold cyan]Enter your choice: [/]").strip().lower()


# ───────────────────────────────────────────────
# Clear Screen
# ───────────────────────────────────────────────
def clear_screen():
    """Clears the terminal screen (cross-platform)."""
    os.system("clear" if os.name == "posix" else "cls")

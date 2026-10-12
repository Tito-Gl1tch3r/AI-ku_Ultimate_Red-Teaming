import json
import logging
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align
import subprocess

# Import UHT modules
from lib.os_utils import get_os_type
from lib.menu_handler import (
    display_banner, display_main_menu, display_tool_menu, 
    display_tool_options, display_all_tools_menu,
    clear_screen, display_footer, display_filter_menu
)
from lib.tool_manager import ToolManager
from lib.update_checker import (
    get_remote_tools_data, check_for_tool_updates_and_new_tools, display_update_status
)

# --- Setup Logging ---
log_file_path = Path("logs/uht.log")
log_file_path.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(log_file_path),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Rich Console ---
console = Console()

# --- Global Variables ---
UHT_VERSION = "v1.1.0"
TOOLS_DIR = "tools"
REMOTE_TOOLS_JSON_URL = "https://raw.githubusercontent.com/UfaqTech/UHT-Framework/main/config/tools.json"
TOOLS_DATA = {}
OS_TYPE = get_os_type()

# --- Load Configuration ---
def load_config():
    """Loads settings and tools data from JSON files."""
    global TOOLS_DATA
    tools_path = Path("config/tools.json")
    try:
        with open(tools_path, "r") as f:
            TOOLS_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(
            f"[bold red][ERROR] Tools data file not found or is invalid: {tools_path}[/]",
            justify="center",
        )
        logging.error(f"Error loading tools.json: {e}")
        sys.exit(1)

# --- Self Update Function ---
def self_update_uht():
    """Updates the UHT framework itself via git pull."""
    console.print(Panel("[bold blue]Updating UHT Framework...", style="dim"))
    logging.info("Starting UHT self-update.")
    try:
        result = subprocess.run(
            ["git", "pull"],
            check=True,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        console.print("[bold green][SUCCESS] UHT Framework updated successfully![/]")
        console.print(result.stdout)
        logging.info("UHT Framework updated successfully.")
        load_config()  # Reload config to get new version if updated
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red][ERROR] Failed to update UHT Framework: {e.stderr.strip()}[/]"
        )
        logging.error(f"Failed to update UHT Framework: {e.stderr.strip()}")
    except Exception as e:
        console.print(
            f"[bold red][ERROR] An unexpected error occurred during UHT update: {e}[/]"
        )
        logging.error(f"Unexpected error during UHT update: {e}")
    console.input("\n[bold green]Press Enter to continue...[/]")

# --- Main Loop ---
def main():
    """Main function to run the UHT CLI."""
    load_config()
    manager = ToolManager(TOOLS_DIR, TOOLS_DATA, OS_TYPE)
    
    current_os_filter = "all"
    
    while True:
        clear_screen()
        display_banner(UHT_VERSION, OS_TYPE)
        
        # Display the main menu with the current OS filter
        filtered_tools_data = manager.get_filtered_tools_data(current_os_filter)
        categories = [category_data.get("category") for category_data in filtered_tools_data]

        total_filtered_tools = sum(len(category['tools']) for category in filtered_tools_data)

        main_menu_choice = display_main_menu(
            categories, manager, current_os_filter, UHT_VERSION, total_filtered_tools
        )
        
        if main_menu_choice == "0":
            console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
            break
        
        # Handle OS filter selection via the 'f' menu
        elif main_menu_choice == "f":
            clear_screen()
            display_banner(UHT_VERSION, OS_TYPE)
            filter_choice = display_filter_menu()
            
            if filter_choice == "0":
                console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
                sys.exit(0)
            
            if filter_choice == "1":
                current_os_filter = "all"
            elif filter_choice == "2":
                current_os_filter = "linux"
            elif filter_choice == "3":
                current_os_filter = "windows"
            elif filter_choice == "4":
                current_os_filter = "termux"
            else:
                console.print("[bold red]Invalid choice. Returning to main menu.[/]", justify="center")
            continue
        
        elif main_menu_choice == "installed":
            installed_tools = manager.get_installed_tools_data()
            while True:
                installed_tools_choice = display_all_tools_menu(manager, installed_only=True)
                if installed_tools_choice == "b":
                    break
                elif installed_tools_choice == "0":
                    console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
                    sys.exit(0)
                else:
                    try:
                        tool_index = int(installed_tools_choice) - 1
                        if 0 <= tool_index < len(installed_tools):
                            selected_tool_data = installed_tools[tool_index]
                            while True:
                                tool_options_choice = display_tool_options(selected_tool_data["name"])
                                if tool_options_choice in ["B", "b"]:
                                    break
                                elif tool_options_choice == "0":
                                    console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
                                    sys.exit(0)
                                elif tool_options_choice == "1":
                                    manager.install_tool(selected_tool_data)
                                    console.input("\n[bold green]Press Enter to continue...[/]")
                                    break
                                elif tool_options_choice == "2":
                                    manager.run_tool(selected_tool_data)
                                    console.input("\n[bold green]Press Enter to continue...[/]")
                                    break
                                else:
                                    console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
                                    console.input("\n[bold green]Press Enter to continue...[/]")
                        else:
                            console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
                            console.input("\n[bold green]Press Enter to continue...[/]")
                    except (ValueError, IndexError):
                        console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
                        console.input("\n[bold green]Press Enter to continue...[/]")

        elif main_menu_choice.isdigit() and 1 <= int(main_menu_choice) <= len(categories):
            selected_category_name = categories[int(main_menu_choice) - 1]
            category_tools = filtered_tools_data[int(main_menu_choice) - 1]['tools']
            installed_tools_names = manager.get_installed_tools_names()
            
            while True:
                tool_menu_choice = display_tool_menu(
                    selected_category_name, category_tools, installed_tools_names
                )
                if tool_menu_choice in ["B", "b"]:
                    break
                elif tool_menu_choice == "0":
                    console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
                    sys.exit(0)
                elif tool_menu_choice.isdigit() and 1 <= int(tool_menu_choice) <= len(category_tools):
                    selected_tool_data = category_tools[int(tool_menu_choice) - 1]
                    while True:
                        tool_options_choice = display_tool_options(selected_tool_data["name"])
                        if tool_options_choice in ["B", "b"]:
                            break
                        elif tool_options_choice == "0":
                            console.print("\n[bold red]Exiting UHT. Goodbye![/]", justify="center")
                            sys.exit(0)
                        elif tool_options_choice == "1":
                            manager.install_tool(selected_tool_data)
                            installed_tools_names = manager.get_installed_tools_names()
                            console.input("\n[bold green]Press Enter to continue...[/]")
                            break
                        elif tool_options_choice == "2":
                            manager.run_tool(selected_tool_data)
                            console.input("\n[bold green]Press Enter to continue...[/]")
                            break
                        else:
                            console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
                            console.input("\n[bold green]Press Enter to continue...[/]")
                else:
                    console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
                    console.input("\n[bold green]Press Enter to continue...[/]")

        elif main_menu_choice == "update":
            clear_screen()
            remote_data = get_remote_tools_data(REMOTE_TOOLS_JSON_URL)
            if remote_data:
                new_tools, tools_to_update = check_for_tool_updates_and_new_tools(
                    TOOLS_DATA, remote_data
                )
                display_update_status(new_tools, tools_to_update)
            else:
                console.print(
                    "\n[bold red][ERROR] Could not perform update check. See logs for details.[/]",
                    justify="center",
                )
            console.input("\n[bold green]Press Enter to continue...[/]")

        elif main_menu_choice == "self-update":
            self_update_uht()

        else:
            console.print("[bold red]Invalid choice. Please try again.[/]", justify="center")
            console.input("\n[bold green]Press Enter to continue...[/]")


# --- Entry Point ---
if __name__ == "__main__":
    if "VIRTUAL_ENV" not in os.environ:
        console.print("[bold yellow][!] Virtual environment not active.[/]", justify="center")
        console.print("Please run the following command to activate the virtual environment:", justify="center")
        console.print("[bold cyan]    source venv/bin/activate[/]", justify="center")
        console.print("Then run: [bold cyan]python3 uth.py[/]", justify="center")
        sys.exit(1)
    main()


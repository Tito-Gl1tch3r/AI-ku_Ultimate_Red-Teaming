import json
import os
import sys
import logging
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align
from rich.status import Status

from lib.os_utils import (
    get_os_type, install_system_package, 
    install_python_requirements, run_command_in_os_utils
)

# --- Rich Console ---
console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ToolManager:
    """
    Manages the installation, uninstallation, and execution of tools.
    """
    def __init__(self, tools_dir, tools_data, os_type):
        self.tools_dir = Path(tools_dir)
        self.tools_data = tools_data
        self.os_type = os_type
        self.installed_tools_path = Path("config/installed_tools.json")
        self.installed_tools = self._load_installed_tools()
        self.tools_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_installed_tools(self):
        """Loads the list of installed tools from a JSON file."""
        if self.installed_tools_path.exists():
            try:
                with open(self.installed_tools_path, 'r') as f:
                    return json.load(f)
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Error loading installed tools data: {e}")
                return []
        return []

    def _save_installed_tools(self):
        """Saves the current list of installed tools to a JSON file."""
        try:
            with open(self.installed_tools_path, 'w') as f:
                json.dump(self.installed_tools, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving installed tools data: {e}")

    def get_tools_data(self):
        """Returns the full tools data dictionary."""
        return self.tools_data

    def get_installed_tools_names(self):
        """Returns a list of names of installed tools."""
        return [tool['name'] for tool in self.installed_tools]

    def get_installed_tools_data(self):
        """Returns a list of data for installed tools."""
        return self.installed_tools
    
    def get_all_tools_flattened(self):
        """Returns a flattened list of all tools from all categories."""
        all_tools = []
        for category_data in self.tools_data:
            for tool in category_data.get("tools", []):
                all_tools.append(tool)
        return all_tools
    
    def get_filtered_tools_data(self, os_filter):
        """
        Returns a filtered list of tools based on the specified OS.
        'all', 'linux', 'windows', 'termux'
        """
        if os_filter == "all":
            return self.tools_data

        filtered_data = []
        for category_data in self.tools_data:
            filtered_tools = []
            for tool in category_data.get("tools", []):
                if os_filter in tool.get("os_support", []):
                    filtered_tools.append(tool)
            if filtered_tools:
                filtered_data.append({
                    "category": category_data["category"],
                    "tools": filtered_tools
                })
        return filtered_data

    def install_tool(self, tool_data):
        """Installs a tool based on its configuration."""
        tool_name = tool_data.get("name")
        tool_full_path = self.tools_dir / tool_data.get("path", tool_name)
        
        console.print(Panel(
            f"[*] Preparing to install [bold cyan]{tool_name}[/]...", 
            title="Installation Process"
        ))
        logging.info(f"Attempting to install {tool_name} from {tool_data.get('repo_url', 'N/A')} to {tool_full_path}")
        
        # Check if the tool is already installed and offer to update
        if tool_full_path.exists():
            console.print(f"[bold yellow]Tool '{tool_name}' already exists. Attempting to update...[/]")
            logging.info(f"Tool {tool_name} already exists. Attempting update.")
            
            # Use 'git pull' to update the repository
            if not run_command_in_os_utils(
                ['git', 'pull'],
                f"Pulling latest changes for {tool_name}",
                cwd=str(tool_full_path)
            ):
                console.print(f"[bold red]Failed to update {tool_name}.[/]")
                return False
            
            console.print(f"[bold green]Successfully updated {tool_name}.[/]")
            return True

        # Handle system dependencies
        system_dependencies = tool_data.get("dependencies", {}).get(self.os_type, [])
        if not system_dependencies:
            console.print(f"[yellow]No specific system dependencies defined for {tool_name} on {self.os_type}.[/]", justify="center")
            logging.info(f"No specific system dependencies defined for {tool_name} on {self.os_type}.")
        else:
            with Status("[bold green]Checking for system dependencies...[/]") as status:
                for dep in system_dependencies:
                    status.update(f"[bold green]Installing system dependency: {dep}...[/]")
                    if not install_system_package(dep, self.os_type):
                        console.print(f"[bold red]Failed to install dependency: {dep}. Aborting installation.[/]")
                        return False
        
        # Cloning the repository
        repo_url = tool_data.get("repo_url")
        if not repo_url:
            console.print(f"[bold red]No repository URL provided for {tool_name}. Aborting.[/]")
            return False

        with Status("[bold green]Cloning repository...[/]") as status:
            if not run_command_in_os_utils(['git', 'clone', repo_url, str(tool_full_path)], f"Cloning {tool_name}"):
                console.print(f"[bold red]Failed to clone repository for {tool_name}.[/]")
                return False
            
        # Installing Python requirements
        with Status("[bold green]Installing Python requirements...[/]") as status:
            if not install_python_requirements(tool_full_path):
                console.print(f"[bold red]Failed to install Python requirements for {tool_name}.[/]")
                return False

        # Running post-install commands
        post_install_commands = tool_data.get("post_install", {}).get(self.os_type, [])
        if post_install_commands:
            with Status("[bold green]Running post-install commands...[/]") as status:
                for cmd in post_install_commands:
                    if not run_command_in_os_utils(cmd.split(), f"Post-install command for {tool_name}", cwd=str(tool_full_path)):
                        console.print(f"[bold red]Post-install command failed for {tool_name}.[/]")
                        return False

        # Mark tool as installed
        if tool_data not in self.installed_tools:
            self.installed_tools.append(tool_data)
            self._save_installed_tools()

        console.print(f"\n[bold green]Installation of {tool_name} complete![/]", justify="center")
        return True

    def run_tool(self, tool_data):
        """Runs an installed tool."""
        tool_name = tool_data.get("name")
        tool_full_path = self.tools_dir / tool_data.get("path", tool_name)
        
        if tool_full_path not in self.get_installed_tools_path():
            console.print(f"[bold yellow]Tool '{tool_name}' is not installed. Please install it first.[/]")
            return False

        run_command = tool_data.get("run", {}).get(self.os_type)
        if not run_command:
            console.print(f"[bold red]No run command defined for {tool_name} on {self.os_type}.[/]")
            return False

        console.print(Panel(f"[*] Running [bold cyan]{tool_name}[/]...", title="Tool Execution"))
        logging.info(f"Running tool {tool_name} with command: {run_command}")

        try:
            subprocess.run(
                run_command.split(), 
                cwd=str(tool_full_path), 
                check=True,
                text=True,
                encoding="utf-8"
            )
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Tool '{tool_name}' exited with error code {e.returncode}.[/]")
            console.print(e.stderr)
            logging.error(f"Tool {tool_name} failed: {e.stderr}")
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred while running '{tool_name}': {e}[/]")
            logging.error(f"Unexpected error running tool {tool_name}: {e}")

    def get_installed_tools_path(self):
        """Returns a list of paths for all installed tools."""
        return [self.tools_dir / tool.get("path", tool.get("name")) for tool in self.installed_tools]


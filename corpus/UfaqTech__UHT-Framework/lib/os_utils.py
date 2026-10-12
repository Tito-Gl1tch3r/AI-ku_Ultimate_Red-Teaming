import platform
import subprocess
import sys
import logging
from rich.console import Console
from rich.panel import Panel

# --- Rich Console ---
console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_os_type():
    """
    Returns a normalized string for the current OS type.
    'termux', 'macos', 'windows', 'linux'
    """
    system_name = platform.system().lower()
    if 'android' in platform.platform().lower():
        console.print("[yellow]Detected OS: Android / Termux. Using 'termux' profile.[/]", justify="center")
        return 'termux'
    elif 'linux' in system_name:
        if 'microsoft' in platform.release().lower():
            console.print("[yellow]Detected OS: WSL on Windows. Using 'linux' profile.[/]", justify="center")
        else:
            console.print("[yellow]Detected OS: Other Linux distribution. Package management might differ.[/]", justify="center")
        return 'linux'
    elif 'darwin' in system_name:
        console.print("[yellow]Detected OS: macOS. Using 'macos' profile.[/]", justify="center")
        return 'macos'
    elif 'windows' in system_name:
        console.print("[yellow]Detected OS: Windows. Using 'windows' profile.[/]", justify="center")
        return 'windows'
    else:
        console.print(f"[bold red]Unsupported OS: {system_name}.[/]", justify="center")
        sys.exit(1)

def install_system_package(package_name, os_type):
    """Installs a system package based on the detected OS type."""
    console.print(f"[*] Attempting to install system package: [bold cyan]{package_name}[/]...", justify="center")
    
    if os_type == 'termux':
        cmd = ['pkg', 'install', '-y', package_name]
    elif os_type == 'linux':
        cmd = ['sudo', 'apt-get', 'install', '-y', package_name]
    elif os_type == 'macos':
        cmd = ['brew', 'install', package_name]
    elif os_type == 'windows':
        console.print("[yellow]Windows installation of system packages is not fully supported by UHT at this time.[/]", justify="center")
        return False
    else:
        console.print("[bold red]Unsupported OS for system package installation.[/]", justify="center")
        return False
    
    return run_command_in_os_utils(cmd, f"Installing {package_name}")

def install_python_requirements(tool_path):
    """Installs Python requirements from a requirements.txt file if it exists."""
    req_file = tool_path / "requirements.txt"
    if req_file.exists():
        console.print(f"[*] Installing Python requirements from {req_file}...", justify="center")
        return run_command_in_os_utils([sys.executable, '-m', 'pip', 'install', '-r', str(req_file)], f"Installing Python requirements for {tool_path}")
    return True

def run_command_in_os_utils(command, description, suppress_error=False, cwd=None):
    """
    Executes a shell command.
    
    Args:
        command (list): The command and its arguments.
        description (str): A description of the task for logging.
        suppress_error (bool): If True, a non-zero exit code will not be printed as a rich error message.
        cwd (str): The current working directory for the command.
        
    Returns:
        bool: True if the command succeeded, False otherwise.
    """
    console.print(f"[*] Executing: [cyan]{' '.join(command)}[/]...", justify="center")
    
    try:
        proc = subprocess.run(command, check=True, cwd=cwd, text=True, capture_output=True, encoding="utf-8")
        logging.info(f"Successfully ran command: {description}")
        return True
    except subprocess.CalledProcessError as e:
        if not suppress_error:
            console.print(Panel(f"[bold red]Command failed with exit code {e.returncode}.[/]\n\n{e.stderr.strip()}", title="Standard Error", style="bold red"))
        logging.error(f"Command failed: {description} | Exit Code: {e.returncode} | Error: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        if not suppress_error:
            console.print(f"[bold red]Command not found: '{command[0]}'. Please ensure it's installed and in your PATH.[/]", justify="center")
        logging.error(f"Command not found: '{command[0]}'")
        return False
    except Exception as e:
        if not suppress_error:
            console.print(Panel(f"[bold red]An unexpected error occurred:[/]\n{e}", style="bold red"))
        logging.error(f"Unexpected error executing command: {e}")
        return False


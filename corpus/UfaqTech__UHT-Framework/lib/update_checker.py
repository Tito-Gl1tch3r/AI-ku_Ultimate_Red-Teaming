import json
import requests
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_remote_tools_data(url):
    """
    Fetches the latest tools data from a remote URL.
    
    Args:
        url (str): The URL to the remote tools.json file.

    Returns:
        dict: The parsed JSON data if successful, otherwise an empty dictionary.
    """
    if not url or not url.startswith(('http://', 'https://')):
        console.print(Panel(
            Text("Remote URL is not configured or invalid. Cannot check for updates.", justify="center"),
            title="[red]Update Error[/red]", style="bold red"
        ))
        logging.error("Remote URL is not configured or invalid.")
        return {}

    try:
        console.print(f"[bold blue]Fetching remote tools data from[/bold blue] [link={url}]{url}[/link]...")
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        remote_data = response.json()
        console.print("[bold green]Remote data fetched successfully![/bold green]")
        return remote_data
    except requests.exceptions.RequestException as e:
        console.print(Panel(
            Text(f"Failed to fetch remote tools data: {e}\nPlease check your network connection and the URL.", justify="center"),
            title="[red]Network Error[/red]", style="bold red"
        ))
        logging.error(f"Failed to fetch remote tools data: {e}")
        return {}
    except json.JSONDecodeError as e:
        console.print(Panel(
            Text(f"Failed to parse remote data. The file might be corrupted: {e}", justify="center"),
            title="[red]Data Format Error[/red]", style="bold red"
        ))
        logging.error(f"Failed to parse remote JSON data: {e}")
        return {}
    except Exception as e:
        console.print(Panel(
            Text(f"An unexpected error occurred: {e}", justify="center"),
            title="[red]Unexpected Error[/red]", style="bold red"
        ))
        logging.error(f"An unexpected error occurred during remote data fetch: {e}")
        return {}

def flatten_tools_data(tools_data):
    """
    Flattens the nested tools data into a single dictionary
    mapping tool name to its data and category.
    """
    flat_list = {}
    for category_data in tools_data:
        category_name = category_data.get('category')
        for tool in category_data.get('tools', []):
            tool['category'] = category_name  # Add category to tool data for easier access
            flat_list[tool['name']] = tool
    return flat_list

def check_for_tool_updates_and_new_tools(local_data, remote_data):
    """
    Compares local tools data with remote data to find new tools.
    
    Args:
        local_data (list): The locally loaded tools data.
        remote_data (list): The remotely fetched tools data.

    Returns:
        tuple: A tuple containing two lists: (list of new tools, list of tools to update).
    """
    new_tools = []
    tools_to_update = []  # Placeholder for future version-based updates

    local_flat_list = flatten_tools_data(local_data)
    remote_flat_list = flatten_tools_data(remote_data)
    
    # Check for new tools
    for remote_tool_name, remote_tool_data in remote_flat_list.items():
        if remote_tool_name not in local_flat_list:
            new_tools.append(remote_tool_data)
            
    return new_tools, tools_to_update

def display_update_status(new_tools, tools_to_update):
    """
    Displays the update status in a clear, formatted way using rich.
    
    Args:
        new_tools (list): List of new tools found.
        tools_to_update (list): List of tools to update (currently not used but included for future use).
    """
    if new_tools:
        console.print(f"\n[bold green]Found {len(new_tools)} new tool(s) available for installation:[/bold green]")
        
        table = Table(
            title=Text("New Tools Available", style="bold white"),
            box=box.SIMPLE_HEAD,
            style="bold blue",
            show_lines=False,
            expand=True
        )
        table.add_column("Tool Name", style="cyan", min_width=20)
        table.add_column("Category", style="green", min_width=20)
        table.add_column("Description", style="white")

        for tool in new_tools:
            table.add_row(
                Text(tool.get('name', 'N/A'), style="bold cyan"),
                Text(tool.get('category', 'N/A'), style="green"),
                Text(tool.get('description', 'No description provided.'), style="dim")
            )
        console.print(table)
    elif tools_to_update:
        console.print("\n[bold yellow]The following tools have updates available (run `install` to update):[/bold yellow]")
        for tool in tools_to_update:
            console.print(f"- [cyan]{tool.get('name', 'N/A')}[/cyan] ({tool.get('category', 'N/A')})")
    else:
        console.print(Panel(
            Text("No new tools or updates found.\nYour UHT Framework is up to date!", justify="center"),
            title="[bold green]No Updates[/bold green]", style="bold green"
        ))


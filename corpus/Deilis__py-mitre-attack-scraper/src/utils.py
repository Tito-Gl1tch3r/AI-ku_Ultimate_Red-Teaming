import json
import os


def load_groups_data(filepath):

    """Load group data from a JSON file."""
    
    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist.")
        return []

    with open(filepath, 'r') as json_file:
        return json.load(json_file)


def display_group_info(group):

    """Display information about a specific group in a formatted manner."""

    if group:
        print("\nGroup Information:")
        print(f"ID: {group['ID']}")
        print(f"Name: {group['Name']}")
        print(f"Associated Groups: {group['Associated Groups']}")
        print(f"Description: {group['Description']}\n")
    else:
        print("No group found.")



def cache_group_data(group, cache_dir):

    """Cache group data in a specific directory."""

    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{group['ID']}.json")
    with open(cache_file, 'w') as json_file:
        json.dump(group, json_file, indent=4)
    print(f"Cached group data in {cache_file}")

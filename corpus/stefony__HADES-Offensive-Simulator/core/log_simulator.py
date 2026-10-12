import json
import os
import csv


def generate_log(event_dict, output_path="logs/event_log.json"):
    """
    Write a single event to a JSON file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Write event as standalone JSON object
    with open(output_path, "w") as f:
        json.dump(event_dict, f, indent=4)

    print("[+] Simulated log written to:", output_path)


def generate_csv_log(event_dict, output_path="logs/export.csv"):
    """
    Write event to a simple 2-row CSV (header + values).
    Overwrites existing file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Defensive check
    if not isinstance(event_dict, dict):
        raise ValueError("Event must be a dictionary.")

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(event_dict.keys())
        writer.writerow(event_dict.values())

    print("[+] CSV log written to:", output_path)

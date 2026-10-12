import os
import re
import subprocess

from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

def get_file_path(prompt_text: str) -> str:
    """Get file path with autocomplete support."""

    completer = PathCompleter()
    return prompt(prompt_text, completer=completer).strip()

def get_target_domains():
    """Get target domains from user input or file"""
    target_domains = []

    while True:
        print("\n")
        print("1] Single Domain")
        print("2] Multi Domain (from file)")
        print("\n")

        choice = input("[?] Enter your target type (1 - 2): ").strip()

        if choice == "1":
            domain = input("[?] Enter the target domain: ").strip()
            target_domains.append(domain)
            break

        elif choice == "2":
            file_path = get_file_path("[?] Enter the file path: ")
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    for line in file:
                        domain = line.strip()
                        target_domains.append(domain)
                break
            else:
                print("[!] File not found. Please enter a valid file path.")

        else:
            print("[!] Invalid choice. Please select 1 - 2.")

    return target_domains

def select_depth() -> str:
    """Select search depth for dorking."""

    while True:
        print("\n")
        print("1] target.com")
        print("2] *.target.com")
        print("3] *.*.target.com")
        print("\n")
        depth = input("[?] Choose depth for dorking (1 - 3): ").strip()

        if depth in ["1", "2", "3"]:
            return depth
        else:
            print("[!] Invalid choice. Please enter 1 - 3.")

def get_user_instructions() -> str:
    """Get custom report generation instructions from user."""

    print("You can provide custom instructions for report generation.")
    print("\n")    
    print("Examples:")
    print("  - Write the report in Korean")
    print("  - Use formal technical language")
    print("  - Focus on critical vulnerabilities only")
    print("\n")
    instructions = input("[?] Enter report instructions (press Enter for default): ").strip()

    if not instructions:
        instructions = "Generate a comprehensive security report with clear findings and actionable recommendations."

    return instructions

def integrate_notify() -> str:
    """Ask user if they want to integrate notify tool."""

    while True:
        print("\n")
        print("\n")
        print("\n")
        print("\n")

        notify = input("[?] Do you want to send a report using notify? (Y or N): ").strip()

        if notify in ["Y", "y", "N", "n"]:
            return notify
        else:
            print("[!] Invalid choice. Please enter Y or N")

def adjust_depth(target_domains: list, depth: str) -> list:
    """Apply subdomain wildcard patterns based on depth selection."""

    try:
        depth = int(depth)
        if depth < 1:
            raise ValueError("Invalid depth value")
    except ValueError:
        print("[!] Invalid depth input. Defaulting to depth = 1.")
        depth = 1

    if depth == 1:
        adjusted_domains = target_domains
    else:
        prefix = ".".join(["*"] * (depth - 1))
        adjusted_domains = [f"{prefix}.{domain}" for domain in target_domains]

    return adjusted_domains

def sanitize_filename(domain_name: str) -> str:
    """Sanitize domain name for safe file paths."""
    sanitized = domain_name.replace('*', 'wildcard')
    sanitized = re.sub(r'[\\/*?:"<>|]', '', sanitized)

    return sanitized

def send_notification(report_path: str):
    """Send notification using notify tool if available."""
    try:
        subprocess.run(["notify", "-data", report_path], check=True)
        print("[+] Notification sent successfully!")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] Failed to send notification. Make sure notify tool is installed.")
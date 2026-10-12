import sys, os, subprocess
from datetime import datetime

REQUIRED_PACKAGES = {
    "python-dotenv": "dotenv",
    "crewai": "crewai",
    "crewai-tools": "crewai_tools",
    "crewai[anthropic]": "anthropic",
    "crewai[google-genai]": "google.genai",
    "crewai-tools[serpapi]": "serpapi",
    "termcolor": "termcolor",
    "prompt-toolkit": "prompt_toolkit",
    "pyfiglet": "pyfiglet",
}

def pip_install(spec: str):
    """Install a package via pip with console feedback."""
    try:
        print(f"[+] Installing: {spec} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", spec])
    except Exception as e:
        print(f"[!] Failed to install {spec}: {e}")
        raise

def warn_python_version():
    """Warn when the running Python version differs from the supported version."""
    required_major, required_minor, required_patch = 3, 11, 9
    v = sys.version_info

    if (v.major, v.minor) != (required_major, required_minor) or v.micro != required_patch:
        print(f"[!] Detected Python {v.major}.{v.minor}.{v.micro}. Recommended: 3.11.9.")
        print("[!] Continuing, but if you see issues, use Python 3.11.9.")

warn_python_version()

THIRD_PARTY_IMPORT_ERROR = False
try:
    import pyfiglet
    from crewai import Crew
    from dotenv import load_dotenv
    from termcolor import colored
except ImportError:
    THIRD_PARTY_IMPORT_ERROR = True

if THIRD_PARTY_IMPORT_ERROR:
    print("[!] Missing required packages. Installing automatically...")
    for package_name, import_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            pip_install(package_name)

    print("[+] Package installation complete. Please restart the program.")
    sys.exit(0)

from config import (
    select_llm,
    create_llm,
    select_search_engine,
    ensure_search_engine_api_key
)

import pyfiglet
from crewai import Crew
from dotenv import load_dotenv
from termcolor import colored

from agents import agents as create_agents
from tasks import task
from utils import (
    get_target_domains,
    select_depth,
    get_user_instructions,
    adjust_depth,
    sanitize_filename,
    integrate_notify,
    send_notification
)

load_dotenv()

def clear_terminal():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")

def display_banner():
    """Display the DorkAgent banner and version information."""
    print(" ")
    print(" ")
    ascii_banner = pyfiglet.figlet_format("Dork Agent", font="big")
    print(colored(ascii_banner, "red"))
    print(colored("                                        by yee-yore", "red"))
    print("\n")
    print("DorkAgent is a LLM-powered agent for automated Google Dorking in bug hunting & pentesting.")
    print(colored("[Ver]", "red") + " Current DorkAgent version is v1.4")
    print("=" * 90)

if __name__ == "__main__":
    clear_terminal()
    display_banner()

    load_dotenv()
    provider, model = select_llm()
    llm = create_llm(provider, model)

    search_engine = select_search_engine()
    ensure_search_engine_api_key(search_engine)

    agent_list = create_agents(llm, search_engine)

    clear_terminal()
    display_banner()
    domains = get_target_domains()

    clear_terminal()
    display_banner()
    depth = select_depth()
    target_domains = adjust_depth(domains, depth)

    clear_terminal()
    display_banner()
    user_instructions = get_user_instructions()

    clear_terminal()
    display_banner()
    notify = integrate_notify()

    now = datetime.now()
    date = now.strftime("%y%m%d")
    LOG_DIR = os.path.join("./log", date)
    os.makedirs(LOG_DIR, exist_ok=True)

    for i, domain in enumerate(domains):
        target_domain = target_domains[i]
        original_domain = target_domain

        if '*' in target_domain:
            base_domain = '.'.join([p for p in target_domain.split('.') if p != '*'])
        else:
            base_domain = target_domain

        safe_domain = sanitize_filename(base_domain)

        tasks = task(original_domain, domain, agent_list)

        crew = Crew(
            agents=agent_list,
            tasks=tasks,
            verbose=1,
            max_rpm=15,
            output_log_file=True,
        )

        result = crew.kickoff(inputs={'user_instructions': user_instructions})

        crew_output = str(result)

        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        report_file_path = os.path.join(LOG_DIR, f"{timestamp}_{safe_domain}.md")
        with open(report_file_path, 'w', encoding='utf-8') as file:
            file.write(crew_output)

        print(f"\n[+] Security assessment report saved to: {report_file_path}")

        if notify in ["Y", "y"]:
            send_notification(report_file_path)
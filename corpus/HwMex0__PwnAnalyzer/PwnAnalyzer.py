import json
import re
import hashlib
import logging
import argparse
import os
import glob
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor

init(autoreset=True)

ASCII_LOGO = r"""
 ______                   _______                __                            
|   __ \.--.--.--..-----.|   _   |.-----..---.-.|  |.--.--..-----..-----..----.
|    __/|  |  |  ||     ||       ||     ||  _  ||  ||  |  ||-- __||  -__||   _|
|___|   |________||__|__||___|___||__|__||___._||__||___  ||_____||_____||__|  
                                                    |_____|                    
"""

def load_search_tasks(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    if 'templates' not in data:
        raise KeyError(f"The configuration '{json_file}' file is missing the 'templates' key.")
    return data

def compute_file_hash(file_path):
    hash_func = hashlib.sha256()
    try:
        with open(file_path, 'rb') as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except FileNotFoundError:
        return None

def execute_actions(actions):
    for action in actions:
        if action['type'] == 'alert':
            print(f"{Fore.YELLOW}[!] Alert: {action['message']}")

def search_in_file(file_path, patterns, template_name, context_enabled, results=None):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        for pattern_info in patterns:
            regex = pattern_info['pattern']
            case_sensitive = pattern_info.get('case_sensitive', False)
            context_lines = pattern_info.get('context_lines', 0)

            flags = re.MULTILINE
            if not case_sensitive:
                flags |= re.IGNORECASE

            pattern = re.compile(regex, flags)

            matches = []
            match_indices = []
            for idx, line in enumerate(lines):
                m = pattern.search(line)
                if m:
                    matches.append(m.group(0))
                    match_indices.append(idx)

            if matches:
                execute_actions(pattern_info.get('actions', []))
                log_message = (
                    f"{Fore.GREEN}[+] Template: {template_name}\n"
                    f"{Fore.GREEN}[+] File: {file_path}\n"
                    f"{Fore.GREEN}[+] Pattern: '{pattern_info['pattern']}'\n"
                    f"{Fore.GREEN}[+] Matches: {matches}\n"
                    f"{Fore.GREEN}[+] Severity: {pattern_info.get('severity', 'unknown')}\n"
                )
                logging.info(log_message)
                print(log_message)

                if results is not None:
                    results.append({
                        "template": template_name,
                        "file": file_path,
                        "pattern": pattern_info['pattern'],
                        "matches": matches,
                        "severity": pattern_info.get('severity', 'unknown'),
                    })

                if context_enabled and context_lines > 0:
                    for idx in match_indices:
                        start = max(idx - context_lines, 0)
                        end = min(idx + context_lines + 1, len(lines))
                        context = "".join(lines[start:end])
                        print(
                            f"{Fore.BLUE}Context:\n{context}\n{Fore.BLUE}---------------------------------------")
            else:
                print(f"{Fore.RED}[-] No matches found in {file_path} for pattern '{pattern_info['pattern']}'")

    except FileNotFoundError:
        error_message = f"{Fore.RED}[-] File not found: {file_path}"
        logging.error(error_message)
        print(error_message)
    except Exception as e:
        error_message = f"{Fore.RED}[-] An error occurred while reading {file_path}: {e}"
        logging.error(error_message)
        print(error_message)

def run_search(template_path, template_name, context_enabled, results=None):
    try:
        config = load_search_tasks(template_path)
        log_file = config.get('log_file', 'dfir_search.log')

        logging.basicConfig(filename=log_file, level=logging.INFO)
        print(Fore.CYAN + ASCII_LOGO)
        logging.info('DFIR search started')
        print(Fore.CYAN + '[+] DFIR search started')

        if results is None:
            results = []

        with ThreadPoolExecutor() as executor:
            futures = []
            for template in config['templates']:
                for task in template['search_tasks']:
                    file_pattern = task['file_path']
                    patterns = task['patterns']

                    matched_files = glob.glob(file_pattern, recursive=True)
                    if not matched_files:
                        matched_files = [file_pattern]

                    for file_path in matched_files:
                        file_hash_before = compute_file_hash(file_path)
                        logging.info(f"File hash before search: {file_hash_before}")
                        print(f"{Fore.CYAN}[+] File hash before search: {file_hash_before}")

                        futures.append(executor.submit(search_in_file, file_path, patterns, template_name, context_enabled, results))

                        file_hash_after = compute_file_hash(file_path)
                        logging.info(f"File hash after search: {file_hash_after}")
                        print(f"{Fore.CYAN}[+] File hash after search: {file_hash_after}")

            for future in futures:
                future.result()

        logging.info('DFIR search completed')
        print(Fore.CYAN + '[+] DFIR search completed')
        return results
    except KeyError as e:
        print(f"{Fore.RED}[-] Configuration error: {e}")
    except Exception as e:
        print(f"{Fore.RED}[-] An unexpected error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description='PwnAnalyzer - Exploitation detection tool')
    parser.add_argument('-t', '--template', required=True,
                        help='Path to the JSON configuration file or directory containing JSON files')
    parser.add_argument('-c', '--context', action='store_true', help='Enable context printing')
    parser.add_argument('-o', '--output', help='Path to JSON file for saving results')
    args = parser.parse_args()

    template_path = args.template
    context_enabled = args.context
    output_file = args.output

    all_results = []

    if os.path.isdir(template_path):
        for filename in os.listdir(template_path):
            if filename.endswith('.json'):
                all_results.extend(run_search(os.path.join(template_path, filename), filename, context_enabled))
    else:
        all_results.extend(run_search(template_path, os.path.basename(template_path), context_enabled))

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)

if __name__ == "__main__":
    main()

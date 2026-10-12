#!/usr/bin/env python3
# Simple proxy extractor for convinience sake

def extract_ip_port(input_file='proxies_raw.txt', output_file='proxy.txt'):
    """
    Extracts IP:PORT from lines like:
    46.254.93.26:80 | 6.01ms | HTTP
    and writes clean 'ip:port' lines to output_file.
    """
    cleaned = []
    try:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Extract everything before the first " | "
                ip_port = line.split(' | ')[0]
                # Validate basic IP:PORT format
                if ':' in ip_port and ip_port.replace('.', '').replace(':', '').replace(' ', '').isdigit():
                    cleaned.append(ip_port)
                else:
                    print(f"[!] Skipping invalid line: {line}")
    except FileNotFoundError:
        print(f"[ERROR] Input file '{input_file}' not found.")
        return

    # Write cleaned proxies
    with open(output_file, 'w') as f:
        for proxy in cleaned:
            f.write(proxy + '\n')

    print(f"[+] Successfully extracted {len(cleaned)} proxies to '{output_file}'.")

if __name__ == "__main__":
    # You can change filenames here if needed
    extract_ip_port('proxies_raw.txt', 'proxy.txt')
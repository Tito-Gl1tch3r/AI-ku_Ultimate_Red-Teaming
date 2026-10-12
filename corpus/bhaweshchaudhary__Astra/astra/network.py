import socket
import logging
from typing import List, Tuple
from ipaddress import ip_network
import concurrent.futures

def extract_ips(cidr_ranges: List[str], max_ips: int = None, max_ips_per_cidr: int = None) -> List[str]:
    """Extract IPs from CIDR ranges, applying global and per-CIDR limits."""
    all_ips = []
    for cidr in cidr_ranges:
        try:
            network = ip_network(cidr, strict=False)
            total_ips_in_cidr = network.num_addresses
            logging.debug(f"Processing CIDR {cidr} with {total_ips_in_cidr} total IPs")

            # Convert CIDR to list of IPs
            ip_list = [str(ip) for ip in network]

            # Apply per-CIDR limit if specified
            if max_ips_per_cidr is not None and len(ip_list) > max_ips_per_cidr:
                logging.info(f"Limiting {cidr} to {max_ips_per_cidr} IPs (out of {total_ips_in_cidr})")
                ip_list = ip_list[:max_ips_per_cidr]
            else:
                logging.debug(f"Using all {len(ip_list)} IPs from {cidr}")

            all_ips.extend(ip_list)

            # Apply global max_ips limit if specified
            if max_ips is not None and len(all_ips) > max_ips:
                logging.info(f"Reached global max-ips limit of {max_ips}, truncating IP list")
                all_ips = all_ips[:max_ips]
                break

        except ValueError as e:
            logging.error(f"Invalid CIDR range {cidr}: {e}")

    return all_ips

def is_host_alive(ip: str, timeout: float) -> bool:
    """Check if a host is alive by attempting a TCP connection."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, 80))  # Try port 80 as a common port
        sock.close()
        return True
    except (socket.timeout, socket.error):
        return False

def scan_port(ip: str, port: int, timeout: float) -> bool:
    """Scan a specific port on an IP to check if it's open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except socket.error:
        return False

def scan_network(ips: List[str], ports: List[int], timeout: float) -> Tuple[List[str], List[Tuple[str, int]]]:
    """Scan a list of IPs for live hosts and open ports."""
    live_hosts = []
    open_ports = []

    # Step 1: Find live hosts
    logging.info(f"Scanning {len(ips)} IPs for live hosts")
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_ip = {executor.submit(is_host_alive, ip, timeout): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            if future.result():
                live_hosts.append(ip)

    if not live_hosts:
        logging.info("No live hosts found")
        return [], []

    # Step 2: Scan ports on live hosts
    total_ports = len(ports) * len(live_hosts)
    logging.info(f"Scanning {len(ports)} ports on {len(live_hosts)} live hosts ({total_ports} total scans)")
    
    # Optimize for large port ranges
    max_workers = min(100, len(live_hosts) * len(ports) // 10 + 1)  # Scale workers based on workload
    scanned = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {}
        for ip in live_hosts:
            for port in ports:
                future = executor.submit(scan_port, ip, port, timeout)
                future_to_task[future] = (ip, port)
        
        for future in concurrent.futures.as_completed(future_to_task):
            ip, port = future_to_task[future]
            if future.result():
                open_ports.append((ip, port))
            scanned += 1
            if scanned % 1000 == 0:  # Log progress every 1000 scans
                logging.debug(f"Scanned {scanned}/{total_ports} ports")

    return live_hosts, open_ports
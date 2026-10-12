import json
import csv
import logging
from datetime import datetime
from typing import List, Set, Tuple

def report_results(
    org: str,
    cidrs: List[str],
    live_hosts: Set[str],
    open_ports: List[Tuple[str, int]],
    output_file: str = None,
    output_format: str = "json"
):
    """Generate and output scan results."""
    results = {
        "organization": org,
        "timestamp": datetime.utcnow().isoformat(),
        "cidr_ranges": cidrs,
        "live_hosts": sorted(list(live_hosts)),
        "open_ports": [{"ip": ip, "port": port} for ip, port in open_ports]
    }

    # Console output
    logging.info(f"Scan Results for {org}")
    logging.info(f"CIDR Ranges ({len(cidrs)}): {cidrs}")
    logging.info(f"Live Hosts ({len(live_hosts)}):")
    for host in sorted(live_hosts):
        logging.info(f" - {host}")
    logging.info(f"Open Ports ({len(open_ports)}):")
    if open_ports:
        for ip, port in sorted(open_ports):
            logging.info(f" - {ip}:{port}")
    else:
        logging.info("No open ports found.")

    # File output
    if output_file:
        try:
            if output_format == "json":
                with open(output_file, "w") as f:
                    json.dump(results, f, indent=2)
                logging.info(f"Results saved as JSON to {output_file}")
            elif output_format == "csv":
                with open(output_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["IP", "Port"])
                    for ip, port in open_ports:
                        writer.writerow([ip, port])
                logging.info(f"Results saved as CSV to {output_file}")
        except Exception as e:
            logging.error(f"Error saving results to {output_file}: {e}")

def save_results(org: str, cidr_ranges: List[str], live_hosts: List[str], open_ports: List[Tuple[str, int]], output_file: str, output_format: str):
    """Save scan results to a file in the specified format."""
    timestamp = datetime.now().isoformat()
    results = {
        "organization": org,
        "timestamp": timestamp,
        "cidr_ranges": cidr_ranges,
        "live_hosts": live_hosts,
        "open_ports": [{"ip": ip, "port": port} for ip, port in open_ports]
    }

    try:
        if output_format == "json":
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
        elif output_format == "csv":
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["IP", "Port"])
                for ip, port in open_ports:
                    writer.writerow([ip, port])
        logging.info(f"Results saved as {output_format.upper()} to {output_file}")
    except Exception as e:
        logging.error(f"Error saving results to {output_file}: {e}")
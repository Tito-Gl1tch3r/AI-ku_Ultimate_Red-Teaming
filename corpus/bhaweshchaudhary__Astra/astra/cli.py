import argparse
import logging
import sys
from typing import List, Tuple
from .config import load_config
from .api import get_cidr_ranges
from .network import extract_ips, scan_network
from .report import save_results

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Astra: A Powerful Network Scanner")
    parser.add_argument("org", nargs='?', help="Organization name or domain (e.g., apple or apple.com), optional if --cidr is provided")
    parser.add_argument("--api-token", help="ipinfo.io API token (overrides config)")

    # Port range group (mutually exclusive)
    port_range_group = parser.add_mutually_exclusive_group()
    port_range_group.add_argument("--ports", help="Comma-separated ports to scan (e.g., 80,443)")
    port_range_group.add_argument("--first-1000", action="store_true", help="Scan the first 1000 ports (0-999)")
    port_range_group.add_argument("--first-300", action="store_true", help="Scan the first 300 ports (0-299)")

    # Per-CIDR IP limit group (mutually exclusive)
    cidr_limit_group = parser.add_mutually_exclusive_group()
    cidr_limit_group.add_argument("--max-ips-per-cidr", type=int, help="Maximum number of IPs to scan per CIDR range")
    cidr_limit_group.add_argument("--first-1-per-cidr", action="store_true", help="Scan only the first IP per CIDR range")
    cidr_limit_group.add_argument("--first-2-per-cidr", action="store_true", help="Scan only the first 2 IPs per CIDR range")
    cidr_limit_group.add_argument("--first-10-per-cidr", action="store_true", help="Scan only the first 10 IPs per CIDR range")

    parser.add_argument("--timeout", type=float, help="Timeout for host/port scans in seconds (default: 1.0 from config)")
    parser.add_argument("--max-ips", type=int, help="Maximum total number of IPs to scan (global limit)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output with detailed logs")
    parser.add_argument("--output", help="File to save results (e.g., results.json)")
    parser.add_argument("--output-format", choices=["json", "csv"], help="Output format (json, csv)")
    parser.add_argument("--config", help="Path to config file (default: ~/.astra/config.json)")
    parser.add_argument("--cidr", help="Comma-separated CIDR ranges to scan (e.g., 192.168.1.0/24), skips domain resolution; org is optional when used")
    args = parser.parse_args()

    # Validate that org is provided if --cidr is not used
    if not args.cidr and not args.org:
        parser.error("the following arguments are required: org (unless --cidr is provided)")
    
    # If org is not provided, use a placeholder for logging purposes
    if not args.org:
        args.org = "CIDR-only scan"

    # Determine max_ips_per_cidr based on flags
    if args.first_1_per_cidr:
        args.max_ips_per_cidr = 1
    elif args.first_2_per_cidr:
        args.max_ips_per_cidr = 2
    elif args.first_10_per_cidr:
        args.max_ips_per_cidr = 10

    return args

def display_banner():
    """Display the ASCII art banner for Astra."""
    banner = """
###########################################
# █████╗ ███████╗████████╗██████╗  █████╗ #
#██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗#
#███████║███████╗   ██║   ██████╔╝███████║#
#██╔══██║╚════██║   ██║   ██╔══██╗██╔══██║#
#██║  ██║███████║   ██║   ██║  ██║██║  ██║#
#╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝#
#     A S T R A   S C A N N E R     v1.1  #
###########################################
    """
    print(banner)

def main():
    """Main entry point for Astra CLI."""
     # Display the banner
    display_banner()

    args = parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Load configuration
    config = load_config(args.config)
    api_token = args.api_token or config.get("api_token")
    default_ports = config.get("default_ports", "22,80,443,8080,8443")
    default_timeout = config.get("default_timeout", 1.0)

    # Determine ports to scan
    if args.first_1000:
        ports = list(range(1000))  # Ports 0-999
    elif args.first_300:
        ports = list(range(300))   # Ports 0-299
    elif args.ports:
        ports = [int(p) for p in args.ports.split(",")]
    else:
        ports = list(range(65536))  # All ports 0-65535

    # Parse timeout and max_ips
    timeout = args.timeout if args.timeout is not None else default_timeout
    max_ips = args.max_ips
    max_ips_per_cidr = args.max_ips_per_cidr

    # Get CIDR ranges
    logging.info(f"Starting scan for {args.org}")
    cidr_ranges = get_cidr_ranges(args.org, api_token, args.cidr)
    if not cidr_ranges:
        logging.error("No CIDR ranges found. Exiting.")
        sys.exit(1)

    # Extract IPs from CIDR ranges
    all_ips = extract_ips(cidr_ranges, max_ips, max_ips_per_cidr)
    if not all_ips:
        logging.error("No IPs extracted. Exiting.")
        sys.exit(1)
    logging.info(f"Extracted {len(all_ips)} IPs")

    # Scan the network
    live_hosts, open_ports = scan_network(all_ips, ports, timeout)

    # Save results
    output_format = args.output_format or "json"
    if args.output:
        save_results(args.org, cidr_ranges, live_hosts, open_ports, args.output, output_format)
    else:
        logging.info(f"Found {len(live_hosts)} live hosts")
        for host in live_hosts:
            logging.info(f"  - {host}")
        logging.info(f"Found {len(open_ports)} open ports")
        for ip, port in open_ports:
            logging.info(f"  - {ip}:{port}")

if __name__ == "__main__":
    main()
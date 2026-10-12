import dns.resolver
import socket
import logging
from typing import List
from ipaddress import ip_network

def get_cidr_ranges_local(org: str) -> List[str]:
    """Resolve domain to IPs locally using dns.resolver."""
    logging.debug(f"Resolving domain for {org} locally")
    try:
        domain = org if '.' in org else f"{org}.com"
        # Use dns.resolver to get all A records
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(domain, 'A')
        ips = list(set([answer.to_text() for answer in answers]))
        logging.info(f"Resolved {len(ips)} IPs for {domain}: {ips}")
        if not ips:
            logging.error(f"No IPs resolved for {domain}")
            return []
        return [f"{ip}/32" for ip in ips]
    except dns.resolver.NXDOMAIN:
        logging.error(f"Domain {domain} does not exist")
        return []
    except dns.resolver.NoAnswer:
        logging.error(f"No A records found for {domain}")
        return []
    except dns.resolver.LifetimeTimeout:
        logging.error(f"DNS query for {domain} timed out")
        return []
    except Exception as e:
        logging.error(f"Unexpected error while resolving {domain}: {e}")
        return []

def get_cidr_ranges(org: str, api_token: str = None, cidr: str = None) -> List[str]:
    """Resolve CIDR ranges or IPs for the given organization."""
    logging.debug(f"Processing CIDR ranges for {org}")

    # If the user provided a CIDR range, use it directly
    if cidr:
        try:
            # Validate and expand the CIDR range
            network = ip_network(cidr, strict=False)
            logging.info(f"Using user-provided CIDR: {cidr} (total IPs: {network.num_addresses})")
            return [str(network)]
        except ValueError as e:
            logging.error(f"Invalid CIDR range {cidr}: {e}")
            return []

    # Otherwise, resolve the domain to IPs
    return get_cidr_ranges_local(org)
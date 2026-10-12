import argparse
import sys
from scanner import Scanner
from configs.settings import TARGET_URL, TIMEOUT
from utils.utils import log_scan_results, setup_logging
from reports.report_generator import generate_report

def main():
    parser = argparse.ArgumentParser(description='XSS Finder - Automated XSS Vulnerability Scanner')
    parser.add_argument('-u', '--url', type=str, help='Target URL to scan')
    parser.add_argument('-c', '--category', type=str, choices=['basic', 'encoded', 'event_handlers', 'dom_based', 'filter_bypass', 'all'], 
                        default='all', help='Payload category to test (default: all)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-r', '--report', type=str, help='Generate report to specified file')
    parser.add_argument('-t', '--timeout', type=int, default=TIMEOUT, help=f'Request timeout in seconds (default: {TIMEOUT})')
    
    args = parser.parse_args()
    
    # Determine target URL
    target_url = args.url or TARGET_URL
    
    if not target_url:
        print("Error: No URL provided. Use -u/--url to specify a target URL.")
        sys.exit(1)
    
    # Add scheme if missing
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    
    # Setup logging
    setup_logging()
    
    # Determine category
    category = None if args.category == 'all' else args.category
    
    print(f"\n{'='*60}")
    print(f"XSS Finder - Automated XSS Vulnerability Scanner")
    print(f"{'='*60}")
    print(f"Target URL: {target_url}")
    print(f"Category: {args.category}")
    print(f"Timeout: {args.timeout}s")
    print(f"{'='*60}\n")
    
    # Run scan
    scanner = Scanner(target_url, category=category)
    scan_results = scanner.run_scan(verbose=args.verbose)
    
    # Log results
    log_scan_results(scan_results)
    print(f"\nScan completed. Results saved in logs/scan.log")
    
    # Generate report if requested
    if args.report:
        generate_report({
            'target_url': target_url,
            'category': args.category,
            'timeout': args.timeout,
            'vulnerabilities': scan_results
        }, args.report)
    else:
        # Generate default report
        generate_report({
            'target_url': target_url,
            'category': args.category,
            'timeout': args.timeout,
            'vulnerabilities': scan_results
        })
    
    # Print summary
    vulnerable_count = len([r for r in scan_results if r['vulnerable']])
    total_count = len(scan_results)
    print(f"\n{'='*60}")
    print(f"SUMMARY: Found {vulnerable_count} vulnerabilities out of {total_count} tests")
    if vulnerable_count > 0:
        print(f"⚠️  WARNING: Vulnerabilities detected!")
        print(f"Check the report for details.")
    else:
        print(f"✓ No vulnerabilities detected with current payloads.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

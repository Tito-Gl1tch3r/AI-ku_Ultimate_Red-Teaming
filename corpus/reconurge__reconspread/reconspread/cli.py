import argparse
import sys
import os

# Add parent directory to path when run as script
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from reconspread import Crawler

def cli():
    parser = argparse.ArgumentParser(description="List all links found on a website, recursive or not.")
    parser.add_argument("url", help="URL of the website to analyze")
    parser.add_argument("--max-pages", "-mp", type=int, default=50, help="Maximum number of pages to crawl (default: 50)")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="Delay between requests in seconds (default: 1.0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print every page being searched")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification (default: SSL verification enabled)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Follow every internal link (default: only crawl the final page after redirects)")
    parser.add_argument("--all-domains", action="store_true", help="Extract URLs from all domains, not just same domain (default: same domain only)")
    parser.add_argument("-o", "--output", type=str, help="Output filename to save results as JSON")
    args = parser.parse_args()

    # Create crawler instance
    crawler = Crawler(
        url=args.url,
        max_pages=args.max_pages,
        timeout=args.timeout,
        delay=args.delay,
        verbose=args.verbose,
        recursive=args.recursive,
        verify_ssl=not args.no_verify_ssl,  # Default to True unless --no-verify-ssl is passed
        same_domain_only=not args.all_domains # Default to True unless --all-domains is passed
    )
    
    try:
        print(f"Fetching content from: {args.url}")
        crawler.fetch()
        print(f"Final URL after redirects: {crawler.final_url}")
        print("Extracting urls...")
        crawler.extract_urls()
        
        results = crawler.get_results()
        if results:
            print("\nFound internal items:")
            for item in results.internal: 
                print(f"\n-> {item.url}")
            print("\nFound external items:")
            for item in results.external: 
                print(f"\n-> {item.url}")
            print(f"\nSummary: {len(results.internal + results.external)} urls found across {len(crawler.visited_urls)} pages")
        else:
            print("\nNo url found.")
            
        # Save to file if output option is specified
        if args.output:
            crawler.save_to_file(args.output)
            print(f"\nResults saved to: {args.output}")
            
    except RuntimeError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    cli()

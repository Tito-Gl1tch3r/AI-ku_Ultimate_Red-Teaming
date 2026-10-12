#!/usr/bin/env python3
"""
Subdomain Enumerator Tool
Author: Your Name
Description: Comprehensive subdomain enumeration using multiple sources and bruteforce
"""

import argparse
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Import custom modules
from sources.passive_enum import PassiveEnumerator
from sources.bruteforce_enum import BruteforceEnumerator
from utils.domain_validator import DomainValidator
from utils.http_checker import HTTPChecker
from utils.file_handler import FileHandler
from utils.logger import Logger, Colors
from utils.tech_analyzer import TechAnalyzer

class SubdomainEnumerator:
    def __init__(self, domain, output_dir="results", threads=50, timeout=10, no_browser=False, debug_browser=False):
        self.domain = domain
        self.output_dir = output_dir
        self.threads = threads
        self.timeout = timeout
        self.subdomains = set()
        self.live_subdomains = set()
        self.no_browser = no_browser
        self.debug_browser = debug_browser
        
        # Initialize components
        self.logger = Logger()
        self.validator = DomainValidator()
        self.passive_enum = PassiveEnumerator(domain, timeout)
        self.bruteforce_enum = BruteforceEnumerator(domain, timeout)
        self.http_checker = HTTPChecker(timeout, threads)
        self.file_handler = FileHandler(output_dir, domain)
        self.tech_analyzer = TechAnalyzer()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def run_passive_enumeration(self):
        """Run passive enumeration from multiple sources"""
        self.logger.info(f"Starting passive enumeration for {self.domain}")
        
        passive_subdomains = self.passive_enum.enumerate_all()
        self.subdomains.update(passive_subdomains)
        
        self.logger.success(f"Passive enumeration found {len(passive_subdomains)} subdomains")
        return passive_subdomains
    
    def run_bruteforce_enumeration(self, wordlist_path=None):
        """Run bruteforce enumeration using wordlists"""
        self.logger.info(f"Starting bruteforce enumeration for {self.domain}")
        
        bruteforce_subdomains = self.bruteforce_enum.enumerate(wordlist_path)
        self.subdomains.update(bruteforce_subdomains)
        
        self.logger.success(f"Bruteforce enumeration found {len(bruteforce_subdomains)} subdomains")
        return bruteforce_subdomains
    
    def check_live_subdomains(self):
        """Check which subdomains are live and responding to HTTP/HTTPS"""
        self.logger.info(f"Checking {len(self.subdomains)} subdomains for HTTP/HTTPS response")
        
        live_results = self.http_checker.check_multiple(list(self.subdomains))
        self.live_subdomains = set(live_results.keys())
        
        self.logger.success(f"Found {len(self.live_subdomains)} live subdomains")
        return live_results
    
    def _open_html_report(self, html_file_path):
        """Auto-open HTML report in default browser with enhanced Kali Linux support"""
        import os
        import webbrowser
        import subprocess
        from urllib.parse import urljoin
        from pathlib import Path
        
        self.logger.info(f"🔍 Debug: _open_html_report called with: {html_file_path}")
        
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(html_file_path)
            self.logger.info(f"🔍 Debug: Absolute path: {abs_path}")
            
            # Check if file actually exists
            if not os.path.exists(abs_path):
                self.logger.error(f"❌ HTML file does not exist: {abs_path}")
                return
            
            # Create file:// URL for local file
            file_url = Path(abs_path).as_uri()
            self.logger.info(f"🔍 Debug: File URL: {file_url}")
            
            # Display clickable link information
            self.logger.header("HTML Report Generated")
            print(f"🌐 {Colors.CYAN}{Colors.BOLD}HTML Report URL:{Colors.END}")
            print(f"   {Colors.BLUE}{Colors.UNDERLINE}{file_url}{Colors.END}")
            print(f"\n📁 {Colors.CYAN}Local Path:{Colors.END}")
            print(f"   {Colors.WHITE}{abs_path}{Colors.END}")
            
            # Try to open in default browser
            self.logger.info("🚀 Attempting to open HTML report...")
            
            opened = False
            
            # Method 1: Try xdg-open (most common on Linux)
            if not opened and os.name == 'posix':
                self.logger.info("🔍 Debug: Trying xdg-open method...")
                try:
                    # Check if xdg-open exists
                    result = subprocess.run(['which', 'xdg-open'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.logger.info(f"🔍 Debug: xdg-open found at: {result.stdout.strip()}")
                        # Use xdg-open with proper error handling
                        result = subprocess.run(['xdg-open', abs_path], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            self.logger.success("✅ Report opened with xdg-open")
                            opened = True
                        else:
                            self.logger.warning(f"⚠️ xdg-open failed: {result.stderr}")
                    else:
                        self.logger.info("🔍 Debug: xdg-open not found")
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                    self.logger.warning(f"⚠️ xdg-open method failed: {e}")
            
            # Method 2: Try Firefox directly (common on Kali)
            if not opened:
                self.logger.info("🔍 Debug: Trying Firefox method...")
                firefox_paths = [
                    '/usr/bin/firefox',
                    '/usr/bin/firefox-esr',
                    'firefox',
                    'firefox-esr'
                ]
                
                for firefox_path in firefox_paths:
                    try:
                        self.logger.info(f"🔍 Debug: Checking Firefox path: {firefox_path}")
                        # Check if Firefox exists
                        if firefox_path.startswith('/'):
                            if os.path.exists(firefox_path):
                                self.logger.info(f"🔍 Debug: Firefox found at: {firefox_path}")
                                proc = subprocess.Popen([firefox_path, abs_path], 
                                               stdout=subprocess.DEVNULL, 
                                               stderr=subprocess.DEVNULL)
                                self.logger.success(f"✅ Report opened with Firefox ({firefox_path})")
                                opened = True
                                break
                        else:
                            # Try to find Firefox in PATH
                            result = subprocess.run(['which', firefox_path], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                self.logger.info(f"🔍 Debug: Firefox found in PATH: {result.stdout.strip()}")
                                proc = subprocess.Popen([firefox_path, abs_path],
                                               stdout=subprocess.DEVNULL, 
                                               stderr=subprocess.DEVNULL)
                                self.logger.success(f"✅ Report opened with Firefox ({firefox_path})")
                                opened = True
                                break
                    except Exception as e:
                        self.logger.warning(f"⚠️ Firefox method {firefox_path} failed: {e}")
                        continue
            
            # Method 3: Try Chromium (also common on Kali)
            if not opened:
                self.logger.info("🔍 Debug: Trying Chromium method...")
                chromium_paths = [
                    '/usr/bin/chromium',
                    '/usr/bin/chromium-browser',
                    'chromium',
                    'chromium-browser',
                    'google-chrome'
                ]
                
                for chromium_path in chromium_paths:
                    try:
                        self.logger.info(f"🔍 Debug: Checking Chromium path: {chromium_path}")
                        if chromium_path.startswith('/'):
                            if os.path.exists(chromium_path):
                                self.logger.info(f"🔍 Debug: Chromium found at: {chromium_path}")
                                proc = subprocess.Popen([chromium_path, abs_path],
                                               stdout=subprocess.DEVNULL, 
                                               stderr=subprocess.DEVNULL)
                                self.logger.success(f"✅ Report opened with Chromium ({chromium_path})")
                                opened = True
                                break
                        else:
                            result = subprocess.run(['which', chromium_path], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                self.logger.info(f"🔍 Debug: Chromium found in PATH: {result.stdout.strip()}")
                                proc = subprocess.Popen([chromium_path, abs_path],
                                               stdout=subprocess.DEVNULL, 
                                               stderr=subprocess.DEVNULL)
                                self.logger.success(f"✅ Report opened with Chromium ({chromium_path})")
                                opened = True
                                break
                    except Exception as e:
                        self.logger.warning(f"⚠️ Chromium method {chromium_path} failed: {e}")
                        continue
            
            # Method 4: Python webbrowser fallback
            if not opened:
                self.logger.info("🔍 Debug: Trying Python webbrowser method...")
                try:
                    webbrowser.open(file_url)
                    self.logger.success("✅ Report opened using Python webbrowser")
                    opened = True
                except Exception as e:
                    self.logger.warning(f"⚠️ Python webbrowser failed: {e}")
            
            # Show manual instructions
            if opened:
                print(f"\n{Colors.GREEN}🎉 HTML Report opened successfully!{Colors.END}")
            else:
                self.logger.warning("⚠️  Could not auto-open browser")
                print(f"\n{Colors.YELLOW}📋 Manual Instructions:{Colors.END}")
                print(f"   1. Copy this URL: {Colors.BLUE}{file_url}{Colors.END}")
                print(f"   2. Paste it in your browser address bar")
                print(f"   3. Or run: {Colors.CYAN}firefox \"{abs_path}\"{Colors.END}")
                print(f"   4. Or run: {Colors.CYAN}chromium \"{abs_path}\"{Colors.END}")
            
            print(f"\n{Colors.CYAN}💡 Pro Tips:{Colors.END}")
            print(f"   • File ready for sharing and analysis")
            print(f"   • Click subdomain names in report to visit them")
            print(f"   • Report auto-refreshes if you re-run the scan")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling HTML report: {str(e)}")
            self.logger.info(f"Please manually open: {html_file_path}")
            print(f"\n{Colors.YELLOW}Manual commands:{Colors.END}")
            print(f"   firefox \"{html_file_path}\"")
            print(f"   chromium \"{html_file_path}\"")
            print(f"   xdg-open \"{html_file_path}\"")
    
    def save_results(self, live_results):
        """Save all results to files including technology analysis"""
        self.logger.info("Saving results to files")
        
        # Save all subdomains
        all_subdomains_file = self.file_handler.save_subdomains(
            list(self.subdomains), 
            "all_subdomains.txt"
        )
        
        # Save live subdomains with HTTP info
        live_file = self.file_handler.save_live_subdomains(
            live_results, 
            "live_http_web.txt"
        )
        
        # Save CSV results
        csv_file = self.file_handler.save_csv_results(
            live_results,
            "results.csv"
        )
        
        # Save detailed JSON results
        json_file = self.file_handler.save_detailed_results(
            live_results,
            "detailed_results.json"
        )
        
        # Technology analysis
        if live_results:
            try:
                self.logger.info("Performing technology analysis...")
                tech_analysis = self.tech_analyzer.analyze_technologies(live_results)
                
                # Save technology analysis report
                tech_report_file = self.file_handler.get_file_path("technology_analysis.txt")
                tech_report = self.tech_analyzer.generate_report(tech_analysis, tech_report_file)
                
                # Print technology summary to console
                self.logger.subheader("Technology Analysis Summary")
                
                # Show high-value targets
                high_value = tech_analysis.get('high_value_targets', [])
                if high_value:
                    self.logger.info("🎯 High-Value Targets Found:")
                    for i, target in enumerate(high_value[:3], 1):
                        reasons = ', '.join(target.get('reasons', [])[:2])
                        self.logger.info(f"  {i}. {target.get('subdomain', 'Unknown')} (Score: {target.get('score', 0)}) - {reasons}")
                
                # Show vulnerability summary
                vuln_assessment = tech_analysis.get('vulnerability_assessment', {})
                vuln_summary = vuln_assessment.get('risk_summary', {})
                if any(vuln_summary.values()):
                    risk_info = []
                    for risk, count in vuln_summary.items():
                        if count > 0:
                            risk_info.append(f"{risk}: {count}")
                    
                    if risk_info:
                        self.logger.warning(f"🚨 Potential Issues Found - {', '.join(risk_info)}")
                
                # Show technology summary
                tech_summary = tech_analysis.get('technology_summary', {})
                common_techs = tech_summary.get('most_common_technologies', [])[:5]
                if common_techs:
                    tech_list = [f"{tech}({count})" for tech, count in common_techs]
                    self.logger.info(f"💻 Common Technologies: {', '.join(tech_list)}")
                    
            except Exception as e:
                self.logger.error(f"Error during technology analysis: {str(e)}")
                tech_report_file = None
        
        # Save summary report
        try:
            summary_file = self.file_handler.save_summary({
                'domain': self.domain,
                'total_subdomains': len(self.subdomains),
                'live_subdomains': len(self.live_subdomains),
                'timestamp': datetime.now().isoformat(),
                'files': {
                    'all_subdomains': all_subdomains_file,
                    'live_subdomains': live_file,
                    'csv_results': csv_file,
                    'json_results': json_file,
                    'tech_analysis': tech_report_file if 'tech_report_file' in locals() and tech_report_file else None
                }
            })
        except Exception as e:
            self.logger.error(f"Error saving summary: {str(e)}")
            summary_file = None
        
        # Create HTML report
        try:
            html_file = self.file_handler.create_html_report(
                live_results,
                list(self.subdomains),
                "report.html"
            )
            self.logger.info(f"🔍 Debug: HTML file creation result: {html_file}")
        except Exception as e:
            self.logger.error(f"Error creating HTML report: {str(e)}")
            html_file = None
        
        self.logger.success(f"Results saved:")
        self.logger.info(f"  📄 All subdomains: {all_subdomains_file or 'Failed to save'}")
        self.logger.info(f"  🌐 Live subdomains: {live_file or 'Failed to save'}")
        self.logger.info(f"  📊 CSV results: {csv_file or 'Failed to save'}")
        if json_file:
            self.logger.info(f"  📋 JSON results: {json_file}")
        if 'tech_report_file' in locals() and tech_report_file:
            self.logger.info(f"  🔍 Technology analysis: {tech_report_file}")
        else:
            self.logger.info(f"  🔍 Technology analysis: Failed to generate")
        if html_file:
            self.logger.info(f"  📱 HTML report: {html_file}")
        else:
            self.logger.info(f"  📱 HTML report: Failed to generate")
        if summary_file:
            self.logger.info(f"  📝 Summary: {summary_file}")
        else:
            self.logger.info(f"  📝 Summary: Failed to generate")
        
        # Debug HTML file existence
        self.logger.info(f"🔍 Debug: About to check HTML auto-open...")
        self.logger.info(f"🔍 Debug: html_file = {html_file}")
        self.logger.info(f"🔍 Debug: self.no_browser = {self.no_browser}")
        
        # Auto-open HTML report if created successfully and not disabled
        if html_file and not self.no_browser:
            self.logger.info("🔍 Debug: HTML file exists, attempting to open...")
            self.logger.info(f"🔍 Debug: HTML file path: {html_file}")
            self.logger.info(f"🔍 Debug: no_browser flag: {self.no_browser}")
            self._open_html_report(html_file)
        elif html_file and self.no_browser:
            self.logger.info(f"📱 HTML report generated: {html_file}")
            self.logger.info("💡 Auto-open disabled with --no-browser flag")
        elif not html_file:
            self.logger.warning("⚠️ HTML file was not created successfully")
        else:
            self.logger.warning("⚠️ Unknown condition preventing HTML report opening")
    
    def run_full_enumeration(self, wordlist_path=None, skip_passive=False, skip_bruteforce=False):
        """Run complete subdomain enumeration process"""
        start_time = time.time()
        
        self.logger.info(f"Starting subdomain enumeration for: {self.domain}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Threads: {self.threads}")
        
        # Validate domain
        if not self.validator.is_valid_domain(self.domain):
            self.logger.error(f"Invalid domain: {self.domain}")
            return False
        
        try:
            # Passive enumeration
            if not skip_passive:
                self.run_passive_enumeration()
            
            # Bruteforce enumeration
            if not skip_bruteforce:
                self.run_bruteforce_enumeration(wordlist_path)
            
            # Remove duplicates and invalid subdomains
            valid_subdomains = set()
            for subdomain in self.subdomains:
                if self.validator.is_valid_subdomain(subdomain):
                    valid_subdomains.add(subdomain)
            
            self.subdomains = valid_subdomains
            self.logger.info(f"Total unique valid subdomains: {len(self.subdomains)}")
            
            # Check live subdomains
            live_results = self.check_live_subdomains()
            
            # Save results
            self.save_results(live_results)
            
            # Print summary
            elapsed_time = time.time() - start_time
            self.logger.success(f"Enumeration completed in {elapsed_time:.2f} seconds")
            self.logger.info(f"Total subdomains found: {len(self.subdomains)}")
            self.logger.info(f"Live subdomains: {len(self.live_subdomains)}")
            
            self.logger.info(f"🔍 Debug: End of enumeration, about to return...")
            
            return True
            
        except KeyboardInterrupt:
            self.logger.warning("Enumeration interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Error during enumeration: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Subdomain Enumerator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py -d example.com
  python3 main.py -d example.com -w /path/to/wordlist.txt -t 100
  python3 main.py -d example.com -o results --skip-passive
        """
    )
    
    parser.add_argument('-d', '--domain', required=True, 
                       help='Target domain to enumerate')
    parser.add_argument('-w', '--wordlist', 
                       help='Custom wordlist path (default: uses SecLists)')
    parser.add_argument('-o', '--output', default='results',
                       help='Output directory (default: results)')
    parser.add_argument('-t', '--threads', type=int, default=50,
                       help='Number of threads (default: 50)')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Request timeout in seconds (default: 10)')
    parser.add_argument('--skip-passive', action='store_true',
                       help='Skip passive enumeration')
    parser.add_argument('--skip-bruteforce', action='store_true',
                       help='Skip bruteforce enumeration')
    parser.add_argument('--no-browser', action='store_true',
                       help='Skip auto-opening HTML report in browser')
    parser.add_argument('--debug-browser', action='store_true',
                       help='Show debug info for browser opening')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.skip_passive and args.skip_bruteforce:
        print("Error: Cannot skip both passive and bruteforce enumeration")
        sys.exit(1)
    
    # Initialize enumerator
    enumerator = SubdomainEnumerator(
        domain=args.domain,
        output_dir=args.output,
        threads=args.threads,
        timeout=args.timeout,
        no_browser=args.no_browser,
        debug_browser=args.debug_browser
    )
    
    # Set verbose mode
    if args.verbose:
        enumerator.logger.set_verbose(True)
    
    # Run enumeration
    success = enumerator.run_full_enumeration(
        wordlist_path=args.wordlist,
        skip_passive=args.skip_passive,
        skip_bruteforce=args.skip_bruteforce
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
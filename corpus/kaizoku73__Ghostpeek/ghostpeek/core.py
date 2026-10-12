#!/usr/bin/env python3
"""
GhostPeek - Domain Reconnaissance Tool
Author: kaizoku73
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "kaizoku73"

import requests
import dns.resolver
import json
import whois
import socket
from concurrent.futures import ThreadPoolExecutor
import argparse
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from selenium import webdriver


try:
    from Wappalyzer import Wappalyzer, WebPage
    WAPPALYZER_AVAILABLE = True
except ImportError:
    WAPPALYZER_AVAILABLE = False


console = Console()

###### Class to store the results
class ReconResults:
    def __init__(self, domain):
        self.domain = domain
        self.whois_info = {}
        self.subdomains = []
        self.ip_info = {}  # Domain -> IP
        self.asn_info = {}  # IP -> ASN info
        self.dns_records = {}  # Domain -> record type -> values
        self.technologies = {}  # Domain -> [technologies]
        self.screenshots = {}  # Domain -> screenshot path
        self.errors = []  # List of errors encountered

###### Create output directory to store the result
def create_output_directory(domain):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"recon_{domain}_{timestamp}"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    return output_dir

###### normalize the domain by removing extra things like path or https://
def normalize_domain(domain):
    if "://" in domain:
        parsed = urlparse(domain)
        domain = parsed.netloc
    return domain.lower()

def iplook(domain, output_dir, results):
    try:
        ip = socket.gethostbyname(domain)
        results.ip_info[domain] = ip
        console.print(f"[green]✓[/green] {domain} resolves to {ip}")
        
        asn_info = aslook(ip, output_dir, results)
        dnsrec(domain, output_dir, results)
        wapp(domain, output_dir, results)
        seli(domain, output_dir, results)
        return ip
    except socket.gaierror:
        console.print(f"[yellow]![/yellow] Could not resolve {domain}")
        results.ip_info[domain] = "Could not resolve"
        return None


def dnsrec(domain, output_dir, results):
    console.print(f"[bold]Decoding DNS secrets for {domain}...[/bold]")
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]
    
    if domain not in results.dns_records:
        results.dns_records[domain] = {}
    
    
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3.0       # Reduce timeout from default (usually 5s) to fail faster
    resolver.lifetime = 10.0     # Overall timeout for the resolution process
    resolver.retry_servfail = True
    resolver.nameservers = [
        '8.8.8.8',   
        '1.1.1.1',   
        '9.9.9.9'    
    ]  
    
    for record in record_types:
        
        for attempt in range(2):
            try:
                answers = resolver.resolve(domain, record)
                results.dns_records[domain][record] = []
                
                for answer in answers:
                    answer_text = answer.to_text()
                    console.print(f"[cyan]{record}[/cyan]: {answer_text}")
                    results.dns_records[domain][record].append(answer_text)
                
                break
                
            except dns.resolver.Timeout:
                if attempt == 0:
                    console.print(f"[yellow]Timeout resolving {record} record for {domain}, retrying...[/yellow]")
                else:
                    console.print(f"[yellow]Timeout resolving {record} record for {domain} after retry[/yellow]")
                    
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers) as e:
                # These are "normal" DNS errors, not timeout issues
                # console.print(f"[yellow]No {record} records for {domain}: {str(e)}[/yellow]")
                break  
                
            except Exception as e:
                console.print(f"[yellow]Error resolving {record} records for {domain}: {str(e)}[/yellow]")
                results.errors.append(f"DNS lookup error for {domain} {record}: {str(e)}")
                break  

def aslook(ip, output_dir, results):
    if ip in results.asn_info:
        return results.asn_info[ip]
        
    console.print(f"[bold]Tracing ASN network for {ip}...[/bold]")
    try:
        url = f"https://api.bgpview.io/ip/{ip}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            console.print(f"[yellow]Error fetching ASN data: HTTP {response.status_code}[/yellow]")
            return {}
            
        data = response.json()
        
        if not data.get('status') == 'ok':
            console.print("[yellow]BGP View API returned an error[/yellow]")
            return {}
            
        prefixes = data['data'].get('prefixes', [])
        asn_info = prefixes[0].get('asn', {}) if prefixes else {}

        asn = asn_info.get('asn', 'N/A')
        name = asn_info.get('name', 'N/A')
        description = asn_info.get('description', 'N/A')
        country = asn_info.get('country_code', 'N/A')

        rir = data['data'].get('rir_allocation', {}).get('rir_name') or \
              data['data'].get('iana_assignment', {}).get('description', 'N/A')

        result = {
            "ip": ip,
            "asn": asn,
            "name": name, 
            "description": description,
            "rir": rir,
            "country": country
        }
        
        results.asn_info[ip] = result
        
        console.print(f"ASN         : [green]{asn}[/green]")
        console.print(f"Name        : [green]{name}[/green]")
        console.print(f"Description : [green]{description}[/green]")
        console.print(f"RIR         : [green]{rir}[/green]")
        console.print(f"Country     : [green]{country}[/green]")
        
        return result
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error in ASN lookup: {str(e)}[/red]")
        results.errors.append(f"ASN lookup error for {ip}: {str(e)}")
        return {}

def wapp(domain, output_dir, results):
    url = f"https://{domain}"
    
    try:
        console.print(f"[bold]Identifying technology fingerprints for {domain}...[/bold]")

        console.print(f"[yellow]Waiting 2 seconds to ensure page loads completely...[/yellow]")
        time.sleep(2)

        webpage = WebPage.new_from_url(url)
        wappalyzer = Wappalyzer.latest()
        technologies = wappalyzer.analyze(webpage)

        tech_list = []
        for tech in technologies:
            console.print(f"- [green]{tech}[/green]")
            tech_list.append(tech)
            
        results.technologies[domain] = tech_list
        return tech_list
    except Exception as e:
        console.print(f"[yellow]Error detecting technologies for {domain}: {str(e)}[/yellow]")
        results.errors.append(f"Technology detection error for {domain}: {str(e)}")
        return []

def seli(domain, output_dir, results, max_retries=1):
    screenshot_path = os.path.join(output_dir, f"screenshot_{domain}.png")
    
    for attempt in range(max_retries + 1):
        try:
            console.print(f"[yellow]Capturing visual evidence of {domain} (attempt {attempt+1}/{max_retries+1})...[/yellow]")
            
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
            options.add_argument('--disable-default-apps')
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)  # Increase timeout to 30 seconds
            
            url = f"https://{domain}"
            console.print(f"[yellow]Loading {url}...[/yellow]")
            
            try:
                driver.get(url)
            except Exception as page_load_error:
                console.print(f"[yellow]Page load issue: {str(page_load_error)}. Trying with http://...[/yellow]")
                try:
                    # Try with http if https fails
                    driver.get(f"http://{domain}")
                except Exception:
                    pass
            
            console.print(f"[yellow]Waiting for page to stabilize...[/yellow]") #Let the page laods
            time.sleep(3)
            
            # Get page dimensions
            try:
                # Get page height
                original_size = driver.execute_script("""
                    return {
                        width: Math.max(
                            document.body.scrollWidth,
                            document.documentElement.scrollWidth,
                            document.body.offsetWidth,
                            document.documentElement.offsetWidth,
                            document.body.clientWidth,
                            document.documentElement.clientWidth
                        ),
                        height: Math.max(
                            document.body.scrollHeight,
                            document.documentElement.scrollHeight,
                            document.body.offsetHeight,
                            document.documentElement.offsetHeight,
                            document.body.clientHeight,
                            document.documentElement.clientHeight
                        )
                    };
                """)
                
                console.print(f"[yellow]Setting viewport to capture full page: {original_size['width']}x{original_size['height']}[/yellow]")
                driver.set_window_size(original_size['width'], original_size['height'])
                
                console.print(f"[yellow]Scrolling through page...[/yellow]")
                total_height = original_size['height']
                viewport_height = driver.execute_script("return window.innerHeight")
                scroll_steps = max(int(total_height / viewport_height), 1)
                
                # Scroll from top to bottom in steps
                for i in range(scroll_steps + 1):
                    scroll_position = min(i * viewport_height, total_height)
                    driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                    time.sleep(0.3)  
                
                driver.execute_script("window.scrollTo(0, 0);") # back to top
                time.sleep(1)
                
            except Exception as scroll_error:
                console.print(f"[yellow]Error during scrolling: {str(scroll_error)}. Will try basic screenshot.[/yellow]")
            
            console.print(f"[yellow]Taking screenshot...[/yellow]")
            
            try:
                # Try to take full page screenshot if supported
                required_height = driver.execute_script("return document.body.parentNode.scrollHeight")
                driver.set_window_size(1920, required_height)
                time.sleep(0.5)  # Wait for resize
                driver.save_screenshot(screenshot_path)
            except Exception:
                # Fall back to viewport screenshot
                driver.save_screenshot(screenshot_path)

            driver.quit()
            
            # Check if screenshot was created and has content
            if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                console.print(f"[green]Screenshot saved to {screenshot_path}[/green]")
                results.screenshots[domain] = screenshot_path
                return screenshot_path
            else:
                raise Exception("Screenshot file is empty or not created")
                
        except Exception as e:
            if 'driver' in locals():
                try:
                    driver.quit()
                except:
                    pass
            
            if attempt < max_retries:
                console.print(f"[yellow]Selenium attempt {attempt+1} failed: {str(e)}. Retrying...[/yellow]")
                time.sleep(2)  # Wait before retry
            else:
                console.print(f"[red]All Selenium attempts failed: {str(e)}[/red]")
                results.errors.append(f"Selenium screenshot error for {domain}: {str(e)}")
                return None
    
    return None


def find_subdomains(domain, output_dir, results):
    console.print(Panel(f"[bold blue]Hunting for subdomains of {domain}[/bold blue]"))
    
    try:
        url = f"https://crt.sh/?q={domain}&output=json"
        response = requests.get(url=url, timeout=30)
        
        if response.status_code != 200:
            console.print(f"[red]Error: HTTP {response.status_code}[/red]")
            results.errors.append(f"Subdomain search error: HTTP {response.status_code}")
            return []
            
        try:
            data = response.json()
        except json.JSONDecodeError:
            console.print("[red]Error: Invalid JSON response from crt.sh[/red]")
            results.errors.append("Subdomain search error: Invalid JSON response")
            return []
            
        subdomains = set()
        
        for entry in data:
            if "name_value" in entry:
                
                for item in entry['name_value'].replace('\n', ',').split(','):
                    subdomain = item.strip().lower()
                    
                    subdomain = subdomain.replace("*.", "")
                    if subdomain.endswith(domain) and subdomain != domain:
                        subdomains.add(subdomain)
        
        
        subdomains.add(domain)
        
        
        subdomain_list = sorted(list(subdomains))
        results.subdomains = subdomain_list
        
        console.print(f"[green]Found {len(subdomain_list)} unique domain(s)[/green]")
        
        # Save subdomains to file
        with open(os.path.join(output_dir, "subdomains.txt"), "w") as f:
            for subdomain in subdomain_list:
                f.write(f"{subdomain}\n")
                
        # Display results
        for subdomain in subdomain_list:
            console.print(f"[cyan]→[/cyan] {subdomain}")
            
        return subdomain_list
            
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Connection error: {str(e)}[/red]")
        results.errors.append(f"Subdomain search error: {str(e)}")
        return []

def get_whois_info(domain, output_dir, results):
    console.print(Panel(f"[bold blue]Revealing WHOIS secrets for {domain}[/bold blue]"))
    try:
        w = whois.whois(domain)
        
        # Extract relevant WHOIS info
        whois_data = {}
        important_fields = [
            'domain_name', 'registrar', 'creation_date', 'expiration_date', 
            'updated_date', 'name_servers', 'status', 'emails', 'name',
            'org', 'address', 'city', 'state', 'zipcode', 'country'
        ]
        
        for field in important_fields:
            if hasattr(w, field) and getattr(w, field):
                value = getattr(w, field)
                # Convert lists to string
                if isinstance(value, list):
                    if field == 'creation_date' or field == 'expiration_date' or field == 'updated_date':
                        value = value[0]
                    else:
                        value = ', '.join(str(v) for v in value)
                whois_data[field] = value
        
        # Save raw WHOIS data
        with open(os.path.join(output_dir, "whois.txt"), "w") as f:
            f.write(str(w))
            
        # Store in results
        results.whois_info = whois_data
            
        # Display key WHOIS information
        console.print(f"Domain Name      : [green]{whois_data.get('domain_name', 'N/A')}[/green]")
        console.print(f"Registrar        : [green]{whois_data.get('registrar', 'N/A')}[/green]")
        console.print(f"Creation Date    : [green]{whois_data.get('creation_date', 'N/A')}[/green]")
        console.print(f"Expiration Date  : [green]{whois_data.get('expiration_date', 'N/A')}[/green]")
        
        return whois_data
    except Exception as e:
        console.print(f"[red]WHOIS lookup error: {str(e)}[/red]")
        results.errors.append(f"WHOIS lookup error: {str(e)}")
        return {}

def generate_report(results, output_dir):
    domain = results.domain
    report_path = os.path.join(output_dir, "report.html")
    
    # Create HTML report with all data
    with open(report_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Reconnaissance Report for {domain}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        h1, h2, h3 {{ 
            color: #2c3e50;
            margin-top: 30px;
        }}
        header h1 {{
            color: white;
            margin: 0;
        }}
        .section {{ 
            margin-bottom: 40px;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .data-table {{ 
            border-collapse: collapse; 
            width: 100%;
            margin-bottom: 20px;
        }}
        .data-table th, .data-table td {{ 
            border: 1px solid #ddd; 
            padding: 12px; 
            text-align: left; 
        }}
        .data-table th {{ 
            background-color: #2c3e50; 
            color: white;
        }}
        .data-table tr:nth-child(even) {{ 
            background-color: #f2f2f2; 
        }}
        .data-table tr:hover {{
            background-color: #e9e9e9;
        }}
        .screenshot {{ 
            max-width: 100%; 
            height: auto;
            border: 1px solid #ddd; 
            margin-top: 20px;
            border-radius: 5px;
        }}
        .summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-box {{
            flex: 1;
            min-width: 200px;
            padding: 20px;
            background-color: #f2f2f2;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-box h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .summary-box p {{
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
            color: #3498db;
        }}
        .tabs {{
            overflow: hidden;
            border: 1px solid #ccc;
            background-color: #f1f1f1;
            border-radius: 5px 5px 0 0;
        }}
        .tab-button {{
            background-color: inherit;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 16px;
            transition: 0.3s;
            font-size: 16px;
        }}
        .tab-button:hover {{
            background-color: #ddd;
        }}
        .tab-button.active {{
            background-color: #2c3e50;
            color: white;
        }}
        .tab-content {{
            display: none;
            padding: 20px;
            border: 1px solid #ccc;
            border-top: none;
            border-radius: 0 0 5px 5px;
            animation: fadeEffect 1s;
        }}
        @keyframes fadeEffect {{
            from {{opacity: 0;}}
            to {{opacity: 1;}}
        }}
        .tech-badge {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 5px 10px;
            margin: 3px;
            border-radius: 3px;
        }}
        .errors {{
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Reconnaissance Report for {domain}</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </header>
        
        <div class="summary">
            <div class="summary-box">
                <h3>Subdomains</h3>
                <p>{len(results.subdomains)}</p>
            </div>
            <div class="summary-box">
                <h3>IP Addresses</h3>
                <p>{len([ip for ip in results.ip_info.values() if ip != "Could not resolve"])}</p>
            </div>
            <div class="summary-box">
                <h3>Screenshots</h3>
                <p>{len(results.screenshots)}</p>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab-button active" onclick="openTab(event, 'overview')">Overview</button>
            <button class="tab-button" onclick="openTab(event, 'whois')">WHOIS</button>
            <button class="tab-button" onclick="openTab(event, 'subdomains')">Subdomains</button>
            <button class="tab-button" onclick="openTab(event, 'dns')">DNS Records</button>
            <button class="tab-button" onclick="openTab(event, 'technology')">Technologies</button>
            <button class="tab-button" onclick="openTab(event, 'screenshots')">Screenshots</button>
        </div>
        
        <div id="overview" class="tab-content" style="display: block;">
            <h2>Overview</h2>
            <p>This report contains reconnaissance information gathered about <strong>{domain}</strong> and its subdomains.</p>
            
            <table class="data-table">
                <tr>
                    <th>Domain</th>
                    <td>{domain}</td>
                </tr>
                <tr>
                    <th>IP Address</th>
                    <td>{results.ip_info.get(domain, 'Could not resolve')}</td>
                </tr>
                <tr>
                    <th>Registrar</th>
                    <td>{results.whois_info.get('registrar', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Creation Date</th>
                    <td>{results.whois_info.get('creation_date', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Expiration Date</th>
                    <td>{results.whois_info.get('expiration_date', 'N/A')}</td>
                </tr>
                <tr>
                    <th>ASN</th>
                    <td>{results.asn_info.get(results.ip_info.get(domain, ''), {}).get('asn', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Organization</th>
                    <td>{results.asn_info.get(results.ip_info.get(domain, ''), {}).get('name', 'N/A')}</td>
                </tr>
                <tr>
                    <th>Country</th>
                    <td>{results.asn_info.get(results.ip_info.get(domain, ''), {}).get('country', 'N/A')}</td>
                </tr>
            </table>
            
            <h3>Technologies</h3>
            <div>
                {' '.join(['<span class="tech-badge">' + tech + '</span>' for tech in results.technologies.get(domain, [])])}
            </div>
            
            <h3>Primary Screenshot</h3>
            <img src="screenshot_{domain}.png" class="screenshot" alt="Screenshot of {domain}" onerror="this.style.display='none';this.nextSibling.style.display='block';">
            <p style="display:none;">Screenshot not available.</p>
        </div>
        
        <div id="whois" class="tab-content">
            <h2>WHOIS Information</h2>
            <table class="data-table">
                <tr>
                    <th>Field</th>
                    <th>Value</th>
                </tr>
        """)
        
        # Add WHOIS information
        for field, value in results.whois_info.items():
            f.write(f"<tr><td>{field}</td><td>{value}</td></tr>\n")
        
        f.write("""        
            </table>
        </div>
        
        <div id="subdomains" class="tab-content">
            <h2>Subdomains</h2>
            <p>Discovered {len(results.subdomains)} subdomains for {domain}</p>
            <table class="data-table">
                <tr>
                    <th>Subdomain</th>
                    <th>IP Address</th>
                    <th>ASN</th>
                    <th>Organization</th>
                </tr>
        """)
        
        # Add subdomain information
        for subdomain in results.subdomains:
            ip = results.ip_info.get(subdomain, "Could not resolve")
            asn = results.asn_info.get(ip, {}).get('asn', 'N/A')
            org = results.asn_info.get(ip, {}).get('name', 'N/A')
            f.write(f"<tr><td><link><a href='https://{subdomain}' target='_blank'>{subdomain}</a></link></td><td>{ip}</td><td>{asn}</td><td>{org}</td></tr>\n")
        
        f.write("""
            </table>
        </div>
        
        <div id="dns" class="tab-content">
            <h2>DNS Records</h2>
        """)
        
        # Add DNS records for each domain
        for domain, records in results.dns_records.items():
            f.write(f"<h3>DNS Records for {domain}</h3>\n")
            f.write("""<table class="data-table">
                <tr>
                    <th>Record Type</th>
                    <th>Value</th>
                </tr>
            """)
            
            for record_type, values in records.items():
                for value in values:
                    f.write(f"<tr><td>{record_type}</td><td>{value}</td></tr>\n")
            
            f.write("</table>\n")
        
        f.write("""
        </div>
        
        <div id="technology" class="tab-content">
            <h2>Technologies</h2>
            <table class="data-table">
                <tr>
                    <th>Domain</th>
                    <th>Technologies</th>
                </tr>
        """)
        
        # Add technology information
        for domain, techs in results.technologies.items():
            tech_badges = ' '.join([f'<span class="tech-badge">{tech}</span>' for tech in techs])
            f.write(f"<tr><td>{domain}</td><td>{tech_badges}</td></tr>\n")
        
        f.write("""
            </table>
        </div>
        
        <div id="screenshots" class="tab-content">
            <h2>Screenshots</h2>
        """)
        
        # Add screenshots
        for domain, screenshot_path in results.screenshots.items():
            rel_path = os.path.basename(screenshot_path)
            f.write(f"""
            <div class="section">
                <h3><a href='https://{domain}' target='_blanked'>{domain}</a></h3>
                <img src="{rel_path}" class="screenshot" alt="Screenshot of {domain}" onerror="this.style.display='none';this.nextSibling.style.display='block';">
                <p style="display:none;">Screenshot not available.</p>
            </div>
            """)
        
        f.write("""
        </div>
        
        <script>
        function openTab(evt, tabName) {
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {
                tabcontent[i].style.display = "none";
            }
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {
                tabbuttons[i].className = tabbuttons[i].className.replace(" active", "");
            }
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.className += " active";
        }
        </script>
    </div>
</body>
</html>
        """)
    
    return report_path

def process_domain(domain, output_dir, results, with_threading=True):
    console.print(f"[bold cyan]Infiltrating {domain}...[/bold cyan]")
    ip = iplook(domain, output_dir, results)
    return ip

def main():
    
    parser = argparse.ArgumentParser(description="Domain Reconnaissance Tool")
    parser.add_argument("-d", "--domain", help="Target domain")
    parser.add_argument("-o", "--output", help="Output directory (optional)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads (default: 10)")
    parser.add_argument("--no-threading", action="store_true", help="Disable threading")
    args = parser.parse_args()
    
    ghost_peek_art = """
  ▄████  ██░ ██  ▒█████    ██████ ▄▄▄█████▓ ██▓███  ▓█████ ▓█████  ██ ▄█▀
 ██▒ ▀█▒▓██░ ██▒▒██▒  ██▒▒██    ▒ ▓  ██▒ ▓▒▓██░  ██▒▓█   ▀ ▓█   ▀  ██▄█▒ 
▒██░▄▄▄░▒██▀▀██░▒██░  ██▒░ ▓██▄   ▒ ▓██░ ▒░▓██░ ██▓▒▒███   ▒███   ▓███▄░ 
░▓█  ██▓░▓█ ░██ ▒██   ██░  ▒   ██▒░ ▓██▓ ░ ▒██▄█▓▒ ▒▒▓█  ▄ ▒▓█  ▄ ▓██ █▄ 
░▒▓███▀▒░▓█▒░██▓░ ████▓▒░▒██████▒▒  ▒██▒ ░ ▒██▒ ░  ░░▒████▒░▒████▒▒██▒ █▄
 ░▒   ▒  ▒ ░░▒░▒░ ▒░▒░▒░ ▒ ▒▓▒ ▒ ░  ▒ ░░   ▒▓▒░ ░  ░░░ ▒░ ░░░ ▒░ ░▒ ▒▒ ▓▒
  ░   ░  ▒ ░▒░ ░  ░ ▒ ▒░ ░ ░▒  ░ ░    ░    ░▒ ░      ░ ░  ░ ░ ░  ░░ ░▒ ▒░     [dim italic]made by kaizoku[/dim italic]
░ ░   ░  ░  ░░ ░░ ░ ░ ▒  ░  ░  ░    ░      ░░          ░      ░   ░ ░░ ░ 
      ░  ░  ░  ░    ░ ░        ░                      ░  ░   ░  ░░  ░   
"""
    
    console.print(Panel(ghost_peek_art, border_style="blue", padding=(1, 2)))
    # Get domain from args or user input
    domain = args.domain
    if not domain:
        domain = console.input("[bold yellow]Give your desire domain: [/bold yellow]")
    
    # Normalize domain (remove http://, www, etc.)
    domain = normalize_domain(domain)
    
    results = ReconResults(domain)
    
    if args.output:
        output_dir = args.output
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    else:
        output_dir = create_output_directory(domain)
    console.print(f"[bold]Your secrets will be stored in: [green]{output_dir}[/green][/bold]")
    
    get_whois_info(domain, output_dir, results)
    
    subdomains = find_subdomains(domain, output_dir, results)
    
    # Process all subdomains
    if subdomains:
        console.print(Panel(f"[bold blue]Unmasking {len(subdomains)} domains[/bold blue]"))
        
        if not args.no_threading and len(subdomains) > 1:
            # Use threading for multiple domains
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = []
                for subdomain in subdomains:
                    futures.append(executor.submit(process_domain, subdomain, output_dir, results, False))
                
                # Wait for all tasks to complete
                for future in futures:
                    future.result()
        else:
            
            for subdomain in subdomains:
                process_domain(subdomain, output_dir, results, False)
    
    # Generate HTML report
    report_path = generate_report(results, output_dir)
    console.print(f"\n[bold green]Mission accomplished![/bold green]")
    console.print(f"[bold]Your intelligence report awaits: [green]{report_path}[/green][/bold]")
    
    
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(report_path))
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Mission aborted by user[/bold red]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")
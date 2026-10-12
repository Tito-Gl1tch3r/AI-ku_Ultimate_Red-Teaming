#!/usr/bin/env python3
"""
File Handler Module
Handles file operations for saving results
"""

import os
import json
from datetime import datetime
import csv

class FileHandler:
    def __init__(self, output_dir, domain):
        self.output_dir = output_dir
        self.domain = domain
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create domain-specific directory
        self.domain_dir = os.path.join(output_dir, self.domain)
        os.makedirs(self.domain_dir, exist_ok=True)
    
    def get_file_path(self, filename):
        """Get full file path with timestamp"""
        base_name, ext = os.path.splitext(filename)
        timestamped_name = f"{base_name}_{self.timestamp}{ext}"
        return os.path.join(self.domain_dir, timestamped_name)
    
    def save_subdomains(self, subdomains, filename="subdomains.txt"):
        """Save list of subdomains to text file"""
        file_path = self.get_file_path(filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Subdomain enumeration results for {self.domain}\n")
                f.write(f"# Generated on: {datetime.now().isoformat()}\n")
                f.write(f"# Total subdomains: {len(subdomains)}\n\n")
                
                # Sort subdomains
                sorted_subdomains = sorted(subdomains)
                
                for subdomain in sorted_subdomains:
                    f.write(f"{subdomain}\n")
            
            return file_path
        except Exception as e:
            print(f"Error saving subdomains to {file_path}: {e}")
            return None
    
    def save_live_subdomains(self, live_results, filename="live_http_web.txt"):
        """Save live subdomains with comprehensive HTTP information"""
        file_path = self.get_file_path(filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Live subdomains for {self.domain}\n")
                f.write(f"# Generated on: {datetime.now().isoformat()}\n")
                f.write(f"# Total live subdomains: {len(live_results)}\n")
                f.write("# Format: SUBDOMAIN [PROTOCOL] STATUS TITLE | TECHNOLOGIES | CMS | SECURITY\n")
                f.write("="*80 + "\n\n")
                
                # Sort by subdomain name
                sorted_results = sorted(live_results.items())
                
                for subdomain, result in sorted_results:
                    protocols = result.get('protocols', {})
                    
                    for protocol, info in protocols.items():
                        status_code = info.get('status_code', 'N/A')
                        title = info.get('title', 'No Title') or 'No Title'  # Handle None values
                        server = info.get('server', 'Unknown') or 'Unknown'
                        
                        # Clean title for single line - handle None case
                        if title and isinstance(title, str):
                            clean_title = title.replace('\n', ' ').replace('\r', ' ')[:60]
                        else:
                            clean_title = 'No Title'
                        
                        # Technology information
                        technologies = info.get('technologies', []) or []
                        tech_str = ', '.join(technologies[:5]) if technologies else 'None detected'
                        
                        # CMS information
                        cms_info = info.get('cms_info', {}) or {}
                        cms_str = cms_info.get('CMS', 'Unknown') or 'Unknown'
                        if cms_info.get('Version'):
                            cms_str += f" v{cms_info['Version']}"
                        
                        # Security information
                        security_info = info.get('security_info', {}) or {}
                        security_features = []
                        if 'HSTS Enabled' in security_info:
                            security_features.append('HSTS')
                        if 'CSP Enabled' in security_info:
                            security_features.append('CSP')
                        if 'WAF' in security_info:
                            security_features.append('WAF')
                        
                        security_str = ', '.join(security_features) if security_features else 'Basic'
                        
                        # Main line
                        f.write(f"{subdomain} [{protocol.upper()}] {status_code} \"{clean_title}\" ({server})\n")
                        
                        # Technology details
                        if technologies:
                            f.write(f"  └─ Technologies: {tech_str}\n")
                        
                        # CMS details
                        if cms_info:
                            f.write(f"  └─ CMS: {cms_str}\n")
                            if cms_info.get('Admin Panel'):
                                f.write(f"  └─ Admin: {cms_info['Admin Panel']}\n")
                        
                        # Security details
                        if security_info:
                            f.write(f"  └─ Security: {security_str}\n")
                        
                        # Redirect info
                        if info.get('redirect'):
                            f.write(f"  └─ Redirects to: {info.get('url')}\n")
                        
                        f.write("\n")
                    
                    f.write("-" * 60 + "\n")
            
            return file_path
        except Exception as e:
            print(f"Error saving live subdomains to {file_path}: {e}")
            return None
    
    def save_detailed_results(self, live_results, filename="detailed_results.json"):
        """Save detailed results in JSON format"""
        file_path = self.get_file_path(filename)
        
        try:
            output_data = {
                'domain': self.domain,
                'timestamp': datetime.now().isoformat(),
                'total_live': len(live_results),
                'results': live_results
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            return file_path
        except Exception as e:
            print(f"Error saving detailed results to {file_path}: {e}")
            return None
    
    def save_csv_results(self, live_results, filename="results.csv"):
        """Save enhanced results in CSV format"""
        file_path = self.get_file_path(filename)
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'subdomain', 'protocol', 'status_code', 'title', 'server', 'url', 
                    'redirect', 'content_length', 'content_type', 'technologies', 
                    'cms', 'cms_version', 'admin_panel', 'security_features', 'waf_detected'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for subdomain, result in sorted(live_results.items()):
                    protocols = result.get('protocols', {})
                    
                    for protocol, info in protocols.items():
                        # Basic info
                        row = {
                            'subdomain': subdomain,
                            'protocol': protocol.upper(),
                            'status_code': info.get('status_code', ''),
                            'title': (info.get('title') or 'No Title').replace('\n', ' ').replace('\r', ' ') if info.get('title') else 'No Title',
                            'server': info.get('server', '') or '',
                            'url': info.get('url', '') or '',
                            'redirect': 'Yes' if info.get('redirect') else 'No',
                            'content_length': info.get('content_length', '') or '',
                            'content_type': info.get('content_type', '') or ''
                        }
                        
                        # Enhanced info
                        technologies = info.get('technologies', []) or []
                        row['technologies'] = '; '.join(technologies) if technologies else ''
                        
                        cms_info = info.get('cms_info', {}) or {}
                        row['cms'] = cms_info.get('CMS', '') or ''
                        row['cms_version'] = cms_info.get('Version', '') or ''
                        row['admin_panel'] = cms_info.get('Admin Panel', '') or ''
                        
                        security_info = info.get('security_info', {}) or {}
                        security_features = []
                        waf_detected = 'No'
                        
                        for key, value in security_info.items():
                            if key == 'WAF':
                                waf_detected = 'Yes'
                            else:
                                security_features.append(key)
                        
                        row['security_features'] = '; '.join(security_features)
                        row['waf_detected'] = waf_detected
                        
                        writer.writerow(row)
            
            return file_path
        except Exception as e:
            print(f"Error saving CSV results to {file_path}: {e}")
            return None
    
    def save_summary(self, summary_data, filename="summary.txt"):
        """Save enumeration summary"""
        file_path = self.get_file_path(filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("SUBDOMAIN ENUMERATION SUMMARY\n")
                f.write("="*60 + "\n\n")
                
                f.write(f"Target Domain: {summary_data.get('domain', 'N/A')}\n")
                f.write(f"Timestamp: {summary_data.get('timestamp', 'N/A')}\n")
                f.write(f"Total Subdomains Found: {summary_data.get('total_subdomains', 0)}\n")
                f.write(f"Live Subdomains: {summary_data.get('live_subdomains', 0)}\n")
                
                if summary_data.get('live_subdomains', 0) > 0:
                    success_rate = (summary_data.get('live_subdomains', 0) / summary_data.get('total_subdomains', 1)) * 100
                    f.write(f"Success Rate: {success_rate:.2f}%\n")
                
                f.write("\n" + "-"*40 + "\n")
                f.write("FILES GENERATED:\n")
                f.write("-"*40 + "\n")
                
                files = summary_data.get('files', {})
                for file_type, file_path in files.items():
                    if file_path:
                        f.write(f"{file_type.replace('_', ' ').title()}: {file_path}\n")
                
                f.write("\n" + "="*60 + "\n")
            
            return file_path
        except Exception as e:
            print(f"Error saving summary to {file_path}: {e}")
            return None
    
    def create_html_report(self, live_results, all_subdomains, filename="report.html"):
        """Create an HTML report of the results"""
        file_path = self.get_file_path(filename)
        
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subdomain Enumeration Report - {self.domain}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            display: block;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        .subdomain-link {{
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }}
        .subdomain-link:hover {{
            text-decoration: underline;
            color: #0056b3;
        }}
        .protocol-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 5px;
        }}
        .https {{
            background-color: #28a745;
            color: white;
        }}
        .http {{
            background-color: #ffc107;
            color: black;
        }}
        .clickable-note {{
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #007bff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Subdomain Enumeration Report</h1>
        <p style="text-align: center;">
            Target: <strong>{self.domain}</strong> | 
            Generated: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
        </p>
        
        <div class="stats">
            <div class="stat-card">
                <span class="stat-number">{len(all_subdomains)}</span>
                <span>Total Subdomains</span>
            </div>
            <div class="stat-card">
                <span class="stat-number">{len(live_results)}</span>
                <span>Live Subdomains</span>
            </div>
        </div>
        
        <div class="clickable-note">
            <h3>🔗 Quick Access Links</h3>
            <p><strong>Click on any subdomain below to visit directly!</strong></p>
            <p>💡 <em>All links open in new tabs for easy testing and analysis.</em></p>
        </div>
        
        <h2>Live Subdomains</h2>
        <table>
            <thead>
                <tr>
                    <th>Subdomain (Click to Visit)</th>
                    <th>Protocols</th>
                    <th>Status</th>
                    <th>Title</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for subdomain, result in sorted(live_results.items()):
                protocols = result.get('protocols', {}) or {}
                if not protocols:  # Skip if no protocols data
                    continue
                    
                protocol_badges = []
                status_codes = []
                titles = []
                primary_url = None
                
                for protocol, info in protocols.items():
                    if info and isinstance(info, dict):  # Ensure info is valid dict
                        status_code = info.get('status_code', 'N/A')
                        title = info.get('title', 'No Title') or 'No Title'
                        url = info.get('url', f"{protocol}://{subdomain}")
                        
                        # Use HTTPS URL as primary, fallback to HTTP
                        if protocol == 'https' or primary_url is None:
                            primary_url = url
                        
                        # Create protocol badge
                        badge_class = 'https' if protocol == 'https' else 'http'
                        protocol_badges.append(f'<span class="protocol-badge {badge_class}">{protocol.upper()}</span>')
                        
                        status_codes.append(str(status_code))
                        # Safe title handling
                        if isinstance(title, str):
                            titles.append(title[:50])
                        else:
                            titles.append('No Title')
                
                # Only add row if we have valid data
                if protocol_badges and status_codes and titles and primary_url:
                    html_content += f"""
                <tr>
                    <td><a href="{primary_url}" target="_blank" class="subdomain-link">{subdomain}</a></td>
                    <td>{''.join(protocol_badges)}</td>
                    <td>{' / '.join(status_codes)}</td>
                    <td>{' / '.join(titles)}</td>
                </tr>
"""
            
            html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>Report generated by Subdomain Enumerator Tool</p>
        </div>
    </div>
</body>
</html>
"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return file_path
        except Exception as e:
            print(f"Error creating HTML report: {e}")
            return None
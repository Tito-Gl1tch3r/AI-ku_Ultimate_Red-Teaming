#!/usr/bin/env python3
"""
GhostTagger Reporting Module
Handles logging, report generation, and result export
"""

import json
import os
import time
from datetime import datetime
from colorama import Fore, Style
import logging

class ReportGenerator:
    def __init__(self, output_dir='reports'):
        self.output_dir = output_dir
        self.scan_results = {}
        self.start_time = datetime.now()
        
        # Create output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = os.path.join(self.output_dir, f"ghosttagger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('GhostTagger')
        print(Fore.GREEN + f"[REPORTER] Logging initialized: {log_file}")
    
    def log_scan_start(self, target, scan_type):
        """Log scan start"""
        self.logger.info(f"Starting {scan_type} scan for {target}")
        
        if target not in self.scan_results:
            self.scan_results[target] = {
                'target': target,
                'start_time': datetime.now().isoformat(),
                'reconnaissance': {},
                'vulnerabilities': [],
                'defacements': [],
                'scan_duration': 0,
                'status': 'In Progress'
            }
    
    def log_reconnaissance_results(self, target, recon_data):
        """Log reconnaissance results"""
        self.logger.info(f"Reconnaissance completed for {target}")
        
        if target in self.scan_results:
            self.scan_results[target]['reconnaissance'] = recon_data
            
            # Log summary
            subdomains = len(recon_data.get('subdomains', []))
            endpoints = len(recon_data.get('endpoints', []))
            ports = len(recon_data.get('open_ports', []))
            
            self.logger.info(f"Found {subdomains} subdomains, {endpoints} endpoints, {ports} open ports")
    
    def log_vulnerability_results(self, target, vulnerabilities):
        """Log vulnerability scan results"""
        self.logger.info(f"Vulnerability scan completed for {target}")
        
        if target in self.scan_results:
            self.scan_results[target]['vulnerabilities'].extend(vulnerabilities)
            
            # Log summary by vulnerability type
            vuln_types = {}
            for vuln in vulnerabilities:
                vuln_type = vuln.get('type', 'Unknown')
                vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1
            
            for vuln_type, count in vuln_types.items():
                self.logger.info(f"Found {count} {vuln_type} vulnerabilities")
    
    def log_defacement_results(self, target, defacement_data):
        """Log defacement results"""
        self.logger.info(f"Defacement attempt completed for {target}")
        
        if target in self.scan_results:
            self.scan_results[target]['defacements'].extend(defacement_data)
            
            # Log success/failure
            successful = len([d for d in defacement_data if d.get('success', False)])
            total = len(defacement_data)
            
            if successful > 0:
                self.logger.warning(f"Defacement successful: {successful}/{total} attempts")
            else:
                self.logger.info(f"Defacement failed: {total} attempts made")
    
    def log_scan_complete(self, target):
        """Log scan completion"""
        if target in self.scan_results:
            end_time = datetime.now()
            start_time = datetime.fromisoformat(self.scan_results[target]['start_time'])
            duration = (end_time - start_time).total_seconds()
            
            self.scan_results[target]['end_time'] = end_time.isoformat()
            self.scan_results[target]['scan_duration'] = duration
            self.scan_results[target]['status'] = 'Completed'
            
            self.logger.info(f"Scan completed for {target} in {duration:.2f} seconds")
    
    def generate_html_report(self, output_file=None):
        """Generate HTML report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"ghosttagger_report_{timestamp}.html")
        
        # Calculate summary statistics
        total_targets = len(self.scan_results)
        total_vulnerabilities = sum(len(data['vulnerabilities']) for data in self.scan_results.values())
        total_defacements = sum(len([d for d in data['defacements'] if d.get('success', False)]) 
                               for data in self.scan_results.values())
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GhostTagger Security Assessment Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
            color: #ffffff;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.8);
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #00ff00;
            padding-bottom: 20px;
        }}
        
        .header h1 {{
            color: #00ff00;
            font-size: 2.5rem;
            margin: 0;
            text-shadow: 0 0 10px #00ff00;
        }}
        
        .header .subtitle {{
            color: #cccccc;
            font-size: 1.2rem;
            margin: 10px 0;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #333333, #444444);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #00ff00;
            text-align: center;
        }}
        
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #00ff00;
            font-size: 1.1rem;
        }}
        
        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #ffffff;
        }}
        
        .target-section {{
            margin-bottom: 40px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
        }}
        
        .target-header {{
            background: linear-gradient(135deg, #ff0000, #cc0000);
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        .target-header h2 {{
            margin: 0;
            font-size: 1.5rem;
        }}
        
        .subsection {{
            margin-bottom: 25px;
        }}
        
        .subsection h3 {{
            color: #00ff00;
            border-bottom: 1px solid #00ff00;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }}
        
        .vulnerability {{
            background: rgba(255, 0, 0, 0.1);
            border-left: 4px solid #ff0000;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }}
        
        .vulnerability.high {{
            border-left-color: #ff0000;
            background: rgba(255, 0, 0, 0.15);
        }}
        
        .vulnerability.medium {{
            border-left-color: #ff8800;
            background: rgba(255, 136, 0, 0.15);
        }}
        
        .vulnerability.low {{
            border-left-color: #ffff00;
            background: rgba(255, 255, 0, 0.15);
        }}
        
        .vulnerability-type {{
            font-weight: bold;
            color: #ff0000;
            font-size: 1.1rem;
        }}
        
        .vulnerability-details {{
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 3px;
            font-size: 0.9rem;
        }}
        
        .defacement {{
            background: rgba(255, 0, 0, 0.2);
            border: 2px solid #ff0000;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }}
        
        .defacement.success {{
            background: rgba(255, 0, 0, 0.3);
            border-color: #ff0000;
        }}
        
        .defacement.failed {{
            background: rgba(128, 128, 128, 0.2);
            border-color: #888888;
        }}
        
        .recon-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .recon-card {{
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            padding: 15px;
            border-radius: 5px;
        }}
        
        .recon-card h4 {{
            margin: 0 0 10px 0;
            color: #00ff00;
        }}
        
        .recon-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .recon-list li {{
            padding: 5px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #333333;
            color: #888888;
        }}
        
        .warning {{
            background: rgba(255, 165, 0, 0.2);
            border: 2px solid #ffa500;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .warning strong {{
            color: #ffa500;
        }}
        
        .timestamp {{
            color: #888888;
            font-size: 0.9rem;
        }}
        
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 10px;
        }}
        
        .badge.critical {{
            background: #ff0000;
            color: white;
        }}
        
        .badge.high {{
            background: #ff4444;
            color: white;
        }}
        
        .badge.medium {{
            background: #ff8800;
            color: white;
        }}
        
        .badge.low {{
            background: #ffff00;
            color: black;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔴 GhostTagger Security Assessment Report</h1>
            <div class="subtitle">Automated Offensive Web Security Testing</div>
            <div class="subtitle">Made by: xunops</div>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="warning">
            <strong>⚠️ ETHICAL HACKING DISCLAIMER ⚠️</strong><br>
            This report contains results from authorized security testing only. 
            All testing was conducted with explicit permission for educational and security assessment purposes.
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Targets Scanned</h3>
                <div class="value">{total_targets}</div>
            </div>
            <div class="summary-card">
                <h3>Vulnerabilities Found</h3>
                <div class="value">{total_vulnerabilities}</div>
            </div>
            <div class="summary-card">
                <h3>Successful Defacements</h3>
                <div class="value">{total_defacements}</div>
            </div>
            <div class="summary-card">
                <h3>Scan Duration</h3>
                <div class="value">{(datetime.now() - self.start_time).total_seconds():.0f}s</div>
            </div>
        </div>
"""
        
        # Add detailed results for each target
        for target, data in self.scan_results.items():
            html_content += f"""
        <div class="target-section">
            <div class="target-header">
                <h2>🎯 {target}</h2>
                <div class="timestamp">Scanned: {data.get('start_time', 'Unknown')} | Duration: {data.get('scan_duration', 0):.2f}s</div>
            </div>
"""
            
            # Reconnaissance section
            recon = data.get('reconnaissance', {})
            if recon:
                html_content += """
            <div class="subsection">
                <h3>🔍 Reconnaissance Results</h3>
                <div class="recon-grid">
"""
                
                # Subdomains
                subdomains = recon.get('subdomains', [])
                if subdomains:
                    html_content += f"""
                    <div class="recon-card">
                        <h4>Subdomains ({len(subdomains)})</h4>
                        <ul class="recon-list">
"""
                    for subdomain in subdomains[:10]:  # Limit to first 10
                        html_content += f"<li>{subdomain}</li>"
                    if len(subdomains) > 10:
                        html_content += f"<li>... and {len(subdomains) - 10} more</li>"
                    html_content += "</ul></div>"
                
                # Open ports
                ports = recon.get('open_ports', [])
                if ports:
                    html_content += f"""
                    <div class="recon-card">
                        <h4>Open Ports ({len(ports)})</h4>
                        <ul class="recon-list">
"""
                    for port in ports:
                        html_content += f"<li>Port {port}</li>"
                    html_content += "</ul></div>"
                
                # Technologies
                tech = recon.get('technologies', {})
                if tech:
                    html_content += """
                    <div class="recon-card">
                        <h4>Technologies</h4>
                        <ul class="recon-list">
"""
                    for key, value in tech.items():
                        if value and value != 'Unknown':
                            html_content += f"<li>{key.title()}: {value}</li>"
                    html_content += "</ul></div>"
                
                # Endpoints
                endpoints = recon.get('endpoints', [])
                if endpoints:
                    html_content += f"""
                    <div class="recon-card">
                        <h4>Discovered Endpoints ({len(endpoints)})</h4>
                        <ul class="recon-list">
"""
                    for endpoint in endpoints[:10]:  # Limit to first 10
                        status = endpoint.get('status', 'Unknown')
                        url = endpoint.get('url', endpoint.get('endpoint', ''))
                        html_content += f"<li>{url} [{status}]</li>"
                    if len(endpoints) > 10:
                        html_content += f"<li>... and {len(endpoints) - 10} more</li>"
                    html_content += "</ul></div>"
                
                html_content += "</div></div>"
            
            # Vulnerabilities section
            vulnerabilities = data.get('vulnerabilities', [])
            if vulnerabilities:
                html_content += f"""
            <div class="subsection">
                <h3>🚨 Vulnerabilities ({len(vulnerabilities)})</h3>
"""
                for vuln in vulnerabilities:
                    confidence = vuln.get('confidence', 'Medium').lower()
                    vuln_type = vuln.get('type', 'Unknown')
                    
                    html_content += f"""
                <div class="vulnerability {confidence}">
                    <div class="vulnerability-type">{vuln_type}<span class="badge {confidence}">{confidence.upper()}</span></div>
"""
                    
                    # Add vulnerability details
                    details = []
                    if 'parameter' in vuln:
                        details.append(f"Parameter: {vuln['parameter']}")
                    if 'payload' in vuln:
                        details.append(f"Payload: {vuln['payload']}")
                    if 'url' in vuln:
                        details.append(f"URL: {vuln['url']}")
                    if 'method' in vuln:
                        details.append(f"Method: {vuln['method']}")
                    
                    if details:
                        html_content += f"""
                    <div class="vulnerability-details">
                        {' | '.join(details)}
                    </div>
"""
                    html_content += "</div>"
                
                html_content += "</div>"
            
            # Defacements section
            defacements = data.get('defacements', [])
            if defacements:
                html_content += f"""
            <div class="subsection">
                <h3>💀 Defacement Attempts ({len(defacements)})</h3>
"""
                for defacement in defacements:
                    if defacement.get('type') == 'backup':
                        continue  # Skip backup entries
                    
                    success = defacement.get('success', False)
                    method = defacement.get('method', 'Unknown')
                    status_class = 'success' if success else 'failed'
                    status_text = '✅ SUCCESS' if success else '❌ FAILED'
                    
                    html_content += f"""
                <div class="defacement {status_class}">
                    <strong>{status_text}</strong> - {method}
"""
                    
                    if 'timestamp' in defacement:
                        html_content += f"<div class=\"timestamp\">Time: {defacement['timestamp']}</div>"
                    
                    html_content += "</div>"
                
                html_content += "</div>"
            
            html_content += "</div>"  # Close target-section
        
        # Footer
        html_content += f"""
        <div class="footer">
            <p><strong>GhostTagger</strong> - Automated Offensive Web Defacement Simulation Tool</p>
            <p>Made by: <strong>xunops</strong></p>
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</p>
            <p style="color: #ff0000; font-weight: bold;">⚠️ For Ethical Hacking and Red Team Training Only ⚠️</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(Fore.GREEN + f"[REPORTER] HTML report generated: {output_file}")
            self.logger.info(f"HTML report generated: {output_file}")
            return output_file
            
        except Exception as e:
            print(Fore.RED + f"[-] Error generating HTML report: {str(e)}")
            self.logger.error(f"Error generating HTML report: {str(e)}")
            return None
    
    def generate_json_report(self, output_file=None):
        """Generate JSON report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"ghosttagger_report_{timestamp}.json")
        
        # Prepare report data
        report_data = {
            'metadata': {
                'tool': 'GhostTagger',
                'version': '1.0',
                'author': 'xunops',
                'generated': datetime.now().isoformat(),
                'start_time': self.start_time.isoformat(),
                'total_duration': (datetime.now() - self.start_time).total_seconds()
            },
            'summary': {
                'total_targets': len(self.scan_results),
                'total_vulnerabilities': sum(len(data['vulnerabilities']) for data in self.scan_results.values()),
                'total_defacements': sum(len([d for d in data['defacements'] if d.get('success', False)]) 
                                       for data in self.scan_results.values()),
                'vulnerability_types': self._get_vulnerability_summary(),
                'defacement_methods': self._get_defacement_summary()
            },
            'results': self.scan_results
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            print(Fore.GREEN + f"[REPORTER] JSON report generated: {output_file}")
            self.logger.info(f"JSON report generated: {output_file}")
            return output_file
            
        except Exception as e:
            print(Fore.RED + f"[-] Error generating JSON report: {str(e)}")
            self.logger.error(f"Error generating JSON report: {str(e)}")
            return None
    
    def _get_vulnerability_summary(self):
        """Get summary of vulnerability types"""
        vuln_summary = {}
        for data in self.scan_results.values():
            for vuln in data['vulnerabilities']:
                vuln_type = vuln.get('type', 'Unknown')
                vuln_summary[vuln_type] = vuln_summary.get(vuln_type, 0) + 1
        return vuln_summary
    
    def _get_defacement_summary(self):
        """Get summary of defacement methods"""
        defacement_summary = {}
        for data in self.scan_results.values():
            for defacement in data['defacements']:
                if defacement.get('success', False):
                    method = defacement.get('method', 'Unknown')
                    defacement_summary[method] = defacement_summary.get(method, 0) + 1
        return defacement_summary
    
    def get_scan_statistics(self):
        """Get overall scan statistics"""
        total_targets = len(self.scan_results)
        total_vulnerabilities = sum(len(data['vulnerabilities']) for data in self.scan_results.values())
        total_defacements = sum(len([d for d in data['defacements'] if d.get('success', False)]) 
                               for data in self.scan_results.values())
        
        return {
            'total_targets': total_targets,
            'total_vulnerabilities': total_vulnerabilities,
            'total_defacements': total_defacements,
            'vulnerability_types': self._get_vulnerability_summary(),
            'defacement_methods': self._get_defacement_summary(),
            'scan_duration': (datetime.now() - self.start_time).total_seconds()
        }


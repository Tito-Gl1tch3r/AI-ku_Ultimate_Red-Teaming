import json
from datetime import datetime

def generate_report(vulnerabilities, file_name="xss_report.json"):
    """Generate a comprehensive JSON report of XSS vulnerabilities"""
    
    # Calculate statistics
    total_tests = len(vulnerabilities.get('vulnerabilities', []))
    vulnerable_count = len([v for v in vulnerabilities.get('vulnerabilities', []) if v['vulnerable']])
    safe_count = total_tests - vulnerable_count
    
    # Group vulnerabilities by category
    categories = {}
    for vuln in vulnerabilities.get('vulnerabilities', []):
        if vuln['vulnerable']:
            cat = vuln.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(vuln)
    
    # Group by parameter
    parameters = {}
    for vuln in vulnerabilities.get('vulnerabilities', []):
        if vuln['vulnerable']:
            param = vuln.get('parameter', 'unknown')
            if param not in parameters:
                parameters[param] = []
            parameters[param].append(vuln)
    
    report = {
        'report_metadata': {
            'generated_at': datetime.now().isoformat(),
            'tool_name': 'XSS Finder',
            'version': '2.0'
        },
        'scan_summary': {
            'target_url': vulnerabilities.get('target_url', 'N/A'),
            'category_filter': vulnerabilities.get('category', 'all'),
            'timeout': vulnerabilities.get('timeout', 5),
            'total_tests': total_tests,
            'vulnerabilities_found': vulnerable_count,
            'safe_tests': safe_count,
            'risk_level': 'HIGH' if vulnerable_count > 5 else 'MEDIUM' if vulnerable_count > 0 else 'LOW'
        },
        'vulnerabilities_by_category': categories,
        'vulnerabilities_by_parameter': parameters,
        'detailed_findings': [v for v in vulnerabilities.get('vulnerabilities', []) if v['vulnerable']],
        'recommendations': [
            'Implement proper input validation and sanitization',
            'Use Content Security Policy (CSP) headers',
            'Encode output data appropriately',
            'Use HTTPOnly and Secure flags on cookies',
            'Regular security audits and penetration testing'
        ] if vulnerable_count > 0 else ['Continue regular security monitoring']
    }
    
    with open(file_name, 'w', encoding='utf-8') as report_file:
        json.dump(report, report_file, indent=4, ensure_ascii=False)

    print(f"\n📄 Report generated: {file_name}")
    print(f"   - Total tests: {total_tests}")
    print(f"   - Vulnerabilities found: {vulnerable_count}")
    print(f"   - Risk level: {report['scan_summary']['risk_level']}")

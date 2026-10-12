#!/usr/bin/env python3
"""
Technology Analyzer Module
Analyzes and categorizes detected technologies for pentesting insights
"""

import json
from collections import Counter, defaultdict

class TechAnalyzer:
    def __init__(self):
        # Known vulnerability patterns for different technologies
        self.vuln_patterns = {
            'WordPress': {
                'common_issues': ['Plugin vulnerabilities', 'Theme exploits', 'Weak passwords', 'Outdated core'],
                'check_paths': ['/wp-admin/', '/wp-content/', '/wp-json/wp/v2/users'],
                'default_creds': ['admin:admin', 'admin:password', 'admin:123456'],
                'risk_level': 'Medium'
            },
            'Joomla': {
                'common_issues': ['Component vulnerabilities', 'Configuration.php exposure', 'SQL injection'],
                'check_paths': ['/administrator/', '/components/', '/modules/'],
                'default_creds': ['admin:admin', 'super:super'],
                'risk_level': 'Medium'
            },
            'Drupal': {
                'common_issues': ['Module vulnerabilities', 'SQLi in core', 'File upload bypass'],
                'check_paths': ['/user/login', '/admin/', '/sites/default/'],
                'default_creds': ['admin:admin'],
                'risk_level': 'Medium'
            },
            'phpMyAdmin': {
                'common_issues': ['Default credentials', 'Unrestricted access', 'Version disclosure'],
                'check_paths': ['/phpmyadmin/', '/pma/', '/mysql/'],
                'default_creds': ['root:', 'root:root', 'admin:admin'],
                'risk_level': 'High'
            },
            'Apache': {
                'common_issues': ['Server info disclosure', 'Directory traversal', 'Misconfiguration'],
                'check_paths': ['/server-status', '/server-info', '/.htaccess'],
                'risk_level': 'Low'
            },
            'Nginx': {
                'common_issues': ['Alias traversal', 'Misconfiguration', 'Version disclosure'],
                'check_paths': ['/nginx_status', '/../', '/basic_status'],
                'risk_level': 'Low'
            },
            'IIS': {
                'common_issues': ['ISAPI vulnerabilities', 'Directory traversal', 'Authentication bypass'],
                'check_paths': ['/_vti_bin/', '/aspnet_client/', '/iisstart.htm'],
                'risk_level': 'Medium'
            },
            'PHP': {
                'common_issues': ['Version disclosure', 'Configuration errors', 'Code injection'],
                'check_paths': ['/phpinfo.php', '/info.php', '/test.php'],
                'risk_level': 'Medium'
            },
            'ASP.NET': {
                'common_issues': ['ViewState manipulation', 'Debug mode enabled', 'Trace enabled'],
                'check_paths': ['/trace.axd', '/elmah.axd', '/glimpse.axd'],
                'risk_level': 'Medium'
            },
            'Shopify': {
                'common_issues': ['Limited attack surface', 'Business logic flaws'],
                'check_paths': ['/admin', '/checkout'],
                'risk_level': 'Low'
            }
        }
        
        # Technology categories for better analysis
        self.tech_categories = {
            'CMS': ['WordPress', 'Joomla', 'Drupal', 'Magento', 'Shopify'],
            'Web Servers': ['Apache', 'Nginx', 'IIS', 'LiteSpeed', 'OpenResty'],
            'Programming Languages': ['PHP', 'Python', 'Ruby', 'Java', 'ASP.NET'],
            'Frameworks': ['Laravel', 'CodeIgniter', 'Django', 'Express.js', 'React', 'Vue.js', 'Angular'],
            'Databases': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'MSSQL'],
            'CDN/Proxy': ['Cloudflare', 'Fastly', 'Varnish', 'AWS CloudFront'],
            'Security': ['WAF', 'HSTS', 'CSP', 'XSS Protection'],
            'Admin Panels': ['phpMyAdmin', 'cPanel', 'Plesk', 'WHM']
        }
    
    def analyze_technologies(self, live_results):
        """Analyze all detected technologies and provide pentesting insights"""
        analysis = {
            'technology_summary': self._get_technology_summary(live_results),
            'vulnerability_assessment': self._assess_vulnerabilities(live_results),
            'attack_surface': self._analyze_attack_surface(live_results),
            'recommendations': self._generate_recommendations(live_results),
            'high_value_targets': self._identify_high_value_targets(live_results)
        }
        
        return analysis
    
    def _get_technology_summary(self, live_results):
        """Get summary of all detected technologies"""
        tech_counter = Counter()
        cms_counter = Counter()
        server_counter = Counter()
        framework_counter = Counter()
        
        total_subdomains = len(live_results)
        
        for subdomain, result in live_results.items():
            protocols = result.get('protocols', {})
            
            for protocol, info in protocols.items():
                # Count technologies - handle None values
                technologies = info.get('technologies', []) or []
                for tech in technologies:
                    if tech and isinstance(tech, str):  # Ensure tech is a valid string
                        tech_counter[tech] += 1
                        
                        # Categorize technologies
                        for category, tech_list in self.tech_categories.items():
                            if any(known_tech.lower() in tech.lower() for known_tech in tech_list if known_tech):
                                if category == 'CMS':
                                    cms_counter[tech] += 1
                                elif category == 'Web Servers':
                                    server_counter[tech] += 1
                                elif category == 'Frameworks':
                                    framework_counter[tech] += 1
        
        return {
            'total_subdomains_analyzed': total_subdomains,
            'unique_technologies': len(tech_counter),
            'most_common_technologies': tech_counter.most_common(10),
            'cms_distribution': dict(cms_counter),
            'server_distribution': dict(server_counter),
            'framework_distribution': dict(framework_counter)
        }
    
    def _assess_vulnerabilities(self, live_results):
        """Assess potential vulnerabilities based on detected technologies"""
        vulnerabilities = defaultdict(list)
        risk_summary = {'High': 0, 'Medium': 0, 'Low': 0}
        
        for subdomain, result in live_results.items():
            protocols = result.get('protocols', {}) or {}
            
            for protocol, info in protocols.items():
                # Safe handling of None values
                technologies = info.get('technologies', []) or []
                cms_info = info.get('cms_info', {}) or {}
                security_info = info.get('security_info', {}) or {}
                
                # Check for known vulnerable technologies
                for tech in technologies:
                    if tech and isinstance(tech, str):  # Ensure tech is valid string
                        for vuln_tech, vuln_data in self.vuln_patterns.items():
                            if vuln_tech.lower() in tech.lower():
                                vuln_entry = {
                                    'subdomain': subdomain,
                                    'protocol': protocol,
                                    'technology': tech,
                                    'issues': vuln_data['common_issues'],
                                    'check_paths': vuln_data['check_paths'],
                                    'risk_level': vuln_data['risk_level']
                                }
                                
                                if 'default_creds' in vuln_data:
                                    vuln_entry['default_creds'] = vuln_data['default_creds']
                                
                                vulnerabilities[vuln_data['risk_level']].append(vuln_entry)
                                risk_summary[vuln_data['risk_level']] += 1
                
                # Check for missing security headers
                if not security_info:
                    vulnerabilities['Medium'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'technology': 'Security Headers',
                        'issues': ['Missing security headers', 'No HSTS', 'No CSP'],
                        'risk_level': 'Medium'
                    })
                    risk_summary['Medium'] += 1
        
        return {
            'risk_summary': risk_summary,
            'vulnerabilities_by_risk': dict(vulnerabilities)
        }
    
    def _analyze_attack_surface(self, live_results):
        """Analyze the attack surface"""
        attack_surface = {
            'admin_panels': [],
            'development_environments': [],
            'api_endpoints': [],
            'file_uploads': [],
            'login_pages': []
        }
        
        for subdomain, result in live_results.items():
            protocols = result.get('protocols', {})
            
            for protocol, info in protocols.items():
                # Handle None values safely
                technologies = info.get('technologies', []) or []
                cms_info = info.get('cms_info', {}) or {}
                security_info = info.get('security_info', {}) or {}
                title = info.get('title', '') or ''
                url = info.get('url', '') or ''
                
                # Detect admin panels - safe string operations
                admin_keywords = ['admin', 'administrator', 'panel', 'dashboard', 'control']
                title_lower = title.lower() if isinstance(title, str) else ''
                subdomain_lower = subdomain.lower() if isinstance(subdomain, str) else ''
                
                if any(keyword in title_lower or keyword in subdomain_lower for keyword in admin_keywords):
                    attack_surface['admin_panels'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'title': title,
                        'url': url
                    })
                
                # Detect development environments
                dev_keywords = ['dev', 'test', 'staging', 'beta', 'demo']
                if any(keyword in subdomain_lower for keyword in dev_keywords):
                    attack_surface['development_environments'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'environment_type': 'Development/Testing'
                    })
                
                # Detect API endpoints
                api_keywords = ['api', 'rest', 'graphql', 'webhook']
                if any(keyword in subdomain_lower or keyword in title_lower for keyword in api_keywords):
                    attack_surface['api_endpoints'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'type': 'API Endpoint'
                    })
                
                # Detect potential file upload areas
                upload_keywords = ['upload', 'file', 'media', 'assets']
                if any(keyword in subdomain_lower or keyword in title_lower for keyword in upload_keywords):
                    attack_surface['file_uploads'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'type': 'File Upload Area'
                    })
                
                # Detect login pages
                login_keywords = ['login', 'signin', 'auth', 'sso']
                if any(keyword in title_lower or keyword in subdomain_lower for keyword in login_keywords):
                    attack_surface['login_pages'].append({
                        'subdomain': subdomain,
                        'protocol': protocol,
                        'type': 'Authentication'
                    })
        
        return attack_surface
    
    def _generate_recommendations(self, live_results):
        """Generate pentesting recommendations"""
        recommendations = {
            'immediate_actions': [],
            'enumeration_targets': [],
            'vulnerability_testing': [],
            'tools_suggested': []
        }
        
        # Analyze technologies for specific recommendations
        all_technologies = set()
        has_admin_panels = False
        has_cms = False
        missing_security = 0
        
        for subdomain, result in live_results.items():
            protocols = result.get('protocols', {}) or {}
            
            for protocol, info in protocols.items():
                # Safe handling of technologies
                technologies = info.get('technologies', []) or []
                if isinstance(technologies, list):
                    for tech in technologies:
                        if tech and isinstance(tech, str):
                            all_technologies.add(tech)
                
                # Safe handling of CMS info
                cms_info = info.get('cms_info', {}) or {}
                if isinstance(cms_info, dict):
                    if cms_info.get('CMS'):
                        has_cms = True
                    if cms_info.get('Admin Panel'):
                        has_admin_panels = True
                
                # Safe handling of security info
                security_info = info.get('security_info', {}) or {}
                if not security_info or not isinstance(security_info, dict):
                    missing_security += 1
        
        # Generate specific recommendations
        if has_admin_panels:
            recommendations['immediate_actions'].append(
                "Test admin panels for default credentials and weak authentication"
            )
            recommendations['tools_suggested'].extend(['Hydra', 'Burp Suite', 'OWASP ZAP'])
        
        if has_cms:
            recommendations['vulnerability_testing'].append(
                "Scan CMS installations for known vulnerabilities and outdated plugins"
            )
            recommendations['tools_suggested'].extend(['WPScan', 'CMSmap', 'Nikto'])
        
        # Safe string operations for technology checking
        all_tech_str = ' '.join(str(tech) for tech in all_technologies if tech and isinstance(tech, str))
        
        if 'WordPress' in all_tech_str:
            recommendations['enumeration_targets'].append(
                "Enumerate WordPress users, plugins, and themes"
            )
            recommendations['tools_suggested'].append('WPScan')
        
        if missing_security > len(live_results) * 0.5:
            recommendations['immediate_actions'].append(
                "Many subdomains lack security headers - test for XSS, CSRF, and clickjacking"
            )
        
        # Safe checking for development keywords
        if any('dev' in str(tech).lower() or 'test' in str(tech).lower() 
               for tech in all_technologies if tech and isinstance(tech, str)):
            recommendations['immediate_actions'].append(
                "Development/staging environments detected - likely have weaker security"
            )
        
        # Add general recommendations
        recommendations['enumeration_targets'].extend([
            "Directory and file enumeration on all live subdomains",
            "Check for backup files and configuration files",
            "Test for subdomain takeover vulnerabilities"
        ])
        
        recommendations['tools_suggested'] = list(set(recommendations['tools_suggested']))
        
        return recommendations
    
    def _identify_high_value_targets(self, live_results):
        """Identify high-value targets for focused testing"""
        high_value = []
        
        for subdomain, result in live_results.items():
            protocols = result.get('protocols', {}) or {}
            score = 0
            reasons = []
            
            # Track what we've already counted to avoid duplicates
            counted_features = set()
            
            for protocol, info in protocols.items():
                # Safe handling of all data types
                technologies = info.get('technologies', []) or []
                cms_info = info.get('cms_info', {}) or {}
                security_info = info.get('security_info', {}) or {}
                title = info.get('title', '') or ''
                
                # Convert to safe strings for comparison
                tech_str = ' '.join(str(tech) for tech in technologies if tech and isinstance(tech, str))
                title_safe = str(title).lower() if title else ''
                subdomain_safe = str(subdomain).lower() if subdomain else ''
                
                # Scoring system with safe operations and duplicate prevention
                if isinstance(cms_info, dict) and cms_info.get('Admin Panel') and 'admin_panel' not in counted_features:
                    score += 30
                    reasons.append("Admin panel detected")
                    counted_features.add('admin_panel')
                
                if any('admin' in word for word in [subdomain_safe, title_safe] if word) and 'admin_keyword' not in counted_features:
                    score += 25
                    reasons.append("Admin-related subdomain/title")
                    counted_features.add('admin_keyword')
                
                if 'phpMyAdmin' in tech_str and 'phpmyadmin' not in counted_features:
                    score += 40
                    reasons.append("phpMyAdmin detected")
                    counted_features.add('phpmyadmin')
                
                if any(tech in tech_str for tech in ['WordPress', 'Joomla', 'Drupal', 'Magento']) and 'cms' not in counted_features:
                    score += 20
                    reasons.append("CMS detected")
                    counted_features.add('cms')
                
                if (not security_info or not isinstance(security_info, dict)) and 'security' not in counted_features:
                    score += 15
                    reasons.append("Missing security headers")
                    counted_features.add('security')
                
                if any(env in subdomain_safe for env in ['dev', 'test', 'staging', 'beta'] if subdomain_safe) and 'dev_env' not in counted_features:
                    score += 25
                    reasons.append("Development environment")
                    counted_features.add('dev_env')
                
                if any(keyword in subdomain_safe for keyword in ['api', 'upload', 'mail'] if subdomain_safe) and 'sensitive_func' not in counted_features:
                    score += 15
                    reasons.append("Potentially sensitive functionality")
                    counted_features.add('sensitive_func')
            
            if score >= 30:  # Threshold for high-value target
                high_value.append({
                    'subdomain': subdomain,
                    'score': score,
                    'reasons': list(set(reasons)),  # Remove any remaining duplicates
                    'protocols': list(protocols.keys())
                })
        
        # Sort by score
        high_value.sort(key=lambda x: x['score'], reverse=True)
        
        return high_value[:10]  # Return top 10
    
    def generate_report(self, analysis, output_file=None):
        """Generate a comprehensive technology analysis report"""
        report = []
        
        report.append("="*80)
        report.append("TECHNOLOGY ANALYSIS REPORT")
        report.append("="*80)
        
        # Technology Summary
        summary = analysis['technology_summary']
        report.append(f"\n📊 TECHNOLOGY SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Subdomains Analyzed: {summary['total_subdomains_analyzed']}")
        report.append(f"Unique Technologies Found: {summary['unique_technologies']}")
        
        report.append(f"\n🔝 MOST COMMON TECHNOLOGIES:")
        for tech, count in summary['most_common_technologies']:
            report.append(f"  • {tech}: {count} instances")
        
        # Vulnerability Assessment
        vuln = analysis['vulnerability_assessment']
        report.append(f"\n🚨 VULNERABILITY ASSESSMENT")
        report.append("-" * 40)
        report.append(f"Risk Summary:")
        for risk, count in vuln['risk_summary'].items():
            report.append(f"  • {risk} Risk: {count} findings")
        
        # High Value Targets
        targets = analysis['high_value_targets']
        report.append(f"\n🎯 HIGH VALUE TARGETS")
        report.append("-" * 40)
        for i, target in enumerate(targets[:5], 1):
            report.append(f"{i}. {target['subdomain']} (Score: {target['score']})")
            report.append(f"   Reasons: {', '.join(target['reasons'])}")
        
        # Recommendations
        recommendations = analysis['recommendations']
        report.append(f"\n💡 RECOMMENDATIONS")
        report.append("-" * 40)
        
        if recommendations['immediate_actions']:
            report.append("Immediate Actions:")
            for action in recommendations['immediate_actions']:
                report.append(f"  • {action}")
        
        if recommendations['tools_suggested']:
            report.append(f"\nSuggested Tools:")
            report.append(f"  {', '.join(set(recommendations['tools_suggested']))}")
        
        # Add detailed vulnerability breakdown
        vuln_details = analysis['vulnerability_assessment']['vulnerabilities_by_risk']
        if any(vuln_details.values()):
            report.append(f"\n🔍 DETAILED VULNERABILITY BREAKDOWN")
            report.append("-" * 40)
            
            for risk_level in ['High', 'Medium', 'Low']:
                if risk_level in vuln_details and vuln_details[risk_level]:
                    report.append(f"\n{risk_level} Risk Issues:")
                    seen_issues = set()
                    for vuln in vuln_details[risk_level]:
                        issue_key = f"{vuln.get('technology', 'Unknown')}_{vuln.get('subdomain', '')}"
                        if issue_key not in seen_issues:
                            seen_issues.add(issue_key)
                            subdomain = vuln.get('subdomain', 'Unknown')
                            technology = vuln.get('technology', 'Unknown')
                            issues = vuln.get('issues', [])
                            
                            report.append(f"  • {subdomain} - {technology}")
                            for issue in issues[:2]:  # Show first 2 issues
                                report.append(f"    - {issue}")
                            
                            # Add check paths if available
                            check_paths = vuln.get('check_paths', [])
                            if check_paths:
                                report.append(f"    → Check: {', '.join(check_paths[:3])}")
                            
                            # Add default creds if available
                            default_creds = vuln.get('default_creds', [])
                            if default_creds:
                                report.append(f"    → Try: {', '.join(default_creds[:3])}")
        
        # Add attack surface summary
        attack_surface = analysis['attack_surface']
        if any(attack_surface.values()):
            report.append(f"\n🎯 ATTACK SURFACE ANALYSIS")
            report.append("-" * 40)
            
            if attack_surface['admin_panels']:
                report.append(f"Admin Panels Found ({len(attack_surface['admin_panels'])}):")
                for panel in attack_surface['admin_panels'][:3]:
                    report.append(f"  • {panel['subdomain']} - {panel.get('title', 'Admin Panel')}")
            
            if attack_surface['development_environments']:
                report.append(f"\nDevelopment Environments ({len(attack_surface['development_environments'])}):")
                for env in attack_surface['development_environments'][:3]:
                    report.append(f"  • {env['subdomain']} - {env.get('environment_type', 'Dev Environment')}")
            
            if attack_surface['api_endpoints']:
                report.append(f"\nAPI Endpoints ({len(attack_surface['api_endpoints'])}):")
                for api in attack_surface['api_endpoints'][:3]:
                    report.append(f"  • {api['subdomain']} - {api.get('type', 'API')}")
        
        # Add testing methodology
        report.append(f"\n🧪 TESTING METHODOLOGY")
        report.append("-" * 40)
        report.append("1. Information Gathering:")
        report.append("   → Run technology-specific scanners")
        report.append("   → Enumerate directories and files")
        report.append("   → Check for backup files and configs")
        
        report.append("\n2. Authentication Testing:")
        report.append("   → Test default credentials on admin panels")
        report.append("   → Check for authentication bypass")
        report.append("   → Brute force weak passwords")
        
        report.append("\n3. Application Security:")
        report.append("   → Test for SQL injection")
        report.append("   → Check for XSS vulnerabilities")
        report.append("   → File upload testing")
        
        report.append("\n4. CMS-Specific Testing:")
        tech_summary = analysis.get('technology_summary', {})
        common_techs = tech_summary.get('most_common_technologies', [])
        
        # Check for WordPress
        if any('WordPress' in str(tech) for tech, count in common_techs):
            report.append("   → WordPress: Plugin/theme enumeration")
            report.append("   → WordPress: User enumeration")
            report.append("   → WordPress: wp-config.php exposure")
        
        # Check for Magento
        if any('Magento' in str(tech) for tech, count in common_techs):
            report.append("   → Magento: Admin panel bruteforce")
            report.append("   → Magento: API key exposure")
            report.append("   → Magento: Version-specific exploits")
        
        # Check for Joomla
        if any('Joomla' in str(tech) for tech, count in common_techs):
            report.append("   → Joomla: Component enumeration")
            report.append("   → Joomla: Configuration.php exposure")
        
        # Check for Drupal
        if any('Drupal' in str(tech) for tech, count in common_techs):
            report.append("   → Drupal: Module enumeration")
            report.append("   → Drupal: User enumeration")
        
        report.append("\n" + "="*80)
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text
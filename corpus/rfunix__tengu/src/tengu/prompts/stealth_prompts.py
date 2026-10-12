"""Stealth/OPSEC prompts for Tengu."""

from __future__ import annotations


def stealth_assessment(target: str) -> str:
    """Pentest workflow with full stealth/anonymity for authorized engagements.

    Args:
        target: Authorized target (must be in tengu.toml allowlist)
    """
    return f"""You are conducting an authorized penetration test of {target} with maximum stealth.

## Pre-Engagement OPSEC Setup
1. Run `check_anonymity()` to verify current anonymity level
2. Run `tor_check()` to confirm Tor connectivity
3. Enable stealth in tengu.toml: `[stealth] enabled = true`
4. Verify proxy is working: `proxy_check(proxy_url="socks5://127.0.0.1:9050")`

## Stealth Recon Phase
- Use passive recon first (OSINT, whois, DNS passive queries)
- Enable timing jitter: stealth.timing.enabled = true
- Use DNS-over-HTTPS: stealth.dns.method = "doh"
- Rotate identity between phases: `rotate_identity()`

## Low-Noise Active Scanning
- nmap with Tor proxy + slow timing: T1-T2 timing
- Avoid aggressive scans that generate large traffic bursts
- Prefer nuclei passive templates before active ones

## Stealth Workflow for {target}
1. `check_anonymity()` — verify anonymity
2. `tor_check()` — confirm Tor exit node
3. `whois_lookup(target="{target}")` — passive info gathering
4. `dns_enumerate(domain="{target}")` — DNS records (via DoH if enabled)
5. `nmap_scan(target="{target}", scan_type="connect", timing="T2")` — connect scan via Tor
6. `nuclei_scan(target="https://{target}", severity=["high", "critical"])` — targeted scan
7. `rotate_identity()` — rotate between major phases
8. Document all findings with stealth annotations

## Post-Engagement
- Clear browser history and logs
- Verify no real IP leaked during engagement
- Run final `check_anonymity()` to confirm identity was maintained throughout"""


def opsec_checklist() -> str:
    """Pre-engagement OPSEC checklist for authorized penetration tests."""
    return """# OPSEC Pre-Engagement Checklist

## Identity Verification
- [ ] Run `check_anonymity()` — verify anonymity level is "high" or "medium"
- [ ] Run `tor_check()` — confirm Tor is connected and exit node is not in target country
- [ ] Run `proxy_check(proxy_url="socks5://127.0.0.1:9050")` — confirm proxy latency < 2000ms

## Tool Configuration
- [ ] tengu.toml: `[stealth] enabled = true`
- [ ] tengu.toml: `[stealth.proxy] enabled = true`
- [ ] tengu.toml: `[stealth.timing] enabled = true`
- [ ] tengu.toml: `[stealth.user_agent] enabled = true`
- [ ] tengu.toml: `[stealth.dns] method = "doh"`

## Authorization Verification
- [ ] Written authorization obtained (scope, dates, POC)
- [ ] Target in tengu.toml `[targets] allowed_hosts`
- [ ] Emergency stop procedure established with client
- [ ] Engagement window confirmed (time zone, hours)

## Logging & Evidence
- [ ] Audit log path configured and writable
- [ ] Screen recording active for evidence
- [ ] Note-taking system ready
- [ ] Backup communication channel established with client

## Legal & Compliance
- [ ] Rules of engagement signed
- [ ] Exclusions documented and in tengu.toml blocklist
- [ ] Incident response procedure confirmed
- [ ] VPN/Tor exit country complies with local laws

## Ready to Engage
Run: `rotate_identity()` immediately before starting active scanning."""

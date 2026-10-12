# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def Lookup(email, socket_timeout):
    try:    domain_all     = email.split('@')[-1]
    except: domain_all     = None
    try:    name           = email.split('@')[0]
    except: name           = None
    try:    domain         = re.search(r"@([^@.]+)\.", email).group(1)
    except: domain         = None
    try:    tld            = f".{email.split('.')[-1]}"
    except: tld            = None
    try:    valid_syntax   = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None
    except: valid_syntax   = None

    try:    domain_ip, _, _    = TargetGetIp(domain_all, "Email", log=False)
    except: domain_ip          = None
    try:    domain_reverse_dns = IpGetDns(domain_ip, log=False)[0]
    except: domain_reverse_dns = None

    try:
        domain_smtp_banner, domain_starttls, domain_smtp_check, domain_catch_all = None, None, None, None
        domain_mx_servers = [str(r.exchange).rstrip('.') for r in dns.resolver.resolve(domain_all, 'MX')]
        if domain_mx_servers:
            for server in domain_mx_servers:
                try:
                    s = smtplib.SMTP(timeout=socket_timeout)
                    _, banner          = s.connect(server)
                    domain_smtp_banner = banner.decode() if isinstance(banner, bytes) else str(banner)
                    s.ehlo()
                    domain_starttls    = s.has_extn('starttls')
                    s.mail("test@test.com")
                    code_real, _       = s.rcpt(email)
                    fake               = ''.join(random.choices(string.ascii_lowercase, k=10))
                    fake_email         = f"{fake}@{domain_all}"
                    code_fake, _       = s.rcpt(fake_email)
                    domain_smtp_check  = (code_real == 250)
                    domain_catch_all   = (code_fake == 250)
                    s.quit()
                    break
                except: continue
    except: domain_smtp_banner, domain_starttls, domain_smtp_check, domain_catch_all = None, None, None, None

    email_infos = {
        "Email": email,
        "Name": name,
        "Domain": domain,
        "Domain all": domain_all,
        "TLD": tld,
        "Valid syntax": valid_syntax,
        "Domain IP": domain_ip,
        "Domain reverse DNS": domain_reverse_dns,
        "Domain SMTP banner": domain_smtp_banner,
        "Domain STARTTLS": domain_starttls,
        "Domain SMTP valid": domain_smtp_check,
        "Domain catch-all": domain_catch_all,
    }

    vars = {k: str(v) for k, v in email_infos.items() if v is not None}
    for name, value in vars.items(): Add(f"{name}: {white + str(value)}")

    return email_infos

def EmailLookup(email=None, socket_timeout=None, socket_proxy=None, output=None):
    Title("Email Lookup")

    if not email: email = Input("Email [-e] -> ")
    if not "@" in email: ErrorEmail()
    
    if not has_cli_args: 
        socket_timeout = Input(f"Max socket timeout [-ST] (default: {str(default_socket_timeout)}) -> ")
        socket_proxy   = Input(f"Socket proxy [-SP] (default: {str(default_socket_proxy)}) -> ")

    if not socket_proxy: socket_proxy = default_socket_proxy

    try:
        if not socket_timeout: socket_timeout = default_socket_timeout
        else: socket_timeout = float(socket_timeout)
        Info(f"Max socket timeout: {white}{str(socket_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    EnableSocketProxy(socket_proxy=socket_proxy, socket_timeout=socket_timeout)

    Wait("Scanning..")
    email_infos = Lookup(email, socket_timeout)

    json_data = {
        "Parameters": {
            "Socket timeout": socket_timeout if socket_timeout else None,
            "Socket proxy": socket_proxy if socket_proxy else None,
        },
        "Informations": email_infos,
    }

    if output in (True, None): SaveJsonToFile(json_data, f"Result_EmailLookup_{email}", json_output=output)
    Continue()
    Reset()
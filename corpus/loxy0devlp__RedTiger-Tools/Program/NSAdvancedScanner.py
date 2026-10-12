# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def AdvancedScanner(target=None, output=None, http_timeout=None, socket_timeout=None, http_proxy=None, socket_proxy=None, useragent=None, cookie=None):
    Title("Advanced Scanner")
    
    if not target: target = Input("Target [-t] -> ")
    detect_target = DetectTarget(target)
    if not detect_target in ["url", "url/page", "domain", "domain/page", "localhost", "localhost:port", "localhost:port/page", "ip", "ip:port", "ip:port/page"]: ErrorUrlDomainLocalhostIp()
    elif any(bad in target for bad in blacklists): ErrorTarget()

    if not has_cli_args: 
        http_timeout   = Input(f"Max HTTP timeout [-HT] (default: {str(default_http_timeout)}) -> ")
        socket_timeout = Input(f"Max socket timeout [-ST] (default: {str(default_socket_timeout)}) -> ")
        http_proxy     = Input(f"HTTP proxy [-HP] (default: {str(default_http_proxy)}) -> ")
        socket_proxy   = Input(f"Socket proxy [-SP] (default: {str(default_socket_proxy)}) -> ")
        useragent      = Input(f"User-Agent [-u] (for random: random, default: {str(default_useragent)}) -> ")
        cookie         = Input(f"Cookie [-c] (default: {str(default_cookie)}) -> ")

    if not http_proxy  : http_proxy   = default_http_proxy
    if not socket_proxy: socket_proxy = default_socket_proxy
    if not useragent   : useragent    = default_useragent
    if not cookie      : cookie       = default_cookie

    try:
        if not http_timeout: http_timeout = default_http_timeout
        else: http_timeout = float(http_timeout)
        if not socket_timeout: socket_timeout = default_socket_timeout
        else: socket_timeout = float(socket_timeout)
        Info(f"Max HTTP timeout: {white}{str(http_timeout)}s")
        Info(f"Max socket timeout: {white}{str(socket_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, cookie=cookie, http_timeout=http_timeout)
    EnableSocketProxy(socket_proxy=socket_proxy, socket_timeout=socket_timeout)

    json_data = {
        "Parameters": {
            "HTTP timeout": http_timeout if http_timeout else None,
            "Socket timeout": socket_timeout if socket_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "Socket proxy": socket_proxy if socket_proxy else None,
            "User-agent": useragent if useragent else None,
            "Cookie": cookie if cookie else None,
        }
    }

    Wait("Scanning..")
    ctx            = {}
    total_function = 36
    state          = {"stop": False, "completed": 0, "completed_total": total_function}
    StartThread(StatsPressed, state, time_start=time.time())

    ctx["domain"] = target
    certificates_json_format = None
    url, response, status_url, latency_url, json_format = TargetGetUrlAndStatusAndLatency(target.strip(), session, http_timeout)
    MergeJson(json_data, json_format)
    state["completed"] += 1

    if url and status_url != "404":
        RunSpeed(state, ctx, json_data, ["status"], lambda: UrlSecureConnection(url))
        RunSpeed(state, ctx, json_data, ["redirects"], lambda: UrlCheckRedirects(response))
        RunSpeed(state, ctx, json_data, ["result"], lambda: UrlDetectInlineScripts(response))
        RunSpeed(state, ctx, json_data, ["forms_info"], lambda: UrlCheckFormsSecurity(response, url))
        RunSpeed(state, ctx, json_data, ["apis"], lambda: UrlDetectApi(response))
        RunSpeed(state, ctx, json_data, ["headers_dict"], lambda: TargetGetHttpHeaders(response))
        RunSpeed(state, ctx, json_data, ["results"], lambda: TargetAnalyzeCookies(response))
        RunSpeed(state, ctx, json_data, ["detected_technologies"], lambda: TargetDetectTechnologies(response))
        RunSpeed(state, ctx, json_data, ["detected_backend"], lambda: FingerprintBackend(response, url))
        RunSpeed(state, ctx, json_data, ["detected_waf"], lambda: TargetDetectWaf(response))
        RunSpeed(state, ctx, json_data, ["domain"], lambda: TargetGetDomain(url))
        RunSpeed(state, ctx, json_data, ["is_reserved"], lambda: DomainReserved(ctx["domain"]))

    if DomainStatus(ctx["domain"]) or IpStatus(ctx["domain"]):
        RunSpeed(state, ctx, json_data, ["cn","issuer","issuer_org","san","not_before","not_after","expired","not_yet_valid"], lambda: TargetSslCertificateInfo(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["key_type","key_bits","sig_algo","weak_key"], lambda: TargetSslKeyInfo(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["tls_version","cipher_suite","cipher_bits","forward_secrecy","weak_cipher"], lambda: TargetSslCipherInfo(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["sslv3","tlsv1_0","tlsv1_1","tlsv1_2","tlsv1_3"], lambda: TargetSslTlsSupport(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["ocsp_enabled"], lambda: TargetSslOcspStapling(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["revocation_status"], lambda: TargetSslCertRevocation(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["reused","known_keys"], lambda: TargetSslKeyReuse(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["renegotiation_supported"], lambda: TargetSslRenegotiation(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["compression"], lambda: TargetSslCompression(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["resumption"], lambda: TargetSslSessionResumption(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["resumption"], lambda: TargetSslSessionResumption(ctx["domain"], socket_timeout))
        RunSpeed(state, ctx, json_data, ["domain_age_days"], lambda: DomainAge(ctx["domain"]))

        certificates, certificates_json_format = DomainCertificateTransparency(session, ctx["domain"], http_timeout)
        state["completed"] += 1

    RunSpeed(state, ctx, json_data, ["ip","port_default"], lambda: TargetGetIp(ctx["domain"], detect_target))
    if not ctx["ip"]:
        state["stop"] = True
        ErrorTarget()

    RunSpeed(state, ctx, json_data, ["status"], lambda: IpType(ctx["ip"]))
    RunSpeed(state, ctx, json_data, ["is_private"], lambda: IpPrivate(ctx["ip"]))
    RunSpeed(state, ctx, json_data, ["ping_status", "latency"], lambda: IpGetPingAndLatency(ctx["ip"], status="ICMP"))
    RunSpeed(state, ctx, json_data, ["dns"], lambda: IpGetDns(ctx["ip"]))
    if DomainStatus(ctx["domain"]) or IpStatus(ctx["domain"]):
        RunSpeed(state, ctx, json_data, ["records"], lambda: DomainDnsRecords(ctx["domain"]))
    RunSpeed(state, ctx, json_data, ["provider"], lambda: IpDetectHostingProvider(ctx["ip"], proxies))
    RunSpeed(state, ctx, json_data, ["tcp_port_stats", "udp_port_stats"], lambda: IpGetPort(ctx["ip"], socket_timeout=socket_timeout, all=False, mass_scan=True, port_default=ctx["port_default"], protocol_scan=default_protocol))
    RunSpeed(state, ctx, json_data, ["banners"], lambda: IpGetServiceBanner(ctx["ip"], ctx["tcp_port_stats"]["Open"], socket_timeout, log=True))
    RunSpeed(state, ctx, json_data, ["final_os","confidence"], lambda: IpOsFingerprint(ctx["ip"], ctx["tcp_port_stats"]["Open"], socket_timeout))
    RunSpeed(state, ctx, json_data, ["vars"], lambda: IpGetLookup(ctx["ip"], session, http_timeout))

    MergeJson(json_data, certificates_json_format)
    state["stop"] = True

    if output in (True, None): SaveJsonToFile(json_data, f"Result_AdvancedScanner_{target}", json_output=output)
    Continue()
    Reset()
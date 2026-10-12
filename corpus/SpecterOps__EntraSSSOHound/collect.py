#!/usr/bin/env python3
import base64
import datetime
import hashlib
import hmac
import json
import os
import requests
import xmltodict


def _request(method: str, host: str, uri: str, token_id: str, token_key: str, body=None, content_type="application/json") -> requests.Response:
    # Digester is initialzed with HMAC-SHA-256 using the token key as the HMAC digest key
    digester = hmac.new(
        token_key.encode(), None, hashlib.sha256)

    digester.update(f'{method}{uri}'.encode())

    digester = hmac.new(digester.digest(), None, hashlib.sha256)

    datetime_formatted = datetime.datetime.now().astimezone().isoformat('T')
    digester.update(datetime_formatted[:13].encode())

    digester = hmac.new(digester.digest(), None, hashlib.sha256)

    if body is not None:
        if type(body) == dict:
            body = json.dumps(body).encode()
        digester.update(body)

    return requests.request(
        method=method,
        url=host + uri,
        headers={
            'User-Agent': 'bhe-python-sdk 0001',
            'Authorization': f'bhesignature {token_id}',
            'RequestDate': datetime_formatted,
            'Signature': base64.b64encode(digester.digest()),
            'Content-Type': content_type,
        },
        data=body,
    )


def get_all_hybrid_users(base_url: str, token_id: str, token_key: str):
    body = {
        "query": 'MATCH (a:AZUser) WHERE a.onpremid <> "" RETURN a',
        "include_properties": False
    }
    uri = "/api/v2/graphs/cypher"
    r = _request("POST", base_url, uri, token_id, token_key, body)
    r.raise_for_status()
    return r.json()["data"]["nodes"]


def get_all_sso_computers(base_url: str, token_id: str, token_key: str):
    body = {
        "query": 'MATCH (a:Computer) WHERE a.serviceprincipalnames CONTAINS "HTTP/autologon.microsoftazuread-sso.com" RETURN a',
        "include_properties": True
    }
    uri = "/api/v2/graphs/cypher"
    r = _request("POST", base_url, uri, token_id, token_key, body)
    r.raise_for_status()
    return r.json()["data"]["nodes"]


def extract_tenant_id_from_jwt(jwt_token: str):
    """
    Extracts the Entra ID tenant ID (tid) from a JWT token.

    Args:
        jwt_token (str): The JWT token string.

    Returns:
        str: The tenant ID if present, else None.
    """
    try:
        parts = jwt_token.split(".")
        if len(parts) < 2:
            raise ValueError("Invalid JWT format")

        payload_b64 = parts[1]

        padding = '=' * (-len(payload_b64) % 4)
        payload_b64 += padding

        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json.decode("utf-8"))

        return payload.get("tid")

    except Exception as e:
        print(f"Error extracting tenant ID: {e}")
        return None


def get_sso_status(msappproxy_jwt: str):
    tenant_uuid = extract_tenant_id_from_jwt(msappproxy_jwt)
    if not tenant_uuid:
        print("[!] failed to get tenant id from token")
        return None
    url = f"https://{tenant_uuid}.registration.msappproxy.net/register/GetDesktopSsoStatus"
    body = f'<TokenAuthenticationRequest xmlns="http://schemas.datacontract.org/2004/07/Microsoft.ApplicationProxy.Common.Security.AadSecurity" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"> <AuthenticationToken>{msappproxy_jwt}</AuthenticationToken></TokenAuthenticationRequest>'
    headers = {
        "Content-Type": "application/xml"
    }
    resp = requests.post(url, data=body, headers=headers)
    retDict = {}
    sso_query = xmltodict.parse(resp.content.decode())
    retDict['Enable'] = sso_query['DesktopSsoStatusResult']['Enable']
    retDict['Exists'] = sso_query['DesktopSsoStatusResult']['Exists']
    domains = sso_query['DesktopSsoStatusResult']['Domains']['a:string']
    if not type(domains) == list:
        domains = [domains]
    retDict['Domains'] = domains

    return retDict


def build_desktop_sso_edges(msappproxy_jwt: str, base_url: str, token_id: str, token_key: str, output_file_path: str):

    # First, determine if desktop sso is enabled
    sso_query = get_sso_status(msappproxy_jwt)

    # Second, get all azusers with on-premises sid
    hybrid_users = get_all_hybrid_users(base_url, token_id, token_key)

    # Third, get all computers that have HTTP/autologon.microsoftazuread-sso.com in their SPNs
    sso_computers = get_all_sso_computers(base_url, token_id, token_key)

    enabled_computers = []
    # Cross reference all sso_computers with active domains from the SSO query
    for id, value in sso_computers.items():
        domain = value['properties']['domain']
        if any(domain.lower() == d.lower() for d in sso_query['Domains']):
            enabled_computers.append(value)

    # build our edges
    nodes = []
    edges = []
    for computer in enabled_computers:
        for user in hybrid_users.values():
            edge = {
                'kind': "DesktopSSOIdentityTransform",
                "start": {
                    "value": computer['objectId'],
                    "match_by": "id"
                },
                "end": {
                    "value": user['objectId'],
                    "match_by": "id"
                }
            }
            edges.append(edge)

    graph_data = {
        "graph": {
            "nodes": nodes,
            "edges": edges
        }
    }

    with open(output_file_path, 'w') as output_file:
        output_file.write(json.dumps(graph_data, indent=4))


def required_env(name: str):
    val = os.getenv(name)
    return val, val is None


def upload_output(output_file_path: str, base_url: str, token_id: str, token_key: str):
    uri_path = "/api/v2/file-upload"
    r = _request("POST", base_url, f"{uri_path}/start", token_id, token_key)
    r.raise_for_status()
    job_id = r.json()["data"]["id"]
    with open(output_file_path, 'r') as f:
        upload_uri_path = f"{uri_path}/{job_id}"
        r = _request("POST", base_url, upload_uri_path,
                     token_id, token_key, body=f.read().encode('utf-8'))
        r.raise_for_status()

    end_path = f"{uri_path}/{job_id}/end"
    r = _request("POST", base_url, end_path, token_id, token_key)
    r.raise_for_status()


if __name__ == "__main__":
    from dotenv import load_dotenv
    import argparse

    load_dotenv(".env")

    parser = argparse.ArgumentParser()

    default, required = required_env("MSAPPPROXY_TOKEN")
    parser.add_argument("--msappproxy-token",
                        default=default, required=required)
    default, required = required_env("BH_URL")
    parser.add_argument(
        "--bh-url", help="The URL of the BH instance", default=default, required=required)
    default, required = required_env("TOKEN_ID")
    parser.add_argument(
        "--token-id", help="The API Token Key ID for BH API calls", default=default, required=required)
    default, required = required_env("TOKEN_KEY")
    parser.add_argument(
        "--token-key", help="The API Token Key for BH API calls", default=default, required=required)

    default, required = required_env("OUTPUT_FILE")
    parser.add_argument(
        "--output-file", help="The path to write the output JSON to", default=default, required=required,
    )

    parser.add_argument(
        "--upload", help="Automatically upload the file after generating", action="store_true")

    args = parser.parse_args()

    build_desktop_sso_edges(args.msappproxy_token,
                            args.bh_url, args.token_id, args.token_key, args.output_file)

    if args.upload:
        upload_output(args.output_file, args.bh_url,
                      args.token_id, args.token_key)

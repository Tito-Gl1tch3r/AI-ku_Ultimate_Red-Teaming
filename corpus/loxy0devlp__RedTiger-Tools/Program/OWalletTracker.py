# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def SendRequest(session, url, http_timeout, method="get", json=None):
    try:
        if method == "post": response = session.post(url, json=json, timeout=http_timeout)
        else: response = session.get(url, timeout=10)
        if response.status_code != 200: return None
        return response.json()
    except: return None

def Normalize(data):
    if not data: return data

    def Parse(x):
        try:
            if isinstance(x, datetime.datetime): return x
            if isinstance(x, (int, float)): return datetime.datetime.fromtimestamp(int(x))
            if isinstance(x, str): return datetime.datetime.fromisoformat(x.replace("Z", ""))
        except: return None
        return None

    for item in data:
        if "date" in item: item["date"] = Parse(item["date"])

    return data

def IsDict(x):
    return isinstance(x, dict)

def IsList(x):
    return isinstance(x, list)

def Evm(address, session, http_timeout, url, chain):
    output   = []
    response = SendRequest(session, f"{url}/api?module=account&action=txlist&address={address}&sort=desc", http_timeout)

    if not IsDict(response): return []
    result = response.get("result")
    if not IsList(result): return []

    for tx in result[:30]:
        if not IsDict(tx): continue
        output.append({
            "chain": chain,
            "transaction_id": tx.get("hash"),
            "value": int(tx.get("value", 0)) / 1e18,
            "date": tx.get("timeStamp")
        })

    return output

def Btc(address, session, http_timeout):
    output   = []
    response = SendRequest(session, f"https://mempool.space/api/address/{address}/txs", http_timeout)

    if not IsList(response): return []

    for tx in response:
        if not IsDict(tx): continue
        value = 0
        for v in tx.get("vout", []):
            if not IsDict(v): continue
            if v.get("scriptpubkey_address") == address: value += v.get("value", 0)

        output.append({
            "chain": "BTC",
            "transaction_id": tx.get("txid"),
            "value": value / 1e8,
            "date": tx.get("status", {}).get("block_time") if IsDict(tx.get("status")) else None
        })

    return output

def Sol(address, session, http_timeout):
    output = []
    url    = "https://api.mainnet-beta.solana.com"
    sigs   = SendRequest(session, url, http_timeout, "post", {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [address]})
    
    if not sigs or "result" not in sigs: return []

    for s in sigs["result"]:
        sig   = s.get("signature")
        tx    = SendRequest(session, url, http_timeout, "post", {"jsonrpc": "2.0", "id": 1, "method": "getTransaction", "params": [sig, "jsonParsed"]})
        value = None
        
        try:
            if tx and tx.get("result"):
                meta = tx["result"].get("meta", {})
                pre = meta.get("preBalances", [])
                post = meta.get("postBalances", [])
                if pre and post: value = abs(sum(post) - sum(pre)) / 1e9
        except: value = None

        output.append({
            "chain": "SOL",
            "transaction_id": sig,
            "value": value,
            "date": s.get("blockTime")
        })

    return output

def Tron(address, session, http_timeout):
    output   = []
    response = SendRequest(session, f"https://apilist.tronscanapi.com/api/transaction?address={address}&limit=999999", http_timeout)

    if not IsDict(response): return []
    data = response.get("data")
    if not IsList(data): return []

    for tx in data:
        if not IsDict(tx): continue
        output.append({
            "chain": "TRX",
            "transaction_id": tx.get("hash"),
            "value": float(tx.get("amount", 0) or 0) / 1e6,
            "date": (int(tx.get("timestamp")) / 1000) if tx.get("timestamp") else None
        })

    return output

def Ltc(address, session, http_timeout):
    output   = []
    response = SendRequest(session, f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}", http_timeout)

    if not IsDict(response): return []
    txs = response.get("txrefs", [])
    if not IsList(txs): return []

    for tx in txs:
        if not IsDict(tx): continue
        value = tx.get("value", 0)
        if not isinstance(value, (int, float)): value = 0
        output.append({
            "chain": "LTC",
            "transaction_id": tx.get("tx_hash"),
            "value": value / 1e8,
            "date": tx.get("confirmed")
        })

    return output

def Xrp(address, session, http_timeout):
    output   = []
    response = SendRequest(session, "https://s1.ripple.com:51234/", http_timeout, "post", {"method": "account_tx", "params": [{"account": address, "ledger_index_min": -1, "ledger_index_max": -1, "binary": False}]})
   
    if not IsDict(response): return []
    txs = response.get("result", {}).get("transactions", [])

    for item in txs:
        tx     = item.get("tx", {})
        amount = tx.get("Amount")
        value  = 0

        if isinstance(amount, dict):
            try: value = float(amount.get("value", 0))
            except: value = 0
        elif isinstance(amount, str):
            try: value = int(amount) / 1e6
            except: value = 0

        raw_date = tx.get("date")
        date     = None

        if isinstance(raw_date, (int, float)): date = datetime.datetime.fromtimestamp(raw_date + 946684800)
        output.append({
            "chain": "XRP",
            "transaction_id": tx.get("hash"),
            "value": value,
            "date": date
        })

    return output

def WalletTracker(address=None, http_timeout=None, http_proxy=None, useragent=None, output=None):
    Title("Wallet Tracker")

    if not address: address = Input("Wallet address [-a] -> ")

    if not has_cli_args: 
        http_timeout = Input(f"Max HTTP timeout for the API [-HT] (default: {str(default_http_timeout)}) -> ")
        http_proxy   = Input(f"HTTP proxy for the API [-HP] (default: {str(default_http_proxy)}) -> ")
        useragent    = Input(f"User-Agent for the API [-u] (for random: random, default: {str(default_useragent)}) -> ")

    if not http_proxy: http_proxy = default_http_proxy
    if not useragent : useragent  = default_useragent

    try:
        if not http_timeout: http_timeout = default_http_timeout
        else: http_timeout = float(http_timeout)
        Info(f"Max HTTP timeout: {white}{str(http_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, http_timeout=http_timeout, enable_cookie=False)

    Wait(f"Address scanning: {white}{address}")

    data  = []
    data += Evm( address, session, http_timeout, "https://eth.blockscout.com",       "ETH")
    data += Evm( address, session, http_timeout, "https://polygon.blockscout.com",   "POLYGON")
    data += Evm( address, session, http_timeout, "https://ftm.blockscout.com",       "FTM")
    data += Evm( address, session, http_timeout, "https://snowtrace.blockscout.com", "AVAX")
    data += Evm( address, session, http_timeout, "https://bsc.blockscout.com",       "BSC")
    data += Btc( address, session, http_timeout)
    data += Sol( address, session, http_timeout)
    data += Tron(address, session, http_timeout)
    data += Ltc( address, session, http_timeout)
    data += Xrp( address, session, http_timeout)
    data  = Normalize(data)

    if not data:
        Info("No data found.")
        Continue()
        Reset()

    cols = ["chain", "transaction_id", "value", "date"]
    data = [{k: item.get(k, None) for k in cols} for item in data]

    data = [{
        "chain": "Unknown" if x["chain"] is None else str(x["chain"]),
        "transaction_id": "Unknown" if x["transaction_id"] is None else str(x["transaction_id"]),
        "value": ("Unknown" if x["value"] is None else f"{float(x['value']):.6f}"),
        "date": "Unknown" if x["date"] is None else str(x["date"])
    } for x in data]

    max_chain     = max(map(len, [x["chain"] for x in data])) if data else 0
    if max_chain <= 5: w_chain = 7
    else: w_chain = max_chain + 1
    max_tx        = max(map(len, [x["transaction_id"] for x in data])) if data else 0
    if max_tx    <= 14: w_tx = 16
    else: w_tx    = max_tx + 1
    max_val       = max(map(len, [x["value"] for x in data])) if data else 0
    if max_val   <= 5: w_val = 7
    else: w_val   = max_val + 1

    print(f"{red}{'':<14} {'Chain:':<{w_chain}} {'Transaction ID:':<{w_tx}} {'Value:':<{w_val}} {'Date:'}{reset}")
    for i, row in enumerate(data):
        Add(f"{white}{row['chain']:<{w_chain}} {row['transaction_id']:<{w_tx}} {row['value']:<{w_val}} {row['date']}")

    json_data = {
        "Parameters": {
            "Address": address,
            "HTTP timeout": http_timeout if http_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None,
        },
        "History": data
    }
    
    if output in (True, None): SaveJsonToFile(json_data, f"Result_WalletTracker_{address}", json_output=output)
    Continue()
    Reset()
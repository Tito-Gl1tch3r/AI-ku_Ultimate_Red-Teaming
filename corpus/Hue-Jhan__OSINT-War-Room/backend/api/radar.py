from fastapi import APIRouter
import asyncio
import requests
import time as _time
_cache = {}  # key → {data, ts}
_pending = {}  # key → asyncio.Event (in-flight lock)
CACHE_TTL = { "bases": 3600 * 6, "conflicts": 900 }

router = APIRouter()

@router.get("/alarms")
async def get_ukraine_alarms():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        print("[Alarms] Fetching live Ukraine air raid alerts...")
        res = await asyncio.to_thread(
            requests.get,
            "https://api.alerts.in.ua/v1/alerts/active.json",
            headers=headers, timeout=8
        )
        if res.status_code != 200:
            return {"status": "error", "data": []}

        raw = res.json()
        alerts = []
        # Region centroids for mapping oblast names → coordinates
        OBLAST_COORDS = {
            "Kyiv":            [50.4501,  30.5234],
            "Kharkiv":         [49.9935,  36.2304],
            "Odessa":          [46.4825,  30.7233],
            "Dnipropetrovsk":  [48.4647,  35.0462],
            "Donetsk":         [48.0159,  37.8028],
            "Zaporizhzhia":    [47.8388,  35.1396],
            "Kherson":         [46.6354,  32.6169],
            "Mykolaiv":        [46.9750,  31.9946],
            "Sumy":            [50.9216,  34.7981],
            "Chernihiv":       [51.4982,  31.2893],
            "Poltava":         [49.5883,  34.5514],
            "Kirovograd":      [48.5132,  32.2597],
            "Vinnytsia":       [49.2331,  28.4682],
            "Khmelnytsky":     [49.4229,  26.9871],
            "Zhytomyr":        [50.2547,  28.6587],
            "Cherkasy":        [49.4444,  32.0598],
            "Rivne":           [50.6199,  26.2516],
            "Volyn":           [50.7472,  25.3254],
            "Lviv":            [49.8397,  24.0297],
            "Ivano-Frankivsk": [48.9226,  24.7111],
            "Ternopil":        [49.5535,  25.5948],
            "Chernivtsi":      [48.2921,  25.9358],
            "Zakarpattia":     [48.6208,  22.2879],
            "Luhansk":         [48.5740,  39.3078],
            "Crimea":          [44.9521,  34.1024],
            "Kyiv City":       [50.4501,  30.5234],
        }

        active = raw if isinstance(raw, list) else raw.get("alerts", [])
        for alert in active:
            region = alert.get("regionTitle") or alert.get("region_title") or ""
            atype  = alert.get("alertType")  or alert.get("type", "")
            # Match region name to coords (fuzzy: check if key is substring)
            coords = None
            for key, c in OBLAST_COORDS.items():
                if key.lower() in region.lower() or region.lower() in key.lower():
                    coords = c
                    break
            if coords:
                alerts.append({
                    "region":  region,
                    "type":    atype,
                    "coords":  coords,
                    "started": alert.get("startedAt") or alert.get("started_at", ""),
                })
        print(f"[Alarms] Successfully parsed {len(alerts)} active alert regions.")
        return {"status": "success", "data": alerts}

    except Exception as e:
        print(f"[!] Ukraine alarms error: {e}")
        return {"status": "error", "data": []}


@router.get("/bases")
async def get_military_bases():
    if "bases" in _cache and (_time.time() - _cache["bases"]["ts"]) < CACHE_TTL["bases"]:
        print("[Cache] Serving cached bases")
        return {"status": "success", "data": _cache["bases"]["data"]}
    if "bases" in _pending:
        print("[Cache] Waiting for in-flight bases request...")
        await _pending["bases"].wait()
        if "bases" in _cache:
            return {"status": "success", "data": _cache["bases"]["data"]}
    _pending["bases"] = asyncio.Event()
    # Focused on active conflict regions to avoid flooding the map
    REGIONS = [
        {"name": "Ukraine",      "bbox": "44.0,22.0,52.5,40.5"},
        {"name": "Middle East",  "bbox": "12.0,29.0,38.0,60.0"},
        {"name": "Taiwan",       "bbox": "21.5,118.0,27.0,123.5"},
    ]

    query_parts = []
    for r in REGIONS:
        bb = r["bbox"]
        query_parts.append(f'node["military"~"base|airfield|naval_base|barracks|range|checkpoint"]({bb});')
        query_parts.append(f'way["military"~"base|airfield|naval_base|barracks|range|checkpoint"]({bb});')

    query = f"""
    [out:json][timeout:25];
    (
      {''.join(query_parts)}
    );
    out center 200;
    """

    try:
        print("[OSM] Querying Overpass military bases in active regions...")
        res = await asyncio.to_thread(
            requests.post,
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=30
        )
        if res.status_code != 200:
            return {"status": "error", "data": []}

        elements = res.json().get("elements", [])
        bases = []
        seen = set()

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en") or tags.get("operator") or "Military Site"
            mil_type = tags.get("military", "base")

            # Get coords — nodes have lat/lon directly, ways have center
            if el["type"] == "node":
                lat, lon = el.get("lat"), el.get("lon")
            else:
                center = el.get("center", {})
                lat, lon = center.get("lat"), center.get("lon")

            if lat is None or lon is None:
                continue

            # Deduplicate by rounded position
            key = f"{round(lat,2)},{round(lon,2)}"
            if key in seen:
                continue
            seen.add(key)

            bases.append({
                "name":    name,
                "type":    mil_type,
                "coords":  [lat, lon],
            })
        
        print(f"[OSM] Successfully fetched {len(bases)} military bases.")
        if bases:
            _cache["bases"] = {"data": bases, "ts": _time.time()}
        ev = _pending.pop("bases", None)
        if ev: ev.set()
        return {"status": "success", "data": bases}

    except Exception as e:
        print(f"[!] OSM bases error: {e}")
        ev = _pending.pop("bases", None)
        if ev: ev.set()
        return {"status": "error", "data": []}

ACLED_EMAIL     = "aa"
ACLED_PASSWORD  = "bb"
ACLED_CLIENT_ID = "cc"

_acled_token   = None
_acled_token_ts = 0

async def get_acled_token():
    global _acled_token, _acled_token_ts
    import time
    if _acled_token and (time.time() - _acled_token_ts) < 82800:
        return _acled_token
    try:
        res = await asyncio.to_thread(
            requests.post,
            "https://acleddata.com/oauth/token",
            data={
                "username":   ACLED_EMAIL,
                "password":   ACLED_PASSWORD,
                "grant_type": "password",
                "client_id":  ACLED_CLIENT_ID,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )
        print(f"[ACLED token] status={res.status_code} body={res.text[:300]}")
        if res.status_code == 200:
            _acled_token    = res.json().get("access_token")
            _acled_token_ts = time.time()
            print(f"[✓] ACLED token OK")
            return _acled_token
        else:
            print(f"[!] ACLED token failed: {res.text[:300]}")
    except Exception as e:
        print(f"[!] ACLED token exception: {e}")
    return None

@router.get("/conflicts")
async def get_conflict_events():
    """
    GDELT Project - free, no auth, updates every 15min.
    Filters for explosion/attack event codes in Middle East + Ukraine.
    """
    from datetime import date, timedelta
    import csv, io
    if "conflicts" in _cache and (_time.time() - _cache["conflicts"]["ts"]) < CACHE_TTL["conflicts"]:
        return {"status": "success", "data": _cache["conflicts"]["data"]}
    if "conflicts" in _pending:
        await _pending["conflicts"].wait()
        if "conflicts" in _cache:
            return {"status": "success", "data": _cache["conflicts"]["data"]}
    _pending["conflicts"] = asyncio.Event()

    CONFLICT_CODES = {"180","181","182","183","190","191","192","193","194","195","1453"}

    PRIORITY_FIPS = {
        "IS": "Israel", "WE": "West Bank", "GZ": "Gaza Strip",
        "IR": "Iran",   "IZ": "Iraq",      "SY": "Syria",
        "LB": "Lebanon","YM": "Yemen",     "UP": "Ukraine",
        "RS": "Russia", "SU": "Sudan",
    }

    try:
        import zipfile

        def try_zip(r):
            try:
                zf = zipfile.ZipFile(io.BytesIO(r.content))
                return zf.read(zf.namelist()[0]).decode("latin-1")
            except Exception:
                return None

        csv_data = None
        version_used = "v2"

        # 1) Live 15-min feed first
        print("[GDELT] Attempting to fetch live 15-min CSV...")
        try:
            lu = await asyncio.to_thread(requests.get, "http://data.gdeltproject.org/gdeltv2/lastupdate.txt", timeout=10)
            for line in lu.text.strip().split("\n"):
                if "export.CSV.zip" in line:
                    r = await asyncio.to_thread(requests.get, line.split(" ")[-1].strip(), timeout=30)
                    csv_data = try_zip(r)
                    if csv_data: 
                        print("[GDELT] Success: Downloaded live 15-min feed (v2 format).")
                    break
        except Exception as e:
            print(f"[!] GDELT live feed error: {e}")

        # 2) Fallback: daily exports
        if not csv_data:
            version_used = "v1"
            print("[GDELT] Falling back to daily exports (v1 format)...")
            for days_back in [1, 2, 3]:
                try:
                    d = (date.today() - timedelta(days=days_back)).strftime("%Y%m%d")
                    r = await asyncio.to_thread(requests.get, f"http://data.gdeltproject.org/events/{d}.export.CSV.zip", timeout=30)
                    csv_data = try_zip(r)
                    if csv_data: 
                        print(f"[GDELT] Success: Downloaded daily -{days_back}d export.")
                        break
                except Exception: continue

        if not csv_data:
            print("[!] GDELT FATAL: Could not download any CSV data.")
            return {"status": "error", "data": []}

        events, other = [], []
        reader = csv.reader(io.StringIO(csv_data), delimiter="\t")
        
        valid_rows = 0
        skipped_format = 0
        skipped_coords = 0

        print("[GDELT] Parsing CSV data...")
        for row in reader:
            try:
                row_len = len(row)
                if row_len < 50: 
                    skipped_format += 1
                    continue
                
                event_code = row[26]
                if event_code not in CONFLICT_CODES: continue

                # Dynamic mapping based on GDELT CSV Version
                if row_len >= 60:  
                    # GDELT 2.0 format
                    country_code  = row[53]
                    lat_str       = row[56]
                    lon_str       = row[57]
                    location      = row[52]
                else:              
                    # GDELT 1.0 format
                    country_code  = row[51]
                    lat_str       = row[53]
                    lon_str       = row[54]
                    location      = row[50]

                if not lat_str or not lon_str:
                    skipped_coords += 1
                    continue

                lat = float(lat_str)
                lon = float(lon_str)
                if lat == 0 and lon == 0: 
                    skipped_coords += 1
                    continue

                country_name = PRIORITY_FIPS.get(country_code, country_code)
                loc_name = location or country_name
                date_str = row[1][:4] + "-" + row[1][4:6] + "-" + row[1][6:8]

                dot_type = ("strike" if event_code in {"194","193","1453"} else
                            "missile" if event_code == "195" else "explosion")

                EVENT_LABELS = {
                    "193": "Bombing/Explosion", "194": "Air/Drone Strike",
                    "195": "Remote Violence", "190": "Use of Force",
                    "191": "Seize/Attack", "192": "Violent Battle", "1453": "IED/Roadside Bomb",
                }
                subtype = EVENT_LABELS.get(event_code, f"Conflict Event {event_code}")
                actor   = row[6] or row[15] or "Unknown actor"
                
                # GDELT proxy numbers for intensity (using mentions/sources as pseudo-casualty metrics)
                try:    killed   = int(float(row[31])) if row[31] else 0
                except: killed   = 0
                try:    wounded  = int(float(row[33])) if row[33] else 0
                except: wounded  = 0

                item = {
                    "name":     loc_name,
                    "actor":    actor[:60],
                    "date":     date_str,
                    "subtype":  subtype,
                    "country":  country_name,
                    "notes":    "",
                    "dot_type": dot_type,
                    "coords":   [lat, lon],
                    "killed":   killed,
                    "wounded":  wounded,
                }

                if country_code in PRIORITY_FIPS:
                    events.append(item)
                else:
                    other.append(item)

                valid_rows += 1

                if len(events) >= 300 and len(other) >= 100:
                    break

            except (ValueError, IndexError):
                skipped_format += 1
                continue

        print(f"[GDELT] Parsing Complete | Found: {valid_rows} valid events | Filtered: {len(events)} Priority, {len(other)} Other | Skipped Bad Coords: {skipped_coords}")
    
        combined = events + other[:50]
        if combined:
            _cache["conflicts"] = {"data": combined, "ts": _time.time()}
        
        ev = _pending.pop("conflicts", None)
        if ev: ev.set()
        return {"status": "success", "data": combined}

    except Exception as e:
        print(f"[!] GDELT critical error: {e}")
        ev = _pending.pop("conflicts", None)
        if ev: ev.set()
        return {"status": "error", "data": []}

@router.get("/ground")
async def get_ground_radar():
    return {"status": "success", "data": []}


@router.get("/aircraft")
async def get_aircraft(
    lamin: float = -90, lomin: float = -180,
    lamax: float = 90,  lomax: float = 180
):
    try:
        print(f"[OpenSky] Fetching live aircraft data...")
        res = await asyncio.to_thread(
            requests.get,
            "https://opensky-network.org/api/states/all",
            params={"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
            timeout=15
        )
        if res.status_code != 200:
            print(f"[OpenSky] HTTP {res.status_code}")
            return {"status": "error", "data": []}

        states = res.json().get("states") or []
        aircraft = []
        for s in states:
            # s[5]=lon, s[6]=lat, s[10]=heading, s[1]=callsign, s[2]=country
            # s[7]=on_ground, s[9]=velocity(m/s)
            if s[5] is None or s[6] is None: continue
            if s[7]: continue  # skip ground vehicles
            aircraft.append({
                "icao":     s[0],
                "callsign": (s[1] or "").strip() or s[0],
                "country":  s[2] or "",
                "lat":      s[6],
                "lon":      s[5],
                "heading":  s[10] or 0,
                "altitude": round(s[13] or s[7] or 0),  # geo alt, fallback baro
                "speed":    round((s[9] or 0) * 1.94384),  # m/s → knots
            })

        print(f"[OpenSky] {len(aircraft)} aircraft in bbox")
        return {"status": "success", "data": aircraft}

    except Exception as e:
        print(f"[!] OpenSky error: {e}")
        return {"status": "error", "data": []}


# AIS ship positions via AISStream HTTP snapshot, doesnt work bc it keeps blocking my ip 
@router.get("/ships")
async def get_ships():
    try:
        import websockets, json as _j
        ships = {}
        uri = "wss://stream.aisstream.io/v0/stream"
        print("[AIS] Opening websocket conn to AISStream for ships...")
        async with websockets.connect(uri, ping_interval=None, open_timeout=15) as ws:
            await ws.send(_j.dumps({
                "Apikey": "xxx",
                "BoundingBoxes": [
                    [[10.0, 20.0],  [45.0, 65.0]],
                    [[-10.0, 50.0], [30.0, 80.0]],
                    [[15.0, 110.0], [40.0, 135.0]],
                ],
                "FilterMessageTypes": ["PositionReport"]
            }))

            import asyncio as _a
            deadline = _a.get_event_loop().time() + 10
            while _a.get_event_loop().time() < deadline:
                try:
                    raw  = await _a.wait_for(ws.recv(), timeout=3)
                    msg  = _j.loads(raw)
                    meta = msg.get("MetaData", {})
                    lat  = meta.get("latitude")
                    lon  = meta.get("longitude")
                    if not lat or not lon: continue
                    mmsi = str(meta.get("MMSI", ""))
                    pos  = msg.get("Message", {}).get("PositionReport", {})
                    ships[mmsi] = {
                        "name":    meta.get("ShipName", "").strip() or mmsi,
                        "lat":     lat, "lon": lon,
                        "heading": pos.get("TrueHeading") or pos.get("Cog") or 0,
                        "speed":   pos.get("Sog") or 0,
                        "type":    "cargo",
                    }
                except _a.TimeoutError:
                    break

        print(f"[AIS] {len(ships)} ships collected")
        return {"status": "success", "data": list(ships.values())}
    except Exception as e:
        print(f"[!] AIS error: {e}")
        return {"status": "error", "data": []}
    
@router.get("/cyber")
async def get_cyber_events():
    """CISA Known Exploited Vulnerabilities + recent breach data — no auth needed"""
    try:
        results = []
        print("[Cyber] Fetching latest CISA Exploited Vulnerabilities...")
        # CISA KEV catalog — free, no key, official US govt feed
        r = await asyncio.to_thread(
            requests.get,
            "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            timeout=15
        )
        if r.status_code == 200:
            vulns = r.json().get("vulnerabilities", [])
            # Most recent 20
            for v in vulns[:20]:
                results.append({
                    "type":    "exploit",
                    "title":   v.get("vulnerabilityName", "Unknown CVE"),
                    "id":      v.get("cveID", ""),
                    "vendor":  v.get("vendorProject", ""),
                    "product": v.get("product", ""),
                    "date":    v.get("dateAdded", ""),
                    "detail":  v.get("shortDescription", ""),
                    "url":     f"https://nvd.nist.gov/vuln/detail/{v.get('cveID','')}",
                })

        print(f"[Cyber] {len(results)} events")
        return {"status": "success", "data": results}
    except Exception as e:
        print(f"[!] Cyber error: {e}")
        return {"status": "error", "data": []}
    


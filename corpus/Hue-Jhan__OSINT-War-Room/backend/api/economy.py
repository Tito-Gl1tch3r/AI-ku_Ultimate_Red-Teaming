from fastapi import APIRouter
import requests
from bs4 import BeautifulSoup
import asyncio
import json
import yfinance as yf

router = APIRouter()

MARKET_TICKERS = {
    "S&P 500":   ("^GSPC",  "Stocks",      "🇺🇸"),
    "FTSE 100":  ("^FTSE",  "Stocks",      "🇬🇧"),
    "Nikkei":    ("^N225",  "Stocks",      "🇯🇵"),
    "Gold":      ("GC=F",   "Metals",      "🪙"),
    "Silver":    ("SI=F",   "Metals",      "🥈"),
    "WTI Crude": ("CL=F",   "Commodities", "🛢️"),
    "Nat Gas":   ("NG=F",   "Commodities", "🔥"),
    "Wheat":     ("ZW=F",   "Commodities", "🌾"),
    "VIX":       ("^VIX",   "Fear",        "⚠️"),
    "BTC":       ("BTC-USD","Crypto",      "₿"),
    "ETH":       ("ETH-USD","Crypto",      "Ξ"),
    "XMR":       ("XMR-USD","Crypto",      "🔒"),
}

def fetch_ticker(symbol: str):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d", interval="1d")
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 2:
            hist = t.history(period="1mo", interval="1d").dropna(subset=["Close"])
        if len(hist) < 2:
            return None
        prev_close = hist["Close"].iloc[-2]
        curr_close = hist["Close"].iloc[-1]
        change_pct = ((curr_close - prev_close) / prev_close) * 100
        return {
            "price": curr_close,
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"[!] yfinance error for {symbol}: {e}")
        return None

def format_price(name: str, price: float) -> str:
    if "BTC" in name or price > 10000:
        return f"${price:,.0f}"
    elif price > 100:
        return f"${price:,.2f}" if name in ("Gold", "Silver", "WTI Crude", "Nat Gas", "Wheat") else f"{price:,.2f}"
    else:
        return f"${price:.2f}"

@router.get("/markets")
async def get_market_data():
    results = []
    for name, (symbol, category, icon) in MARKET_TICKERS.items():
        data = await asyncio.to_thread(fetch_ticker, symbol)
        if data:
            change = data["change_pct"]
            results.append({
                "symbol":   name,
                "category": category,
                "icon":     icon,
                "price":    format_price(name, data["price"]),
                "change":   f"{'+' if change >= 0 else ''}{change:.2f}%",
                "type":     "up" if change >= 0 else "down",
            })
        else:
            results.append({
                "symbol":   name,
                "category": category,
                "icon":     icon,
                "price":    "N/A",
                "change":   "N/A",
                "type":     "down",
            })
    return {"status": "success", "data": results}

@router.get("/vix")
async def get_vix():
    data = await asyncio.to_thread(fetch_ticker, "^VIX")
    if data:
        return {"status": "success", "price": round(data["price"], 2), "change_pct": round(data["change_pct"], 2)}
    return {"status": "error"}

@router.get("/polymarket")
async def get_polymarket_bets():
    try:
        import json as _json
        headers = {'User-Agent': 'Mozilla/5.0'}

        # Fetch top by 24h volume (filtered, so grab more to account for sports being removed)
        r1 = await asyncio.to_thread(
            requests.get,
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "limit": 60, "order": "volume24hr", "ascending": "false"},
            headers=headers, timeout=10
        )

        # Fetch top by all-time volume for the "top 3 by value" section
        r2 = await asyncio.to_thread(
            requests.get,
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "limit": 40, "order": "volume", "ascending": "false"},
            headers=headers, timeout=10
        )

        if r1.status_code != 200:
            return {"status": "error", "data": [], "top_volume": []}

        SPORTS_KEYWORDS = [
            "nba", "nfl", "nhl", "mlb", "ufc", "mma", "golf", "f1", "formula 1",
            "championship", "playoff", "super bowl", "world cup", "premier league",
            "la liga", "serie a", "bundesliga", "champions league", "europa league",
            "transfer", "fixture", "match", "game winner", "mvp", "draft pick",
            "season wins", "most kills", "counter-strike", "cct ", "esport",
            "vs.", " vs ", "celtics", "lakers", "warriors", "bucks", "nuggets",
            "clippers", "jazz", "knicks", "heat", "suns", "spurs", "nets",
            "patriots", "chiefs", "cowboys", "eagles", "49ers",
            "yankees", "dodgers", "red sox", "cubs",
            "play-in", "series:", "bo3", "bo5", "map ", "round ",
        ]

        def is_sports(question):
            q = question.lower()
            if " vs " in q or " vs." in q:
                return True
            return any(kw in q for kw in SPORTS_KEYWORDS)

        def is_valid_market(m, parsed):
            # Filter out markets where outcome is already decided (>97% or <3%)
            if parsed["yes_prob"] >= 97 or parsed["yes_prob"] <= 3:
                return False
            # Filter out very low volume (likely test/dead markets)
            if parsed["volume24hr"] < 1000 and parsed["total_volume"] < 5000:
                return False
            return True

        def parse_market(m):
            question = m.get("question", "Unknown")
            volume = float(m.get("volume24hr") or 0)
            total_volume = float(m.get("volume") or 0)
            url = f"https://polymarket.com/event/{m.get('slug', '')}"
            prices_raw = m.get("outcomePrices", '["0.5","0.5"]')
            prices = _json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
            yes_prob = round(float(prices[0]) * 100)
            change_raw = m.get("priceChange24hr")
            change_pct = round(float(change_raw) * 100, 1) if change_raw is not None else 0
            return {
                "question": question,
                "yes_prob": yes_prob,
                "no_prob": 100 - yes_prob,
                "volume24hr": volume,
                "total_volume": total_volume,
                "change_pct": change_pct,
                "url": url,
            }

        # Top 5 by 24h volume, no sports
        trending = []
        for m in r1.json():
            if is_sports(m.get("question", "")): continue
            try:
                parsed = parse_market(m)
                if not is_valid_market(m, parsed): continue
                trending.append(parsed)
            except: continue
            if len(trending) >= 5: break

        # Top 3 by all-time volume, no sports
        top_volume = []
        seen = {m["question"] for m in trending}
        for m in (r2.json() if r2.status_code == 200 else []):
            if is_sports(m.get("question", "")): continue
            try:
                parsed = parse_market(m)
                if parsed["question"] in seen: continue
                if not is_valid_market(m, parsed): continue
                top_volume.append(parsed)
                seen.add(parsed["question"])
            except: continue
            if len(top_volume) >= 3: break

        return {"status": "success", "data": trending, "top_volume": top_volume}

    except Exception as e:
        print(f"[!] Polymarket API error: {e}")
        return {"status": "error", "data": [], "top_volume": []}
    
@router.get("/pizza")
async def get_pizza_report():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = await asyncio.to_thread(
            requests.get, "https://monitor-the-situation.com/api/pizza", headers=headers, timeout=10
        )
        if response.status_code == 200:
            raw = response.json()
            current = raw.get("current", {})
            history = raw.get("history", [])
            baselines = raw.get("baselines", {})

            # Map alertLevel string to DOUGHCON number (inverted: high activity = low DOUGHCON)
            level_map = {"low": 4, "elevated": 3, "high": 2, "critical": 1}
            alert_level = (current.get("alertLevel") or current.get("alert_level") or "low").lower()
            doughcon = level_map.get(alert_level, 4)

            # Build graph data from last 24 history points
            graph = [{"ts": h.get("ts",""), "avgWait": h.get("avgWait", h.get("avg_wait", 0)), "alertLevel": h.get("alertLevel", h.get("alert_level","low"))} for h in history]
            return {
                "status": "success",
                "data": {
                    "doughcon": doughcon,
                    "alertLevel": alert_level,
                    "avgWait": current.get("avgDeliveryWait", 0),
                    "storesOpen": len([s for s in current.get("stores", []) if s.get("isOpen")]),
                    "totalStores": len(current.get("stores", [])),
                    "graph": graph,
                    "timestamp": raw.get("timestamp", "")
                }
            }
    except Exception as e:
        print(f"[!] Pizza API error: {e}")

    return {"status": "error", "data": {"doughcon": None, "alertLevel": "unknown", "graph": []}}

@router.get("/ticker")
async def get_ticker_headlines():
    import feedparser
    
    FEEDS = [
        ("BBC",       "http://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Reuters",   "https://feeds.reuters.com/reuters/worldNews"),
        ("Al Jazeera","https://www.aljazeera.com/xml/rss/all.xml"),
        ("AP",        "https://feeds.apnews.com/rss/apf-topnews"),
    ]
    
    headlines = []
    for source, url in FEEDS:
        try:
            feed = await asyncio.to_thread(feedparser.parse, url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "#")
                if title:
                    headlines.append({"title": title, "source": source, "url": link})
        except Exception as e:
            print(f"[!] RSS error {source}: {e}")
    
    return {"status": "success", "data": headlines}




from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import aiofiles

app = FastAPI(title="ScayOSINT API", version="3.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration file
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from JSON file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "services": {
            "email_rep": {"api_key": "", "enabled": True},
            "haveibeenpwned": {"api_key": "", "enabled": True},
            "breach_directory": {"api_key": "", "enabled": True},
            "intelx": {"api_key": "", "enabled": True},
            "spotify": {"enabled": True},
            "twitter": {"enabled": True},
            "instagram": {"enabled": True}
        }
    }

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def email_rep_check(email: str, api_key: str) -> Dict[str, Any]:
    """Check email reputation via EmailRep.io"""
    try:
        if not api_key:
            return {"success": False, "error": "API key required", "data": {}}
        
        url = f"https://emailrep.io/{email}"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": {
                    "reputation": data.get("reputation", "unknown"),
                    "suspicious": data.get("suspicious", False),
                    "details": data
                }
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}", "data": {}}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def haveibeenpwned_check(email: str, api_key: str) -> Dict[str, Any]:
    """Check if email was in data breaches via HaveIBeenPwned"""
    try:
        if not api_key:
            return {"success": False, "error": "API key required", "data": {}}
        
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {
            "hibp-api-key": api_key,
            "user-agent": "ScayOSINT-3.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            breaches = response.json()
            return {
                "success": True,
                "data": {
                    "breaches": len(breaches),
                    "details": breaches
                }
            }
        elif response.status_code == 404:
            return {
                "success": True,
                "data": {
                    "breaches": 0,
                    "details": []
                }
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}", "data": {}}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def breach_directory_check(email: str, api_key: str) -> Dict[str, Any]:
    """Check breach directory for email"""
    try:
        if not api_key:
            return {"success": False, "error": "API key required", "data": {}}
        
        url = "https://breachdirectory.p.rapidapi.com/"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com"
        }
        params = {"func": "auto", "q": email}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": {
                    "found": data.get("found", False),
                    "details": data
                }
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}", "data": {}}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def intelx_check(email: str, api_key: str) -> Dict[str, Any]:
    """Search Intelligence X for email"""
    try:
        if not api_key:
            return {"success": False, "error": "API key required", "data": {}}
        
        url = "https://intelx.io/api/v1/search"
        headers = {"X-Key": api_key}
        params = {"term": email, "maxresults": 10}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": {
                    "results": data.get("results", []),
                    "total": data.get("total", 0)
                }
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}", "data": {}}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def spotify_check(email: str) -> Dict[str, Any]:
    """Check if email has Spotify account"""
    try:
        url = "https://spclient.wg.spotify.com/signup/public/v2/account/create"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        data = {"email": email, "password": "test123", "displayname": "test"}
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        # If we get a specific error about email already existing, it means the account exists
        if "email already exists" in response.text.lower():
            return {
                "success": True,
                "data": {
                    "exists": True,
                    "message": "Email has Spotify account"
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "exists": False,
                    "message": "Email not found on Spotify"
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def twitter_check(email: str) -> Dict[str, Any]:
    """Check if email has Twitter account"""
    try:
        url = "https://api.twitter.com/1.1/users/lookup.json"
        # This is a simplified check - Twitter API requires authentication
        # For demo purposes, we'll return a placeholder
        return {
            "success": True,
            "data": {
                "exists": "Unknown",
                "message": "Twitter check requires API authentication"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

def instagram_check(email: str) -> Dict[str, Any]:
    """Check if email has Instagram account"""
    try:
        url = "https://www.instagram.com/accounts/web_create_ajax/attempt/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        data = {"email": email}
        response = requests.post(url, data=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if "errors" in result and "email" in result["errors"]:
                return {
                    "success": True,
                    "data": {
                        "exists": True,
                        "message": "Email has Instagram account"
                    }
                }
            else:
                return {
                    "success": True,
                    "data": {
                        "exists": False,
                        "message": "Email not found on Instagram"
                    }
                }
        else:
            return {"success": False, "error": f"API error: {response.status_code}", "data": {}}
    except Exception as e:
        return {"success": False, "error": str(e), "data": {}}

@app.get("/")
async def read_root():
    """Serve the main HTML file"""
    try:
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
        if os.path.exists(frontend_path):
            return FileResponse(frontend_path)
        else:
            # Try relative path
            return FileResponse("../frontend/index.html")
    except FileNotFoundError:
        # Fallback to a simple HTML page if frontend files are not found
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ScayOSINT - Backend Running</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white; }
                .container { max-width: 600px; margin: 0 auto; }
                .status { background: #10b981; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
                .api-link { color: #6366f1; text-decoration: none; }
                .api-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🕵️‍♂️ ScayOSINT Backend</h1>
                <div class="status">
                    ✅ Backend server is running successfully!
                </div>
                <h2>API Endpoints:</h2>
                <p><a href="/api/config" class="api-link">GET /api/config</a> - Get configuration</p>
                <p><a href="/api/history" class="api-link">GET /api/history</a> - Get scan history</p>
                <p>POST /api/scan - Scan email (use with JSON body)</p>
                <p>POST /api/config - Update configuration (use with JSON body)</p>
                <h3>Frontend Status:</h3>
                <p>⚠️ Frontend files not found. Please ensure the frontend directory exists.</p>
                <p>You can still use the API endpoints directly.</p>
            </div>
        </body>
        </html>
        """)

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {"config": load_config()}

@app.post("/api/config")
async def update_config(config_data: Dict[str, Any]):
    """Update configuration"""
    try:
        save_config(config_data["config"])
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def scan_email(scan_data: Dict[str, Any]):
    """Scan email with selected services"""
    email = scan_data.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    config = load_config()
    results = {}
    
    # EmailRep check
    if config["services"]["email_rep"]["enabled"]:
        results["email_rep"] = email_rep_check(email, config["services"]["email_rep"]["api_key"])
    
    # HaveIBeenPwned check
    if config["services"]["haveibeenpwned"]["enabled"]:
        results["haveibeenpwned"] = haveibeenpwned_check(email, config["services"]["haveibeenpwned"]["api_key"])
    
    # BreachDirectory check
    if config["services"]["breach_directory"]["enabled"]:
        results["breach_directory"] = breach_directory_check(email, config["services"]["breach_directory"]["api_key"])
    
    # IntelX check
    if config["services"]["intelx"]["enabled"]:
        results["intelx"] = intelx_check(email, config["services"]["intelx"]["api_key"])
    
    # Spotify check
    if config["services"]["spotify"]["enabled"]:
        results["spotify"] = spotify_check(email)
    
    # Twitter check
    if config["services"]["twitter"]["enabled"]:
        results["twitter"] = twitter_check(email)
    
    # Instagram check
    if config["services"]["instagram"]["enabled"]:
        results["instagram"] = instagram_check(email)
    
    scan_result = {
        "email": email,
        "timestamp": datetime.now().isoformat(),
        "results": results
    }
    
    # Save to history
    try:
        history_file = os.path.join(os.path.dirname(__file__), "scan_history.json")
        async with aiofiles.open(history_file, "a") as f:
            await f.write(json.dumps(scan_result) + "\n")
    except Exception as e:
        print(f"Warning: Could not save to history: {e}")  # Log but don't fail
    
    return scan_result

@app.get("/api/history")
async def get_history():
    """Get scan history"""
    try:
        history = []
        history_file = os.path.join(os.path.dirname(__file__), "scan_history.json")
        if os.path.exists(history_file):
            async with aiofiles.open(history_file, "r") as f:
                content = await f.read()
                for line in content.strip().split("\n"):
                    if line.strip():
                        try:
                            history.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue  # Skip invalid JSON lines
        return history[-50:]  # Return last 50 scans
    except Exception as e:
        print(f"Error reading history: {e}")
        return []

# Try to mount static files if frontend directory exists
try:
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.exists(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
        print("✅ Frontend files mounted successfully")
    elif os.path.exists("../frontend"):
        app.mount("/static", StaticFiles(directory="../frontend"), name="static")
        print("✅ Frontend files mounted successfully (relative path)")
    else:
        print("⚠️ Frontend directory not found - serving API only")
except Exception as e:
    print(f"⚠️ Could not mount frontend files: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 
# chrome.py - Extract and decrypt Chrome cookies on Windows

import os
import sys
import shutil
import sqlite3
import platform

if platform.system() == "Windows":
    import win32crypt
elif platform.system() == "Darwin":
    # Placeholder: macOS Keychain decryption not implemented yet
    pass
else:
    raise NotImplementedError("Only Windows and macOS are supported for now.")
from pathlib import Path


def extract_cookies():
    cookies = []
    system = platform.system()

    if system == "Windows":
        local_app_data = os.getenv('LOCALAPPDATA')
        if not local_app_data:
            return cookies

        chrome_paths = [
            Path(local_app_data) / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cookies',
            Path(local_app_data) / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Network' / 'Cookies'
        ]
        chrome_path = next((p for p in chrome_paths if p.exists()), None)
        if not chrome_path:
            return cookies

        conn = sqlite3.connect(chrome_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT host_key, name, encrypted_value, creation_utc FROM cookies")
            for host, name, encrypted, creation_utc in cursor.fetchall():
                try:
                    decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode()
                except Exception:
                    decrypted = ''
                cookies.append({
                    'host': host,
                    'domain': host,
                    'name': name,
                    'value': decrypted,
                    'creation_utc': creation_utc if creation_utc is not None else 0
                })
        finally:
            cursor.close()
            conn.close()

    elif system == "Darwin":
        chrome_path = Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies"
        if not chrome_path.exists():
            print("[!] Chrome cookie DB not found on macOS.")
            return cookies

        conn = sqlite3.connect(str(chrome_path))
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT host_key, name FROM cookies")
            for host, name in cursor.fetchall():
                cookies.append({
                    'host': host,
                    'domain': host,
                    'name': name,
                    'value': "[encrypted]",
                    'creation_utc': 0
                })
        finally:
            cursor.close()
            conn.close()

    else:
        raise NotImplementedError("Only Windows and macOS are supported.")

    return cookies
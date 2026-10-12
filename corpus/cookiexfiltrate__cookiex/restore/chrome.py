import os
import platform
import sqlite3
import shutil
import tempfile
from datetime import datetime, timedelta

def get_chrome_cookie_path():
    system = platform.system()
    if system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
    elif system == "Windows":
        # Chrome 115+ moved cookies to Network/Cookies
        base_path = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Default")
        new_path = os.path.join(base_path, r"Network\Cookies")
        legacy_path = os.path.join(base_path, "Cookies")
        if os.path.exists(new_path):
            return new_path
        elif os.path.exists(legacy_path):
            return legacy_path
        else:
            raise FileNotFoundError("Neither legacy nor new Chrome cookie DB found on Windows.")
    else:
        raise Exception("Unsupported OS for Chrome cookie restoration")

def restore_chrome(cookie_data_list):
    print("[+] Restoring cookies to Chrome...")

    db_path = get_chrome_cookie_path()
    if not os.path.exists(db_path):
        print("[!] Chrome cookie DB not found.")
        return

    # Backup the existing cookie DB
    backup_path = db_path + ".bak"
    shutil.copy2(db_path, backup_path)
    print(f"[+] Backup saved to {backup_path}")

    # Write to a temp copy, then replace
    tmp_db_fd, tmp_db_path = tempfile.mkstemp()
    os.close(tmp_db_fd)
    shutil.copy2(db_path, tmp_db_path)

    conn = sqlite3.connect(tmp_db_path)
    cursor = conn.cursor()

    try:
        for cookie in cookie_data_list:
            try:
                name = cookie['name']
                value = cookie['value']
                domain = cookie['domain']
                path = cookie.get('path', '/')
                secure = cookie.get('secure', 0)
                expires = cookie.get('expires', 0)

                # Translate expires to Chrome format
                if expires == 0:
                    expires_utc = 9999999999
                else:
                    expires_utc = int(expires) * 1000000  # Chromium format

                cursor.execute("""
                    INSERT OR REPLACE INTO cookies (
                        host_key, name, value, path, creation_utc, expires_utc, is_secure,
                        is_httponly, last_access_utc, has_expires, is_persistent,
                        top_frame_site_key, encrypted_value, samesite, priority,
                        source_scheme, source_port, last_update_utc, source_type, has_cross_site_ancestor
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain,
                    name,
                    value,
                    path,
                    0,
                    expires_utc,
                    int(secure),
                    0,
                    int(datetime.utcnow().timestamp() * 1000000),
                    1,
                    1,
                    "",
                    b"",
                    cookie.get('samesite', -1),
                    cookie.get('priority', 1),
                    cookie.get('source_scheme', 0),
                    cookie.get('source_port', 0),
                    int(datetime.utcnow().timestamp() * 1000000),
                    cookie.get('source_type', 0),
                    cookie.get('has_cross_site_ancestor', 0)
                ))

            except Exception as inner_error:
                print(f"[!] Error restoring cookie {cookie.get('name', '')}: {inner_error}")

        conn.commit()
        conn.close()

        # Overwrite Chrome DB with modified one
        shutil.copy2(tmp_db_path, db_path)
        print("[+] Cookies restored successfully!")

    except Exception as e:
        print(f"[!] Failed to restore cookies: {e}")
    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)
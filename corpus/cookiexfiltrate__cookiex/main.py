# main.py - Entry point for CookieX

import os
import platform
import argparse
import getpass
from extract import chrome
from storage.vault import save_vault
from storage.vault import load_vault
from restore.chrome import restore_chrome


def banner():
    print("""
    ╔═══════════════════════════╗
    ║     🕵️  CookieX v0.1       ║
    ║  Cookie Extractor Utility ║
    ╚═══════════════════════════╝
    """)


def main():
    parser = argparse.ArgumentParser(description="CookieX - Cookie Extractor Utility")
    parser.add_argument('--browser', choices=['chrome'], default='chrome', help='Browser to extract cookies from')
    parser.add_argument('--output', help='Output encrypted vault file path')
    parser.add_argument('--decrypt', help='Path to encrypted vault to decrypt and inspect')
    parser.add_argument('--restore', help='Path to encrypted vault to restore cookies into browser')
    args = parser.parse_args()

    if args.decrypt:
        pw = getpass.getpass("[?] Enter passphrase to decrypt vault: ")
        vault = load_vault(args.decrypt, pw)
        print("\n[+] Vault Metadata:")
        print(f" - Hostname: {vault['hostname']}")
        print(f" - Timestamp: {vault['timestamp']}")
        print(f" - Cookies: {len(vault['cookies'])}")
        for cookie in vault['cookies'][:5]:
            print(f"   • {cookie['host']} | {cookie['name']} = {cookie['value'][:20]}...")
        return

    if args.restore:
        pw = getpass.getpass("[?] Enter passphrase to decrypt vault: ")
        vault = load_vault(args.restore, pw)
        restore_chrome(vault['cookies'])
        return

    banner()
    host = platform.node()
    print(f"[+] Running on: {host}")

    cookies = []

    if args.browser == 'chrome':
        cookies = chrome.extract_cookies()

    print(f"[+] Extracted {len(cookies)} cookies from {args.browser.capitalize()}")

    for cookie in cookies[:5]:
        print(f" - {cookie['host']} | {cookie['name']} = {cookie['value'][:10]}...")

    if args.output:
        pw = getpass.getpass("[?] Enter passphrase to encrypt vault: ")
        save_vault(cookies, args.output, pw)


if __name__ == "__main__":
    main()

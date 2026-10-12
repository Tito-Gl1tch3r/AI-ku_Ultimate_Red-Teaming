#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CyberLeaks v2.1 - Email Breach Checker (Menú interactivo + Apify & RapidAPI)

import os
import sys
import json
import time
import logging
import random
import string
import threading
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional

# Suprimir warnings antes de importar
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'
logging.getLogger().setLevel(logging.ERROR)

from dotenv import load_dotenv
from apify_client import ApifyClient
from colorama import init, Fore, Style
import requests

init(autoreset=True)

# ==============================
# CONFIGURACIÓN
# ==============================
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# ==============================
# BANNER & COLORES (DEGRADADO AZUL)
# ==============================
BANNER = r"""
 ▗▄▄▖▄   ▄ ▗▖   ▗▞▀▚▖ ▄▄▄     ▗▖▗▞▀▚▖▗▞▀▜▌█  ▄  ▄▄▄ 
▐▌   █   █ ▐▌   ▐▛▀▀▘█        ▐▌▐▛▀▀▘▝▚▄▟▌█▄▀  ▀▄▄  
▐▌    ▀▀▀█ ▐▛▀▚▖▝▚▄▄▖█        ▐▌▝▚▄▄▖     █ ▀▄ ▄▄▄▀ 
▝▚▄▄▖▄   █ ▐▙▄▞▘              ▐▙▄▄▖       █  █      
      ▀▀▀        
"""
GRADIENT = [
    Fore.LIGHTBLUE_EX,
    Fore.CYAN,
    Fore.BLUE,
    Fore.LIGHTCYAN_EX,
    Fore.CYAN,
    Fore.LIGHTBLUE_EX,
    Fore.BLUE,
]

def print_banner():
    lines = BANNER.strip('\n').split('\n')
    for i, line in enumerate(lines):
        print(GRADIENT[i % len(GRADIENT)] + line)
    print(f"\n{Fore.RED}{Style.BRIGHT}CyberLeaks - Email Breach Checker v2.1{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}☕ Donations: https://buymeacoffee.com/hackunderway{Style.RESET_ALL}\n")

# ==============================
# SPINNER / ALIVE PROGRESS
# ==============================
class Spinner:
    """Spinner animado en un hilo separado"""
    def __init__(self, message="⏳ Procesando", delay=0.1):
        self.message = message
        self.delay = delay
        self.running = False
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.thread = None

    def _spin(self):
        i = 0
        start_time = time.time()
        while self.running:
            elapsed = int(time.time() - start_time)
            char = self.spinner_chars[i % len(self.spinner_chars)]
            sys.stdout.write(f'\r{Fore.YELLOW}{char} {self.message}... ({elapsed}s){Fore.RESET}')
            sys.stdout.flush()
            i += 1
            time.sleep(self.delay)
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        sys.stdout.write(f'\r{Fore.GREEN}✅ {self.message} completado{Fore.RESET}\n')
        sys.stdout.flush()

# ==============================
# SUPPRESS OUTPUT (condicional)
# ==============================
class SuppressOutput:
    def __enter__(self):
        self.devnull = open(os.devnull, 'w')
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self.devnull
        sys.stderr = self.devnull
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.devnull.close()

# ==============================
# CONFIGURACIÓN DE API KEYS
# ==============================
def setup_api_keys():
    print(Fore.YELLOW + "🔑 Configuración de API Keys\n")
    print("Deja vacío y presiona Enter para omitir una clave.")
    apify = input("👉 Apify API Token (opcional, recomendado): ").strip()
    rapid = input("👉 RapidAPI Key (opcional): ").strip()
    with open(".env", "w") as f:
        if apify:
            f.write(f"APIFY_TOKEN={apify}\n")
        if rapid:
            f.write(f"RAPIDAPI_KEY={rapid}\n")
    print(Fore.GREEN + "✅ Keys guardadas en .env\n")
    return apify or rapid

# ==============================
# CONSULTA APIFY (Email Breach Checker)
# ==============================
def run_apify_email_check(emails: List[str]) -> List[Dict]:
    client = ApifyClient(APIFY_TOKEN)
    run_input = {"emails": emails}
    run = client.actor("lofomachines/email-breach-checker").call(run_input=run_input)
    items = list(client.dataset(run.default_dataset_id).iterate_items())
    return items

# ==============================
# CONSULTA RAPIDAPI (BreachDirectory)
# ==============================
def run_rapidapi_breach(term: str) -> Dict:
    url = "https://breachdirectory.p.rapidapi.com/"
    querystring = {"func": "auto", "term": term}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "breachdirectory.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    resp = requests.get(url, headers=headers, params=querystring, timeout=30)
    return resp.json()

# ==============================
# FORMATEO DE RESULTADOS (Apify)
# ==============================
def format_apify_item(item: Dict):
    email = item.get('email', 'N/A')
    status = item.get('status', 'N/A')
    breach_count = item.get('breachCount', 0)
    breach_names = item.get('breachNames', [])
    risk_label = item.get('riskLabel', 'N/A')
    risk_score = item.get('riskScore', 0)
    checked_at = item.get('checkedAt', 'N/A')

    print(f"\n{Fore.CYAN}{'='*60}{Fore.RESET}")
    print(f"{Fore.GREEN}📧 [APIFY] Email: {email}{Fore.RESET}")
    print(f"   Status    : {status}")
    print(f"   Breaches  : {breach_count}")
    if breach_names:
        print(f"   Sites     : {', '.join(breach_names[:20])}{'...' if len(breach_names) > 20 else ''}")
    print(f"   Risk Score: {risk_score} ({risk_label})")
    print(f"   Checked   : {checked_at}")
    print(f"{Fore.CYAN}{'='*60}{Fore.RESET}")

# ==============================
# FORMATEO DE RESULTADOS (RapidAPI)
# ==============================
def format_rapidapi_result(data: Dict):
    if not data or not data.get('success', False):
        print(f"\n{Fore.RED}[RAPIDAPI] La búsqueda no fue exitosa.{Style.RESET_ALL}")
        if data and 'error' in data:
            print(f"{Fore.RED}[RAPIDAPI] Mensaje de error: {data['error']}{Style.RESET_ALL}")
        return
    found = data.get('found', 0)
    result_list = data.get('result', [])
    print(f"\n{Fore.GREEN}✅ [RAPIDAPI] Búsqueda exitosa. Resultados encontrados: {found}{Style.RESET_ALL}\n")
    if not result_list:
        print(Fore.YELLOW + "[RAPIDAPI] No se encontraron resultados para este término.")
        return
    for idx, entry in enumerate(result_list[:5]): # Mostrar primeros 5
        email = entry.get('email', 'N/A')
        password = entry.get('password', None)
        sources = entry.get('sources', 'Unknown')
        print(f"{Fore.CYAN}─── [RAPIDAPI] Resultado #{idx} ───")
        print(f"{Fore.LIGHTBLUE_EX}Correo: {Fore.WHITE}{email}")
        if password:
            print(f"{Fore.YELLOW}Contraseña: {Fore.WHITE}{password}")
        else:
            print(f"{Fore.YELLOW}Contraseña: {Fore.RED}No disponible")
        print(f"{Fore.LIGHTBLUE_EX}Fuente(s): {Fore.WHITE}{sources}")
        print()

# ==============================
# GUARDAR REPORTES
# ==============================
def ensure_reports_folder():
    if not os.path.exists("reports"):
        os.makedirs("reports")

def generate_filename(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{ts}_{rand}"

def save_report(data: List[Dict], base_filename: str):
    json_path = os.path.join("reports", f"{base_filename}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    txt_path = os.path.join("reports", f"{base_filename}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("CyberLeaks Email Breach Report\n")
        f.write("="*60 + "\n")
        f.write(f"Total items: {len(data)}\n")
        f.write("="*60 + "\n\n")
        for idx, item in enumerate(data, 1):
            f.write(f"Item {idx}:\n")
            f.write(json.dumps(item, indent=2, ensure_ascii=False))
            f.write("\n\n" + "-"*40 + "\n\n")
    return json_path, txt_path

# ==============================
# MAIN (Menú interactivo)
# ==============================
def main():
    global APIFY_TOKEN, RAPIDAPI_KEY
    
    print_banner()
    print(f"{Fore.CYAN}⚠️  Uso exclusivo para investigaciones éticas y consultas autorizadas.{Style.RESET_ALL}")
    print()

    while True:
        print("Selecciona una opción:")
        print("1. Verificar un email")
        print("2. Verificar emails desde archivo (uno por línea)")
        print("3. Configurar API Keys (.env)")
        print("0. Salir")
        
        try:
            opcion = input(f"\n{Fore.WHITE}Opción (0-3): {Style.RESET_ALL}").strip()
        except KeyboardInterrupt:
            print("\nSaliendo...")
            sys.exit(0)

        if opcion == '0':
            print(f"{Fore.GREEN}¡Hasta luego!{Style.RESET_ALL}")
            break

        # Configurar API
        if opcion == '3':
            setup_api_keys()
            load_dotenv(override=True)
            APIFY_TOKEN = os.getenv("APIFY_TOKEN")
            RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
            print(Fore.GREEN + "✅ API keys configuradas.")
            continue

        # Obtener emails
        emails = []
        if opcion == '1':
            valor = input(f"{Fore.WHITE}Ingresa el email a verificar: {Style.RESET_ALL}").strip()
            if not valor:
                print(f"{Fore.RED}✖ El email no puede estar vacío.{Style.RESET_ALL}")
                continue
            emails.append(valor)
        elif opcion == '2':
            filepath = input(f"{Fore.WHITE}Ingresa la ruta del archivo (ej: emails.txt): {Style.RESET_ALL}").strip()
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    emails.extend([line.strip() for line in f if line.strip()])
                if not emails:
                    print(f"{Fore.RED}✖ El archivo no contiene emails.{Style.RESET_ALL}")
                    continue
            except FileNotFoundError:
                print(f"{Fore.RED}✖ Archivo no encontrado: {filepath}{Style.RESET_ALL}")
                continue
        else:
            print(f"{Fore.RED}✖ Opción inválida.{Style.RESET_ALL}")
            continue

        print(Fore.CYAN + f"\n[+] Emails a verificar: {len(emails)}")
        for e in emails:
            print(f"    {e}")

        results = []
        print()

        # Intentar Apify primero
        if APIFY_TOKEN:
            spinner = Spinner("⏳ Consultando Apify (lofomachines/email-breach-checker)")
            spinner.start()
            try:
                with SuppressOutput():
                    apify_results = run_apify_email_check(emails)
                for item in apify_results:
                    format_apify_item(item)
                    results.append(item)
            except Exception as e:
                print(Fore.YELLOW + f"\n⚠️ Apify falló: {e}")
            finally:
                spinner.stop()

        # Intentar RapidAPI después (aunque Apify funcione)
        if RAPIDAPI_KEY:
            spinner = Spinner("⏳ Consultando RapidAPI (BreachDirectory)")
            spinner.start()
            try:
                for email in emails:
                    with SuppressOutput():
                        data = run_rapidapi_breach(email)
                    format_rapidapi_result(data)
                    if data and data.get('success'):
                        results.append(data)
            except Exception as e:
                print(Fore.RED + f"\n❌ Error en RapidAPI: {e}")
            finally:
                spinner.stop()

        if not APIFY_TOKEN and not RAPIDAPI_KEY:
            print(Fore.RED + "❌ No hay API keys configuradas. Ejecuta opción 3 para configurar.")
            continue

        # Guardar reporte
        if results:
            ensure_reports_folder()
            base = generate_filename("report")
            json_path, txt_path = save_report(results, base)
            print(Fore.CYAN + f"\n📁 Reports saved:")
            print(f"   JSON: {json_path}")
            print(f"   TXT : {txt_path}")
        else:
            print(Fore.YELLOW + "No se obtuvieron resultados de ninguna fuente.")

        print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n⚠️ Interrumpido por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"❌ Error crítico: {e}")
        sys.exit(1)

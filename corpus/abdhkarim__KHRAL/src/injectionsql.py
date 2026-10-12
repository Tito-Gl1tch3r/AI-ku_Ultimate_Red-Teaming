import customtkinter as ctk
from tkinter import Text
import requests
import json
import urllib.parse
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
import tkinter.messagebox as messagebox
from shared import clear_container  # Import de la fonction pour effacer le conteneur


import json
import requests
import urllib.parse

class SQLInjectionTester:
    def __init__(self, url, db_type):
        """Initialisation de la classe avec l'URL cible et le type de base de données."""
        self.url = url
        self.db_type = db_type

    @staticmethod
    def load_payloads(file_path):
        """Charge les payloads SQL depuis un fichier JSON."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data.get("payloads", [])
        except FileNotFoundError:
            print(f"[!] Fichier non trouvé : {file_path}")
            return []
        except json.JSONDecodeError:
            print("[!] Erreur de formatage dans le fichier JSON.")
            return []

    @staticmethod
    def encode_sql_payload(payload):
        """Encode un payload SQL pour qu'il soit correctement transmis dans l'URL."""
        return urllib.parse.quote(payload)

    def test_injection(self, payload, description, cve):
        """
        Test d'injection SQL en envoyant un payload et en vérifiant les erreurs dans la réponse.
        """
        encoded_payload = self.encode_sql_payload(payload) if self.db_type == "sql" else payload
        test_url = f"{self.url}?id={encoded_payload}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            if self.db_type == "sql":
                error_keywords = ["sql syntax", "mysql", "syntax error", "unclosed quotation mark", "odbc"]
                detected = any(keyword in response.text.lower() for keyword in error_keywords)
            else:
                no_sql_keywords = ["mongodb", "no sql", "bson", "unrecognized"]
                detected = any(keyword in response.text.lower() for keyword in no_sql_keywords)

            if detected:
                return True, {"description": description, "cve": cve}
            else:
                return False, "Aucune vulnérabilité détectée"
        except requests.exceptions.RequestException as e:
            error_message = f"[!] Erreur lors de la requête HTTP : {str(e)}"
            print(error_message)
            return False, error_message


class VulnerabilityManager:
    def __init__(self, vuln_file="vulnerabilities.json"):
        self.vuln_file = vuln_file

    def save_vulnerability(self, data):
        """Enregistre une vulnérabilité dans un fichier JSON."""
        try:
            with open(self.vuln_file, "r", encoding="utf-8") as file:
                vulnerabilities = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            vulnerabilities = []

        vulnerabilities.append(data)

        with open(self.vuln_file, "w", encoding="utf-8") as file:
            json.dump(vulnerabilities, file, ensure_ascii=False, indent=4)

    def load_vulnerabilities(self):
        """Charge l'historique des vulnérabilités depuis le fichier JSON."""
        try:
            with open(self.vuln_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []


class SQLInjectionApp:
    def __init__(self, root):
        self.root = root
        self.vuln_manager = VulnerabilityManager()
        self.sql_tester = None

        # Nettoyage et initialisation de l'interface
        clear_container(self.root)
        self.create_widgets()

    def create_widgets(self):
        """
        Crée tous les widgets nécessaires pour l'application.
        """
        # Colonne pour l'historique
        self.vuln_list_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e", width=300)
        self.vuln_list_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.vuln_list_label = ctk.CTkLabel(
            self.vuln_list_frame, 
            text="Historique des vulnérabilités", 
            text_color="white", 
            font=("Helvetica", 16)
        )
        self.vuln_list_label.pack(pady=10)

        self.vuln_list = ctk.CTkTextbox(
            self.vuln_list_frame, 
            fg_color="#2e2e2e", 
            text_color="white", 
            font=("Helvetica", 14), 
            wrap="none", 
            state="disabled"
        )
        self.vuln_list.pack(fill="both", expand=True)

        # Zone principale
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#2e2e2e")
        self.main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Barre pour entrer l'URL
        self.url_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.url_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        self.url_label = ctk.CTkLabel(
            self.url_frame, 
            text="Entrez l'URL :", 
            text_color="white", 
            font=("Helvetica", 14)
        )
        self.url_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(self.url_frame, font=("Helvetica", 14), width=400)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Section pour les choix d'injection
        self.choices_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.choices_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        self.choices_label = ctk.CTkLabel(
            self.choices_frame, 
            text="Choisir un type d'injection (1-5) en défilant la liste ci-dessous :", 
            text_color="white", 
            font=("Helvetica", 14)
        )
        self.choices_label.pack(anchor="nw", padx=5, pady=5)

        self.choices_textbox = ctk.CTkTextbox(
            self.choices_frame, 
            fg_color="#1e1e1e", 
            text_color="white", 
            font=("Helvetica", 14), 
            height=5, 
            wrap="word", 
            state="normal"
        )
        self.choices_textbox.pack(fill="x", pady=5)
        self.choices_textbox.insert(
            "end",
            "1. In-band SQLi (Classic SQLi)\n"
            "2. Error-based SQLi\n"
            "3. Time-based SQLi\n"
            "4. Union-based SQLi (Blind SQLi)\n"
            "5. Auth bypass SQLi",
        )
        self.choices_textbox.configure(state="disabled")

        # Entrée pour le choix
        self.choice_entry = ctk.CTkEntry(
            self.choices_frame, font=("Helvetica", 14), width=100, placeholder_text="Ex: 1"
        )
        self.choice_entry.pack(anchor="nw", pady=5, padx=5)

        # Zone des résultats
        self.results_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.results_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.results_textbox = ctk.CTkTextbox(
            self.results_frame, 
            fg_color="#1e1e1e", 
            text_color="white", 
            font=("Courier", 12),  # Police de style monospace
            wrap="word", 
            state="normal"
        )
        self.results_textbox.pack(fill="both", pady=10, padx=20, expand=True)

        # Ajouter le contenu initial
        initial_message = r""" 
        ________  ________  ___                     ___  __    ___  ___     
        |\   ____\|\   __  \|\  \                   |\  \|\  \ |\  \|\  \    
        \ \  \___|\ \  \|\  \ \  \      ____________ \ \  \/  /|\ \  \\\  \   
        \ \_____  \ \  \\\  \ \  \    |\____________  \ \   ___  \ \   __  \  
        \|____|\  \ \  \\\  \ \  \___\|____________|  \ \  \\ \  \ \  \ \   \ 
            ____\_\  \ \_____  \ \_______\             \ \__\\ \__\ \__\ \__\
            |\_________\|___| \__\|_______|             \|__| \|__|\|__|\|__|
            \|_________|     \|__|                                                                            
                                                                     
        """
        self.results_textbox.insert("end", initial_message)
        self.results_textbox.configure(state="disabled")

        # Boutons en bas
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.bottom_frame.pack(side="bottom", fill="x", pady=10, padx=20)

        self.doc_button = ctk.CTkButton(
            self.bottom_frame, 
            text="Documentation", 
            command=self.open_documentation, 
            width=150, 
            height=40
        )
        self.doc_button.pack(side="left", padx=5)

        self.test_button = ctk.CTkButton(
            self.bottom_frame, 
            text="Tester", 
            command=self.start_testing, 
            fg_color="#4CAF50", 
            hover_color="#388E3C", 
            text_color="white", 
            corner_radius=10, 
            font=("Helvetica", 16), 
            height=40
        )
        self.test_button.pack(side="right", padx=5)

    def open_documentation(self):
        """
        Ouvre un lien vers la documentation sur les injections SQL.
        """
        webbrowser.open(
            "https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection"
        )

    def start_testing(self):
        """
        Démarre les tests d'injection SQL en fonction des options sélectionnées.
        """
        choice = self.choice_entry.get()
        try:
            choice = int(choice)
            if choice < 1 or choice > 5:
                raise ValueError
        except ValueError:
            self.display_result("[!] Choix invalide. Veuillez entrer un numéro entre 1 et 5.\n")
            return

        payload_files = {
            1: "src/payloads/SQLInj/inband_sql.json",
            2: "src/payloads/SQLInj/error_based.json",
            3: "src/payloads/SQLInj/time_based_sql.json",
            4: "src/payloads/SQLInj/union_based_sql.json",
            5: "src/payloads/SQLInj/authbypass.json",
        }

        payload_file = payload_files.get(choice)
        if not payload_file:
            self.display_result("[!] Type d'injection non trouvé.\n")
            return

        self.sql_tester = SQLInjectionTester(self.url_entry.get(), "sql")
        payloads = self.sql_tester.load_payloads(payload_file)
        if not payloads:
            self.display_result("[!] Aucun payload disponible pour ce type d'injection.\n")
            return

        for payload_data in payloads:
            payload = payload_data.get("payload")
            description = payload_data.get("description")
            cve = payload_data.get("cve")  # Ajout des CVE depuis les données JSON
            detected, result = self.sql_tester.test_injection(payload, description, cve)
            if detected:
                self.display_result(f"[!] Vulnérabilité détectée : {result['description']} (CVE : {result['cve']})\n")
            else:
                self.display_result("[-] Pas de vulnérabilité détectée.\n")

    def display_result(self, message):
        """
        Affiche un message dans la zone des résultats.
        """
        self.results_textbox.configure(state="normal")
        self.results_textbox.insert("end", message)
        self.results_textbox.configure(state="disabled")
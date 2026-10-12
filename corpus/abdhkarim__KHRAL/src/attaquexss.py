import customtkinter as ctk
from tkinter import Text
import requests
import json
import webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


class XSSApp:
    def __init__(self, container):
        """
        Initialise l'application XSSApp.
        """
        self.container = container
        self.payloads_file = "src/payloads/XSS/payloadXSS.txt"  # Fichier texte pour les payloads
        self.vuln_file = "vulnerabilities.json"
        self.create_widgets()

    def create_widgets(self):
        """
        Crée tous les widgets pour l'interface utilisateur de l'application XSSApp.
        """
        self.clear_container()

        # Colonne pour l'historique
        vuln_list_frame = ctk.CTkFrame(self.container, fg_color="#1e1e1e", width=300)
        vuln_list_frame.pack(side="left", fill="y", padx=10, pady=10)

        vuln_list_label = ctk.CTkLabel(vuln_list_frame, text="Historique des vulnérabilités", text_color="white", font=("Helvetica", 16))
        vuln_list_label.pack(pady=10)

        self.vuln_list = ctk.CTkTextbox(vuln_list_frame, fg_color="#2e2e2e", text_color="white", font=("Helvetica", 14), wrap="none", state="normal")
        self.vuln_list.pack(fill="both", expand=True)

        # Zone principale
        main_frame = ctk.CTkFrame(self.container, fg_color="#2e2e2e")
        main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Barre pour entrer l'URL
        url_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        url_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        url_label = ctk.CTkLabel(url_frame, text="Entrez l'URL :", text_color="white", font=("Helvetica", 14))
        url_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(url_frame, font=("Helvetica", 14), width=400)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Zone de résultats
        self.results_text = ctk.CTkTextbox(main_frame, fg_color="#1e1e1e", text_color="white", font=("Helvetica", 14), height=20, wrap="word", state="normal")
        self.results_text.pack(pady=10, padx=20, fill="both", expand=True)

        # Boutons en bas
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        bottom_frame.pack(side="bottom", fill="x", pady=10, padx=20)

        # Documentation bouton
        doc_button = ctk.CTkButton(bottom_frame, text="Documentation", command=self.open_documentation, width=150, height=40)
        doc_button.pack(side="left", padx=5)

        # Bouton pour lancer le test
        test_button = ctk.CTkButton(
            bottom_frame,
            text="Tester",
            command=self.test_xss,
            fg_color="#4CAF50",  # Vert
            hover_color="#388E3C",  # Vert plus foncé au survol
            text_color="white",
            corner_radius=10,
            font=("Helvetica", 16),
            height=40
        )
        test_button.pack(side="right", padx=5)

    def open_documentation(self):
        """
        Ouvre la documentation OWASP XSS dans le navigateur par défaut.
        """
        webbrowser.open("https://owasp.org/www-community/attacks/xss/")

    def load_payloads(self):
        """
        Charge les payloads XSS à partir d'un fichier texte.
        """
        try:
            with open(self.payloads_file, "r", encoding="utf-8") as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"Fichier introuvable : {self.payloads_file}")
            return []
        except Exception as e:
            print(f"Erreur lors du chargement des payloads : {e}")
            return []

    def save_vulnerability(self, data):
        """
        Enregistre une vulnérabilité dans un fichier JSON.
        """
        try:
            with open(self.vuln_file, "r", encoding="utf-8") as file:
                vulnerabilities = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            vulnerabilities = []

        vulnerabilities.append(data)

        with open(self.vuln_file, "w", encoding="utf-8") as file:
            json.dump(vulnerabilities, file, ensure_ascii=False, indent=4)

    def test_xss(self):
        """
        Teste les vulnérabilités XSS avec multithreading.
        """
        url = self.url_entry.get()
        payloads = self.load_payloads()

        if not payloads:
            self.results_text.configure(state="normal")
            self.results_text.insert("end", "Aucun payload disponible.\n")
            self.results_text.configure(state="disabled")
            return

        successful_tests = []

        def test_payload(payload):
            """Teste un payload XSS sur une URL."""
            test_url = f"{url}{payload}"
            try:
                response = requests.get(test_url, timeout=5)
                if payload in response.text:
                    return {
                        "url": url,
                        "payload": payload,
                        "description": "XSS trouvé",
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
            except requests.RequestException as e:
                return {"error": f"Erreur avec le payload {payload}: {str(e)}"}

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_payload = {executor.submit(test_payload, payload): payload for payload in payloads}

            for future in as_completed(future_to_payload):
                result = future.result()
                if isinstance(result, dict) and "error" not in result:
                    self.save_vulnerability(result)
                    successful_tests.append(result["payload"])
                    self.results_text.insert("end", f"Vulnérabilité trouvée : {result['payload']}\n")
                elif "error" in result:
                    self.results_text.insert("end", f"{result['error']}\n")

        if successful_tests:
            self.results_text.insert("end", f"\n{len(successful_tests)} vulnérabilité(s) détectée(s).\n")
        else:
            self.results_text.insert("end", "Aucune vulnérabilité détectée.\n")

        self.results_text.configure(state="disabled")

    def clear_container(self):
        """
        Efface tous les widgets contenus dans le conteneur de l'application.
        """
        for widget in self.container.winfo_children():
            widget.destroy()

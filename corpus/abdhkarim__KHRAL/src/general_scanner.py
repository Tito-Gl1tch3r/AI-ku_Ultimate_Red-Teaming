import customtkinter as ctk
import socket
import nmap
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox
from shared import clear_container

# Initialisation du thread pool pour exécuter le scan de manière asynchrone
executor = ThreadPoolExecutor()

class NmapScannerApp:
    def __init__(self, container):
        """
        Initialise l'application NmapScannerApp.

        Cette méthode configure l'application, initialise le conteneur de l'interface graphique et 
        prépare l'exécution des scans de manière asynchrone en utilisant un ThreadPoolExecutor.

        Paramètres :
        container (tkinter.Widget) : Le conteneur parent dans lequel les widgets de l'application seront ajoutés.
        """
        self.container = container
        self.executor = executor
        self.create_widgets()

    def create_widgets(self):
        """
        Crée tous les widgets pour la page de scan Nmap.

        Cette méthode définit l'interface utilisateur de l'application, y compris :
        - Une section pour entrer l'adresse cible (IP ou nom d'hôte).
        - Une section pour entrer la plage de ports à scanner.
        - Une zone pour afficher les résultats du scan.
        - Un bouton pour démarrer le scan Nmap.

        Elle configure également les boutons et les zones de saisie des informations de la cible et des ports.

        Aucun retour.
        """
        clear_container(self.container)

        # Conteneur principal
        self.main_frame = ctk.CTkFrame(self.container, fg_color="#2e2e2e")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Section pour entrer la cible
        self.target_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.target_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        self.target_label = ctk.CTkLabel(self.target_frame, text="Cible (IP ou Nom d'hôte) :", text_color="white", font=("Helvetica", 14))
        self.target_label.pack(side="left", padx=5)

        self.target_entry = ctk.CTkEntry(self.target_frame, font=("Helvetica", 14), width=400)
        self.target_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Section pour entrer la plage de ports
        self.ports_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.ports_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        self.ports_label = ctk.CTkLabel(self.ports_frame, text="Plage de ports (ex : 1-1024) :", text_color="white", font=("Helvetica", 14))
        self.ports_label.pack(side="left", padx=5)

        self.start_port_label = ctk.CTkLabel(self.ports_frame, text="Port de début :", text_color="white", font=("Helvetica", 12))
        self.start_port_label.pack(side="left", padx=5)

        self.start_port_entry = ctk.CTkEntry(self.ports_frame, font=("Helvetica", 14), width=100)
        self.start_port_entry.insert(0, "1")
        self.start_port_entry.pack(side="left", padx=5)

        self.end_port_label = ctk.CTkLabel(self.ports_frame, text="Port de fin :", text_color="white", font=("Helvetica", 12))
        self.end_port_label.pack(side="left", padx=5)

        self.end_port_entry = ctk.CTkEntry(self.ports_frame, font=("Helvetica", 14), width=100)
        self.end_port_entry.insert(0, "1024")
        self.end_port_entry.pack(side="left", padx=5)

        # Zone des résultats
        self.results_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.results_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.results_textbox = ctk.CTkTextbox(self.results_frame, fg_color="#1e1e1e", text_color="white", font=("Helvetica", 14), wrap="word")
        self.results_textbox.pack(fill="both", pady=10, padx=20, expand=True)

        # Zone du bouton
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e")
        self.button_frame.pack(side="bottom", fill="x", pady=10, padx=20)

        self.scan_button = ctk.CTkButton(self.button_frame, text="Scanner", command=self.start_nmap_scan, fg_color="#4CAF50", hover_color="#388E3C", text_color="white", corner_radius=10, font=("Helvetica", 16), height=40)
        self.scan_button.pack(side="right", padx=5)

    def validate_target(self, target):
        """
        Valide que la cible est une adresse IP ou un nom d'hôte valide.

        Cette méthode vérifie si l'adresse donnée est une adresse IP valide en utilisant 
        la bibliothèque ipaddress. Si ce n'est pas une adresse IP, elle essaie de résoudre 
        le nom d'hôte à l'aide de la bibliothèque socket.

        Paramètres :
        target (str) : L'adresse cible à valider (peut être une IP ou un nom d'hôte).

        Retours :
        bool : Retourne True si la cible est valide (IP ou nom d'hôte), False sinon.
        """
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            pass

        # Si ce n'est pas une adresse IP, essaie de résoudre le nom d'hôte
        try:
            socket.gethostbyname(target)
            return True
        except socket.gaierror:
            return False

    def validate_ports(self, start_port, end_port):
        """
        Valide que les ports sont dans les limites valides et dans un format correct.

        Cette méthode vérifie que les ports fournis sont des entiers et qu'ils sont compris 
        dans la plage valide de 1 à 65535, et que le port de départ est inférieur ou égal au port de fin.

        Paramètres :
        start_port (str) : Le port de départ à valider.
        end_port (str) : Le port de fin à valider.

        Retours :
        bool : Retourne True si les ports sont valides, False sinon.
        """
        try:
            start_port = int(start_port)
            end_port = int(end_port)
            if 1 <= start_port <= 65535 and 1 <= end_port <= 65535 and start_port <= end_port:
                return True
            else:
                return False
        except ValueError:
            return False

    def start_nmap_scan(self):
        """
        Lance un scan Nmap après avoir validé les entrées de l'utilisateur.

        Cette méthode récupère l'URL de la cible et la plage de ports spécifiés par l'utilisateur, 
        puis valide ces entrées. Si elles sont valides, elle désactive le bouton de scan et lance 
        le scan dans un thread séparé pour éviter de bloquer l'interface utilisateur.

        Aucun retour.
        """
        target = self.target_entry.get()
        start_port = self.start_port_entry.get()
        end_port = self.end_port_entry.get()

        # Valider la cible
        if not self.validate_target(target):
            self.update_results("[Erreur] Cible invalide. Veuillez entrer une adresse IP ou un nom d'hôte valide.\n")
            print("[Erreur] Cible invalide.")
            return

        # Valider les ports
        if not self.validate_ports(start_port, end_port):
            self.update_results("[Erreur] Plage de ports invalide. Assurez-vous que les ports sont entre 1 et 65535 et dans le bon format.\n")
            print("[Erreur] Plage de ports invalide.")
            return

        # Désactiver le bouton pendant le scan
        self.scan_button.configure(state="disabled")

        # Lancer le scan dans un thread séparé
        self.executor.submit(self.nmap_scan, target, start_port, end_port)

    def nmap_scan(self, target, start_port, end_port):
        """
        Effectue un scan de ports avec Nmap sur la cible spécifiée.

        Cette méthode utilise la bibliothèque nmap pour effectuer un scan de ports en utilisant les 
        paramètres de la cible et de la plage de ports fournis. Les résultats du scan sont formatés 
        et affichés dans l'interface utilisateur. Si une erreur se produit, un message d'erreur est 
        affiché.

        Paramètres :
        target (str) : L'adresse cible à scanner (IP ou nom d'hôte).
        start_port (str) : Le port de début de la plage de ports à scanner.
        end_port (str) : Le port de fin de la plage de ports à scanner.

        Aucun retour. Les résultats sont affichés dans l'interface utilisateur.
        """
        nm = nmap.PortScanner()
        results = []

        try:
            print(f"Début du scan pour {target} sur les ports {start_port}-{end_port}...")
            nm.scan(hosts=target, arguments=f'-p {start_port}-{end_port}')

            if nm.all_hosts():
                for host in nm.all_hosts():
                    for proto in nm[host].all_protocols():
                        lport = nm[host][proto].keys()
                        for port in sorted(lport):
                            state = nm[host][proto][port]['state']
                            results.append(f"Port {port} : {state.upper()}")
                            print(f"Port {port} : {state.upper()}")

            if not results:
                results.append("Aucun port ouvert trouvé.")
            results.insert(0, "Scan terminé.\n")
        except Exception as e:
            results.append(f"[Erreur] {str(e)}")
            print(f"[Erreur] {str(e)}")

        # Mettre à jour les résultats dans la zone de texte
        self.container.after(0, self.update_results, "\n".join(results))
        self.container.after(0, self.enable_scan_button)

    def update_results(self, message):
        """
        Met à jour la zone de texte avec le message fourni.

        Cette méthode efface tout texte existant dans la zone de texte des résultats et 
        insère le message spécifié, qui contient les résultats du scan ou les erreurs rencontrées.

        Paramètres :
        message (str) : Le message à afficher dans la zone de texte. Cela peut inclure les résultats 
                        du scan ou des messages d'erreur.

        Aucun retour.
        """
        self.results_textbox.delete("1.0", "end")  # Effacer le texte précédent
        self.results_textbox.insert("end", message)  # Ajouter le nouveau message

    def enable_scan_button(self):
        """
        Réactive le bouton de scan après la fin du scan.

        Cette méthode permet de réactiver le bouton de scan une fois que le processus de scan est terminé, 
        permettant à l'utilisateur de lancer un nouveau scan si nécessaire.

        Aucun paramètre et aucun retour.
        """
        self.scan_button.configure(state="normal")
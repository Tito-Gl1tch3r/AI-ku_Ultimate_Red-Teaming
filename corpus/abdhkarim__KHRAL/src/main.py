"""
main.py
=======
Application principale pour KHRAL, un outil interactif de sécurité informatique.

Ce module contient la classe principale `App`, qui gère l'interface utilisateur
et la navigation entre les différentes fonctionnalités.

Modules requis :
----------------
- tkinter
- customtkinter
- PIL (Pillow)
- os
- shared
- injectionsql
- attaquexss
- access_control
- general_scanner
- passwordgen
- bruteforce
- apropos

Classes :
---------
- App : Classe principale de l'application KHRAL.

Fonction principale :
---------------------
- Lance l'interface utilisateur et initialise les composants.
"""

from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
import os

# Import des pages spécifiques
from shared import navigate_to_page
from injectionsql import SQLInjectionApp
from attaquexss import XSSApp
from access_control import AccessControlApp
from general_scanner import NmapScannerApp
from bruteforce import BruteForcePage
from apropos import show_about_page

class App:
    """
        Classe principale de l'application KHRAL.

        Cette classe initialise et gère l'interface utilisateur graphique (GUI)
        et les interactions avec les différentes fonctionnalités.

        Attributs :
        -----------
        root : ctk.CTk
            La fenêtre principale de l'application.
        main_frame : ctk.CTkFrame
            Conteneur principal de l'application.
        menu_frame : ctk.CTkFrame
            Cadre pour le menu latéral.
        content_frame : ctk.CTkFrame
            Cadre pour afficher le contenu dynamique des pages.
        features : list
            Liste des fonctionnalités avec leurs titres et actions associées.
    """
    
    def __init__(self):
        """Initialise l'application et configure la fenêtre principale."""
        self.root = ctk.CTk()
        self.root.title("KHRAL")  # Titre de la fenêtre principale

        # Définir les dimensions et la position de la fenêtre
        window_width, window_height = 1200, 800
        x_position = (self.root.winfo_screenwidth() - window_width) // 2
        y_position = (self.root.winfo_screenheight() - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.configure(bg="#1e1e1e")  # Couleur de fond principale

        # Initialiser les différentes parties de l'interface
        self.create_top_frame()
        self.create_main_frame()
        self.show_default_page()

    def create_top_frame(self):
        """
        Crée la barre de titre et ajoute le logo de l'application.

        Vérifie si l'image du logo existe dans le dossier "assets"
        avant de l'afficher.
        """
        top_frame = ctk.CTkFrame(self.root, fg_color="#2e2e2e", height=80)
        top_frame.pack(fill="x", side="top")

        # Charger et afficher le logo
        assets_path = os.path.join(os.path.dirname(__file__), "assets")
        logo_path = os.path.join(assets_path, "kh-logo.png")
        if os.path.exists(logo_path):
            logo_image = Image.open(logo_path).resize((50, 50))
            logo_ctk = ctk.CTkImage(logo_image, size=(50, 50))
            logo_label = ctk.CTkLabel(top_frame, text="", image=logo_ctk)
            logo_label.pack(side="left", padx=20, pady=5)

    def create_main_frame(self):
        """
        Crée le cadre principal, incluant le menu latéral et
        la zone de contenu dynamique.

        Ajoute les boutons pour chaque fonctionnalité dans le menu
        et configure le bouton "Quitter".
        """
        # Cadre principal
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e")
        self.main_frame.pack(fill="both", expand=True)

        # Cadre pour le menu latéral
        self.menu_frame = ctk.CTkFrame(self.main_frame, fg_color="#2e2e2e", width=200)
        self.menu_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Cadre pour le contenu dynamique
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e")
        self.content_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        # Titre pour les vulnérabilités
        title_label = ctk.CTkLabel(
            self.menu_frame,
            text="Vulnérabilités",
            font=("Helvetica", 18, "bold"),
            text_color="white",
        )
        title_label.pack(pady=20)

        # Ajouter les boutons pour chaque fonctionnalité
        self.features = [
            ("Injection SQL", self.show_sql_page),
            ("Attaque XSS", self.show_xss_page),
            ("Contrôle des Autorisations", self.show_access_control_page),
            ("Attaque Brute Force", self.show_brute_force_page),
            ("Scanner des ports", self.show_nmap_page),
            ("À Propos", self.show_about_page),
        ]

        for title, function in self.features:
            button = ctk.CTkButton(
                self.menu_frame,
                text=title,
                command=lambda func=function: self.navigate_to_page(func),
                fg_color="#2e2e2e",
                hover_color="#3e3e3e",
                corner_radius=10,
                font=("Helvetica", 14),
                height=40
            )
            button.pack(pady=10, padx=10, fill="x")

        # Bouton pour quitter l'application
        quit_button = ctk.CTkButton(
            self.menu_frame,
            text="Quitter",
            command=self.quit_application,
            fg_color="#D32F2F",
            hover_color="#C62828",
            text_color="white",
            corner_radius=10,
            font=("Helvetica", 14),
            height=40
        )
        quit_button.pack(side="bottom", pady=10, padx=10)

    def show_default_page(self):
        """
        Affiche la page par défaut avec un message de bienvenue.

        Cette page contient des informations générales sur l'application
        et propose un bouton interactif pour en savoir plus.
        """
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        welcome_label = ctk.CTkLabel(
            self.content_frame,
            text="Bienvenue dans KHRAL",
            font=("Helvetica", 24, "bold"),
            text_color="white",
        )
        welcome_label.pack(pady=20)

        description_label = ctk.CTkLabel(
            self.content_frame,
            text=(
                "Choisissez une fonctionnalité dans le menu pour commencer.\n\n"
                "Fonctionnalités disponibles :\n"
                " - Tester les injections SQL\n"
                " - Analyser les failles XSS\n"
                " - Scanner des ports\n"
                " - Attaque Brute Force\n"
                " - Contrôle des Autorisations\n"
            ),
            font=("Helvetica", 16),
            text_color="lightgray",
            justify="left",
        )
        description_label.pack(pady=10)

    def navigate_to_page(self, page_function):
        """
        Navigue vers une page spécifique et affiche un message
        d'erreur en cas d'échec.

        Paramètres :
        ------------
        page_function : callable
            La fonction à appeler pour charger le contenu de la page.
        """
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        try:
            page_function(self.content_frame)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir la page : {e}")
            self.show_default_page()

    def quit_application(self):
        """
        Ferme proprement l'application.
        """
        self.root.quit()

    # Fonctions pour les pages spécifiques
    def show_sql_page(self, content_frame):
        """
        Charge la page dédiée à l'injection SQL.

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        SQLInjectionApp(content_frame)

    def show_xss_page(self, content_frame):
        """
        Charge la page dédiée aux attaques XSS.

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        XSSApp(content_frame)

    def show_access_control_page(self, content_frame):
        """
        Charge la page dédiée au contrôle des autorisations.

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        AccessControlApp(content_frame)

    def show_nmap_page(self, content_frame):
        """
        Charge la page dédiée au scanner de ports (Nmap).

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        NmapScannerApp(content_frame)

    def show_brute_force_page(self, content_frame):
        """
        Charge la page dédiée aux attaques par force brute.

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        BruteForcePage(content_frame)

    def show_about_page(self, content_frame):
        """
        Charge la page "À propos" pour afficher des informations
        sur les vulnérabilités et les outils.

        Paramètres :
        ------------
        content_frame : ctk.CTkFrame
            Cadre dans lequel charger le contenu de la page.
        """
        show_about_page(content_frame)


if __name__ == "__main__":
    app = App()
    app.root.mainloop()
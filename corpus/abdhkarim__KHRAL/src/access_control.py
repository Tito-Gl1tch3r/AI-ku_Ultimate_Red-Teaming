# src/access_control.py
import customtkinter as ctk
import requests
import webbrowser
from shared import navigate_to_page

class AccessControlApp:
    def __init__(self, container):
        """
        Initialise l'application avec le conteneur donné (frame principal) et crée les widgets.
        """
        self.container = container
        self.create_widgets()

    def create_widgets(self):
        """
        Crée tous les widgets pour la page de contrôle d'accès (Broken Access Control).
        """
        self.clear_container()

        # Colonne pour l'historique des vulnérabilités
        vuln_list_frame = ctk.CTkFrame(self.container, fg_color="#1e1e1e", width=300)
        vuln_list_frame.pack(side="left", fill="y", padx=10, pady=10)

        vuln_list_label = ctk.CTkLabel(vuln_list_frame, text="Historique des vulnérabilités", text_color="white", font=("Helvetica", 16))
        vuln_list_label.pack(pady=10)

        self.vuln_list = ctk.CTkTextbox(vuln_list_frame, fg_color="#2e2e2e", text_color="white", font=("Helvetica", 14), wrap="none", state="disabled")
        self.vuln_list.pack(fill="both", expand=True)

        # Zone principale pour l'URL et les tests
        main_frame = ctk.CTkFrame(self.container, fg_color="#2e2e2e")
        main_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Section pour entrer l'URL
        url_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        url_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        url_label = ctk.CTkLabel(url_frame, text="Entrez l'URL :", text_color="white", font=("Helvetica", 14))
        url_label.pack(side="left", padx=5)

        self.url_entry = ctk.CTkEntry(url_frame, font=("Helvetica", 14), width=400)
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Section pour choisir le type d'accès (horizontal, vertical, ou non authentifié)
        choices_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        choices_frame.pack(pady=5, padx=20, anchor="n", fill="x")

        choices_label = ctk.CTkLabel(
            choices_frame,
            text="Choisir un type d'accès (horizontal, vertical, ou non authentifié) en défilant la liste ci-dessous :",
            text_color="white",
            font=("Helvetica", 14),
        )
        choices_label.pack(anchor="nw", padx=5, pady=5)

        self.choices_textbox = ctk.CTkTextbox(
            choices_frame,
            fg_color="#1e1e1e",
            text_color="white",
            font=("Helvetica", 14),
            height=5,
            wrap="word",
            state="normal",
        )
        self.choices_textbox.pack(fill="x", pady=5)
        self.choices_textbox.insert(
            "end",
            "1. Accès Horizontal\n"
            "2. Accès Vertical\n"
            "3. Accès Non Authentifié",
        )
        self.choices_textbox.configure(state="disabled")

        self.choice_entry = ctk.CTkEntry(
            choices_frame,
            font=("Helvetica", 14),
            width=100,
            placeholder_text="Ex: 1",
        )
        self.choice_entry.pack(anchor="nw", pady=5, padx=5)

        # Zone des résultats
        results_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        results_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.results_textbox = ctk.CTkTextbox(
            results_frame,
            fg_color="#1e1e1e",
            text_color="white",
            font=("Helvetica", 14),
            wrap="word",
            state="normal",
        )
        self.results_textbox.pack(fill="both", pady=10, padx=20, expand=True)
        self.results_textbox.configure(state="disabled")

        # Boutons en bas
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="#2e2e2e")
        bottom_frame.pack(side="bottom", fill="x", pady=10, padx=20)

        # Documentation bouton
        def open_documentation():
            """
            Ouvre la documentation OWASP concernant le Broken Access Control.
            """
            webbrowser.open("https://owasp.org/Top10/A01_2021-Broken_Access_Control/")

        doc_button = ctk.CTkButton(bottom_frame, text="Documentation", command=open_documentation, width=150, height=40)
        doc_button.pack(side="left", padx=5)

        # Bouton pour lancer le test
        test_button = ctk.CTkButton(
            bottom_frame,
            text="Tester",
            command=self.run_test,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            text_color="white",
            corner_radius=10,
            font=("Helvetica", 16),
            height=40,
        )
        test_button.pack(side="right", padx=5)

    def run_test(self):
        """
        Lance le test en fonction du choix de l'utilisateur pour le type d'accès.
        """
        url = self.url_entry.get()
        choice = self.choice_entry.get()

        # Appel à la méthode d'affichage des résultats du test en fonction du choix
        self.display_access_control_choices(url, choice)

    def display_access_control_choices(self, url, choice):
        """
        Affiche les résultats du test d'accès en fonction du choix de l'utilisateur.
        """
        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("1.0", "end")
        
        try:
            if choice == "1":
                results = self.test_horizontal_access(url)
            elif choice == "2":
                results = self.test_vertical_access(url)
            elif choice == "3":
                results = self.test_unauthenticated_access(url)
            else:
                results = "Choix invalide. Veuillez entrer 1, 2 ou 3."

            # Affichage des résultats dans la textbox des résultats
            self.results_textbox.insert("end", results + "\n")
            self.vuln_list.insert("end", results + "\n")
        except Exception as e:
            self.results_textbox.insert("end", f"Erreur lors du test : {str(e)}\n")
        self.results_textbox.configure(state="disabled")

    def test_horizontal_access(self, url):
        """
        Teste l'accès horizontal (accès non autorisé à des ressources d'autres utilisateurs).
        """
        user_ids = [123, 124, 125, 126]
        session = requests.Session()  # Créer une session pour maintenir les cookies/headers entre les requêtes
        results = []

        # Se connecter avec un utilisateur normal pour générer une session authentifiée
        login_url = f"{url}/login"
        login_payload = {"username": "testuser", "password": "password123"}  # Exemple de login
        login_response = session.post(login_url, data=login_payload)
        if login_response.status_code != 200:
            results.append(f"Échec de la connexion (code {login_response.status_code})")
            return "\n".join(results)

        for user_id in user_ids:
            # Exemple d'URL avec un paramètre d'ID utilisateur
            test_url = f"{url}/{user_id}"
            response = session.get(test_url)

            if response.status_code == 200:
                # Analyse du contenu de la réponse pour vérifier l'accès aux informations sensibles
                if "account" in response.text.lower():  # Adaptable selon la page
                    results.append(f"Accès non autorisé pour l'ID {user_id}.")
                else:
                    results.append(f"Accès autorisé pour l'ID {user_id} (problème d'accès horizontal).")
            elif response.status_code == 403:
                results.append(f"Accès bloqué pour l'ID {user_id} (comportement attendu).")
            elif response.status_code == 404:
                results.append(f"Ressource non trouvée pour l'ID {user_id}.")
            else:
                results.append(f"Erreur lors de l'accès à l'ID {user_id} (code {response.status_code}).")

        return "\n".join(results)
    

    def test_vertical_access(self, url):
        """
        Teste l'accès vertical (accès à des ressources réservées aux administrateurs) avec 3 mécanismes d'authentification.
        """
        # Liste des pages réservées aux administrateurs
        admin_urls = [
            f"{url}/admin/dashboard",
            f"{url}/admin",
            f"{url}/dashboard",
            f"{url}/admin/tableofuser"
        ]
        
        session = requests.Session()
        results = []

        # --- 1. Test avec OAuth2 ---
        oauth2_login_url = f"{url}/login/oauth2"  # URL de login OAuth2
        oauth2_login_payload = {"username": "admin", "password": "adminpassword"}  # Remplacez par les bons identifiants
        oauth2_login_response = session.post(oauth2_login_url, data=oauth2_login_payload)
        
        if oauth2_login_response.status_code == 200:
            oauth2_token = oauth2_login_response.json().get("access_token")  # On suppose que l'OAuth2 renvoie un token
            oauth2_headers = {"Authorization": f"Bearer {oauth2_token}"}

            for admin_url in admin_urls:
                response = session.get(admin_url, headers=oauth2_headers)
                if response.status_code == 200:
                    results.append(f"(OAuth2) Accès autorisé à la page {admin_url}.")
                else:
                    results.append(f"(OAuth2) Erreur d'accès à la page {admin_url} (code {response.status_code}).")
        else:
            results.append(f"Échec de la connexion OAuth2 (code {oauth2_login_response.status_code})")

        # --- 2. Test avec JWT ---
        jwt_login_url = f"{url}/login/jwt"  # URL de login JWT
        jwt_login_payload = {"username": "admin", "password": "adminpassword"}  
        jwt_login_response = session.post(jwt_login_url, data=jwt_login_payload)
        
        if jwt_login_response.status_code == 200:
            jwt_token = jwt_login_response.json().get("token")  # On suppose que JWT renvoie un token
            jwt_headers = {"Authorization": f"Bearer {jwt_token}"}

            for admin_url in admin_urls:
                response = session.get(admin_url, headers=jwt_headers)
                if response.status_code == 200:
                    results.append(f"(JWT) Accès autorisé à la page {admin_url}.")
                else:
                    results.append(f"(JWT) Erreur d'accès à la page {admin_url} (code {response.status_code}).")
        else:
            results.append(f"Échec de la connexion JWT (code {jwt_login_response.status_code})")

        # --- 3. Test avec méthode classique (login avec formulaire) ---
        classic_login_url = f"{url}/login"  # URL de login classique
        classic_login_payload = {"username": "admin", "password": "adminpassword"}  # Identifiants classiques
        classic_login_response = session.post(classic_login_url, data=classic_login_payload)
        
        if classic_login_response.status_code == 200:
            for admin_url in admin_urls:
                response = session.get(admin_url)
                if response.status_code == 200:
                    results.append(f"(Classique) Accès autorisé à la page {admin_url}.")
                else:
                    results.append(f"(Classique) Erreur d'accès à la page {admin_url} (code {response.status_code}).")
        else:
            results.append(f"Échec de la connexion classique (code {classic_login_response.status_code})")

        return "\n".join(results)

        # Test d'accès à la page administrateur avec un utilisateur normal
        admin_token = self.get_admin_token(url)  # Exemple pour obtenir un token administrateur
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = session.get(admin_url, headers=headers)
        if response.status_code == 200:
            results.append("Accès non autorisé à la page admin (problème d'accès vertical).")
        elif response.status_code == 403:
            results.append("Accès bloqué pour la page admin (comportement attendu).")
        elif response.status_code == 401:
            results.append("Authentification nécessaire pour accéder à la page admin (comportement attendu).")
        else:
            results.append(f"Erreur d'accès à la page admin (code {response.status_code}).")

        return "\n".join(results)

    def get_admin_token(self, url):
        """
        Retourne un token JWT valide pour un administrateur.
        """
        admin_login_url = f"{url}/login"
        admin_payload = {"username": "adminuser", "password": "adminpassword123"}
        response = requests.post(admin_login_url, data=admin_payload)
        
        if response.status_code == 200:
            return response.json().get("token")  # Supposons que le token est renvoyé en JSON
        else:
            raise Exception("Échec de la connexion en tant qu'administrateur.")

    def test_unauthenticated_access(self, url):
        """
        Teste l'accès non authentifié (accès sans connexion).
        """
        test_url = f"{url}/profile"  # Exemple de page de profil qui nécessite une authentification
        results = []

        # Test sans authentification (sans cookies ou token)
        response = requests.get(test_url)
        if response.status_code == 200:
            results.append("Accès autorisé sans authentification (problème de sécurité).")
        elif response.status_code == 403:
            results.append("Accès bloqué sans authentification (comportement attendu).")
        elif response.status_code == 401:
            results.append("Authentification nécessaire pour accéder à la page (comportement attendu).")
        else:
            results.append(f"Erreur d'accès sans authentification (code {response.status_code}).")
        
        return "\n".join(results)

    def clear_container(self):
        """
        Efface tous les widgets du conteneur.
        """
        for widget in self.container.winfo_children():
            widget.destroy()
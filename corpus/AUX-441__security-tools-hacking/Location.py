import os.path
import requests
import time
from datetime import datetime
import random
import uuid

# Get Target [Country , City , Language , IPV4 , IPV4 , MAC , LTude,LTude , Others ... ] Location information
# 8/13/2025
# AUX-441



class Request_Location:
    def Location(self):
        try:
            url = "https://ident.me/json"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                time.sleep(random.randint(1, 3))

                folder = "full_informations"
                path = "location.txt"
                full = os.path.join(folder, path)

                if not os.path.exists(folder):
                    os.makedirs(folder)

                with open(full, "a", encoding="utf-8") as file:
                    file.write("=" * 40 + "\n")
                    file.write("Your information :\n")
                    file.write("=" * 40 + "\n")

                    for key, value in data.items():
                        file.write(f"{key.capitalize()}: {value}\n")

                    file.write("=" * 40 + "\n\n")

            else:
                print(f"Failed to Get information Error code : {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Connection Failed : {e}")
        except ValueError:
            print("Wrong Answer from JSON ...")

if __name__ == "__main__":
    C = Request_Location()
    C.Location()



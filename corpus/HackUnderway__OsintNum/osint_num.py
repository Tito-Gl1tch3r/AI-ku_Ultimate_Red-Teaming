#BY: HACK UNDERWAY

import requests
from tabulate import tabulate
import time
import sys

# API Key para el servicio de validación (debe ser proporcionada por el usuario)
API_KEY = "Your_API_Key"

def validate_number(phone_number):
    url = f"https://api.apilayer.com/number_verification/validate?number={phone_number}"
    
    headers = {
        "apikey": API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Verifica si hubo errores HTTP
        data = response.json()

        if data.get("valid"):
            return {
                "Número": data.get("number", "N/A"),
                "Formato Internacional": data.get("international_format", "N/A"),
                "País": data.get("country_name", "N/A"),
                "Código País": data.get("country_code", "N/A"),
                "Operador": data.get("carrier", "N/A"),
                "Tipo de Línea": data.get("line_type", "N/A"),
                "Válido": "Sí"
            }
        else:
            return {
                "Número": phone_number,
                "Válido": "No"
            }
    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP: {http_err}")
    except Exception as err:
        print(f"Error al procesar el número {phone_number}: {err}")

    return None

def validate_numbers_from_file(file_path):
    try:
        with open(file_path, "r") as file:
            numbers = file.readlines()
        
        results = []
        for number in numbers:
            number = number.strip()
            if number:
                print(f"Validando número: {number}")
                result = validate_number(number)
                if result:
                    results.append(result)
                time.sleep(1)  # Evitar problemas de límite de solicitudes a la API

        if results:
            print("\nResultados de la validación:")
            print(tabulate(results, headers="keys", tablefmt="grid"))

    except FileNotFoundError:
        print(f"El archivo {file_path} no fue encontrado.")
    except Exception as e:
        print(f"Error al procesar el archivo {file_path}: {e}")

if __name__ == "__main__":
    # Verifica si se está ejecutando el script con el archivo o número individual
    if len(sys.argv) == 2:
        input_data = sys.argv[1]

        if input_data == "-h":
            print("Uso del script:")
            print("  Validar un número: python osint_num.py <numero>")
            print("  Validar números desde archivo: python osint_num.py <archivo.txt>")
            print("\nOpciones:")
            print("  -h    Muestra este mensaje de ayuda.")
        elif input_data.endswith(".txt"):
            # Si es un archivo
            validate_numbers_from_file(input_data)
        else:
            # Si es un solo número
            result = validate_number(input_data)
            if result:
                print(tabulate([result], headers="keys", tablefmt="grid"))
    else:
        print("Uso del script:")
        print("  Validar un número: python osint_num.py <numero>")
        print("  Validar números desde archivo: python osint_num.py <archivo.txt>")

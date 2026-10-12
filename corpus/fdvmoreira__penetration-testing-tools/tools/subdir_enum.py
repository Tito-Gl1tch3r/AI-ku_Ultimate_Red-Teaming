#!/usr/bin/python3

"""
Subdir_Enum: Enumerate subdirectories of a website

Author: Flavio Moreira

"""

import argparse
import requests

parser = argparse.ArgumentParser(prog="SubdirEnum", description="Enumerate subdirectories", epilog="Best regards,\nFlavio Moreira")
parser.add_argument("--url","-u","--ip", required=True, type=str, help="Url or IP address")
parser.add_argument("--wordlist", "-w", required=True, type=str, help="Wordlist file")
parser.add_argument("--port", "-p", nargs="*", type=int, default=[80], help="Every port to enumerate the subdirectories")
parser.add_argument("--extension", "-x", type=str, choices=["html","php","phtm","asp","aspx"], help="remote file extension")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbosity")

# represents a subdirectory
class Subdirectory:
    pass

subdirectory = Subdirectory()
args = parser.parse_args(namespace=subdirectory)

# Enumerate subdirectories under every ports
for port in subdirectory.port:
    print(f"Starting enumeration on port {port}")

    FILE_OPEN_MODE = "r"
    
    url = subdirectory.url
    input_file = subdirectory.wordlist
    extension = "."+subdirectory.extension if subdirectory.extension else ""
    verbose = subdirectory.verbose


    # read the file
    content = None
    with open(input_file, FILE_OPEN_MODE) as file:
        content = file.read()
        content = content.splitlines()

    # send the requests
    if content:
        for dir in content:
            response = None
            # construct the full URL
            full_url = f"{url}:{port}/{dir}{extension}"

            try:
                if verbose:
                    print(f"Trying {full_url}")
                
                response = requests.get(full_url)
            except Exception as err:
                print(f"Error: {err}")
            else:
                if response.status_code in [200,301]:
                    print(f"Status={response.status_code}  Found /{dir}\nURL --> {full_url}")
                else:
                    if verbose:
                        print(f"Status={response.status_code} Not found")
                    



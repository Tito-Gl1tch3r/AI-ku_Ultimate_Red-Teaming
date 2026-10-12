#!/usr/bin/python3

"""
Downloader
Download any file from the internet
"""

import pyfiglet, argparse, requests

# banner
banner = pyfiglet.figlet_format(f"Downloader")
print(banner)

# setup argument list
parser = argparse.ArgumentParser(prog="Downloader", description="Download any file from the internet", epilog="By Flavio Moreira")
parser.add_argument("--url", "-u", type=str, required=True, help="URL to the file to download")
parser.add_argument("--output", "-o", type=str, help="Name of the file to save")
parser.add_argument("--output-binary", action="store_true", default=False, help="Save file as binary")

# Downloader construct
class Downloader:
    pass

downloader = Downloader()
parser.parse_args(namespace=downloader)

url = downloader.url
output = downloader.output
binary_mode = "b" if downloader.output_binary else ""

# Download the file
print(f"Fetching {url} ...")
response = requests.request(method="GET", url=url, allow_redirects=True, stream=True)

if response.ok and response.status_code == 200:
    # save content in the file
    try:
        with open(output,"w"+binary_mode) as file:
            print(f"Saving {output} ... ", end="")
            bytes_written = file.write((response.content).decode())

            if bytes_written > 0:
                print(f"Content Saved!")

    except UnicodeDecodeError as uderr:
        # If the decoding throws an exception it is probably a binary file that was downloaded
        # Try to save the content as binary
        with open(output, "wb") as file:
            print(f"\rSaving {output} ... ")
            bytes_written = file.write(response.content)
            print(f"[{bytes_written}] bytes saved.")

    except Exception as err:
        print(f"Something went wrong while saving the file!\n{err}")

else:
    print(f"Download has failed!")


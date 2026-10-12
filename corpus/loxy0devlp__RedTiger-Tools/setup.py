# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import subprocess
import shutil
import argparse
import sys

ERROR = "[x]"
INPUT = "[>]"
INFO  = "[!]"

def IsPath(path): return shutil.which(path) is not None

def CheckPath():
    path_python = IsPath("python") or IsPath("python3")
    path_pip    = IsPath("pip") or IsPath("pip3")

    if not path_python:
        print(f"{ERROR} Python is not in your path. Please install it or fix your path..")
        return False
    elif not path_pip:
        print(f"{ERROR} Pip is not in your path. Please install it or fix your path.")
        return False
    else: 
        print(f"{INFO} Python and pip are correctly in your path.")
        return True

def InstallDependencies():
    print(f"{INFO} Installing the Python dependencies required for the RedTiger-Tools:")
    try: subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--break-system-packages"], check=True)
    except: 
        try: subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        except: pass
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"], check=True)
    
def Choice(mode):
    if mode.lower().strip() in ("1", "01", "enable"):    version = "enable"
    elif mode.lower().strip() in ("2", "02", "disable"): version = "disable"
    else: 
        version = None
        print(f"{ERROR} Invalid choice.")
    return version

def InterfaceConfiguration(SettingsUpdate, version_decorated, version_interface):
    if not version_decorated or not version_interface: print(f"\n{INFO} Interface configuration:")

    if not version_decorated:
        while True:
            print(f"""
  [01] Enable decorative output (recommended)
  [02] Disable decorative output
        """)
            version_decorated = Choice(input(f"{INPUT} Select decorative output mode -> "))
            if version_decorated: break
            else: continue

    if not version_interface:
        while True:
            print(f"""
  [01] Enable interactive command-line interface (recommended)
  [02] Disable interactive command-line interface
        """)
            version_interface = Choice(input(f"{INPUT} Select interactive CLI mode -> "))
            if version_interface: break
            else: continue

    if version_decorated in ["enable", "disable"]: SettingsUpdate(mode="decorated", status=version_decorated, setup=True)
    if version_interface in ["enable", "disable"]: SettingsUpdate(mode="interface", status=version_interface, setup=True)
    print(f"{INFO} The configuration has been saved.")

def Setup(version_decorated, version_interface):
    print("RedTiger-Tools setup.\n")
    if CheckPath(): 
        InstallDependencies()
        try:
            from Program.TSettingsUpdate import SettingsUpdate
            InterfaceConfiguration(SettingsUpdate, version_decorated, version_interface)
            print(f"{INFO} Setup was completed successfully.")
        except ModuleNotFoundError as e: 
            print(f"{ERROR} The modules were not installed correctly: {e}")
            return
        except Exception as e:
            print(f"{ERROR} Error: {e}")
            return
    else: return

parser = argparse.ArgumentParser(description="RedTiger-Tools setup")
parser.add_argument("-d", "--decorated", choices=["enable", "disable"], help="Enable or disable the tool's decorative output: enable (recommended) / disable")
parser.add_argument("-i", "--interface", choices=["enable", "disable"], help="Enable or disable the tool's interactive command-line interface: enable (recommended) / disable")

args              = parser.parse_args()
version_decorated = args.decorated
version_interface = args.interface

Setup(version_decorated, version_interface)
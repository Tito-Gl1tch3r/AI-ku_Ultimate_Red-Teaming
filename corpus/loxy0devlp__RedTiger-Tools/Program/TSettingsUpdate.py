# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def SettingsUpdate(mode=None, status=None, setup=None):
    def Stats(version_interface, version_decorated):
        print(f"""
  {BEFORE}01{AFTER} Decorative output (status: {white + version_decorated + red})
  {BEFORE}02{AFTER} Interactive command-line interface (status: {white + version_interface + red})
        """)

    def Update(data, version_decorated=None, version_interface=None):
        if version_decorated != None: data["version_decorated"] = str(version_decorated)
        if version_interface != None: data["version_interface"] = str(version_interface)
        else: return
        with open(path_file_version_settings, "w", encoding="utf-8") as file: json.dump(data, file, indent=4)

    mode_decorated, mode_interface = None, None
    if mode == "decorated": mode_decorated = status
    elif mode == "interface": mode_interface = status

    with open(path_file_version_settings, "r", encoding="utf-8") as file: data = json.load(file)

    version_decorated = data["version_decorated"]
    version_interface = data["version_interface"]
    
    if not mode:
        Stats(version_interface, version_decorated)
        choice_mode = Input(f"Select a mode -> ").lower().strip()
        if choice_mode in ("1", "01"):
            if not mode_decorated:
                print(f"""
  {BEFORE}01{AFTER} Enable decorative output (recommended)
  {BEFORE}02{AFTER} Disable decorative output{reset}
                """)
                mode_decorated = Input("Select decorative output mode -> ")
        elif choice_mode in ("2", "02"):
            if not mode_interface:
                print(f"""
  {BEFORE}01{AFTER} Enable interactive command-line interface (recommended)
  {BEFORE}02{AFTER} Disable interactive command-line interface{reset}
                """)
                mode_interface = Input("Select interactive CLI mode -> ")
        else: ErrorChoice()

    if mode_decorated:
        if mode_decorated.lower().strip() in ("1", "01", "enable"):    version_decorated = True
        elif mode_decorated.lower().strip() in ("2", "02", "disable"): version_decorated = False
        else: ErrorChoice()

    if mode_interface:
        if mode_interface.lower().strip() in ("1", "01", "enable"):    version_interface = True
        elif mode_interface.lower().strip() in ("2", "02", "disable"): version_interface = False
        else: ErrorChoice()
    
    Update(data, version_decorated, version_interface)
    if not setup:
        Info("Restart to apply the changes.")
        Continue()
        Reset()
    
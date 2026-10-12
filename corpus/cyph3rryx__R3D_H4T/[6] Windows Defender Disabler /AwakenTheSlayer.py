import _winreg
import os
import sys
import ctypes
from ctypes import wintypes

def is_user_admin():
    user = ctypes.windll.advapi32.GetUserNameW(wintypes.LPWSTR(ctypes.create_unicode_buffer(256))).value.decode('utf-16')
    p = ctypes.windll.shell32.ShellExecuteW(None, None, 'cmd.exe', '/c net localgroup administrators "{}"'.format(user), None, 1)
    if p == 0:
        return False
    else:
        return True

def enable_defender_settings():
    if is_user_admin():
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Policies\Microsoft\Windows Defender', 0, _winreg.KEY_ALL_ACCESS)
        if key:
            _winreg.SetValueEx(key, "DisableAntiSpyware", 0, _winreg.REG_DWORD, 0)
            _winreg.DeleteKey(key, "Real-Time Protection")
            _winreg.CloseKey(key)
            print("Hahaha...you are protected again by MacroHard!!")
            print("Lol! Just re-start it already")
            getchar()
            return 0
        else:
            print("Key? Where is the key? Oh so you are not an Admin??? Hell no man!!")
            return
    else:
        print("Be a Doom Slayer of your system and become Admin, then run the script")
        return -1

if __name__ == '__main__':
    result = enable_defender_settings()
    sys.exit(result)

#!/usr/bin/python3
#
# Bluetooth AVRCP Media Controller DBUS Service
#

from __future__ import absolute_import, print_function
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import socket
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
import bluetooth
from bluetooth import *
import subprocess

logging.basicConfig(level=logging.DEBUG)

class BTMediaDevice:
    # Define constants for AVRCP
    P_CONTROL = 23  # PSM for AVCTP Control Channel
    SDP_RECORD_PATH = sys.path[0] + "/sdp_record_avrcp.xml"
    UUID = subprocess.getoutput("bluetoothctl show | awk '/Generic Attribute Profile/' | awk -F'[()]' '{print $2}'") or "0000110e-0000-1000-8000-00805f9b34fb"

    def __init__(self, bt_name, if_name):
        print("2. Setting up BT device")
        self.bt_name = bt_name
        self.if_name = if_name
        self.MY_ADDRESS = if_addr
        self.if_class = if_class
        self.init_bt_device()
        self.init_bluez_profile()

    def init_bt_device(self):
        print("3. Configuring Device name: " + self.bt_name)
        # Ensure Bluetooth service is properly configured
        with open('/etc/init.d/bluetooth') as f:
            if 'NOPLUGIN_OPTION=""' in f.read():
                print('** Fixing bluetooth service patch and restarting... **')
                os.system("sed -i '/NOPLUGIN_OPTION=\"\"/d' /etc/init.d/bluetooth && service bluetooth restart")
        # Set device class to Audio/Video (Remote Control)
        os.system("hciconfig " + self.if_name + " up")
        os.system("hciconfig " + self.if_name + " name \"" + self.bt_name + "\"")
        os.system("hciconfig " + self.if_name + " class " + self.if_class)
        os.system("hciconfig " + self.if_name + " piscan")  # Make discoverable

    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        manager.RegisterProfile("/org/bluez/" + self.if_name, BTMediaDevice.UUID, opts)
        print("6. Profile registered")

    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            with open(BTMediaDevice.SDP_RECORD_PATH, "r") as fh:
                return fh.read()
        except:
            sys.exit("Could not open the sdp record. Exiting...")

    def listen(self):
        print("\033[0;33m7. Waiting for connections\033[0m")
        self.scontrol = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CONTROL))
        self.scontrol.listen(5)
        self.ccontrol, cinfo = self.scontrol.accept()
        print("\033[0;32mGot a connection on the control channel from %s\033[0m" % cinfo[0])

    def send_avrcp_command(self, command):
        # AVRCP commands (Pass-through commands, as per AVRCP 1.3)
        commands = {
            "play": b"\x44\x00",  # Play
            "pause": b"\x46\x00",  # Pause
            "next": b"\x4B\x00",  # Next Track
            "volume_up": b"\x41\x00",  # Volume Up
            "volume_down": b"\x42\x00"  # Volume Down
        }
        if command not in commands:
            print(f"Unknown command: {command}")
            return
        try:
            self.ccontrol.send(commands[command])
            print(f"Sent AVRCP command: {command}")
        except OSError as err:
            print(f"Error sending command: {err}")

class BTMediaService(dbus.service.Object):
    def __init__(self, bt_name, if_name):
        print("1. Setting up service")
        bus_name = dbus.service.BusName("org.thanhle.btmediaservice", bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, "/org/thanhle/btmediaservice")
        self.device = BTMediaDevice(bt_name, if_name)
        self.device.listen()

    @dbus.service.method('org.thanhle.btmediaservice', in_signature='s')
    def send_media_command(self, command):
        print(f"Received media command: {command}")
        self.device.send_avrcp_command(command)

if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("[!] Run as root")

    MY_DEV_NAME = "Media Controller"
    bt_name = MY_DEV_NAME
    if_name = 'hci0'
    sopts = 'hn:i:c:a'
    if_class = '0x40010C'  # Audio/Video, Remote Control
    if_addr = '22:22:EA:CF:3C:1E'
    opts, args = getopt.getopt(sys.argv[1:], sopts)

    for opt, arg in opts:
        if opt == '-h':
            print(f'\nUsage:\n\tpython {sys.argv[0]} -n [BT_NAME] -i [INTERFACE] -c [CLASS] -a [ADDRESS]\n\n\tDefault Values:\n\t\tBT_NAME:\t{bt_name}\n\t\tINTERFACE:\t{if_name}\n\t\tCLASS:\t{if_class}\n\t\tADDRESS:\t{if_addr}')
            sys.exit()
        elif opt == '-n':
            bt_name = arg
        elif opt == '-i':
            if_name = arg
        elif opt == '-c':
            if_class = arg
        elif opt == '-a':
            if_addr = arg

    try:
        DBusGMainLoop(set_as_default=True)
        myservice = BTMediaService(bt_name, if_name)
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        sys.exit()

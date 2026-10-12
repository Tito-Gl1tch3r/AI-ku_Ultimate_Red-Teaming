# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def IpPinger(target=None, mode=None, bytes=None, port=None, interval=None, socket_timeout=None, socket_proxy=None):
    Title("Ip Pinger")

    if not target: target = Input("Target [-t] -> ")
    detect_target = DetectTarget(target)

    if not detect_target in ["ip"]: ErrorIp()
    elif any(bad in target for bad in blacklists): ErrorTarget()

    ip, port_default, json_format = TargetGetIp(target, detect_target)
    if not ip: ErrorTarget()

    if not mode:
        print(f"""
  {BEFORE}01{AFTER + white} ICMP
  {BEFORE}02{AFTER + white} TCP
        """)
        mode = Input("Ping mode [-m] -> ")

    if mode.strip().lower() in ("1", "01", "icmp"): 
        if not has_cli_args: 
            interval = Input(f"Interval [-i] (default: {str(default_interval)}) -> ")
            bytes    = Input(f"Bytes [-b] (default: {str(default_bytes)}) -> ")
        
        try:
            if not interval: interval = default_interval
            else: interval = float(interval)
            Info(f"Interval: {white}{str(interval)}s")
        except (ValueError, TypeError): ErrorInterval()

        try:
            if not bytes: bytes = default_bytes
            elif int(bytes) > max_bytes: ErrorBytes()
            Info(f"Bytes: {white}{str(bytes)}")
        except (ValueError, TypeError): ErrorBytes()

        IpGetPingAndLatency(ip, interval=interval, status="ICMP", bytes=bytes, loop=True, log=False)

    if mode.strip().lower() in ("2", "02", "tcp"): 
        if not has_cli_args: 
            socket_timeout = Input(f"Max socket timeout [-ST] (default: {str(default_socket_timeout)}) -> ")
            socket_proxy   = Input(f"Socket proxy [-SP] (default: {str(default_socket_proxy)}) -> ")
            interval       = Input(f"Interval [-i] (default: {str(default_interval)}) -> ")
            port           = Input(f"Port [-p] (default: {str(default_port)}) -> ")

        if not socket_proxy: socket_proxy = default_socket_proxy
        
        try:
            if not socket_timeout: socket_timeout = default_socket_timeout
            else: socket_timeout = float(socket_timeout)
            Info(f"Max socket timeout: {white}{str(socket_timeout)}s")
        except (ValueError, TypeError): ErrorTimeout()

        try:
            if not interval: interval = default_interval
            else: interval = float(interval)
            Info(f"Interval: {white}{str(interval)}s")
        except (ValueError, TypeError): ErrorInterval()

        try:
            if not port: port = default_port
            elif int(port) > max_port: ErrorPort()
            Info(f"port: {white}{str(port)}")
        except (ValueError, TypeError): ErrorPort()

        EnableSocketProxy(socket_proxy=socket_proxy, socket_timeout=socket_timeout)
        IpGetPingAndLatency(ip, socket_timeout=socket_timeout, interval=interval, status="TCP", port=port, loop=True, log=False)
    else: ErrorMode()
    Continue()
    Reset()
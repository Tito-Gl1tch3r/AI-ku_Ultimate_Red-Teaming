import sys
import os
import signal
import subprocess
import threading
import asyncio
from src.utils import run_command
import cmd.env as env
import src.network.intercept as Intercept
import src.ai.llm as AI
import src.ai.analyze_network as AnalyzeNetwork
import src.macos.proxy as MacProxy
import src.macos.watch_proxy as MacWatchproxy
import src.macos.plist as MacStartup
import src.macos.certificate as MacCertificate
import src.adapter as Adapter

# Create a global variable to control the thread
stop_event = threading.Event()

def cleanup(proxy):
    print("Stop intercept ...")
    proxy.configure_proxy(False)
    print("Intercept Complete.")

def kill_process_on_port():
    try:
        # Get the list of processes using the specified port
        result = subprocess.run(
            ["lsof", "-t", f"-i:{env.ENV_PORT_LISTEN}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        pids = result.stdout.strip().splitlines()

        if pids:
            for pid in pids:
                print(f"Killing process with PID: {pid} on port {env.ENV_PORT_LISTEN}")
                run_command(["kill", "-9", pid])
        else:
            print(f"No process found on port {env.ENV_PORT_LISTEN}.")
    except subprocess.CalledProcessError as e:
        print(f"Error checking for processes on port {env.ENV_PORT_LISTEN}: {e.stderr}")

def signal_handler(proxy):
    def handler(signum, frame):
        print('Received shutdown signal. Cleaning up...')
        # Perform any cleanup actions here
        cleanup(proxy)
        sys.exit(0)

    return handler

def main():

    if len(sys.argv) == 1:
        print("Usage:")
        print("SecretAgent [OPTIONS]")
        print("")
        print("Options:")
        print("  --intercept-on         Run Intercept immediately")
        print("  --intercept-off        Stop Intercept agent")
        print("  --startup              Register startup agent to run intercept at startup")
        print("  --remove-startup       Remove agent at startup")
        print("  --add-certificate      Install SSL certificate")
        print("  --remove-certificate   uninstall SSL certificate")
        print("  --analyze-ai           Run AI analyzer from network.log file")
        print("")
        sys.exit(0)

    # init mac function adapter
    macProxy = MacProxy.Proxy(env)
    macWatchproxy = MacWatchproxy.WatchProxy(env, macProxy)
    macCertificate = MacCertificate.Certificate(env)
    macStartup = MacStartup.Startup(env)

    # the favorite adapter pattern to rewrite the config
    if "--macos" in sys.argv:
        proxy = Adapter.Adapter(macProxy)
        watchproxy = Adapter.Adapter(macWatchproxy)
        certificate = Adapter.Adapter(macCertificate)
        startup = Adapter.Adapter(macStartup)
    else: 
        # default proxy adapter is macos
        proxy = Adapter.Adapter(macProxy)
        watchproxy = Adapter.Adapter(macWatchproxy)
        certificate = Adapter.Adapter(macCertificate)
        startup = Adapter.Adapter(macStartup)

    # Register the signal handler for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler(proxy))
    signal.signal(signal.SIGTERM, signal_handler(proxy))

    if "--startup" in sys.argv:
        startup.write_launch_agent()

        print("Startup registration complete. Proxy will run continuously at startup.")
    
    if "--remove-startup" in sys.argv:
        startup.unload_and_remove_launch_agent()

        print("Remove from Startup complete.")

    if "--add-certificate" in sys.argv:
        certificate.install_cert_to_keychain()

        print("Certificate added")

    if "--remove-certificate" in sys.argv:
        certificate.remove_cert_from_keychain()

        print("Certificate removed")

    if "--analyze-ai" in sys.argv:
        # setup AI 
        ai = AI.AI(env)
        
        analyze_network = AnalyzeNetwork.AnalyzeNetwork(env, ai)
        watcher_thread = threading.Thread(target=analyze_network.analyze_network, args=(os.path.join(f"{env.ENV_CURR_PROJECT_DIR}", "network.log"), os.path.join(f"{env.ENV_CURR_PROJECT_DIR}", "network-analyze.log"), 10))
        
        watcher_thread.daemon = True  # This makes the thread exit when the main program exits
        watcher_thread.start()  # Start the thread

        # Signal the watcher thread to stop
        stop_event.set()
        print("Be patient while AI analyze the network.log . . . ")

        # Wait for the watcher thread to finish
        watcher_thread.join()

    if "--intercept-off" in sys.argv:
        cleanup(proxy)
        return

    if "--intercept-on" in sys.argv:

        # Create a thread for the watch_proxy_env_file function
        watcher_thread = threading.Thread(target=watchproxy.check_and_restore_source_lines)
        watcher_thread = threading.Thread(target=watchproxy.watch_proxy_env_file_and_system_proxy)

        # setup AI 
        ai = AI.AI(env)
        
        analyze_network = AnalyzeNetwork.AnalyzeNetwork(env, ai)
        watcher_thread = threading.Thread(target=analyze_network.analyze_network, args=(os.path.join(f"{env.ENV_CURR_PROJECT_DIR}", "network.log"), os.path.join(f"{env.ENV_CURR_PROJECT_DIR}", "network-analyze.log"), 10))
        
        watcher_thread.daemon = True  # This makes the thread exit when the main program exits
        watcher_thread.start()  # Start the thread

        # Signal the watcher thread to stop
        stop_event.set()

        kill_process_on_port()
        proxy.configure_proxy(True)

        # setup network intercept
        svc = Intercept.Intercept(env, ai)
        svc.run_intercept()
        
        # Wait for the watcher thread to finish
        watcher_thread.join()

if __name__ == "__main__":
    main()
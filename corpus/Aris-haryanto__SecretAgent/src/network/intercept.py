import asyncio
import os
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

class Intercept:
    def __init__(self, env, ai):
        self.env_host_listen = env.ENV_HOST_LISTEN
        self.env_port_listen = env.ENV_PORT_LISTEN
        self.env_curr_project_dir = env.ENV_CURR_PROJECT_DIR

        self.ai = ai

        self.network_addon = LoggerAddon(env)

    async def run_intercept_async(self):
        options = Options(listen_host=self.env_host_listen, listen_port=self.env_port_listen)
        options.ssl_insecure = False

        m = DumpMaster(options)
        m.addons.add(self.network_addon)

        print(f"Starting mitmproxy HTTPS intercepting proxy on https://{self.env_host_listen}:{self.env_port_listen} ...")
        await m.run()

    def run_intercept(self):
        try:
            asyncio.run(self.run_intercept_async())
        except KeyboardInterrupt:
            print("Proxy interrupted by user. Stopping proxy...")


class LoggerAddon:
    def __init__(self, env):
        self.env_curr_project_dir = env.ENV_CURR_PROJECT_DIR
    
    def request(self, flow):
        # Log request method, URL, and payload
        payload = flag = ""
        if flow.request.content:
            payload = {flow.request.content.decode('utf-8', errors='replace')}
            # flag = helpAI(flow.request.url)

        # print(f"{flag} {flow.request.method} {flow.request.url} {payload}")
        self.write_to_file('network.log', f"{flag} {flow.request.method} {flow.request.url} {payload}\n")

    def write_to_file(self, file_name, text):
        file_path = os.path.join(self.env_curr_project_dir, file_name)
        # Check if the file exists and its size
        if os.path.exists(file_path) and os.path.getsize(file_path) >= 1 * 1024 * 1024:  # 1MB in bytes
            # Rewrite the file if it is 1MB or larger
            with open(file_path, 'w') as file:
                file.write(text)
                print(f"File '{file_path}' was too large. It has been rewritten.")
        else:
            # Append to the file if it is smaller than 1MB
            with open(file_path, 'a+') as file:
                file.write(text)
                print(f"Traffic has been write to '{file_path}'.")

        # Show the application that triggered the connection
        # self.show_application_info(flow.request.host)

    # def show_application_info(self, host):
    #     try:
    #         # Get the list of active connections using lsof
    #         result = subprocess.run(
    #             ["lsof", "-i", "TCP"],
    #             check=True,
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE,
    #             text=True
    #         )
    #         print("Applications making connections to the host:")
    #         for line in result.stdout.strip().splitlines()[1:]:  # Skip the header line
    #             parts = line.split()
    #             if len(parts) >= 9:  # Ensure there are enough parts
    #                 command = parts[0]  # Command name
    #                 pid = parts[1]      # PID
    #                 remote_address = parts[8]  # Remote address (IP:port)
    #                 # Check if the remote address matches the requested host
    #                 if host in remote_address:
    #                     print(f"PID: {pid}, Application: {command}")
    #     except Exception as e:
    #         print(f"Error checking for applications: {e}")

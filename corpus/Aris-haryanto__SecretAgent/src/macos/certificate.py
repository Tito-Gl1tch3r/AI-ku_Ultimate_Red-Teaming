
from ..utils import run_command

class Certificate:
    def __init__(self, env):
        self.env_cert = env.ENV_CERT

    def install_cert_to_keychain(self):
        print("Installing the certificate to macOS System Keychain for trust... (requires sudo)")
        
        #remove exist keychain
        self.remove_cert_from_keychain()
        
        run_command(["security", "add-trusted-cert", "-d", "-r", "trustRoot", "-k",
                    "/Library/Keychains/System.keychain", self.env_cert], sudo=True)

        print("Certificate added and trusted to System Keychain.")

    def remove_cert_from_keychain(self):
        print("Removing the certificate from macOS System Keychain... (requires sudo)")
        cert_name = "InterceptCA"

        try:
            output = run_command(
                ["security", "find-certificate", "-c", cert_name, "-a", "-Z", "/Library/Keychains/System.keychain"],
                sudo=True,
                capture_output=True
            )
        except SystemExit:
            print("Certificate not found in keychain or error occurred, skipping removal.")
            return

        sha1s = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SHA-1 hash:"):
                sha1 = line.split("SHA-1 hash:")[1].strip()
                sha1s.append(sha1)

        if not sha1s:
            print("No matching certificates found in keychain.")
            return

        for sha1 in sha1s:
            print(f"Deleting certificate with SHA-1: {sha1}")
            run_command(["security", "delete-certificate", "-Z", sha1, "/Library/Keychains/System.keychain"], sudo=True)

        print("Certificate(s) removed from System Keychain.")

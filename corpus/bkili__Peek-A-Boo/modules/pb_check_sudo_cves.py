# /modules/pb_check_sudo_cves.py
import re
from core.utils.cve_list import get_cve_list
from modules.base import BaseModule
from core.utils.formatter import printc


def parse_version(version):
    parts = re.split(r"[\.p]", version)
    return tuple(map(int, parts + ["0"] * (4 - len(parts))))


def is_vulnerable(target, affected_range):
    def parse(ver_str):
        parts = re.split(r"[\.p]", ver_str)
        return tuple(map(int, parts + ["0"] * (4 - len(parts))))

    if isinstance(target, str):
        target = parse(target)

    lower = parse(affected_range[0])
    upper = parse(affected_range[1])

    return lower <= target <= upper


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_check_sudo_cves"
        self.description = (
            "Check if the detected sudo version is affected by any known CVEs."
        )
        self.category = "recon"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"

        # Default options for the module
        self.default_options = {
            "version": "",
            "rhost": "",
            "rport": "22",
            "username": "",
            "password": "",
        }

        # List of options that are considered required
        # (shown in CLI with 'yes' under Required)
        self.required_options = []

        self.options = self.default_options.copy()

    def requires(self):
        if self.options.get("rhost"):
            return ["pb_check_sudo_version"]
        else:
            return []

    def run(self, shared_data):
        parsed_version = None
        shared_ver = shared_data.get("pb_check_sudo_version", None)

        printc("PB_CHECK_SUDO_CVES", level="headline")

        if shared_ver:
            parsed_version = shared_ver
            version_str = shared_data.get(
                "pb_check_sudo_version_str", ".".join(map(str, shared_ver))
            )
            printc(f"Using sudo version : {version_str}", level="info")
        else:
            version_str = self.options.get("version", "").strip()
            if not version_str:
                printc(
                    "[!] No sudo version found in shared_data or options. Aborting.",
                    level="error",
                )
                return
            try:
                parsed_version = parse_version(version_str)
            except Exception as e:
                printc(f"[!] Failed to parse version string {e}", level="error")
                return

        printc(f"Using sudo version : {version_str}", level="info")

        cve_list = get_cve_list()
        vulnerable = []

        try:
            for cve in cve_list:
                if is_vulnerable(parsed_version, cve["affected_versions"]):
                    vulnerable.append(cve)

            if vulnerable:
                printc(
                    f"[✓] {len(vulnerable)} CVE(s) matched for sudo {version_str}: \n",
                    level="success",
                )
                for cve in vulnerable:
                    printc(f"   - {cve['id']}: {cve['description']}", level="warn")
                    printc(f"   URL: {cve['url']}\n", level="url")
            else:
                printc(
                    "[!] No known vulnerabilities found for this sudo version.",
                    level="unsuccessful",
                )
                return
        except Exception as e:
            printc(
                f"[!] Failed to compare version with known vulnerabilities: {e}",
                level="error",
            )
            return

        shared_data["pb_check_sudo_cves"] = vulnerable

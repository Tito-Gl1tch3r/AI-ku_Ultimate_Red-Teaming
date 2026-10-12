# /modules/pb_wayback.py
import requests
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from rich.text import Text
from core.utils.formatter import printc, colorize
from modules.base import BaseModule


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


class Module(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "pb_wayback"
        self.description = (
            "Queries Wayback Machine to collect historical "
            "URLs for a given target domain."
        )
        self.category = "recon"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = ""
        self.license = ""
        self.version = "0.0.1"
        self.default_options = {"url": "", "output_directory": "URLs"}
        self.required_options = ["url", "output_directory"]
        self.options = self.default_options.copy()

    def run(self, shared_data):
        target_url = self.options.get("url", "").strip()
        output_base = Path(self.options.get("output_directory", "URLs"))

        if not target_url:
            printc(f"[{self.name}] No target URL specified", level="error")
            logging.error("[-] URL is not set.")
            return

        printc(f"[{self.name}] Running Wayback URL collection...", level="module")
        printc(
            f"[{self.name}] Collecting links from Wayback Machine for: "
            f"{colorize(target_url, 'cyan', 'underline')}",
            level="info",
        )

        logging.debug(f"[debug] current options: {self.options}")
        logging.info("[pb_wayback] Running Wayback URL collection...")
        logging.info(f"[*] Collecting links from Wayback Machine for: {target_url}")

        hash_val = hash_url(target_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_base / hash_val
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"all_urls-{timestamp}.txt"

        params = {
            "url": target_url,
            "matchType": "prefix",
            "output": "json",
            "collapse": "digest",
            "filter": "statuscode:200",
            "fl": "timestamp,original",
        }

        try:
            response = requests.get(
                "http://web.archive.org/cdx/search/cdx", params=params
            )
            if response.status_code != 200:
                printc(
                    f"[pb_wayback] CDX API error: {response.status_code}", level="error"
                )
                logging.error(f"[pb_wayback] CDX API error: {response.status_code}")
                return

            data = response.json()[1:]  # Skip header
            urls = sorted(
                set(
                    f"https://web.archive.org/web/{entry[0]}/{entry[1]}"
                    for entry in data
                )
            )

            with open(output_file, "w") as f:
                f.write("\n".join(urls))

            printc(f"[{self.name}] {len(urls)} links found.", level="success")
            msg = Text(f"[{self.name}] Links saved to ") + colorize(
                str(output_file), "green", "underline"
            )
            printc(msg, level="module")

            logging.info(f"[pb_wayback] {len(urls)} links found.")
            logging.info(f"[pb_wayback] Links saved to {output_file}")

            shared_data["wayback_urls"] = urls  # Shared data
            shared_data["last_summary"] = {
                "module": self.name,
                "url": target_url,
                "total": len(urls),
                "output_file": str(output_file),
            }

        except Exception as e:
            logging.error(f"[pb_wayback] Error collecting URLs: {e}")

    def print_summary(self, summary):
        try:
            print(f"URL         : {summary['url']}")
            print(f"Total links : {summary.get('total', 0)}")
            print(f"Saved to    : {summary.get('output_file', '-')}")
        except Exception as e:
            logging.error(f"Error: {e}")
